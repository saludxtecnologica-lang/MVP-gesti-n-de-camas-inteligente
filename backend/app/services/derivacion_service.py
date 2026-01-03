"""
Servicio de Derivaciones.
Gestiona las derivaciones inter-hospitalarias.

"""
from typing import Optional, List
from sqlmodel import Session, select
from dataclasses import dataclass
from datetime import datetime
import logging
import asyncio

from app.models.paciente import Paciente
from app.models.cama import Cama
from app.models.hospital import Hospital
from app.models.servicio import Servicio
from app.models.sala import Sala
from app.models.enums import (
    EstadoCamaEnum,
    TipoPacienteEnum,
    EstadoListaEsperaEnum,
    TipoServicioEnum,
    TipoEnfermedadEnum,
    ComplejidadEnum,
    MAPEO_COMPLEJIDAD_SERVICIO,
    AISLAMIENTOS_SALA_INDIVIDUAL,
)
from app.repositories.paciente_repo import PacienteRepository
from app.repositories.cama_repo import CamaRepository
from app.repositories.hospital_repo import HospitalRepository
from app.core.exceptions import (
    ValidationError,
    PacienteNotFoundError,
    HospitalNotFoundError,
)
from app.core.websocket_manager import manager

# NUEVO IMPORT TTS
from app.core.eventos_audibles import crear_evento_derivacion_aceptada

logger = logging.getLogger("gestion_camas.derivacion")

# ============================================
# CONSTANTE PARA BOOST DE RECHAZO (PROBLEMA 5)
# ============================================
BOOST_RECHAZO_DERIVACION = 15.0  # Puntos de boost para pacientes rechazados


@dataclass
class ResultadoDerivacion:
    """Resultado de una operación de derivación."""
    exito: bool
    mensaje: str
    paciente_id: Optional[str] = None
    hospital_destino_id: Optional[str] = None


@dataclass
class ResultadoVerificacionDerivacion:
    """Resultado de verificación de viabilidad de derivación."""
    es_viable: bool
    mensaje: str
    motivos_rechazo: List[str] = None
    hospital_destino_nombre: str = None
    
    def __post_init__(self):
        if self.motivos_rechazo is None:
            self.motivos_rechazo = []


