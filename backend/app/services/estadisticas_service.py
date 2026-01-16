"""
Servicio de estadísticas para el sistema de gestión de camas.
Calcula todas las métricas y estadísticas solicitadas.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlmodel import Session, select, func, and_, or_
from sqlalchemy import distinct
from collections import defaultdict

from app.models.paciente import Paciente
from app.models.cama import Cama
from app.models.hospital import Hospital
from app.models.servicio import Servicio
from app.models.sala import Sala
from app.models.evento_paciente import EventoPaciente
from app.models.enums import (
    TipoEventoEnum,
    EstadoCamaEnum,
    TipoPacienteEnum,
    ESTADOS_CAMA_OCUPADA,
)


class EstadisticasService:
    """
    Servicio para calcular estadísticas del sistema.

    Provee métodos para calcular todas las métricas solicitadas:
    - Ingresos/egresos diarios
    - Tiempos promedio/máximo/mínimo
    - Tasas de ocupación
    - Flujos más repetidos
    - Servicios con mayor demanda
    - Casos especiales
    - Camas/servicios subutilizados
    - Trazabilidad de pacientes
    """

    @staticmethod
    def calcular_dia_clinico(timestamp: datetime) -> datetime:
        """
        Calcula el día clínico para un timestamp dado.
        Un día clínico inicia a las 8:00 AM.
        """
        if timestamp.hour < 8:
            dia_clinico = timestamp.replace(hour=8, minute=0, second=0, microsecond=0)
            dia_clinico = dia_clinico - timedelta(days=1)
        else:
            dia_clinico = timestamp.replace(hour=8, minute=0, second=0, microsecond=0)
        return dia_clinico

    # ============================================
    # INGRESOS Y EGRESOS DIARIOS
    # ============================================

    @staticmethod
    async def calcular_ingresos_red(
        session: Session,
        fecha_inicio: datetime,
        fecha_fin: datetime
    ) -> Dict[str, int]:
        """
        Calcula los ingresos totales de la red (suma de todos los hospitales).
        Son pacientes nuevos por urgencia o ambulatorio en cualquier hospital.
        """
        statement = select(func.count(distinct(EventoPaciente.paciente_id))).where(
            and_(
                EventoPaciente.tipo_evento.in_([
                    TipoEventoEnum.INGRESO_URGENCIA,
                    TipoEventoEnum.INGRESO_AMBULATORIO
                ]),
                EventoPaciente.timestamp >= fecha_inicio,
                EventoPaciente.timestamp < fecha_fin
            )
        )
        total = session.exec(statement).first() or 0
        return {"total_ingresos_red": total}

    @staticmethod
    async def calcular_ingresos_hospital(
        session: Session,
        hospital_id: str,
        fecha_inicio: datetime,
        fecha_fin: datetime
    ) -> Dict[str, int]:
        """
        Calcula los ingresos de un hospital específico.
        Incluye: urgencias, ambulatorios, derivados aceptados.
        """
        # Ingresos directos (urgencia, ambulatorio)
        statement_directos = select(func.count(distinct(EventoPaciente.paciente_id))).where(
            and_(
                EventoPaciente.hospital_id == hospital_id,
                EventoPaciente.tipo_evento.in_([
                    TipoEventoEnum.INGRESO_URGENCIA,
                    TipoEventoEnum.INGRESO_AMBULATORIO
                ]),
                EventoPaciente.timestamp >= fecha_inicio,
                EventoPaciente.timestamp < fecha_fin
            )
        )
        ingresos_directos = session.exec(statement_directos).first() or 0

        # Derivados aceptados (este hospital acepta al paciente)
        statement_derivados = select(func.count(distinct(EventoPaciente.paciente_id))).where(
            and_(
                EventoPaciente.hospital_id == hospital_id,
                EventoPaciente.tipo_evento == TipoEventoEnum.DERIVACION_ACEPTADA,
                EventoPaciente.timestamp >= fecha_inicio,
                EventoPaciente.timestamp < fecha_fin
            )
        )
        ingresos_derivados = session.exec(statement_derivados).first() or 0

        total = ingresos_directos + ingresos_derivados
        return {
            "total_ingresos_hospital": total,
            "ingresos_directos": ingresos_directos,
            "ingresos_derivados": ingresos_derivados
        }

    @staticmethod
    async def calcular_ingresos_servicio(
        session: Session,
        servicio_id: str,
        fecha_inicio: datetime,
        fecha_fin: datetime
    ) -> Dict[str, int]:
        """
        Calcula los ingresos de un servicio específico.
        Incluye: pacientes que llegan al servicio (urgencias, ambulatorios, derivados, traslados).
        """
        # Obtener todas las camas del servicio
        statement_camas = select(Cama).join(Sala).where(Sala.servicio_id == servicio_id)
        camas = session.exec(statement_camas).all()
        camas_ids = [cama.id for cama in camas]

        if not camas_ids:
            return {"total_ingresos_servicio": 0}

        # Contar eventos de llegada a camas del servicio
        statement = select(func.count(distinct(EventoPaciente.paciente_id))).where(
            and_(
                EventoPaciente.cama_destino_id.in_(camas_ids),
                EventoPaciente.tipo_evento.in_([
                    TipoEventoEnum.CAMA_ASIGNADA,
                    TipoEventoEnum.TRASLADO_COMPLETADO,
                    TipoEventoEnum.DERIVACION_COMPLETADA
                ]),
                EventoPaciente.timestamp >= fecha_inicio,
                EventoPaciente.timestamp < fecha_fin
            )
        )
        total = session.exec(statement).first() or 0
        return {"total_ingresos_servicio": total}

    @staticmethod
    async def calcular_egresos_red(
        session: Session,
        fecha_inicio: datetime,
        fecha_fin: datetime
    ) -> Dict[str, int]:
        """
        Calcula los egresos totales de la red.
        Son pacientes que salen definitivamente (altas, fallecidos).
        """
        statement = select(func.count(distinct(EventoPaciente.paciente_id))).where(
            and_(
                EventoPaciente.tipo_evento.in_([
                    TipoEventoEnum.EGRESO_ALTA,
                    TipoEventoEnum.EGRESO_FALLECIDO
                ]),
                EventoPaciente.timestamp >= fecha_inicio,
                EventoPaciente.timestamp < fecha_fin
            )
        )
        total = session.exec(statement).first() or 0
        return {"total_egresos_red": total}

    @staticmethod
    async def calcular_egresos_hospital(
        session: Session,
        hospital_id: str,
        fecha_inicio: datetime,
        fecha_fin: datetime
    ) -> Dict[str, int]:
        """
        Calcula los egresos de un hospital específico.
        Incluye: altas, fallecidos, derivaciones confirmadas (salen del hospital).
        """
        # Altas y fallecidos
        statement_finales = select(func.count(distinct(EventoPaciente.paciente_id))).where(
            and_(
                EventoPaciente.hospital_id == hospital_id,
                EventoPaciente.tipo_evento.in_([
                    TipoEventoEnum.ALTA_COMPLETADA,
                    TipoEventoEnum.FALLECIDO_EGRESADO
                ]),
                EventoPaciente.timestamp >= fecha_inicio,
                EventoPaciente.timestamp < fecha_fin
            )
        )
        egresos_finales = session.exec(statement_finales).first() or 0

        # Derivaciones confirmadas (paciente sale del hospital)
        statement_derivados = select(func.count(distinct(EventoPaciente.paciente_id))).where(
            and_(
                EventoPaciente.hospital_id == hospital_id,
                EventoPaciente.tipo_evento == TipoEventoEnum.DERIVACION_EGRESO_CONFIRMADO,
                EventoPaciente.timestamp >= fecha_inicio,
                EventoPaciente.timestamp < fecha_fin
            )
        )
        egresos_derivados = session.exec(statement_derivados).first() or 0

        total = egresos_finales + egresos_derivados
        return {
            "total_egresos_hospital": total,
            "egresos_finales": egresos_finales,
            "egresos_derivados": egresos_derivados
        }

    @staticmethod
    async def calcular_egresos_servicio(
        session: Session,
        servicio_id: str,
        fecha_inicio: datetime,
        fecha_fin: datetime
    ) -> Dict[str, int]:
        """
        Calcula los egresos de un servicio específico.
        Incluye: pacientes que salen del servicio (traslados, altas, derivaciones, fallecidos).
        """
        # Obtener todas las camas del servicio
        statement_camas = select(Cama).join(Sala).where(Sala.servicio_id == servicio_id)
        camas = session.exec(statement_camas).all()
        camas_ids = [cama.id for cama in camas]

        if not camas_ids:
            return {"total_egresos_servicio": 0}

        # Contar eventos de salida desde camas del servicio
        statement = select(func.count(distinct(EventoPaciente.paciente_id))).where(
            and_(
                EventoPaciente.cama_origen_id.in_(camas_ids),
                EventoPaciente.tipo_evento.in_([
                    TipoEventoEnum.TRASLADO_COMPLETADO,
                    TipoEventoEnum.ALTA_COMPLETADA,
                    TipoEventoEnum.DERIVACION_EGRESO_CONFIRMADO,
                    TipoEventoEnum.FALLECIDO_EGRESADO
                ]),
                EventoPaciente.timestamp >= fecha_inicio,
                EventoPaciente.timestamp < fecha_fin
            )
        )
        total = session.exec(statement).first() or 0
        return {"total_egresos_servicio": total}

    # ============================================
    # TIEMPOS PROMEDIO/MÁXIMO/MÍNIMO
    # ============================================

    @staticmethod
    async def calcular_tiempo_espera_cama(
        session: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Calcula el tiempo promedio/máximo/mínimo de espera de cama.
        Desde que se inicia búsqueda hasta que se asigna cama.
        """
        # Buscar pares de eventos: BUSQUEDA_CAMA_INICIADA -> CAMA_ASIGNADA
        query = select(EventoPaciente).where(
            EventoPaciente.tipo_evento.in_([
                TipoEventoEnum.BUSQUEDA_CAMA_INICIADA,
                TipoEventoEnum.CAMA_ASIGNADA
            ])
        )

        if fecha_inicio:
            query = query.where(EventoPaciente.timestamp >= fecha_inicio)
        if fecha_fin:
            query = query.where(EventoPaciente.timestamp < fecha_fin)

        query = query.order_by(EventoPaciente.paciente_id, EventoPaciente.timestamp)
        eventos = session.exec(query).all()

        # Agrupar por paciente y calcular duraciones
        duraciones = []
        eventos_por_paciente = defaultdict(list)

        for evento in eventos:
            eventos_por_paciente[evento.paciente_id].append(evento)

        for paciente_id, eventos_paciente in eventos_por_paciente.items():
            inicio = None
            for evento in eventos_paciente:
                if evento.tipo_evento == TipoEventoEnum.BUSQUEDA_CAMA_INICIADA:
                    inicio = evento.timestamp
                elif evento.tipo_evento == TipoEventoEnum.CAMA_ASIGNADA and inicio:
                    duracion = (evento.timestamp - inicio).total_seconds()
                    duraciones.append(duracion)
                    inicio = None

        if not duraciones:
            return {"promedio": 0, "maximo": 0, "minimo": 0, "cantidad": 0}

        return {
            "promedio": sum(duraciones) / len(duraciones),
            "maximo": max(duraciones),
            "minimo": min(duraciones),
            "cantidad": len(duraciones)
        }

    @staticmethod
    async def calcular_tiempo_derivacion_pendiente(
        session: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Calcula el tiempo de espera en derivación pendiente.
        Desde DERIVACION_SOLICITADA hasta DERIVACION_ACEPTADA/RECHAZADA.
        """
        query = select(EventoPaciente).where(
            EventoPaciente.tipo_evento.in_([
                TipoEventoEnum.DERIVACION_SOLICITADA,
                TipoEventoEnum.DERIVACION_ACEPTADA,
                TipoEventoEnum.DERIVACION_RECHAZADA
            ])
        )

        if fecha_inicio:
            query = query.where(EventoPaciente.timestamp >= fecha_inicio)
        if fecha_fin:
            query = query.where(EventoPaciente.timestamp < fecha_fin)

        query = query.order_by(EventoPaciente.paciente_id, EventoPaciente.timestamp)
        eventos = session.exec(query).all()

        duraciones = []
        eventos_por_paciente = defaultdict(list)

        for evento in eventos:
            eventos_por_paciente[evento.paciente_id].append(evento)

        for paciente_id, eventos_paciente in eventos_por_paciente.items():
            inicio = None
            for evento in eventos_paciente:
                if evento.tipo_evento == TipoEventoEnum.DERIVACION_SOLICITADA:
                    inicio = evento.timestamp
                elif evento.tipo_evento in [TipoEventoEnum.DERIVACION_ACEPTADA, TipoEventoEnum.DERIVACION_RECHAZADA] and inicio:
                    duracion = (evento.timestamp - inicio).total_seconds()
                    duraciones.append(duracion)
                    inicio = None

        if not duraciones:
            return {"promedio": 0, "maximo": 0, "minimo": 0, "cantidad": 0}

        return {
            "promedio": sum(duraciones) / len(duraciones),
            "maximo": max(duraciones),
            "minimo": min(duraciones),
            "cantidad": len(duraciones)
        }

    @staticmethod
    async def calcular_tiempo_traslado_saliente(
        session: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Tiempo de paciente hospitalizado en espera de cama.
        Desde TRASLADO_INICIADO hasta TRASLADO_COMPLETADO.
        """
        query = select(EventoPaciente).where(
            EventoPaciente.tipo_evento.in_([
                TipoEventoEnum.TRASLADO_INICIADO,
                TipoEventoEnum.TRASLADO_COMPLETADO
            ])
        )

        if fecha_inicio:
            query = query.where(EventoPaciente.timestamp >= fecha_inicio)
        if fecha_fin:
            query = query.where(EventoPaciente.timestamp < fecha_fin)

        query = query.order_by(EventoPaciente.paciente_id, EventoPaciente.timestamp)
        eventos = session.exec(query).all()

        duraciones = []
        eventos_por_paciente = defaultdict(list)

        for evento in eventos:
            eventos_por_paciente[evento.paciente_id].append(evento)

        for paciente_id, eventos_paciente in eventos_por_paciente.items():
            inicio = None
            for evento in eventos_paciente:
                if evento.tipo_evento == TipoEventoEnum.TRASLADO_INICIADO:
                    inicio = evento.timestamp
                elif evento.tipo_evento == TipoEventoEnum.TRASLADO_COMPLETADO and inicio:
                    duracion = (evento.timestamp - inicio).total_seconds()
                    duraciones.append(duracion)
                    inicio = None

        if not duraciones:
            return {"promedio": 0, "maximo": 0, "minimo": 0, "cantidad": 0}

        return {
            "promedio": sum(duraciones) / len(duraciones),
            "maximo": max(duraciones),
            "minimo": min(duraciones),
            "cantidad": len(duraciones)
        }

    @staticmethod
    async def calcular_tiempo_confirmacion_traslado(
        session: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Tiempo en estado "cama en espera" (confirmación de traslado).
        Desde CAMA_EN_ESPERA_INICIO hasta CAMA_EN_ESPERA_FIN.
        """
        query = select(EventoPaciente).where(
            EventoPaciente.tipo_evento.in_([
                TipoEventoEnum.CAMA_EN_ESPERA_INICIO,
                TipoEventoEnum.CAMA_EN_ESPERA_FIN
            ])
        )

        if fecha_inicio:
            query = query.where(EventoPaciente.timestamp >= fecha_inicio)
        if fecha_fin:
            query = query.where(EventoPaciente.timestamp < fecha_fin)

        query = query.order_by(EventoPaciente.paciente_id, EventoPaciente.timestamp)
        eventos = session.exec(query).all()

        duraciones = []
        eventos_por_paciente = defaultdict(list)

        for evento in eventos:
            eventos_por_paciente[evento.paciente_id].append(evento)

        for paciente_id, eventos_paciente in eventos_por_paciente.items():
            inicio = None
            for evento in eventos_paciente:
                if evento.tipo_evento == TipoEventoEnum.CAMA_EN_ESPERA_INICIO:
                    inicio = evento.timestamp
                elif evento.tipo_evento == TipoEventoEnum.CAMA_EN_ESPERA_FIN and inicio:
                    duracion = (evento.timestamp - inicio).total_seconds()
                    duraciones.append(duracion)
                    inicio = None

        if not duraciones:
            return {"promedio": 0, "maximo": 0, "minimo": 0, "cantidad": 0}

        return {
            "promedio": sum(duraciones) / len(duraciones),
            "maximo": max(duraciones),
            "minimo": min(duraciones),
            "cantidad": len(duraciones)
        }

    @staticmethod
    async def calcular_tiempo_alta(
        session: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calcula tiempos relacionados con altas.
        """
        # Alta sugerida (ALTA_SUGERIDA -> ALTA_INICIADA)
        query_sugerida = select(EventoPaciente).where(
            EventoPaciente.tipo_evento.in_([
                TipoEventoEnum.ALTA_SUGERIDA,
                TipoEventoEnum.ALTA_INICIADA
            ])
        )
        if fecha_inicio:
            query_sugerida = query_sugerida.where(EventoPaciente.timestamp >= fecha_inicio)
        if fecha_fin:
            query_sugerida = query_sugerida.where(EventoPaciente.timestamp < fecha_fin)
        query_sugerida = query_sugerida.order_by(EventoPaciente.paciente_id, EventoPaciente.timestamp)
        eventos_sugerida = session.exec(query_sugerida).all()

        duraciones_sugerida = []
        eventos_por_paciente = defaultdict(list)
        for evento in eventos_sugerida:
            eventos_por_paciente[evento.paciente_id].append(evento)

        for paciente_id, eventos_paciente in eventos_por_paciente.items():
            inicio = None
            for evento in eventos_paciente:
                if evento.tipo_evento == TipoEventoEnum.ALTA_SUGERIDA:
                    inicio = evento.timestamp
                elif evento.tipo_evento == TipoEventoEnum.ALTA_INICIADA and inicio:
                    duracion = (evento.timestamp - inicio).total_seconds()
                    duraciones_sugerida.append(duracion)
                    inicio = None

        # Alta completada (ALTA_INICIADA -> ALTA_COMPLETADA)
        query_completada = select(EventoPaciente).where(
            EventoPaciente.tipo_evento.in_([
                TipoEventoEnum.ALTA_INICIADA,
                TipoEventoEnum.ALTA_COMPLETADA
            ])
        )
        if fecha_inicio:
            query_completada = query_completada.where(EventoPaciente.timestamp >= fecha_inicio)
        if fecha_fin:
            query_completada = query_completada.where(EventoPaciente.timestamp < fecha_fin)
        query_completada = query_completada.order_by(EventoPaciente.paciente_id, EventoPaciente.timestamp)
        eventos_completada = session.exec(query_completada).all()

        duraciones_completada = []
        eventos_por_paciente = defaultdict(list)
        for evento in eventos_completada:
            eventos_por_paciente[evento.paciente_id].append(evento)

        for paciente_id, eventos_paciente in eventos_por_paciente.items():
            inicio = None
            for evento in eventos_paciente:
                if evento.tipo_evento == TipoEventoEnum.ALTA_INICIADA:
                    inicio = evento.timestamp
                elif evento.tipo_evento == TipoEventoEnum.ALTA_COMPLETADA and inicio:
                    duracion = (evento.timestamp - inicio).total_seconds()
                    duraciones_completada.append(duracion)
                    inicio = None

        return {
            "alta_sugerida": {
                "promedio": sum(duraciones_sugerida) / len(duraciones_sugerida) if duraciones_sugerida else 0,
                "maximo": max(duraciones_sugerida) if duraciones_sugerida else 0,
                "minimo": min(duraciones_sugerida) if duraciones_sugerida else 0,
                "cantidad": len(duraciones_sugerida)
            },
            "alta_completada": {
                "promedio": sum(duraciones_completada) / len(duraciones_completada) if duraciones_completada else 0,
                "maximo": max(duraciones_completada) if duraciones_completada else 0,
                "minimo": min(duraciones_completada) if duraciones_completada else 0,
                "cantidad": len(duraciones_completada)
            }
        }

    @staticmethod
    async def calcular_tiempo_fallecido(
        session: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Tiempo desde que se marca como fallecido hasta que egresa.
        Desde FALLECIDO_MARCADO hasta FALLECIDO_EGRESADO.
        """
        query = select(EventoPaciente).where(
            EventoPaciente.tipo_evento.in_([
                TipoEventoEnum.FALLECIDO_MARCADO,
                TipoEventoEnum.FALLECIDO_EGRESADO
            ])
        )

        if fecha_inicio:
            query = query.where(EventoPaciente.timestamp >= fecha_inicio)
        if fecha_fin:
            query = query.where(EventoPaciente.timestamp < fecha_fin)

        query = query.order_by(EventoPaciente.paciente_id, EventoPaciente.timestamp)
        eventos = session.exec(query).all()

        duraciones = []
        eventos_por_paciente = defaultdict(list)

        for evento in eventos:
            eventos_por_paciente[evento.paciente_id].append(evento)

        for paciente_id, eventos_paciente in eventos_por_paciente.items():
            inicio = None
            for evento in eventos_paciente:
                if evento.tipo_evento == TipoEventoEnum.FALLECIDO_MARCADO:
                    inicio = evento.timestamp
                elif evento.tipo_evento == TipoEventoEnum.FALLECIDO_EGRESADO and inicio:
                    duracion = (evento.timestamp - inicio).total_seconds()
                    duraciones.append(duracion)
                    inicio = None

        if not duraciones:
            return {"promedio": 0, "maximo": 0, "minimo": 0, "cantidad": 0}

        return {
            "promedio": sum(duraciones) / len(duraciones),
            "maximo": max(duraciones),
            "minimo": min(duraciones),
            "cantidad": len(duraciones)
        }

    @staticmethod
    async def calcular_tiempo_hospitalizacion(
        session: Session,
        hospital_id: Optional[str] = None,
        solo_casos_especiales: Optional[bool] = None,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Calcula tiempo de hospitalización.
        Desde primer ingreso hasta egreso final.
        """
        # Buscar eventos de ingreso y egreso
        query = select(EventoPaciente).where(
            EventoPaciente.tipo_evento.in_([
                TipoEventoEnum.INGRESO_URGENCIA,
                TipoEventoEnum.INGRESO_AMBULATORIO,
                TipoEventoEnum.DERIVACION_ACEPTADA,
                TipoEventoEnum.ALTA_COMPLETADA,
                TipoEventoEnum.FALLECIDO_EGRESADO
            ])
        )

        if hospital_id:
            query = query.where(EventoPaciente.hospital_id == hospital_id)
        if fecha_inicio:
            query = query.where(EventoPaciente.timestamp >= fecha_inicio)
        if fecha_fin:
            query = query.where(EventoPaciente.timestamp < fecha_fin)

        query = query.order_by(EventoPaciente.paciente_id, EventoPaciente.timestamp)
        eventos = session.exec(query).all()

        duraciones = []
        eventos_por_paciente = defaultdict(list)

        for evento in eventos:
            eventos_por_paciente[evento.paciente_id].append(evento)

        for paciente_id, eventos_paciente in eventos_por_paciente.items():
            # Filtrar por casos especiales si se especifica
            if solo_casos_especiales is not None:
                paciente = session.get(Paciente, paciente_id)
                if paciente:
                    tiene_casos_especiales = paciente.tiene_casos_especiales()
                    if solo_casos_especiales and not tiene_casos_especiales:
                        continue
                    if not solo_casos_especiales and tiene_casos_especiales:
                        continue

            primer_ingreso = None
            for evento in eventos_paciente:
                if evento.tipo_evento in [TipoEventoEnum.INGRESO_URGENCIA, TipoEventoEnum.INGRESO_AMBULATORIO, TipoEventoEnum.DERIVACION_ACEPTADA]:
                    if primer_ingreso is None:
                        primer_ingreso = evento.timestamp
                elif evento.tipo_evento in [TipoEventoEnum.ALTA_COMPLETADA, TipoEventoEnum.FALLECIDO_EGRESADO] and primer_ingreso:
                    duracion = (evento.timestamp - primer_ingreso).total_seconds()
                    duraciones.append(duracion)
                    primer_ingreso = None

        if not duraciones:
            return {"promedio": 0, "maximo": 0, "minimo": 0, "cantidad": 0}

        return {
            "promedio": sum(duraciones) / len(duraciones),
            "maximo": max(duraciones),
            "minimo": min(duraciones),
            "cantidad": len(duraciones)
        }

    # ============================================
    # TASAS DE OCUPACIÓN
    # ============================================

    @staticmethod
    async def calcular_tasa_ocupacion_hospital(
        session: Session,
        hospital_id: str
    ) -> Dict[str, float]:
        """
        Calcula la tasa de ocupación de un hospital.
        """
        # Obtener todas las camas del hospital
        statement = (
            select(Cama)
            .join(Sala)
            .join(Servicio)
            .where(Servicio.hospital_id == hospital_id)
        )
        camas = session.exec(statement).all()

        total_camas = len(camas)
        if total_camas == 0:
            return {"tasa_ocupacion": 0, "camas_ocupadas": 0, "camas_totales": 0}

        camas_ocupadas = sum(1 for cama in camas if cama.esta_ocupada)
        tasa = (camas_ocupadas / total_camas) * 100

        return {
            "tasa_ocupacion": round(tasa, 2),
            "camas_ocupadas": camas_ocupadas,
            "camas_totales": total_camas
        }

    @staticmethod
    async def calcular_tasa_ocupacion_servicio(
        session: Session,
        servicio_id: str
    ) -> Dict[str, float]:
        """
        Calcula la tasa de ocupación de un servicio.
        """
        statement = select(Cama).join(Sala).where(Sala.servicio_id == servicio_id)
        camas = session.exec(statement).all()

        total_camas = len(camas)
        if total_camas == 0:
            return {"tasa_ocupacion": 0, "camas_ocupadas": 0, "camas_totales": 0}

        camas_ocupadas = sum(1 for cama in camas if cama.esta_ocupada)
        tasa = (camas_ocupadas / total_camas) * 100

        return {
            "tasa_ocupacion": round(tasa, 2),
            "camas_ocupadas": camas_ocupadas,
            "camas_totales": total_camas
        }

    @staticmethod
    async def calcular_tasa_ocupacion_red(
        session: Session
    ) -> Dict[str, float]:
        """
        Calcula la tasa de ocupación de toda la red.
        """
        statement = select(Cama)
        camas = session.exec(statement).all()

        total_camas = len(camas)
        if total_camas == 0:
            return {"tasa_ocupacion": 0, "camas_ocupadas": 0, "camas_totales": 0}

        camas_ocupadas = sum(1 for cama in camas if cama.esta_ocupada)
        tasa = (camas_ocupadas / total_camas) * 100

        return {
            "tasa_ocupacion": round(tasa, 2),
            "camas_ocupadas": camas_ocupadas,
            "camas_totales": total_camas
        }

    # ============================================
    # FLUJOS Y DEMANDA
    # ============================================

    @staticmethod
    async def calcular_flujos_mas_repetidos(
        session: Session,
        fecha_inicio: datetime,
        fecha_fin: datetime,
        limite: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Determina los flujos más repetidos (traslados y derivaciones).
        """
        # Traslados internos
        query_traslados = select(EventoPaciente).where(
            and_(
                EventoPaciente.tipo_evento == TipoEventoEnum.TRASLADO_COMPLETADO,
                EventoPaciente.timestamp >= fecha_inicio,
                EventoPaciente.timestamp < fecha_fin
            )
        )
        eventos_traslados = session.exec(query_traslados).all()

        # Contar flujos
        flujos = defaultdict(int)

        for evento in eventos_traslados:
            if evento.servicio_origen_id and evento.servicio_destino_id:
                servicio_origen = session.get(Servicio, evento.servicio_origen_id)
                servicio_destino = session.get(Servicio, evento.servicio_destino_id)

                if servicio_origen and servicio_destino:
                    flujo = f"{servicio_origen.nombre} -> {servicio_destino.nombre}"
                    flujos[flujo] += 1

        # Derivaciones
        query_derivaciones = select(EventoPaciente).where(
            and_(
                EventoPaciente.tipo_evento == TipoEventoEnum.DERIVACION_COMPLETADA,
                EventoPaciente.timestamp >= fecha_inicio,
                EventoPaciente.timestamp < fecha_fin
            )
        )
        eventos_derivaciones = session.exec(query_derivaciones).all()

        for evento in eventos_derivaciones:
            if evento.hospital_destino_id:
                metadata = evento.get_metadata()
                hospital_origen_id = metadata.get("hospital_origen")
                if hospital_origen_id:
                    hospital_origen = session.get(Hospital, hospital_origen_id)
                    hospital_destino = session.get(Hospital, evento.hospital_destino_id)

                    if hospital_origen and hospital_destino:
                        flujo = f"{hospital_origen.nombre} -> {hospital_destino.nombre} (Derivación)"
                        flujos[flujo] += 1

        # Ordenar por frecuencia
        flujos_ordenados = sorted(flujos.items(), key=lambda x: x[1], reverse=True)[:limite]

        return [
            {"flujo": flujo, "cantidad": cantidad}
            for flujo, cantidad in flujos_ordenados
        ]

    @staticmethod
    async def calcular_servicios_mayor_demanda(
        session: Session
    ) -> List[Dict[str, Any]]:
        """
        Determina servicios con mayor demanda.
        Basado en tasa de ocupación y pacientes en espera compatibles.
        """
        servicios = session.exec(select(Servicio)).all()

        resultados = []
        for servicio in servicios:
            # Calcular tasa de ocupación
            tasa_ocupacion = await EstadisticasService.calcular_tasa_ocupacion_servicio(
                session, servicio.id
            )

            # Contar pacientes en espera compatibles con el servicio
            # (esto requeriría lógica de compatibilidad más compleja)
            pacientes_espera = session.exec(
                select(Paciente).where(
                    and_(
                        Paciente.en_lista_espera == True,
                        Paciente.hospital_id == servicio.hospital_id
                    )
                )
            ).all()

            resultados.append({
                "servicio_id": servicio.id,
                "servicio_nombre": servicio.nombre,
                "hospital_id": servicio.hospital_id,
                "tasa_ocupacion": tasa_ocupacion["tasa_ocupacion"],
                "pacientes_en_espera": len(pacientes_espera),
                "demanda_score": tasa_ocupacion["tasa_ocupacion"] + (len(pacientes_espera) * 10)
            })

        # Ordenar por demanda
        resultados.sort(key=lambda x: x["demanda_score"], reverse=True)

        return resultados

    # ============================================
    # CASOS ESPECIALES
    # ============================================

    @staticmethod
    async def calcular_casos_especiales(
        session: Session,
        hospital_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Cuenta pacientes con casos especiales.
        """
        query = select(Paciente).where(Paciente.casos_especiales.isnot(None))

        if hospital_id:
            query = query.where(Paciente.hospital_id == hospital_id)

        pacientes = session.exec(query).all()

        # Contar por tipo
        total = 0
        cardiocirugia = 0
        caso_social = 0
        caso_socio_judicial = 0

        for paciente in pacientes:
            casos = paciente.get_requerimientos_lista("casos_especiales")
            if casos:
                total += 1
                if "cardiocirugía" in casos or "Cardiocirugía" in casos:
                    cardiocirugia += 1
                if "caso social" in casos or "Caso social" in casos:
                    caso_social += 1
                if "caso socio-judicial" in casos or "Caso socio-judicial" in casos:
                    caso_socio_judicial += 1

        return {
            "total": total,
            "cardiocirugia": cardiocirugia,
            "caso_social": caso_social,
            "caso_socio_judicial": caso_socio_judicial
        }

    # ============================================
    # SUBUTILIZACIÓN
    # ============================================

    @staticmethod
    async def calcular_camas_subutilizadas(
        session: Session,
        hospital_id: Optional[str] = None,
        dias: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Identifica camas que se mantienen libres por más tiempo.
        """
        fecha_limite = datetime.utcnow() - timedelta(days=dias)

        query = select(Cama).where(
            and_(
                Cama.estado == EstadoCamaEnum.LIBRE,
                Cama.estado_updated_at <= fecha_limite
            )
        )

        if hospital_id:
            query = query.join(Sala).join(Servicio).where(Servicio.hospital_id == hospital_id)

        camas = session.exec(query).all()

        resultados = []
        for cama in camas:
            tiempo_libre = (datetime.utcnow() - cama.estado_updated_at).total_seconds() / 3600  # horas

            sala = session.get(Sala, cama.sala_id) if cama.sala_id else None
            servicio = session.get(Servicio, sala.servicio_id) if sala and sala.servicio_id else None

            resultados.append({
                "cama_id": cama.id,
                "identificador": cama.identificador,
                "servicio_nombre": servicio.nombre if servicio else "N/A",
                "tiempo_libre_horas": round(tiempo_libre, 2)
            })

        # Ordenar por tiempo libre
        resultados.sort(key=lambda x: x["tiempo_libre_horas"], reverse=True)

        return resultados

    @staticmethod
    async def calcular_servicios_subutilizados(
        session: Session,
        hospital_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Identifica servicios con mayor tasa de camas libres al final del día clínico.
        """
        servicios_query = select(Servicio)
        if hospital_id:
            servicios_query = servicios_query.where(Servicio.hospital_id == hospital_id)

        servicios = session.exec(servicios_query).all()

        resultados = []
        for servicio in servicios:
            tasa = await EstadisticasService.calcular_tasa_ocupacion_servicio(session, servicio.id)

            if tasa["camas_totales"] > 0:
                tasa_libre = 100 - tasa["tasa_ocupacion"]
                camas_libres = tasa["camas_totales"] - tasa["camas_ocupadas"]

                resultados.append({
                    "servicio_id": servicio.id,
                    "servicio_nombre": servicio.nombre,
                    "hospital_id": servicio.hospital_id,
                    "tasa_libre": round(tasa_libre, 2),
                    "camas_libres": camas_libres,
                    "camas_totales": tasa["camas_totales"]
                })

        # Ordenar por tasa libre
        resultados.sort(key=lambda x: x["tasa_libre"], reverse=True)

        return resultados

    # ============================================
    # TRAZABILIDAD
    # ============================================

    @staticmethod
    async def obtener_trazabilidad_paciente(
        session: Session,
        paciente_id: str
    ) -> List[Dict[str, Any]]:
        """
        Obtiene la trazabilidad completa de un paciente.
        Muestra todos los servicios por donde ha pasado con tiempos.
        """
        # Obtener todos los eventos del paciente ordenados cronológicamente
        query = select(EventoPaciente).where(
            EventoPaciente.paciente_id == paciente_id
        ).order_by(EventoPaciente.timestamp)

        eventos = session.exec(query).all()

        trazabilidad = []
        servicio_actual = None
        entrada_servicio = None

        for evento in eventos:
            # Detectar entrada a un servicio
            if evento.tipo_evento in [TipoEventoEnum.CAMA_ASIGNADA, TipoEventoEnum.TRASLADO_COMPLETADO, TipoEventoEnum.DERIVACION_COMPLETADA]:
                if evento.servicio_destino_id:
                    # Si había un servicio previo, cerrar su registro
                    if servicio_actual and entrada_servicio:
                        servicio = session.get(Servicio, servicio_actual)
                        duracion = (evento.timestamp - entrada_servicio).total_seconds()
                        dias = int(duracion // 86400)
                        horas = int((duracion % 86400) // 3600)

                        trazabilidad.append({
                            "servicio_nombre": servicio.nombre if servicio else "Desconocido",
                            "entrada": entrada_servicio.isoformat(),
                            "salida": evento.timestamp.isoformat(),
                            "duracion_dias": dias,
                            "duracion_horas": horas,
                            "duracion_total_segundos": int(duracion)
                        })

                    # Iniciar nuevo servicio
                    servicio_actual = evento.servicio_destino_id
                    entrada_servicio = evento.timestamp

        # Cerrar el servicio actual si existe
        if servicio_actual and entrada_servicio:
            servicio = session.get(Servicio, servicio_actual)
            duracion = (datetime.utcnow() - entrada_servicio).total_seconds()
            dias = int(duracion // 86400)
            horas = int((duracion % 86400) // 3600)

            trazabilidad.append({
                "servicio_nombre": servicio.nombre if servicio else "Desconocido",
                "entrada": entrada_servicio.isoformat(),
                "salida": "Actual",
                "duracion_dias": dias,
                "duracion_horas": horas,
                "duracion_total_segundos": int(duracion)
            })

        return trazabilidad
