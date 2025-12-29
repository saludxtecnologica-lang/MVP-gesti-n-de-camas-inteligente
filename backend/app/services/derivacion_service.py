"""
Servicio de Derivaciones.
Gestiona las derivaciones inter-hospitalarias.

ACTUALIZADO v2: 
- Añadido método confirmar_egreso (alias) para corregir AttributeError
- Modificado confirmar_egreso_derivacion para manejar correctamente el egreso
- Corregida lógica de verificación de paciente en tránsito
- Ahora verifica el estado de la cama origen en lugar de solo si el campo es None
"""
from typing import Optional, List
from sqlmodel import Session, select
from dataclasses import dataclass
from datetime import datetime
import logging

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

logger = logging.getLogger("gestion_camas.derivacion")


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
    # VERIFICACIÓN DE VIABILIDAD
    # ============================================
    
    def verificar_viabilidad_derivacion(
        self,
        paciente_id: str,
        hospital_destino_id: str
    ) -> ResultadoVerificacionDerivacion:
        """
        Verifica si una derivación es viable antes de solicitarla.
        
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
        
        # 1. Obtener la complejidad requerida del paciente
        complejidad = paciente.complejidad_requerida
        if not complejidad:
            from app.services.asignacion_service import AsignacionService
            service = AsignacionService(self.session)
            complejidad = service.calcular_complejidad(paciente)
        
        # 2. Verificar servicios disponibles según complejidad
        servicios_requeridos = MAPEO_COMPLEJIDAD_SERVICIO.get(complejidad, [])
        
        # Buscar servicios del hospital destino
        query_servicios = select(Servicio).where(Servicio.hospital_id == hospital_destino_id)
        servicios_destino = self.session.exec(query_servicios).all()
        tipos_servicios_destino = [s.tipo for s in servicios_destino]
        
        # Verificar si hay al menos un servicio compatible
        servicios_compatibles = [s for s in servicios_requeridos if s in tipos_servicios_destino]
        
        if not servicios_compatibles and servicios_requeridos:
            nombres_requeridos = [s.value for s in servicios_requeridos]
            nombres_disponibles = [s.value for s in tipos_servicios_destino]
            motivos_rechazo.append(
                f"El paciente requiere complejidad {complejidad.value.upper()} "
                f"(servicios: {', '.join(nombres_requeridos)}) pero el hospital {hospital_destino.nombre} "
                f"solo cuenta con: {', '.join(nombres_disponibles)}"
            )
        
        # 3. Verificar aislamiento individual si es requerido
        if paciente.tipo_aislamiento in AISLAMIENTOS_SALA_INDIVIDUAL:
            # Buscar salas individuales en el hospital destino
            query_salas = (
                select(Sala)
                .join(Servicio)
                .where(
                    Servicio.hospital_id == hospital_destino_id,
                    Sala.es_individual == True
                )
            )
            salas_individuales = self.session.exec(query_salas).all()
            
            # También considerar salas en UCI, UTI, Aislamiento como individuales
            query_servicios_individual = (
                select(Servicio)
                .where(
                    Servicio.hospital_id == hospital_destino_id,
                    Servicio.tipo.in_([
                        TipoServicioEnum.UCI,
                        TipoServicioEnum.UTI,
                        TipoServicioEnum.AISLAMIENTO
                    ])
                )
            )
            servicios_individuales = self.session.exec(query_servicios_individual).all()
            
            if not salas_individuales and not servicios_individuales:
                motivos_rechazo.append(
                    f"El paciente requiere aislamiento {paciente.tipo_aislamiento.value} "
                    f"(sala individual) pero el hospital {hospital_destino.nombre} "
                    f"no cuenta con salas individuales ni servicios de UCI/UTI/Aislamiento"
                )
        
        # 4. Verificar pediátrico
        if paciente.es_pediatrico:
            tiene_pediatria = any(s.tipo == TipoServicioEnum.PEDIATRIA for s in servicios_destino)
            if not tiene_pediatria:
                motivos_rechazo.append(
                    f"El paciente es pediátrico pero el hospital {hospital_destino.nombre} "
                    f"no cuenta con servicio de Pediatría"
                )
        
        # 5. Verificar obstetricia (para embarazadas o enf. obstétrica)
        if paciente.es_embarazada or paciente.tipo_enfermedad == TipoEnfermedadEnum.OBSTETRICA:
            tiene_obstetricia = any(s.tipo == TipoServicioEnum.OBSTETRICIA for s in servicios_destino)
            tiene_critico = any(s.tipo in [TipoServicioEnum.UCI, TipoServicioEnum.UTI] for s in servicios_destino)
            if not tiene_obstetricia and not tiene_critico:
                motivos_rechazo.append(
                    f"La paciente es obstétrica/embarazada pero el hospital {hospital_destino.nombre} "
                    f"no cuenta con servicio de Obstetricia"
                )
        
        # Determinar resultado
        es_viable = len(motivos_rechazo) == 0
        
        if es_viable:
            mensaje = f"La derivación a {hospital_destino.nombre} es viable"
        else:
            mensaje = f"La derivación a {hospital_destino.nombre} NO es viable"
        
        logger.info(f"Verificación derivación {paciente.nombre} -> {hospital_destino.nombre}: viable={es_viable}")
        
        return ResultadoVerificacionDerivacion(
            es_viable=es_viable,
            mensaje=mensaje,
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
        Solicita una derivación para un paciente.
        
        Args:
            paciente_id: ID del paciente
            hospital_destino_id: ID del hospital destino
            motivo: Motivo de la derivación
            documento_id: ID del documento adjunto (opcional)
        
        Returns:
            ResultadoDerivacion
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        hospital_destino = self.hospital_repo.obtener_por_id(hospital_destino_id)
        if not hospital_destino:
            raise HospitalNotFoundError(hospital_destino_id)
        
        # Validar que no tenga derivación activa
        if paciente.derivacion_estado in ["pendiente", "aceptada"]:
            raise ValidationError("El paciente ya tiene una derivación activa")
        
        # Guardar cama origen
        cama_origen_id = paciente.cama_id
        if cama_origen_id:
            cama_origen = self.cama_repo.obtener_por_id(cama_origen_id)
            if cama_origen:
                cama_origen.estado = EstadoCamaEnum.ESPERA_DERIVACION
                cama_origen.mensaje_estado = f"Derivación pendiente a {hospital_destino.nombre}"
                cama_origen.paciente_derivado_id = paciente_id
                cama_origen.estado_updated_at = datetime.utcnow()
                self.session.add(cama_origen)
        
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
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        if paciente.derivacion_estado != "pendiente":
            raise ValidationError("La derivación no está pendiente")
        
        hospital_destino = self.hospital_repo.obtener_por_id(
            paciente.derivacion_hospital_destino_id
        )
        
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
        El paciente permanece en hospital origen.
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        if paciente.derivacion_estado != "pendiente":
            raise ValidationError("La derivación no está pendiente")
        
        # Restaurar cama origen
        if paciente.cama_origen_derivacion_id:
            cama_origen = self.cama_repo.obtener_por_id(paciente.cama_origen_derivacion_id)
            if cama_origen:
                cama_origen.estado = EstadoCamaEnum.OCUPADA
                cama_origen.mensaje_estado = None
                cama_origen.paciente_derivado_id = None
                cama_origen.estado_updated_at = datetime.utcnow()
                self.session.add(cama_origen)
        
        # Limpiar datos de derivación
        paciente.derivacion_estado = "rechazada"
        paciente.derivacion_motivo_rechazo = motivo_rechazo
        
        self.session.add(paciente)
        self.session.commit()
        
        logger.info(f"Derivación rechazada: {paciente.nombre} - {motivo_rechazo}")
        
        return ResultadoDerivacion(
            exito=True,
            mensaje=f"Derivación rechazada: {motivo_rechazo}",
            paciente_id=paciente_id
        )
    
    # ============================================
    # CONFIRMACIÓN DE EGRESO - CORREGIDO
    # ============================================
    
    def confirmar_egreso(self, paciente_id: str) -> ResultadoDerivacion:
        """
        Alias para confirmar_egreso_derivacion.
        Agregado para corregir AttributeError en el endpoint.
        """
        return self.confirmar_egreso_derivacion(paciente_id)
    
    def confirmar_egreso_derivacion(self, paciente_id: str) -> ResultadoDerivacion:
        """
        Confirma el egreso del paciente del hospital origen.
        
        FLUJO ACTUALIZADO:
        1. Libera la cama origen (pasa a EN_LIMPIEZA)
        2. NO limpia cama_origen_derivacion_id (se usa para detectar si ya egresó)
        3. NO cambia derivacion_estado a "completada" (eso ocurre al completar traslado)
        4. Mantiene al paciente vinculado a su cama destino
        
        El paciente permanece en estado "aceptada" hasta que complete el traslado
        en el hospital destino. La cama origen en EN_LIMPIEZA indica que ya egresó.
        """
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        if paciente.derivacion_estado != "aceptada":
            raise ValidationError("La derivación no está aceptada")
        
        # Verificar que tenga cama origen y que no haya egresado ya
        if not paciente.cama_origen_derivacion_id:
            raise ValidationError("El paciente no tiene cama de origen o ya ha egresado")
        
        cama_origen = self.cama_repo.obtener_por_id(paciente.cama_origen_derivacion_id)
        if not cama_origen:
            raise ValidationError("Cama de origen no encontrada")
        
        # Verificar que la cama no esté ya en limpieza (ya egresó)
        if cama_origen.estado == EstadoCamaEnum.EN_LIMPIEZA:
            raise ValidationError("El paciente ya ha egresado del hospital de origen")
        
        # Liberar cama origen (pasa a EN_LIMPIEZA)
        cama_origen.estado = EstadoCamaEnum.EN_LIMPIEZA
        cama_origen.limpieza_inicio = datetime.utcnow()
        cama_origen.mensaje_estado = "En limpieza - Paciente derivado en tránsito"
        cama_origen.paciente_derivado_id = None
        cama_origen.cama_asignada_destino = None
        cama_origen.estado_updated_at = datetime.utcnow()
        self.session.add(cama_origen)
        
        # Actualizar sexo de sala
        from app.services.compatibilidad_service import verificar_y_actualizar_sexo_sala_al_egreso
        verificar_y_actualizar_sexo_sala_al_egreso(self.session, cama_origen)
        
        # IMPORTANTE: NO limpiar cama_origen_derivacion_id
        # Este campo se usa para verificar si el paciente ya egresó
        # (verificamos el estado de la cama, no si el campo es None)
        
        self.session.add(paciente)
        self.session.commit()
        
        logger.info(f"Egreso confirmado para derivación: {paciente.nombre}")
        
        return ResultadoDerivacion(
            exito=True,
            mensaje="Egreso confirmado - cama liberada. Paciente en tránsito al hospital destino.",
            paciente_id=paciente_id
        )
    
    # ============================================
    # VERIFICACIÓN DE PACIENTE EN TRÁNSITO - CORREGIDO
    # ============================================
    
    def _verificar_paciente_en_transito(self, paciente: Paciente) -> bool:
        """
        Verifica si el paciente está en tránsito (ya egresó del origen).
        
        Un paciente está en tránsito cuando:
        - Tiene derivación aceptada
        - Tiene cama destino asignada (tiene destino en hospital nuevo)
        - Y la cama de origen (si existía) está ahora en EN_LIMPIEZA
        
        CORREGIDO: Ahora verifica el ESTADO de la cama origen, no solo si el
        campo cama_origen_derivacion_id es None. Esto permite distinguir entre:
        - Paciente que nunca tuvo cama de origen (urgencia/ambulatorio) → SÍ puede cancelar
        - Paciente que tenía cama pero ya egresó (cama en EN_LIMPIEZA) → NO puede cancelar
        
        Returns:
            True si el paciente está en tránsito y NO se puede cancelar
        """
        # Si no tiene derivación aceptada, no está en tránsito de derivación
        if paciente.derivacion_estado != "aceptada":
            return False
        
        # Si no tiene cama destino asignada, no está en tránsito
        if not paciente.cama_destino_id:
            return False
        
        # Si nunca tuvo cama de origen (era urgencia/ambulatorio), puede cancelar
        if not paciente.cama_origen_derivacion_id:
            return False
        
        # Tiene cama de origen - verificar su estado
        cama_origen = self.cama_repo.obtener_por_id(paciente.cama_origen_derivacion_id)
        if not cama_origen:
            # Cama no encontrada, asumimos que ya fue procesada
            return True
        
        # Si la cama origen está en EN_LIMPIEZA, el paciente ya egresó
        if cama_origen.estado == EstadoCamaEnum.EN_LIMPIEZA:
            logger.info(
                f"Paciente {paciente.nombre} ya egresó del origen - "
                f"cama {cama_origen.identificador} en EN_LIMPIEZA"
            )
            return True
        
        # La cama origen aún está en otro estado, el paciente no ha egresado
        return False
    
    def cancelar_derivacion_desde_origen(self, paciente_id: str) -> ResultadoDerivacion:
        """
        Cancela derivación desde el hospital de origen.
        
        Flujo según documento:
        Si se cancela desde cama origen (estando el paciente aceptado en destino):
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