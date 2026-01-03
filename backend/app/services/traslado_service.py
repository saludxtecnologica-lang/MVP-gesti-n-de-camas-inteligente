"""
Servicio de Traslados.
Gestiona la lógica de traslados de pacientes.

ACTUALIZADO: Incluye verificación de compatibilidad al completar traslado
y función para cancelar traslados confirmados.
ACTUALIZADO TTS: Incluye broadcast con datos TTS para notificaciones audibles.

Ubicación: app/services/traslado_service.py
"""
from typing import Optional
from sqlmodel import Session
from dataclasses import dataclass
from datetime import datetime
import logging
import asyncio

from app.models.paciente import Paciente
from app.models.cama import Cama
from app.models.enums import (
    EstadoCamaEnum,
    EstadoListaEsperaEnum,
    TipoPacienteEnum,
)
from app.repositories.paciente_repo import PacienteRepository
from app.repositories.cama_repo import CamaRepository
from app.core.exceptions import (
    ValidationError,
    PacienteNotFoundError,
    CamaNotFoundError,
    EstadoInvalidoError,
)
from app.core.websocket_manager import manager

# NUEVO IMPORT
from app.services.compatibilidad_service import (
    CompatibilidadService,
    verificar_y_actualizar_sexo_sala_al_egreso,
    verificar_y_actualizar_sexo_sala_al_ingreso,
)

# NUEVO IMPORT TTS
from app.core.eventos_audibles import crear_evento_traslado_completado

logger = logging.getLogger("gestion_camas.traslado")


@dataclass
class ResultadoTraslado:
    """Resultado de una operación de traslado."""
    exito: bool
    mensaje: str
    paciente_id: Optional[str] = None
    cama_origen_id: Optional[str] = None
    cama_destino_id: Optional[str] = None


