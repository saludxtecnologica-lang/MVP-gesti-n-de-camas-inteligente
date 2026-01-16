"""
Servicio de registro de eventos de pacientes.
Registra todos los cambios de estado importantes para análisis estadístico.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models.evento_paciente import EventoPaciente
from app.models.enums import TipoEventoEnum
from app.models.paciente import Paciente
from app.models.cama import Cama
from app.models.servicio import Servicio


class EventoService:
    """
    Servicio para registrar eventos de pacientes.

    Este servicio es responsable de registrar todos los eventos importantes
    que ocurren en el sistema para permitir trazabilidad completa y
    cálculos estadísticos precisos.
    """

    @staticmethod
    def calcular_dia_clinico(timestamp: datetime) -> datetime:
        """
        Calcula el día clínico para un timestamp dado.
        Un día clínico inicia a las 8:00 AM.

        Args:
            timestamp: Timestamp del evento

        Returns:
            Fecha del día clínico (8:00 AM)
        """
        # Si es antes de las 8 AM, pertenece al día clínico anterior
        if timestamp.hour < 8:
            dia_clinico = timestamp.replace(hour=8, minute=0, second=0, microsecond=0)
            dia_clinico = dia_clinico - timedelta(days=1)
        else:
            dia_clinico = timestamp.replace(hour=8, minute=0, second=0, microsecond=0)
        return dia_clinico

    @staticmethod
    async def obtener_servicio_de_cama(session: Session, cama_id: Optional[str]) -> Optional[str]:
        """
        Obtiene el servicio_id de una cama.

        Args:
            session: Sesión de base de datos
            cama_id: ID de la cama

        Returns:
            ID del servicio o None
        """
        if not cama_id:
            return None

        cama = session.get(Cama, cama_id)
        if cama and cama.sala_id:
            from app.models.sala import Sala
            sala = session.get(Sala, cama.sala_id)
            if sala:
                return sala.servicio_id
        return None

    @staticmethod
    async def registrar_evento(
        session: Session,
        tipo_evento: TipoEventoEnum,
        paciente_id: str,
        hospital_id: str,
        servicio_origen_id: Optional[str] = None,
        servicio_destino_id: Optional[str] = None,
        cama_origen_id: Optional[str] = None,
        cama_destino_id: Optional[str] = None,
        hospital_destino_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> EventoPaciente:
        """
        Registra un evento del paciente en el sistema.

        Args:
            session: Sesión de base de datos
            tipo_evento: Tipo de evento
            paciente_id: ID del paciente
            hospital_id: ID del hospital
            servicio_origen_id: ID del servicio origen (opcional)
            servicio_destino_id: ID del servicio destino (opcional)
            cama_origen_id: ID de la cama origen (opcional)
            cama_destino_id: ID de la cama destino (opcional)
            hospital_destino_id: ID del hospital destino (opcional)
            metadata: Metadata adicional (opcional)
            timestamp: Timestamp del evento (opcional, usa datetime.utcnow si no se proporciona)

        Returns:
            EventoPaciente creado
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        # Calcular día clínico
        dia_clinico = EventoService.calcular_dia_clinico(timestamp)

        # Si no se proporciona servicio_origen_id pero sí cama_origen_id, obtenerlo
        if servicio_origen_id is None and cama_origen_id is not None:
            servicio_origen_id = await EventoService.obtener_servicio_de_cama(session, cama_origen_id)

        # Si no se proporciona servicio_destino_id pero sí cama_destino_id, obtenerlo
        if servicio_destino_id is None and cama_destino_id is not None:
            servicio_destino_id = await EventoService.obtener_servicio_de_cama(session, cama_destino_id)

        # Crear evento
        evento = EventoPaciente(
            tipo_evento=tipo_evento,
            timestamp=timestamp,
            paciente_id=paciente_id,
            hospital_id=hospital_id,
            servicio_origen_id=servicio_origen_id,
            servicio_destino_id=servicio_destino_id,
            cama_origen_id=cama_origen_id,
            cama_destino_id=cama_destino_id,
            hospital_destino_id=hospital_destino_id,
            dia_clinico=dia_clinico,
        )

        # Establecer metadata si se proporciona
        if metadata:
            evento.set_metadata(metadata)

        # Guardar en base de datos
        try:
            session.add(evento)
            session.commit()
            session.refresh(evento)
            return evento
        except IntegrityError as e:
            session.rollback()
            raise ValueError(f"Error al registrar evento: {str(e)}")

    @staticmethod
    async def registrar_ingreso(
        session: Session,
        paciente: Paciente,
        tipo_ingreso: str = "urgencia"
    ) -> EventoPaciente:
        """
        Registra un ingreso de paciente.

        Args:
            session: Sesión de base de datos
            paciente: Paciente que ingresa
            tipo_ingreso: Tipo de ingreso (urgencia/ambulatorio)

        Returns:
            EventoPaciente creado
        """
        tipo_evento = (
            TipoEventoEnum.INGRESO_URGENCIA if tipo_ingreso == "urgencia"
            else TipoEventoEnum.INGRESO_AMBULATORIO
        )

        metadata = {
            "tipo_paciente": paciente.tipo_paciente,
            "complejidad": paciente.complejidad_requerida,
            "diagnostico": paciente.diagnostico,
        }

        return await EventoService.registrar_evento(
            session=session,
            tipo_evento=tipo_evento,
            paciente_id=paciente.id,
            hospital_id=paciente.hospital_id,
            metadata=metadata,
            timestamp=paciente.created_at,
        )

    @staticmethod
    async def registrar_asignacion_cama(
        session: Session,
        paciente: Paciente,
        cama_id: str
    ) -> EventoPaciente:
        """
        Registra la asignación de una cama a un paciente.

        Args:
            session: Sesión de base de datos
            paciente: Paciente
            cama_id: ID de la cama asignada

        Returns:
            EventoPaciente creado
        """
        return await EventoService.registrar_evento(
            session=session,
            tipo_evento=TipoEventoEnum.CAMA_ASIGNADA,
            paciente_id=paciente.id,
            hospital_id=paciente.hospital_id,
            cama_destino_id=cama_id,
        )

    @staticmethod
    async def registrar_busqueda_cama(
        session: Session,
        paciente: Paciente
    ) -> EventoPaciente:
        """
        Registra el inicio de búsqueda de cama para un paciente.

        Args:
            session: Sesión de base de datos
            paciente: Paciente

        Returns:
            EventoPaciente creado
        """
        metadata = {}
        if paciente.cama_id:
            metadata["cama_origen"] = paciente.cama_id

        return await EventoService.registrar_evento(
            session=session,
            tipo_evento=TipoEventoEnum.BUSQUEDA_CAMA_INICIADA,
            paciente_id=paciente.id,
            hospital_id=paciente.hospital_id,
            cama_origen_id=paciente.cama_id,
            metadata=metadata,
        )

    @staticmethod
    async def registrar_traslado_iniciado(
        session: Session,
        paciente: Paciente,
        cama_origen_id: str,
        cama_destino_id: str
    ) -> EventoPaciente:
        """
        Registra el inicio de un traslado.

        Args:
            session: Sesión de base de datos
            paciente: Paciente
            cama_origen_id: ID de la cama origen
            cama_destino_id: ID de la cama destino

        Returns:
            EventoPaciente creado
        """
        return await EventoService.registrar_evento(
            session=session,
            tipo_evento=TipoEventoEnum.TRASLADO_INICIADO,
            paciente_id=paciente.id,
            hospital_id=paciente.hospital_id,
            cama_origen_id=cama_origen_id,
            cama_destino_id=cama_destino_id,
        )

    @staticmethod
    async def registrar_traslado_confirmado(
        session: Session,
        paciente: Paciente,
        cama_origen_id: str,
        cama_destino_id: str
    ) -> EventoPaciente:
        """
        Registra la confirmación de un traslado.

        Args:
            session: Sesión de base de datos
            paciente: Paciente
            cama_origen_id: ID de la cama origen
            cama_destino_id: ID de la cama destino

        Returns:
            EventoPaciente creado
        """
        return await EventoService.registrar_evento(
            session=session,
            tipo_evento=TipoEventoEnum.TRASLADO_CONFIRMADO,
            paciente_id=paciente.id,
            hospital_id=paciente.hospital_id,
            cama_origen_id=cama_origen_id,
            cama_destino_id=cama_destino_id,
        )

    @staticmethod
    async def registrar_traslado_completado(
        session: Session,
        paciente: Paciente,
        cama_origen_id: str,
        cama_destino_id: str
    ) -> EventoPaciente:
        """
        Registra la finalización de un traslado.

        Args:
            session: Sesión de base de datos
            paciente: Paciente
            cama_origen_id: ID de la cama origen
            cama_destino_id: ID de la cama destino

        Returns:
            EventoPaciente creado
        """
        return await EventoService.registrar_evento(
            session=session,
            tipo_evento=TipoEventoEnum.TRASLADO_COMPLETADO,
            paciente_id=paciente.id,
            hospital_id=paciente.hospital_id,
            cama_origen_id=cama_origen_id,
            cama_destino_id=cama_destino_id,
        )

    @staticmethod
    async def registrar_cama_en_espera_inicio(
        session: Session,
        paciente: Paciente,
        cama_id: str
    ) -> EventoPaciente:
        """
        Registra el inicio de estado "cama en espera".

        Args:
            session: Sesión de base de datos
            paciente: Paciente
            cama_id: ID de la cama

        Returns:
            EventoPaciente creado
        """
        return await EventoService.registrar_evento(
            session=session,
            tipo_evento=TipoEventoEnum.CAMA_EN_ESPERA_INICIO,
            paciente_id=paciente.id,
            hospital_id=paciente.hospital_id,
            cama_destino_id=cama_id,
        )

    @staticmethod
    async def registrar_cama_en_espera_fin(
        session: Session,
        paciente: Paciente,
        cama_id: str
    ) -> EventoPaciente:
        """
        Registra el fin de estado "cama en espera".

        Args:
            session: Sesión de base de datos
            paciente: Paciente
            cama_id: ID de la cama

        Returns:
            EventoPaciente creado
        """
        return await EventoService.registrar_evento(
            session=session,
            tipo_evento=TipoEventoEnum.CAMA_EN_ESPERA_FIN,
            paciente_id=paciente.id,
            hospital_id=paciente.hospital_id,
            cama_destino_id=cama_id,
        )

    @staticmethod
    async def registrar_derivacion_solicitada(
        session: Session,
        paciente: Paciente,
        hospital_destino_id: str,
        cama_origen_id: Optional[str] = None
    ) -> EventoPaciente:
        """
        Registra una solicitud de derivación.

        Args:
            session: Sesión de base de datos
            paciente: Paciente
            hospital_destino_id: ID del hospital destino
            cama_origen_id: ID de la cama origen (opcional)

        Returns:
            EventoPaciente creado
        """
        return await EventoService.registrar_evento(
            session=session,
            tipo_evento=TipoEventoEnum.DERIVACION_SOLICITADA,
            paciente_id=paciente.id,
            hospital_id=paciente.hospital_id,
            hospital_destino_id=hospital_destino_id,
            cama_origen_id=cama_origen_id,
        )

    @staticmethod
    async def registrar_derivacion_aceptada(
        session: Session,
        paciente: Paciente,
        hospital_destino_id: str,
        cama_destino_id: Optional[str] = None
    ) -> EventoPaciente:
        """
        Registra la aceptación de una derivación.

        Args:
            session: Sesión de base de datos
            paciente: Paciente
            hospital_destino_id: ID del hospital destino
            cama_destino_id: ID de la cama asignada (opcional)

        Returns:
            EventoPaciente creado
        """
        return await EventoService.registrar_evento(
            session=session,
            tipo_evento=TipoEventoEnum.DERIVACION_ACEPTADA,
            paciente_id=paciente.id,
            hospital_id=paciente.hospital_id,
            hospital_destino_id=hospital_destino_id,
            cama_destino_id=cama_destino_id,
        )

    @staticmethod
    async def registrar_derivacion_rechazada(
        session: Session,
        paciente: Paciente,
        hospital_destino_id: str,
        motivo: Optional[str] = None
    ) -> EventoPaciente:
        """
        Registra el rechazo de una derivación.

        Args:
            session: Sesión de base de datos
            paciente: Paciente
            hospital_destino_id: ID del hospital destino
            motivo: Motivo del rechazo (opcional)

        Returns:
            EventoPaciente creado
        """
        metadata = {}
        if motivo:
            metadata["motivo_rechazo"] = motivo

        return await EventoService.registrar_evento(
            session=session,
            tipo_evento=TipoEventoEnum.DERIVACION_RECHAZADA,
            paciente_id=paciente.id,
            hospital_id=paciente.hospital_id,
            hospital_destino_id=hospital_destino_id,
            metadata=metadata,
        )

    @staticmethod
    async def registrar_derivacion_egreso_confirmado(
        session: Session,
        paciente: Paciente,
        hospital_destino_id: str,
        cama_origen_id: str
    ) -> EventoPaciente:
        """
        Registra la confirmación de egreso por derivación.

        Args:
            session: Sesión de base de datos
            paciente: Paciente
            hospital_destino_id: ID del hospital destino
            cama_origen_id: ID de la cama origen

        Returns:
            EventoPaciente creado
        """
        return await EventoService.registrar_evento(
            session=session,
            tipo_evento=TipoEventoEnum.DERIVACION_EGRESO_CONFIRMADO,
            paciente_id=paciente.id,
            hospital_id=paciente.hospital_id,
            hospital_destino_id=hospital_destino_id,
            cama_origen_id=cama_origen_id,
        )

    @staticmethod
    async def registrar_derivacion_completada(
        session: Session,
        paciente: Paciente,
        hospital_origen_id: str,
        cama_destino_id: str
    ) -> EventoPaciente:
        """
        Registra la finalización completa de una derivación.

        Args:
            session: Sesión de base de datos
            paciente: Paciente
            hospital_origen_id: ID del hospital origen
            cama_destino_id: ID de la cama destino

        Returns:
            EventoPaciente creado
        """
        return await EventoService.registrar_evento(
            session=session,
            tipo_evento=TipoEventoEnum.DERIVACION_COMPLETADA,
            paciente_id=paciente.id,
            hospital_id=paciente.hospital_id,
            cama_destino_id=cama_destino_id,
            metadata={"hospital_origen": hospital_origen_id},
        )

    @staticmethod
    async def registrar_alta_sugerida(
        session: Session,
        paciente: Paciente,
        cama_id: str
    ) -> EventoPaciente:
        """
        Registra una sugerencia de alta.

        Args:
            session: Sesión de base de datos
            paciente: Paciente
            cama_id: ID de la cama

        Returns:
            EventoPaciente creado
        """
        return await EventoService.registrar_evento(
            session=session,
            tipo_evento=TipoEventoEnum.ALTA_SUGERIDA,
            paciente_id=paciente.id,
            hospital_id=paciente.hospital_id,
            cama_origen_id=cama_id,
        )

    @staticmethod
    async def registrar_alta_iniciada(
        session: Session,
        paciente: Paciente,
        cama_id: str,
        motivo: Optional[str] = None
    ) -> EventoPaciente:
        """
        Registra el inicio de un alta.

        Args:
            session: Sesión de base de datos
            paciente: Paciente
            cama_id: ID de la cama
            motivo: Motivo del alta (opcional)

        Returns:
            EventoPaciente creado
        """
        metadata = {}
        if motivo:
            metadata["motivo"] = motivo

        return await EventoService.registrar_evento(
            session=session,
            tipo_evento=TipoEventoEnum.ALTA_INICIADA,
            paciente_id=paciente.id,
            hospital_id=paciente.hospital_id,
            cama_origen_id=cama_id,
            metadata=metadata,
        )

    @staticmethod
    async def registrar_alta_completada(
        session: Session,
        paciente: Paciente,
        cama_id: str
    ) -> EventoPaciente:
        """
        Registra la finalización de un alta.

        Args:
            session: Sesión de base de datos
            paciente: Paciente
            cama_id: ID de la cama

        Returns:
            EventoPaciente creado
        """
        return await EventoService.registrar_evento(
            session=session,
            tipo_evento=TipoEventoEnum.ALTA_COMPLETADA,
            paciente_id=paciente.id,
            hospital_id=paciente.hospital_id,
            cama_origen_id=cama_id,
        )

    @staticmethod
    async def registrar_fallecido_marcado(
        session: Session,
        paciente: Paciente,
        cama_id: str,
        causa: Optional[str] = None
    ) -> EventoPaciente:
        """
        Registra cuando se marca un paciente como fallecido.

        Args:
            session: Sesión de base de datos
            paciente: Paciente
            cama_id: ID de la cama
            causa: Causa del fallecimiento (opcional)

        Returns:
            EventoPaciente creado
        """
        metadata = {}
        if causa:
            metadata["causa"] = causa

        return await EventoService.registrar_evento(
            session=session,
            tipo_evento=TipoEventoEnum.FALLECIDO_MARCADO,
            paciente_id=paciente.id,
            hospital_id=paciente.hospital_id,
            cama_origen_id=cama_id,
            metadata=metadata,
        )

    @staticmethod
    async def registrar_fallecido_egresado(
        session: Session,
        paciente: Paciente,
        cama_id: str
    ) -> EventoPaciente:
        """
        Registra el egreso de un paciente fallecido.

        Args:
            session: Sesión de base de datos
            paciente: Paciente
            cama_id: ID de la cama

        Returns:
            EventoPaciente creado
        """
        return await EventoService.registrar_evento(
            session=session,
            tipo_evento=TipoEventoEnum.FALLECIDO_EGRESADO,
            paciente_id=paciente.id,
            hospital_id=paciente.hospital_id,
            cama_origen_id=cama_id,
        )