class DerivacionService:
    """
    Servicio para gestión de derivaciones.
    
    Maneja:
    - Solicitud de derivación
    - Aceptación/rechazo
    - Confirmación de egreso
    - Cancelación
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.paciente_repo = PacienteRepository(session)
        self.cama_repo = CamaRepository(session)
        self.hospital_repo = HospitalRepository(session)
    
    # ============================================
    # HELPER: OBTENER COMPLEJIDAD
    # ============================================
    
    def _obtener_complejidad_paciente(self, paciente: Paciente) -> ComplejidadEnum:
        """Obtiene la complejidad del paciente."""
        if paciente.complejidad_requerida:
            return paciente.complejidad_requerida
        
        from app.services.asignacion_service import AsignacionService
        service = AsignacionService(self.session)
        return service.calcular_complejidad(paciente)
    
    def _obtener_complejidad_cama(self, cama: Cama) -> ComplejidadEnum:
        """Obtiene la complejidad de una cama."""
        if not cama.sala or not cama.sala.servicio:
            return ComplejidadEnum.BAJA
        
        tipo_servicio = cama.sala.servicio.tipo
        
        if tipo_servicio == TipoServicioEnum.UCI:
            return ComplejidadEnum.ALTA
        elif tipo_servicio == TipoServicioEnum.UTI:
            return ComplejidadEnum.MEDIA
        else:
            return ComplejidadEnum.BAJA
    
    def _obtener_nivel_complejidad(self, complejidad: ComplejidadEnum) -> int:
        """Convierte complejidad a nivel numérico."""
        mapeo = {
            ComplejidadEnum.NINGUNA: 0,
            ComplejidadEnum.BAJA: 1,
            ComplejidadEnum.MEDIA: 2,
            ComplejidadEnum.ALTA: 3,
        }
        return mapeo.get(complejidad, 0)
    
    def _obtener_complejidad_maxima_hospital(self, hospital_id: str) -> int:
        """
        Obtiene el nivel máximo de complejidad disponible en un hospital.
        
        Returns:
            Nivel numérico (0-3)
        """
        query = select(Servicio).where(Servicio.hospital_id == hospital_id)
        servicios = self.session.exec(query).all()
        
        nivel_max = 0
        for servicio in servicios:
            if servicio.tipo == TipoServicioEnum.UCI:
                nivel_max = max(nivel_max, 3)
            elif servicio.tipo == TipoServicioEnum.UTI:
                nivel_max = max(nivel_max, 2)
            else:
                nivel_max = max(nivel_max, 1)
        
        return nivel_max
    
    # ============================================
    # VERIFICACIÓN DE VIABILIDAD
    # ============================================
    
    def verificar_viabilidad_derivacion(
        self,
        paciente_id: str,
        hospital_destino_id: str
    ) -> ResultadoVerificacionDerivacion:
        """
        Verifica si una derivación es viable antes de solicitarla.
        
        PROBLEMA 2: Incluye verificación de pausa de oxígeno.
        
        Verifica que el hospital destino tenga el tipo de cama que 
        requiere el paciente según sus requerimientos.
        
        Args:
            paciente_id: ID del paciente
            hospital_destino_id: ID del hospital destino
        
        Returns:
            ResultadoVerificacionDerivacion con la viabilidad y motivos
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        hospital_destino = self.hospital_repo.obtener_por_id(hospital_destino_id)
        if not hospital_destino:
            raise HospitalNotFoundError(hospital_destino_id)
        
        motivos_rechazo = []
        
        # ============================================
        # PROBLEMA 2: VERIFICAR PAUSA DE OXÍGENO
        # ============================================
        if paciente.esperando_evaluacion_oxigeno and paciente.cama_id:
            # Obtener cama actual
            cama_actual = self.cama_repo.obtener_por_id(paciente.cama_id)
            
            if cama_actual:
                complejidad_cama_actual = self._obtener_complejidad_cama(cama_actual)
                nivel_cama_actual = self._obtener_nivel_complejidad(complejidad_cama_actual)
                
                # Obtener complejidad máxima del hospital destino
                nivel_hospital_destino = self._obtener_complejidad_maxima_hospital(hospital_destino_id)
                
                # Si el nivel destino es menor que el actual, bloquear
                if nivel_hospital_destino < nivel_cama_actual:
                    motivos_rechazo.append(
                        f"El paciente está en pausa de evaluación de oxígeno. "
                        f"Actualmente en cama de complejidad {complejidad_cama_actual.value.upper()} "
                        f"y el hospital destino ofrece complejidad menor. "
                        f"Debe esperar a que termine la pausa o que se cancele."
                    )
                    logger.info(
                        f"Derivación bloqueada por pausa de oxígeno: {paciente.nombre} "
                        f"(cama {complejidad_cama_actual.value} -> hospital nivel {nivel_hospital_destino})"
                    )
        
        # Verificar complejidad requerida
        complejidad_paciente = self._obtener_complejidad_paciente(paciente)
        nivel_paciente = self._obtener_nivel_complejidad(complejidad_paciente)
        nivel_hospital = self._obtener_complejidad_maxima_hospital(hospital_destino_id)
        
        if nivel_hospital < nivel_paciente:
            motivos_rechazo.append(
                f"El hospital destino no tiene camas de complejidad suficiente. "
                f"Paciente requiere {complejidad_paciente.value.upper()} pero hospital "
                f"solo ofrece hasta nivel {nivel_hospital}."
            )
        
        # Verificar aislamientos específicos
        aislamientos = paciente.get_requerimientos_lista('aislamientos')
        for aislamiento in aislamientos:
            if aislamiento in AISLAMIENTOS_SALA_INDIVIDUAL:
                # Verificar si hay salas individuales
                query = select(Sala).join(Servicio).where(
                    Servicio.hospital_id == hospital_destino_id,
                    Sala.es_individual == True
                )
                salas_individuales = self.session.exec(query).all()
                if not salas_individuales:
                    motivos_rechazo.append(
                        f"El hospital destino no tiene salas individuales "
                        f"requeridas para aislamiento: {aislamiento}"
                    )
                break
        
        es_viable = len(motivos_rechazo) == 0
        
        return ResultadoVerificacionDerivacion(
            es_viable=es_viable,
            mensaje="Derivación viable" if es_viable else "Derivación no viable",
            motivos_rechazo=motivos_rechazo,
            hospital_destino_nombre=hospital_destino.nombre
        )
    
    # ============================================
    # SOLICITUD DE DERIVACIÓN
    # ============================================
    
    def solicitar_derivacion(
        self,
        paciente_id: str,
        hospital_destino_id: str,
        motivo: str,
        documento_id: Optional[str] = None
    ) -> ResultadoDerivacion:
        """
        Solicita una derivación a otro hospital.
        
        PROBLEMA 5: Si el paciente está en lista de espera sin cama,
        se le remueve de la lista de espera.
        
        Args:
            paciente_id: ID del paciente
            hospital_destino_id: ID del hospital destino
            motivo: Motivo de la derivación
            documento_id: ID del documento adjunto (opcional)
        
        Returns:
            Resultado de la solicitud
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        hospital_destino = self.hospital_repo.obtener_por_id(hospital_destino_id)
        if not hospital_destino:
            raise HospitalNotFoundError(hospital_destino_id)
        
        # Verificar viabilidad
        verificacion = self.verificar_viabilidad_derivacion(paciente_id, hospital_destino_id)
        if not verificacion.es_viable:
            return ResultadoDerivacion(
                exito=False,
                mensaje="; ".join(verificacion.motivos_rechazo),
                paciente_id=paciente_id
            )
        
        # Guardar cama de origen si tiene
        cama_origen_id = paciente.cama_id
        
        # Actualizar cama origen si tiene
        if cama_origen_id:
            cama_origen = self.cama_repo.obtener_por_id(cama_origen_id)
            if cama_origen:
                cama_origen.estado = EstadoCamaEnum.ESPERA_DERIVACION
                cama_origen.mensaje_estado = f"Derivación pendiente a {hospital_destino.nombre}"
                cama_origen.paciente_derivado_id = paciente.id
                cama_origen.estado_updated_at = datetime.utcnow()
                self.session.add(cama_origen)
        
        # PROBLEMA 5: Si está en lista de espera, remover
        if paciente.en_lista_espera:
            from app.services.prioridad_service import gestor_colas_global
            cola = gestor_colas_global.obtener_cola(paciente.hospital_id)
            cola.remover(paciente.id)
            paciente.en_lista_espera = False
            paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
        
        # Actualizar paciente
        paciente.derivacion_estado = "pendiente"
        paciente.derivacion_hospital_destino_id = hospital_destino_id
        paciente.derivacion_motivo = motivo
        paciente.cama_origen_derivacion_id = cama_origen_id
        paciente.timestamp_lista_espera = datetime.utcnow()
        
        if documento_id:
            paciente.documento_derivacion_id = documento_id
        
        self.session.add(paciente)
        self.session.commit()
        
        logger.info(
            f"Derivación solicitada: {paciente.nombre} -> {hospital_destino.nombre}"
        )
        
        return ResultadoDerivacion(
            exito=True,
            mensaje=f"Derivación solicitada a {hospital_destino.nombre}",
            paciente_id=paciente_id,
            hospital_destino_id=hospital_destino_id
        )
    
    # ============================================
    # ACCIONES DE DERIVACIÓN
    # ============================================
    
    def aceptar_derivacion(self, paciente_id: str) -> ResultadoDerivacion:
        """
        Acepta una derivación pendiente.
        El paciente pasa a lista de espera del hospital destino.
        
        ACTUALIZADO TTS: Emite evento con datos para notificación audible.
        El mensaje se reproduce SOLO en el servicio de origen del hospital de origen.
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        if paciente.derivacion_estado != "pendiente":
            raise ValidationError("La derivación no está pendiente")
        
        hospital_destino = self.hospital_repo.obtener_por_id(
            paciente.derivacion_hospital_destino_id
        )
        
        # ============================================
        # GUARDAR INFO PARA TTS ANTES DE MODIFICAR
        # ============================================
        servicio_origen_id = None
        servicio_origen_nombre = None
        cama_origen_identificador = None
        hospital_origen_id = paciente.hospital_id
        hospital_origen_nombre = None
        
        # Obtener hospital de origen
        hospital_origen = self.hospital_repo.obtener_por_id(hospital_origen_id)
        if hospital_origen:
            hospital_origen_nombre = hospital_origen.nombre
        
        # Obtener info de cama origen
        if paciente.cama_origen_derivacion_id:
            cama_origen = self.cama_repo.obtener_por_id(paciente.cama_origen_derivacion_id)
            if cama_origen:
                cama_origen_identificador = cama_origen.identificador
                if cama_origen.sala and cama_origen.sala.servicio:
                    servicio_origen_id = cama_origen.sala.servicio.nombre  # Usamos nombre como ID
                    servicio_origen_nombre = cama_origen.sala.servicio.nombre
        
        # Actualizar cama origen
        if paciente.cama_origen_derivacion_id:
            cama_origen = self.cama_repo.obtener_por_id(paciente.cama_origen_derivacion_id)
            if cama_origen:
                cama_origen.estado = EstadoCamaEnum.DERIVACION_CONFIRMADA
                cama_origen.mensaje_estado = f"Derivación aceptada por {hospital_destino.nombre if hospital_destino else 'destino'}"
                cama_origen.estado_updated_at = datetime.utcnow()
                self.session.add(cama_origen)
        
        # Cambiar hospital del paciente
        paciente.hospital_id = paciente.derivacion_hospital_destino_id
        paciente.derivacion_estado = "aceptada"
        paciente.tipo_paciente = TipoPacienteEnum.DERIVADO
        
        # Agregar a lista de espera del hospital destino
        from app.services.prioridad_service import PrioridadService, gestor_colas_global
        prioridad_service = PrioridadService(self.session)
        prioridad = prioridad_service.calcular_prioridad(paciente)
        
        paciente.en_lista_espera = True
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
        paciente.prioridad_calculada = prioridad
        paciente.timestamp_lista_espera = datetime.utcnow()
        paciente.cama_id = None  # Ya no tiene cama asignada en el sistema destino
        
        cola = gestor_colas_global.obtener_cola(paciente.hospital_id)
        cola.agregar(paciente.id, prioridad)
        
        self.session.add(paciente)
        self.session.commit()
        
        logger.info(f"Derivación aceptada: {paciente.nombre}")
        
        # ============================================
        # BROADCAST TTS
        # ============================================
        try:
            evento_tts = crear_evento_derivacion_aceptada(
                paciente_nombre=paciente.nombre,
                servicio_origen_id=servicio_origen_id,
                servicio_origen_nombre=servicio_origen_nombre,
                cama_origen_identificador=cama_origen_identificador,
                hospital_origen_id=hospital_origen_id,
                hospital_origen_nombre=hospital_origen_nombre or "origen",
                hospital_destino_id=str(paciente.derivacion_hospital_destino_id),
                hospital_destino_nombre=hospital_destino.nombre if hospital_destino else "destino",
                paciente_id=str(paciente.id),
                derivacion_id=str(paciente.id)  # Usamos paciente_id como referencia
            )
            
            # Broadcast asíncrono
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(manager.broadcast(evento_tts))
            except RuntimeError:
                # Si no hay event loop, crear uno nuevo
                asyncio.run(manager.broadcast(evento_tts))
                
            logger.info(f"Evento TTS de derivación aceptada emitido")
        except Exception as e:
            logger.warning(f"Error emitiendo evento TTS: {e}")
            # Fallback sin TTS
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(manager.broadcast({
                    "tipo": "derivacion_aceptada",
                    "hospital_id": hospital_origen_id,
                    "reload": True,
                    "play_sound": True
                }))
            except:
                pass
        
        return ResultadoDerivacion(
            exito=True,
            mensaje="Derivación aceptada - paciente en lista de espera",
            paciente_id=paciente_id
        )
    
    def rechazar_derivacion(
        self,
        paciente_id: str,
        motivo_rechazo: str
    ) -> ResultadoDerivacion:
        """
        Rechaza una derivación pendiente.
        
        PROBLEMA 5: Si el paciente no tiene cama, vuelve a lista de espera
        con un boost de prioridad.
        
        Args:
            paciente_id: ID del paciente
            motivo_rechazo: Motivo del rechazo
        
        Returns:
            ResultadoDerivacion
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        if paciente.derivacion_estado != "pendiente":
            raise ValidationError("La derivación no está pendiente")
        
        # Guardar info antes de limpiar
        tenia_cama_origen = paciente.cama_origen_derivacion_id is not None
        hospital_origen_id = None
        
        # Restaurar cama origen si tiene
        if paciente.cama_origen_derivacion_id:
            cama_origen = self.cama_repo.obtener_por_id(paciente.cama_origen_derivacion_id)
            if cama_origen:
                cama_origen.estado = EstadoCamaEnum.OCUPADA
                cama_origen.mensaje_estado = None
                cama_origen.paciente_derivado_id = None
                cama_origen.estado_updated_at = datetime.utcnow()
                self.session.add(cama_origen)
                
                # Obtener hospital de origen
                if cama_origen.sala and cama_origen.sala.servicio:
                    hospital_origen_id = cama_origen.sala.servicio.hospital_id
        
        # Limpiar datos de derivación
        paciente.derivacion_estado = "rechazada"
        paciente.derivacion_motivo_rechazo = motivo_rechazo
        
        # ============================================
        # PROBLEMA 5: Paciente sin cama vuelve a lista de espera con boost
        # ============================================
        if not tenia_cama_origen:
            # Paciente estaba en lista de espera sin cama
            # Devolverlo a lista de espera con boost
            
            from app.services.prioridad_service import PrioridadService, gestor_colas_global
            prioridad_service = PrioridadService(self.session)
            
            # Calcular prioridad base
            prioridad_base = prioridad_service.calcular_prioridad(paciente)
            
            # Aplicar boost
            prioridad_con_boost = prioridad_base + BOOST_RECHAZO_DERIVACION
            
            # Agregar a lista de espera
            paciente.en_lista_espera = True
            paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
            paciente.prioridad_calculada = prioridad_con_boost
            paciente.timestamp_lista_espera = datetime.utcnow()
            
            # Limpiar datos de derivación que ya no aplican
            paciente.derivacion_hospital_destino_id = None
            paciente.derivacion_motivo = None
            paciente.cama_origen_derivacion_id = None
            
            cola = gestor_colas_global.obtener_cola(paciente.hospital_id)
            cola.agregar(paciente.id, prioridad_con_boost)
            
            logger.info(
                f"Paciente {paciente.nombre} sin cama, vuelve a lista de espera "
                f"con boost: prioridad base {prioridad_base} + boost {BOOST_RECHAZO_DERIVACION} = {prioridad_con_boost}"
            )
        else:
            # Paciente tenía cama, restaurar referencia
            paciente.cama_id = paciente.cama_origen_derivacion_id
            if hospital_origen_id:
                paciente.hospital_id = hospital_origen_id
        
        self.session.add(paciente)
        self.session.commit()
        
        mensaje = "Derivación rechazada"
        if not tenia_cama_origen:
            mensaje += " - paciente vuelve a lista de espera con prioridad aumentada"
        else:
            mensaje += " - paciente permanece en cama de origen"
        
        logger.info(f"Derivación rechazada para {paciente.nombre}: {motivo_rechazo}")
        
        return ResultadoDerivacion(
            exito=True,
            mensaje=mensaje,
            paciente_id=paciente_id
        )
    
    # ============================================
    # CONFIRMACIÓN DE EGRESO
    # ============================================
    
    def confirmar_egreso_derivacion(self, paciente_id: str) -> ResultadoDerivacion:
        """
        Confirma el egreso del paciente derivado desde el hospital de origen.
        
        Flujo:
        1. La cama de origen pasa a EN_LIMPIEZA
        2. El paciente queda listo para ser asignado en el hospital destino
        
        Args:
            paciente_id: ID del paciente
        
        Returns:
            Resultado de la confirmación
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        if paciente.derivacion_estado != "aceptada":
            raise ValidationError("La derivación no está aceptada")
        
        # Liberar cama origen
        if paciente.cama_origen_derivacion_id:
            cama_origen = self.cama_repo.obtener_por_id(paciente.cama_origen_derivacion_id)
            if cama_origen:
                cama_origen.estado = EstadoCamaEnum.EN_LIMPIEZA
                cama_origen.limpieza_inicio = datetime.utcnow()
                cama_origen.mensaje_estado = "En limpieza"
                cama_origen.paciente_derivado_id = None
                cama_origen.estado_updated_at = datetime.utcnow()
                self.session.add(cama_origen)
                
                # Actualizar sexo de sala
                from app.services.compatibilidad_service import verificar_y_actualizar_sexo_sala_al_egreso
                verificar_y_actualizar_sexo_sala_al_egreso(self.session, cama_origen)
        
        self.session.commit()
        
        logger.info(f"Egreso confirmado para derivación de {paciente.nombre}")
        
        return ResultadoDerivacion(
            exito=True,
            mensaje="Egreso confirmado - cama de origen en limpieza",
            paciente_id=paciente_id
        )
    
    # ============================================
    # HELPER: Verificar si paciente está en tránsito
    # ============================================
    
    def _verificar_paciente_en_transito(self, paciente: Paciente) -> bool:
        """
        Verifica si el paciente ya egresó del hospital de origen.
        
        Un paciente está "en tránsito" si:
        - Su cama de origen está en EN_LIMPIEZA
        - O ya no tiene cama de origen
        """
        if not paciente.cama_origen_derivacion_id:
            # Si no tiene cama de origen registrada, puede estar en tránsito
            return paciente.derivacion_estado == "aceptada"
        
        cama_origen = self.cama_repo.obtener_por_id(paciente.cama_origen_derivacion_id)
        if not cama_origen:
            return True
        
        # Si la cama está en limpieza, el paciente ya egresó
        return cama_origen.estado == EstadoCamaEnum.EN_LIMPIEZA
    
    # ============================================
    # CANCELACIÓN DE DERIVACIÓN
    # ============================================
    
    def cancelar_derivacion_desde_origen(self, paciente_id: str) -> ResultadoDerivacion:
        """
        Cancela la derivación desde el hospital de origen.
        
        Flujo:
        1. Paciente se elimina del hospital destino (lista espera o asignación)
        2. Cama origen vuelve a estado "OCUPADA"
        
        NUEVO: Si el paciente ya egresó del origen (cama en EN_LIMPIEZA), no se puede cancelar.
        
        Args:
            paciente_id: ID del paciente
        
        Returns:
            Resultado de la cancelación
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        # Verificar si el paciente ya egresó del origen
        if self._verificar_paciente_en_transito(paciente):
            raise ValidationError(
                "No se puede cancelar la asignación, el paciente se encuentra en traslado"
            )
        
        # Liberar cama destino si estaba asignada
        if paciente.cama_destino_id:
            cama_destino = self.cama_repo.obtener_por_id(paciente.cama_destino_id)
            if cama_destino:
                cama_destino.estado = EstadoCamaEnum.LIBRE
                cama_destino.mensaje_estado = None
                cama_destino.estado_updated_at = datetime.utcnow()
                self.session.add(cama_destino)
        
        # Remover de cola de prioridad si estaba en lista de espera
        if paciente.en_lista_espera:
            from app.services.prioridad_service import gestor_colas_global
            cola = gestor_colas_global.obtener_cola(paciente.hospital_id)
            cola.remover(paciente.id)
        
        # Restaurar cama origen a OCUPADA
        cama_origen_id = paciente.cama_origen_derivacion_id
        hospital_origen_id = None
        
        if cama_origen_id:
            cama_origen = self.cama_repo.obtener_por_id(cama_origen_id)
            if cama_origen:
                cama_origen.estado = EstadoCamaEnum.OCUPADA
                cama_origen.mensaje_estado = None
                cama_origen.paciente_derivado_id = None
                cama_origen.cama_asignada_destino = None
                cama_origen.estado_updated_at = datetime.utcnow()
                self.session.add(cama_origen)
                
                # Obtener hospital de origen desde la cama
                if cama_origen.sala and cama_origen.sala.servicio:
                    hospital_origen_id = cama_origen.sala.servicio.hospital_id
        
        # Restaurar paciente al hospital de origen
        if hospital_origen_id:
            paciente.hospital_id = hospital_origen_id
        
        paciente.cama_id = cama_origen_id
        paciente.cama_destino_id = None
        paciente.cama_origen_derivacion_id = None
        paciente.derivacion_estado = None
        paciente.derivacion_hospital_destino_id = None
        paciente.derivacion_motivo = None
        paciente.en_lista_espera = False
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
        paciente.timestamp_lista_espera = None
        paciente.prioridad_calculada = 0.0
        paciente.tipo_paciente = TipoPacienteEnum.HOSPITALIZADO
        
        self.session.add(paciente)
        self.session.commit()
        
        logger.info(f"Derivación cancelada desde origen para {paciente.nombre}")
        
        return ResultadoDerivacion(
            exito=True,
            mensaje="Derivación cancelada - paciente permanece en hospital de origen",
            paciente_id=paciente_id
        )
    
    def cancelar_derivacion_desde_lista_espera(self, paciente_id: str) -> ResultadoDerivacion:
        """
        Cancela derivación desde la lista de espera del hospital destino.
        
        Flujo según documento:
        Si se cancela desde lista de espera:
        1. Paciente sale de lista de espera
        2. Paciente vuelve a lista de "derivados" con opción de rechazar o aceptar
        3. Cama origen pasa de DERIVACION_CONFIRMADA a ESPERA_DERIVACION
        
        NUEVO: Si el paciente ya egresó del origen (cama en EN_LIMPIEZA), no se puede cancelar.
        
        Args:
            paciente_id: ID del paciente
        
        Returns:
            Resultado de la cancelación
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        if paciente.derivacion_estado != "aceptada":
            raise ValidationError("El paciente no tiene una derivación aceptada")
        
        # Verificar si el paciente ya egresó del origen
        if self._verificar_paciente_en_transito(paciente):
            raise ValidationError(
                "No se puede cancelar la asignación, el paciente se encuentra en traslado"
            )
        
        # Liberar cama destino si estaba asignada
        if paciente.cama_destino_id:
            cama_destino = self.cama_repo.obtener_por_id(paciente.cama_destino_id)
            if cama_destino:
                cama_destino.estado = EstadoCamaEnum.LIBRE
                cama_destino.mensaje_estado = None
                cama_destino.estado_updated_at = datetime.utcnow()
                self.session.add(cama_destino)
        
        # Remover de cola de prioridad
        from app.services.prioridad_service import gestor_colas_global
        cola = gestor_colas_global.obtener_cola(paciente.hospital_id)
        cola.remover(paciente.id)
        
        # Restaurar cama origen a ESPERA_DERIVACION
        if paciente.cama_origen_derivacion_id:
            cama_origen = self.cama_repo.obtener_por_id(paciente.cama_origen_derivacion_id)
            if cama_origen:
                hospital_destino = self.hospital_repo.obtener_por_id(
                    paciente.derivacion_hospital_destino_id
                )
                cama_origen.estado = EstadoCamaEnum.ESPERA_DERIVACION
                cama_origen.mensaje_estado = f"Derivación pendiente a {hospital_destino.nombre if hospital_destino else 'destino'}"
                cama_origen.estado_updated_at = datetime.utcnow()
                self.session.add(cama_origen)
        
        # Volver estado a pendiente (vuelve a lista de derivados)
        paciente.derivacion_estado = "pendiente"
        paciente.cama_destino_id = None
        paciente.en_lista_espera = False
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
        paciente.prioridad_calculada = 0.0
        paciente.timestamp_lista_espera = datetime.utcnow()
        
        self.session.add(paciente)
        self.session.commit()
        
        logger.info(f"Paciente {paciente.nombre} devuelto a lista de derivados")
        
        return ResultadoDerivacion(
            exito=True,
            mensaje="Paciente devuelto a lista de derivados pendientes",
            paciente_id=paciente_id
        )
    
    # ============================================
    # CONSULTAS
    # ============================================
    
    def obtener_derivados_pendientes(
        self,
        hospital_id: str
    ) -> List[Paciente]:
        """
        Obtiene los pacientes derivados pendientes hacia un hospital.
        """
        return self.paciente_repo.obtener_derivados_pendientes(hospital_id)
    
    def obtener_derivados_enviados(
        self,
        hospital_id: str
    ) -> List[Paciente]:
        """
        Obtiene los pacientes derivados desde un hospital a otros hospitales.
        """
        query = select(Paciente).where(
            Paciente.cama_origen_derivacion_id.isnot(None),
            Paciente.derivacion_estado.in_(["pendiente", "aceptada"])
        )
        
        pacientes = self.session.exec(query).all()
        
        resultado = []
        for paciente in pacientes:
            if paciente.cama_origen_derivacion_id:
                cama_origen = self.cama_repo.obtener_por_id(paciente.cama_origen_derivacion_id)
                if cama_origen and cama_origen.sala and cama_origen.sala.servicio:
                    if cama_origen.sala.servicio.hospital_id == hospital_id:
                        resultado.append(paciente)
        
        return resultado