class TrasladoService:
    """
    Servicio para gestión de traslados.
    
    Maneja:
    - Completar traslados (con verificación de compatibilidad)
    - Cancelar traslados
    - Cancelar traslados confirmados (NUEVO)
    - Intercambio de pacientes
    - Traslados manuales
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.paciente_repo = PacienteRepository(session)
        self.cama_repo = CamaRepository(session)
    
    def _remover_de_cola_memoria(self, paciente: Paciente) -> None:
        """
        Remueve un paciente de la cola de prioridad en memoria.
        
        Args:
            paciente: El paciente a remover
        """
        from app.services.prioridad_service import gestor_colas_global
        
        try:
            cola = gestor_colas_global.obtener_cola(paciente.hospital_id)
            if cola.contiene(paciente.id):
                cola.remover(paciente.id)
                logger.debug(f"Paciente {paciente.nombre} removido de cola en memoria")
        except Exception as e:
            logger.warning(f"Error al remover de cola en memoria: {e}")
    
    def completar_traslado(self, paciente_id: str) -> ResultadoTraslado:
        """
        Completa el traslado de un paciente a su cama destino.
        
        ACTUALIZADO: Incluye verificación de compatibilidad al llegar.
        Si el paciente no es compatible con la cama, queda en CAMA_EN_ESPERA.
        
        ACTUALIZADO TTS: Emite evento con datos para notificación audible.
        
        Flujo según documento:
        1. Paciente ocupa cama destino (OCUPADA o CAMA_EN_ESPERA según compatibilidad)
        2. Cama origen (si existe) pasa a EN_LIMPIEZA
        3. Paciente sale de lista de espera
        4. Si era derivado: también libera cama origen de derivación
        5. Se actualiza el sexo de las salas afectadas
        6. Se emite evento TTS
        
        Args:
            paciente_id: ID del paciente
        
        Returns:
            Resultado del traslado
        """
        logger.info(f"Iniciando completar_traslado para paciente_id: {paciente_id}")
        
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            logger.error(f"Paciente no encontrado: {paciente_id}")
            raise PacienteNotFoundError(paciente_id)
        
        logger.debug(f"Paciente encontrado: {paciente.nombre}, cama_destino_id: {paciente.cama_destino_id}")
        
        if not paciente.cama_destino_id:
            logger.error(f"Paciente {paciente.nombre} no tiene cama destino asignada")
            raise ValidationError("El paciente no tiene cama destino asignada")
        
        cama_destino = self.cama_repo.obtener_por_id(paciente.cama_destino_id)
        if not cama_destino:
            logger.error(f"Cama destino no encontrada: {paciente.cama_destino_id}")
            raise CamaNotFoundError(paciente.cama_destino_id)
        
        logger.debug(f"Cama destino encontrada: {cama_destino.identificador}")
        
        cama_origen_id = paciente.cama_id
        es_derivado = paciente.derivacion_estado == "aceptada" or paciente.tipo_paciente == TipoPacienteEnum.DERIVADO
        
        # ============================================
        # GUARDAR INFO PARA TTS ANTES DE MODIFICAR
        # ============================================
        cama_origen = None
        cama_origen_identificador = None
        servicio_origen_id = None
        servicio_origen_nombre = None
        servicio_destino_id = None
        servicio_destino_nombre = None
        hospital_id = paciente.hospital_id
        
        # Obtener info de cama origen
        if cama_origen_id:
            cama_origen = self.cama_repo.obtener_por_id(cama_origen_id)
            if cama_origen:
                cama_origen_identificador = cama_origen.identificador
                if cama_origen.sala and cama_origen.sala.servicio:
                    servicio_origen_id = cama_origen.sala.servicio.nombre  # Usamos nombre como ID
                    servicio_origen_nombre = cama_origen.sala.servicio.nombre
        
        # Obtener info de servicio destino
        if cama_destino.sala and cama_destino.sala.servicio:
            servicio_destino_id = cama_destino.sala.servicio.nombre
            servicio_destino_nombre = cama_destino.sala.servicio.nombre
        
        # ============================================
        # VERIFICAR COMPATIBILIDAD AL LLEGAR
        # ============================================
        compatibilidad_service = CompatibilidadService(self.session)
        es_compatible, problemas = compatibilidad_service.verificar_compatibilidad_arribo(
            paciente, cama_destino
        )
        
        # Si tiene cama origen (traslado interno), liberarla
        if cama_origen_id:
            cama_origen = self.cama_repo.obtener_por_id(cama_origen_id)
            if cama_origen:
                cama_origen.estado = EstadoCamaEnum.EN_LIMPIEZA
                cama_origen.limpieza_inicio = datetime.utcnow()
                cama_origen.mensaje_estado = "En limpieza"
                cama_origen.paciente_derivado_id = None
                cama_origen.cama_asignada_destino = None
                cama_origen.estado_updated_at = datetime.utcnow()
                self.session.add(cama_origen)
                logger.debug(f"Cama origen {cama_origen.identificador} puesta en limpieza")
                
                # NUEVO: Actualizar sexo de sala origen
                verificar_y_actualizar_sexo_sala_al_egreso(self.session, cama_origen)
        
        # Si es derivado y tiene cama origen de derivación, también liberarla
        if es_derivado and paciente.cama_origen_derivacion_id:
            cama_origen_derivacion = self.cama_repo.obtener_por_id(paciente.cama_origen_derivacion_id)
            if cama_origen_derivacion:
                # Solo liberar si aún no estaba en limpieza
                if cama_origen_derivacion.estado != EstadoCamaEnum.EN_LIMPIEZA:
                    cama_origen_derivacion.estado = EstadoCamaEnum.EN_LIMPIEZA
                    cama_origen_derivacion.limpieza_inicio = datetime.utcnow()
                    cama_origen_derivacion.mensaje_estado = "En limpieza"
                    cama_origen_derivacion.paciente_derivado_id = None
                    cama_origen_derivacion.cama_asignada_destino = None
                    cama_origen_derivacion.estado_updated_at = datetime.utcnow()
                    self.session.add(cama_origen_derivacion)
                    logger.debug(f"Cama origen derivación {cama_origen_derivacion.identificador} puesta en limpieza")
                    
                    # NUEVO: Actualizar sexo de sala
                    verificar_y_actualizar_sexo_sala_al_egreso(self.session, cama_origen_derivacion)
        
        # ============================================
        # ACTUALIZAR CAMA DESTINO SEGÚN COMPATIBILIDAD
        # ============================================
        if es_compatible:
            cama_destino.estado = EstadoCamaEnum.OCUPADA
            cama_destino.mensaje_estado = None
            paciente.requiere_nueva_cama = False
            mensaje = f"Traslado completado a cama {cama_destino.identificador}"
            logger.info(f"Paciente {paciente.nombre} compatible con cama destino")
        else:
            # NO ES COMPATIBLE - Poner en CAMA_EN_ESPERA
            cama_destino.estado = EstadoCamaEnum.CAMA_EN_ESPERA
            cama_destino.mensaje_estado = "Paciente requiere nueva cama: " + "; ".join(problemas)
            paciente.requiere_nueva_cama = True
            mensaje = f"Paciente llegó a cama {cama_destino.identificador} pero requiere nueva cama"
            logger.warning(f"Paciente {paciente.nombre} NO compatible con cama destino: {problemas}")
        
        cama_destino.paciente_derivado_id = None
        cama_destino.cama_asignada_destino = None
        cama_destino.estado_updated_at = datetime.utcnow()
        self.session.add(cama_destino)
        
        # NUEVO: Actualizar sexo de sala destino
        verificar_y_actualizar_sexo_sala_al_ingreso(self.session, cama_destino, paciente)
        
        # IMPORTANTE: Remover de cola de prioridad en memoria
        self._remover_de_cola_memoria(paciente)
        
        # Actualizar paciente
        paciente.cama_id = cama_destino.id
        paciente.cama_destino_id = None
        paciente.cama_origen_derivacion_id = None  # Limpiar referencia
        paciente.en_lista_espera = False
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
        paciente.timestamp_lista_espera = None
        paciente.prioridad_calculada = 0.0
        
        # Si era derivado, limpiar TODOS los estados de derivación
        if es_derivado:
            paciente.tipo_paciente = TipoPacienteEnum.HOSPITALIZADO
            paciente.derivacion_estado = None
            paciente.derivacion_hospital_destino_id = None
            paciente.derivacion_motivo = None
            paciente.derivacion_motivo_rechazo = None
        
        self.session.add(paciente)
        self.session.commit()
        
        logger.info(f"Traslado completado: {paciente.nombre} -> {cama_destino.identificador}")
        
        # ============================================
        # BROADCAST TTS
        # ============================================
        try:
            evento_tts = crear_evento_traslado_completado(
                cama_origen_identificador=cama_origen_identificador or "origen",
                paciente_nombre=paciente.nombre,
                servicio_origen_id=servicio_origen_id,
                servicio_origen_nombre=servicio_origen_nombre or "origen",
                servicio_destino_id=servicio_destino_id,
                servicio_destino_nombre=servicio_destino_nombre or "destino",
                hospital_id=hospital_id,
                paciente_id=str(paciente.id)
            )
            
            # Broadcast asíncrono
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(manager.broadcast(evento_tts))
            except RuntimeError:
                # Si no hay event loop, crear uno nuevo
                asyncio.run(manager.broadcast(evento_tts))
                
            logger.info(f"Evento TTS de traslado completado emitido")
        except Exception as e:
            logger.warning(f"Error emitiendo evento TTS: {e}")
            # Fallback sin TTS
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(manager.broadcast({
                    "tipo": "traslado_completado",
                    "hospital_id": hospital_id,
                    "reload": True,
                    "play_sound": True
                }))
            except:
                pass
        
        return ResultadoTraslado(
            exito=True,
            mensaje=mensaje,
            paciente_id=paciente_id,
            cama_origen_id=cama_origen_id,
            cama_destino_id=cama_destino.id
        )
    
    # ============================================
    # NUEVA FUNCIÓN: Cancelar traslado confirmado
    # ============================================
    
    def cancelar_traslado_confirmado(self, paciente_id: str) -> ResultadoTraslado:
        """
        Cancela un traslado que está en estado TRASLADO_CONFIRMADO.
        
        Flujo:
        1. Paciente elimina su asignación en la cama destino
        2. Paciente se sale de la lista de espera
        3. Cama destino vuelve a LIBRE
        4. Cama origen vuelve a CAMA_EN_ESPERA
        
        Args:
            paciente_id: ID del paciente con traslado confirmado
        
        Returns:
            ResultadoTraslado con el resultado de la operación
        """
        logger.info(f"Cancelando traslado confirmado para paciente_id: {paciente_id}")
        
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        # Verificar que tenga cama origen (está en traslado)
        if not paciente.cama_id:
            raise ValidationError("El paciente no tiene cama de origen")
        
        cama_origen = self.cama_repo.obtener_por_id(paciente.cama_id)
        if not cama_origen:
            raise ValidationError("Cama de origen no encontrada")
        
        # Verificar que esté en estado traslado confirmado
        if cama_origen.estado != EstadoCamaEnum.TRASLADO_CONFIRMADO:
            raise ValidationError(
                f"La cama no está en estado traslado confirmado (estado actual: {cama_origen.estado.value})"
            )
        
        # Remover de cola de prioridad
        self._remover_de_cola_memoria(paciente)
        
        # Obtener y liberar cama destino si existe
        cama_destino = None
        cama_destino_id = None
        if paciente.cama_destino_id:
            cama_destino = self.cama_repo.obtener_por_id(paciente.cama_destino_id)
            if cama_destino:
                cama_destino_id = cama_destino.id
                cama_destino.estado = EstadoCamaEnum.LIBRE
                cama_destino.mensaje_estado = None
                cama_destino.paciente_derivado_id = None
                cama_destino.cama_asignada_destino = None
                cama_destino.estado_updated_at = datetime.utcnow()
                self.session.add(cama_destino)
        
        # Restaurar cama origen a CAMA_EN_ESPERA
        cama_origen.estado = EstadoCamaEnum.CAMA_EN_ESPERA
        cama_origen.mensaje_estado = "Paciente requiere nueva cama"
        cama_origen.cama_asignada_destino = None
        cama_origen.estado_updated_at = datetime.utcnow()
        self.session.add(cama_origen)
        
        # Actualizar paciente
        paciente.cama_destino_id = None
        paciente.en_lista_espera = False
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
        paciente.timestamp_lista_espera = None
        paciente.prioridad_calculada = 0.0
        paciente.requiere_nueva_cama = True  # Listo para buscar de nuevo
        
        self.session.add(paciente)
        self.session.commit()
        
        logger.info(f"Traslado confirmado cancelado para {paciente.nombre}")
        
        return ResultadoTraslado(
            exito=True,
            mensaje="Traslado cancelado - paciente puede buscar nueva cama",
            paciente_id=paciente_id,
            cama_origen_id=str(cama_origen.id),
            cama_destino_id=str(cama_destino_id) if cama_destino_id else None
        )
    
    def cancelar_traslado(self, paciente_id: str) -> ResultadoTraslado:
        """
        Cancela un traslado pendiente desde la cama destino.
        
        Flujo:
        1. Cama destino vuelve a LIBRE
        2. Si tiene cama origen, esta vuelve a OCUPADA
        3. Paciente vuelve a su cama origen
        
        Args:
            paciente_id: ID del paciente
        
        Returns:
            Resultado de la cancelación
        """
        logger.info(f"Cancelando traslado para paciente_id: {paciente_id}")
        
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        if not paciente.cama_destino_id:
            raise ValidationError("El paciente no tiene traslado pendiente")
        
        # Liberar cama destino
        cama_destino = self.cama_repo.obtener_por_id(paciente.cama_destino_id)
        if cama_destino:
            cama_destino.estado = EstadoCamaEnum.LIBRE
            cama_destino.mensaje_estado = None
            cama_destino.paciente_derivado_id = None
            cama_destino.cama_asignada_destino = None
            cama_destino.estado_updated_at = datetime.utcnow()
            self.session.add(cama_destino)
        
        # Si tiene cama origen, restaurar a OCUPADA
        if paciente.cama_id:
            cama_origen = self.cama_repo.obtener_por_id(paciente.cama_id)
            if cama_origen:
                cama_origen.estado = EstadoCamaEnum.OCUPADA
                cama_origen.mensaje_estado = None
                cama_origen.cama_asignada_destino = None
                cama_origen.estado_updated_at = datetime.utcnow()
                self.session.add(cama_origen)
        
        # Remover de cola de prioridad
        self._remover_de_cola_memoria(paciente)
        
        # Limpiar destino del paciente
        paciente.cama_destino_id = None
        paciente.en_lista_espera = False
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
        paciente.timestamp_lista_espera = None
        paciente.prioridad_calculada = 0.0
        
        self.session.add(paciente)
        self.session.commit()
        
        logger.info(f"Traslado cancelado para {paciente.nombre}")
        
        return ResultadoTraslado(
            exito=True,
            mensaje="Traslado cancelado",
            paciente_id=paciente_id
        )
    
    def cancelar_traslado_desde_origen(self, paciente_id: str) -> ResultadoTraslado:
        """
        Cancela un traslado desde la cama de origen.
        
        Flujo según documento:
        1. Liberar cama destino (vuelve a LIBRE)
        2. Cama origen vuelve a CAMA_EN_ESPERA (paciente sigue necesitando nueva cama)
        3. Paciente sale de lista de espera pero mantiene requiere_nueva_cama
        
        Args:
            paciente_id: ID del paciente
        
        Returns:
            Resultado de la cancelación
        """
        logger.info(f"Cancelando traslado desde origen para paciente_id: {paciente_id}")
        
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            raise PacienteNotFoundError(paciente_id)
        
        # Verificar que tenga cama asignada (traslado en proceso)
        if not paciente.cama_id:
            resultado = ResultadoTraslado(
                exito=False,
                mensaje="El paciente no tiene cama de origen",
                paciente_id=paciente_id
            )
            return resultado
        
        cama_origen = self.cama_repo.obtener_por_id(paciente.cama_id)
        if not cama_origen:
            return ResultadoTraslado(
                exito=False,
                mensaje="Cama de origen no encontrada",
                paciente_id=paciente_id
            )
        
        # Verificar que esté en estado traslado
        estados_traslado = [
            EstadoCamaEnum.TRASLADO_SALIENTE,
            EstadoCamaEnum.TRASLADO_CONFIRMADO
        ]
        if cama_origen.estado not in estados_traslado:
            return ResultadoTraslado(
                exito=False,
                mensaje=f"La cama no está en estado de traslado (estado actual: {cama_origen.estado.value})",
                paciente_id=paciente_id
            )
        
        # Remover de cola de prioridad
        self._remover_de_cola_memoria(paciente)
        
        # Liberar cama destino si existe
        if paciente.cama_destino_id:
            cama_destino = self.cama_repo.obtener_por_id(paciente.cama_destino_id)
            if cama_destino:
                cama_destino.estado = EstadoCamaEnum.LIBRE
                cama_destino.mensaje_estado = None
                cama_destino.paciente_derivado_id = None
                cama_destino.cama_asignada_destino = None
                cama_destino.estado_updated_at = datetime.utcnow()
                self.session.add(cama_destino)
        
        # Restaurar cama origen a CAMA_EN_ESPERA
        if paciente.cama_id:
            cama_origen = self.cama_repo.obtener_por_id(paciente.cama_id)
            if cama_origen:
                cama_origen.estado = EstadoCamaEnum.CAMA_EN_ESPERA
                cama_origen.mensaje_estado = "Paciente requiere nueva cama"
                cama_origen.cama_asignada_destino = None
                cama_origen.estado_updated_at = datetime.utcnow()
                self.session.add(cama_origen)
        
        # Actualizar paciente
        paciente.cama_destino_id = None
        paciente.en_lista_espera = False
        paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
        paciente.timestamp_lista_espera = None
        paciente.prioridad_calculada = 0.0
        paciente.requiere_nueva_cama = True  # Listo para buscar de nuevo
        
        self.session.add(paciente)
        self.session.commit()
        
        logger.info(f"Traslado cancelado desde origen para {paciente.nombre}")
        
        return ResultadoTraslado(
            exito=True,
            mensaje="Traslado cancelado - paciente puede buscar nueva cama",
            paciente_id=paciente_id
        )
    
    def intercambiar_pacientes(
        self,
        paciente_a_id: str,
        paciente_b_id: str
    ) -> ResultadoTraslado:
        """
        Intercambia las camas de dos pacientes.
        
        Args:
            paciente_a_id: ID del primer paciente
            paciente_b_id: ID del segundo paciente
        
        Returns:
            Resultado del intercambio
        """
        logger.info(f"Iniciando intercambio: {paciente_a_id} <-> {paciente_b_id}")
        
        paciente_a = self.paciente_repo.obtener_por_id(paciente_a_id)
        paciente_b = self.paciente_repo.obtener_por_id(paciente_b_id)
        
        if not paciente_a:
            raise PacienteNotFoundError(paciente_a_id)
        if not paciente_b:
            raise PacienteNotFoundError(paciente_b_id)
        
        if not paciente_a.cama_id or not paciente_b.cama_id:
            raise ValidationError("Ambos pacientes deben tener cama asignada")
        
        # Intercambiar camas
        cama_a_id = paciente_a.cama_id
        cama_b_id = paciente_b.cama_id
        
        paciente_a.cama_id = cama_b_id
        paciente_b.cama_id = cama_a_id
        
        self.session.add(paciente_a)
        self.session.add(paciente_b)
        self.session.commit()
        
        logger.info(
            f"Intercambio completado: {paciente_a.nombre} <-> {paciente_b.nombre}"
        )
        
        return ResultadoTraslado(
            exito=True,
            mensaje="Intercambio completado exitosamente"
        )
    
    def traslado_manual(
        self,
        paciente_id: str,
        cama_destino_id: str
    ) -> ResultadoTraslado:
        """
        Inicia un proceso de traslado manual.
        
        ACTUALIZADO v2: En vez de traslado inmediato, inicia el proceso:
        - Cama destino -> TRASLADO_ENTRANTE (con botones completar/cancelar)
        - Cama origen -> TRASLADO_CONFIRMADO (con botones ver/cancelar)
        - Solo se libera la cama origen cuando se complete el traslado
        
        Args:
            paciente_id: ID del paciente
            cama_destino_id: ID de la cama destino
        
        Returns:
            Resultado del traslado
        """
        logger.info(
            f"Iniciando traslado manual: paciente {paciente_id} -> cama {cama_destino_id}"
        )
        
        paciente = self.paciente_repo.obtener_por_id(paciente_id)
        if not paciente:
            logger.error(f"Paciente no encontrado: {paciente_id}")
            raise PacienteNotFoundError(paciente_id)
        
        cama_destino = self.cama_repo.obtener_por_id(cama_destino_id)
        if not cama_destino:
            logger.error(f"Cama no encontrada: {cama_destino_id}")
            raise CamaNotFoundError(cama_destino_id)
        
        if cama_destino.estado != EstadoCamaEnum.LIBRE:
            logger.warning(
                f"Cama {cama_destino.identificador} no está libre "
                f"(estado: {cama_destino.estado.value})"
            )
            raise ValidationError(
                f"La cama {cama_destino.identificador} no está disponible"
            )
        
        cama_origen_id = paciente.cama_id
        
        # ============================================
        # ACTUALIZAR CAMA DESTINO A TRASLADO_ENTRANTE
        # ============================================
        cama_destino.estado = EstadoCamaEnum.TRASLADO_ENTRANTE
        cama_destino.mensaje_estado = f"Esperando a {paciente.nombre}"
        cama_destino.estado_updated_at = datetime.utcnow()
        self.session.add(cama_destino)
        
        # NUEVO: Actualizar sexo de sala destino anticipadamente
        verificar_y_actualizar_sexo_sala_al_ingreso(self.session, cama_destino, paciente)
        
        # ============================================
        # ACTUALIZAR CAMA ORIGEN A TRASLADO_CONFIRMADO
        # ============================================
        if cama_origen_id:
            cama_origen = self.cama_repo.obtener_por_id(cama_origen_id)
            if cama_origen:
                cama_origen.estado = EstadoCamaEnum.TRASLADO_CONFIRMADO
                cama_origen.mensaje_estado = f"Traslado confirmado a {cama_destino.identificador}"
                cama_origen.cama_asignada_destino = cama_destino.id
                cama_origen.estado_updated_at = datetime.utcnow()
                self.session.add(cama_origen)
                logger.info(f"Cama origen {cama_origen.identificador} -> TRASLADO_CONFIRMADO")
        
        # ============================================
        # ACTUALIZAR PACIENTE
        # ============================================
        # IMPORTANTE: NO cambiar cama_id todavía, solo asignar cama_destino_id
        paciente.cama_destino_id = cama_destino_id
        
        # Si estaba en lista de espera, remover
        if paciente.en_lista_espera:
            self._remover_de_cola_memoria(paciente)
            paciente.en_lista_espera = False
            paciente.estado_lista_espera = EstadoListaEsperaEnum.ASIGNADO
        
        self.session.add(paciente)
        self.session.commit()
        
        logger.info(
            f"Traslado manual iniciado: {paciente.nombre} -> {cama_destino.identificador} "
            f"(pendiente completar)"
        )
        
        return ResultadoTraslado(
            exito=True,
            mensaje=f"Traslado iniciado a {cama_destino.identificador}. Confirme cuando el paciente llegue.",
            paciente_id=paciente_id,
            cama_origen_id=cama_origen_id,
            cama_destino_id=cama_destino_id
        )