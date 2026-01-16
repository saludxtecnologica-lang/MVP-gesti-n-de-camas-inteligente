"""
Endpoints de Estadísticas.
"""
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_session
from app.models.hospital import Hospital
from app.models.cama import Cama
from app.models.paciente import Paciente
from app.models.sala import Sala
from app.models.servicio import Servicio
from app.models.enums import EstadoCamaEnum, ESTADOS_CAMA_OCUPADA
from app.schemas.responses import (
    EstadisticasHospitalResponse,
    EstadisticasGlobalesResponse,
    EstadisticasCompletasResponse,
    TiempoEstadisticaResponse,
    TasaOcupacionResponse,
    TrazabilidadServicioResponse,
)
from app.schemas.paciente import ListaEsperaResponse, PacienteListaEsperaResponse
from app.repositories.hospital_repo import HospitalRepository
from app.repositories.paciente_repo import PacienteRepository
from app.services.prioridad_service import gestor_colas_global, PrioridadService
from app.services.estadisticas_service import EstadisticasService
from app.utils.helpers import calcular_estadisticas_camas

router = APIRouter()


@router.get("", response_model=EstadisticasGlobalesResponse)
def obtener_estadisticas_globales(session: Session = Depends(get_session)):
    """Obtiene estadísticas globales del sistema."""
    hospital_repo = HospitalRepository(session)
    hospitales = hospital_repo.obtener_todos()
    
    estadisticas_hospitales = []
    total_camas = 0
    total_ocupadas = 0
    total_pacientes = 0
    
    for hospital in hospitales:
        camas = hospital_repo.obtener_camas_hospital(hospital.id)
        stats = calcular_estadisticas_camas(camas)
        
        cola = gestor_colas_global.obtener_cola(hospital.id)
        pacientes_espera = cola.tamano()
        
        # Contar derivados pendientes
        query_derivados = select(Paciente).where(
            Paciente.derivacion_hospital_destino_id == hospital.id,
            Paciente.derivacion_estado == "pendiente"
        )
        derivados = len(session.exec(query_derivados).all())
        
        ocupacion = (stats["ocupadas"] / stats["total"] * 100) if stats["total"] > 0 else 0
        
        estadisticas_hospitales.append(EstadisticasHospitalResponse(
            hospital_id=hospital.id,
            hospital_nombre=hospital.nombre,
            total_camas=stats["total"],
            camas_libres=stats["libres"],
            camas_ocupadas=stats["ocupadas"],
            camas_traslado=stats["traslado_entrante"],
            camas_limpieza=stats["en_limpieza"],
            camas_bloqueadas=stats["bloqueadas"],
            pacientes_en_espera=pacientes_espera,
            pacientes_derivados_pendientes=derivados,
            ocupacion_porcentaje=round(ocupacion, 1)
        ))
        
        total_camas += stats["total"]
        total_ocupadas += stats["ocupadas"]
        total_pacientes += pacientes_espera
    
    ocupacion_promedio = (total_ocupadas / total_camas * 100) if total_camas > 0 else 0
    
    return EstadisticasGlobalesResponse(
        hospitales=estadisticas_hospitales,
        total_camas_sistema=total_camas,
        total_pacientes_sistema=total_pacientes,
        ocupacion_promedio=round(ocupacion_promedio, 1)
    )


@router.get("/hospital/{hospital_id}", response_model=EstadisticasHospitalResponse)
def obtener_estadisticas_hospital(
    hospital_id: str,
    session: Session = Depends(get_session)
):
    """Obtiene estadísticas de un hospital específico."""
    hospital_repo = HospitalRepository(session)
    hospital = hospital_repo.obtener_por_id(hospital_id)
    
    if not hospital:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Hospital no encontrado")
    
    camas = hospital_repo.obtener_camas_hospital(hospital_id)
    stats = calcular_estadisticas_camas(camas)
    
    cola = gestor_colas_global.obtener_cola(hospital_id)
    
    query_derivados = select(Paciente).where(
        Paciente.derivacion_hospital_destino_id == hospital_id,
        Paciente.derivacion_estado == "pendiente"
    )
    derivados = len(session.exec(query_derivados).all())
    
    ocupacion = (stats["ocupadas"] / stats["total"] * 100) if stats["total"] > 0 else 0
    
    return EstadisticasHospitalResponse(
        hospital_id=hospital.id,
        hospital_nombre=hospital.nombre,
        total_camas=stats["total"],
        camas_libres=stats["libres"],
        camas_ocupadas=stats["ocupadas"],
        camas_traslado=stats["traslado_entrante"],
        camas_limpieza=stats["en_limpieza"],
        camas_bloqueadas=stats["bloqueadas"],
        pacientes_en_espera=cola.tamano(),
        pacientes_derivados_pendientes=derivados,
        ocupacion_porcentaje=round(ocupacion, 1)
    )


@router.get("/lista-espera/{hospital_id}", response_model=ListaEsperaResponse)
def obtener_lista_espera(
    hospital_id: str,
    session: Session = Depends(get_session)
):
    """Obtiene la lista de espera de un hospital."""
    prioridad_service = PrioridadService(session)
    paciente_repo = PacienteRepository(session)
    hospital_repo = HospitalRepository(session)
    
    lista = prioridad_service.obtener_lista_ordenada(hospital_id)
    
    pacientes_response = []
    for paciente, prioridad, posicion in lista:
        # Determinar origen
        origen_tipo = None
        origen_hospital_nombre = None
        origen_hospital_codigo = None
        origen_servicio_nombre = None
        origen_cama_identificador = None
        
        if paciente.derivacion_estado == "aceptada":
            origen_tipo = "derivado"
            hospital_origen = hospital_repo.obtener_por_id(paciente.hospital_id)
            if hospital_origen:
                origen_hospital_nombre = hospital_origen.nombre
                origen_hospital_codigo = hospital_origen.codigo
        elif paciente.cama_id:
            origen_tipo = "hospitalizado"
            from app.repositories.cama_repo import CamaRepository
            cama_repo = CamaRepository(session)
            cama = cama_repo.obtener_por_id(paciente.cama_id)
            if cama:
                origen_cama_identificador = cama.identificador
                if cama.sala and cama.sala.servicio:
                    origen_servicio_nombre = cama.sala.servicio.nombre
        else:
            origen_tipo = paciente.tipo_paciente.value
        
        # Determinar servicio destino
        from app.models.enums import MAPEO_COMPLEJIDAD_SERVICIO
        servicios_destino = MAPEO_COMPLEJIDAD_SERVICIO.get(paciente.complejidad_requerida, [])
        servicio_destino = servicios_destino[0].value if servicios_destino else None
        
        pacientes_response.append(PacienteListaEsperaResponse(
            paciente_id=paciente.id,
            nombre=paciente.nombre,
            run=paciente.run,
            prioridad=prioridad,
            posicion=posicion,
            tiempo_espera_min=paciente.tiempo_espera_min,
            estado_lista=paciente.estado_lista_espera.value,
            tipo_paciente=paciente.tipo_paciente.value,
            complejidad=paciente.complejidad_requerida.value,
            sexo=paciente.sexo.value,
            edad=paciente.edad,
            tipo_enfermedad=paciente.tipo_enfermedad.value,
            tipo_aislamiento=paciente.tipo_aislamiento.value,
            tiene_cama_actual=paciente.cama_id is not None,
            cama_actual_id=paciente.cama_id,
            timestamp=paciente.timestamp_lista_espera.isoformat() if paciente.timestamp_lista_espera else "",
            origen_tipo=origen_tipo,
            origen_hospital_nombre=origen_hospital_nombre,
            origen_hospital_codigo=origen_hospital_codigo,
            origen_servicio_nombre=origen_servicio_nombre,
            origen_cama_identificador=origen_cama_identificador,
            servicio_destino=servicio_destino
        ))
    
    return ListaEsperaResponse(
        hospital_id=hospital_id,
        total_pacientes=len(pacientes_response),
        pacientes=pacientes_response
    )


# ============================================
# NUEVOS ENDPOINTS PARA ESTADÍSTICAS AVANZADAS
# ============================================

@router.get("/avanzadas/completas", response_model=EstadisticasCompletasResponse)
async def obtener_estadisticas_completas(
    dias: int = Query(7, description="Días hacia atrás para calcular estadísticas"),
    session: Session = Depends(get_session)
):
    """
    Obtiene todas las estadísticas avanzadas del sistema.
    Incluye ingresos, egresos, tiempos, ocupación, flujos, demanda, etc.
    """
    fecha_fin = datetime.utcnow()
    fecha_inicio = fecha_fin - timedelta(days=dias)

    # Ingresos y Egresos
    ingresos_red = await EstadisticasService.calcular_ingresos_red(session, fecha_inicio, fecha_fin)
    egresos_red = await EstadisticasService.calcular_egresos_red(session, fecha_inicio, fecha_fin)

    # Tiempos
    tiempo_espera_cama = await EstadisticasService.calcular_tiempo_espera_cama(session, fecha_inicio, fecha_fin)
    tiempo_derivacion = await EstadisticasService.calcular_tiempo_derivacion_pendiente(session, fecha_inicio, fecha_fin)
    tiempo_traslado = await EstadisticasService.calcular_tiempo_traslado_saliente(session, fecha_inicio, fecha_fin)
    tiempo_confirmacion = await EstadisticasService.calcular_tiempo_confirmacion_traslado(session, fecha_inicio, fecha_fin)
    tiempo_alta = await EstadisticasService.calcular_tiempo_alta(session, fecha_inicio, fecha_fin)
    tiempo_fallecido = await EstadisticasService.calcular_tiempo_fallecido(session, fecha_inicio, fecha_fin)
    tiempo_hosp_red = await EstadisticasService.calcular_tiempo_hospitalizacion(session, None, None, fecha_inicio, fecha_fin)

    # Tasas de Ocupación
    tasa_red = await EstadisticasService.calcular_tasa_ocupacion_red(session)

    # Flujos y Demanda
    flujos = await EstadisticasService.calcular_flujos_mas_repetidos(session, fecha_inicio, fecha_fin)
    demanda = await EstadisticasService.calcular_servicios_mayor_demanda(session)

    # Casos Especiales
    casos = await EstadisticasService.calcular_casos_especiales(session)

    # Subutilización
    camas_sub = await EstadisticasService.calcular_camas_subutilizadas(session)
    servicios_sub = await EstadisticasService.calcular_servicios_subutilizados(session)

    return EstadisticasCompletasResponse(
        ingresos_red=ingresos_red,
        egresos_red=egresos_red,
        tiempo_espera_cama=tiempo_espera_cama,
        tiempo_derivacion_pendiente=tiempo_derivacion,
        tiempo_traslado_saliente=tiempo_traslado,
        tiempo_confirmacion_traslado=tiempo_confirmacion,
        tiempo_alta=tiempo_alta,
        tiempo_fallecido=tiempo_fallecido,
        tiempo_hospitalizacion_red=tiempo_hosp_red,
        tasa_ocupacion_red=tasa_red,
        flujos_mas_repetidos=flujos,
        servicios_mayor_demanda=demanda,
        casos_especiales=casos,
        camas_subutilizadas=camas_sub,
        servicios_subutilizados=servicios_sub
    )


@router.get("/ingresos/red")
async def obtener_ingresos_red(
    dias: int = Query(1, description="Días hacia atrás"),
    session: Session = Depends(get_session)
):
    """Obtiene los ingresos totales de la red."""
    fecha_fin = datetime.utcnow()
    fecha_inicio = fecha_fin - timedelta(days=dias)
    return await EstadisticasService.calcular_ingresos_red(session, fecha_inicio, fecha_fin)


@router.get("/ingresos/hospital/{hospital_id}")
async def obtener_ingresos_hospital(
    hospital_id: str,
    dias: int = Query(1, description="Días hacia atrás"),
    session: Session = Depends(get_session)
):
    """Obtiene los ingresos de un hospital específico."""
    fecha_fin = datetime.utcnow()
    fecha_inicio = fecha_fin - timedelta(days=dias)
    return await EstadisticasService.calcular_ingresos_hospital(session, hospital_id, fecha_inicio, fecha_fin)


@router.get("/ingresos/servicio/{servicio_id}")
async def obtener_ingresos_servicio(
    servicio_id: str,
    dias: int = Query(1, description="Días hacia atrás"),
    session: Session = Depends(get_session)
):
    """Obtiene los ingresos de un servicio específico."""
    fecha_fin = datetime.utcnow()
    fecha_inicio = fecha_fin - timedelta(days=dias)
    return await EstadisticasService.calcular_ingresos_servicio(session, servicio_id, fecha_inicio, fecha_fin)


@router.get("/egresos/red")
async def obtener_egresos_red(
    dias: int = Query(1, description="Días hacia atrás"),
    session: Session = Depends(get_session)
):
    """Obtiene los egresos totales de la red."""
    fecha_fin = datetime.utcnow()
    fecha_inicio = fecha_fin - timedelta(days=dias)
    return await EstadisticasService.calcular_egresos_red(session, fecha_inicio, fecha_fin)


@router.get("/egresos/hospital/{hospital_id}")
async def obtener_egresos_hospital(
    hospital_id: str,
    dias: int = Query(1, description="Días hacia atrás"),
    session: Session = Depends(get_session)
):
    """Obtiene los egresos de un hospital específico."""
    fecha_fin = datetime.utcnow()
    fecha_inicio = fecha_fin - timedelta(days=dias)
    return await EstadisticasService.calcular_egresos_hospital(session, hospital_id, fecha_inicio, fecha_fin)


@router.get("/egresos/servicio/{servicio_id}")
async def obtener_egresos_servicio(
    servicio_id: str,
    dias: int = Query(1, description="Días hacia atrás"),
    session: Session = Depends(get_session)
):
    """Obtiene los egresos de un servicio específico."""
    fecha_fin = datetime.utcnow()
    fecha_inicio = fecha_fin - timedelta(days=dias)
    return await EstadisticasService.calcular_egresos_servicio(session, servicio_id, fecha_inicio, fecha_fin)


@router.get("/tiempos/espera-cama", response_model=TiempoEstadisticaResponse)
async def obtener_tiempo_espera_cama(
    dias: int = Query(7, description="Días hacia atrás"),
    session: Session = Depends(get_session)
):
    """Obtiene estadísticas de tiempo de espera de cama."""
    fecha_fin = datetime.utcnow()
    fecha_inicio = fecha_fin - timedelta(days=dias)
    return await EstadisticasService.calcular_tiempo_espera_cama(session, fecha_inicio, fecha_fin)


@router.get("/tiempos/derivacion-pendiente", response_model=TiempoEstadisticaResponse)
async def obtener_tiempo_derivacion_pendiente(
    dias: int = Query(7, description="Días hacia atrás"),
    session: Session = Depends(get_session)
):
    """Obtiene estadísticas de tiempo en espera de respuesta de derivación."""
    fecha_fin = datetime.utcnow()
    fecha_inicio = fecha_fin - timedelta(days=dias)
    return await EstadisticasService.calcular_tiempo_derivacion_pendiente(session, fecha_inicio, fecha_fin)


@router.get("/tiempos/traslado-saliente", response_model=TiempoEstadisticaResponse)
async def obtener_tiempo_traslado_saliente(
    dias: int = Query(7, description="Días hacia atrás"),
    session: Session = Depends(get_session)
):
    """Obtiene estadísticas de tiempo de paciente hospitalizado en espera de cama."""
    fecha_fin = datetime.utcnow()
    fecha_inicio = fecha_fin - timedelta(days=dias)
    return await EstadisticasService.calcular_tiempo_traslado_saliente(session, fecha_inicio, fecha_fin)


@router.get("/tiempos/confirmacion-traslado", response_model=TiempoEstadisticaResponse)
async def obtener_tiempo_confirmacion_traslado(
    dias: int = Query(7, description="Días hacia atrás"),
    session: Session = Depends(get_session)
):
    """Obtiene estadísticas de tiempo de confirmación de traslado (cama en espera)."""
    fecha_fin = datetime.utcnow()
    fecha_inicio = fecha_fin - timedelta(days=dias)
    return await EstadisticasService.calcular_tiempo_confirmacion_traslado(session, fecha_inicio, fecha_fin)


@router.get("/tiempos/alta")
async def obtener_tiempos_alta(
    dias: int = Query(7, description="Días hacia atrás"),
    session: Session = Depends(get_session)
):
    """Obtiene estadísticas de tiempos de alta (sugerida y completada)."""
    fecha_fin = datetime.utcnow()
    fecha_inicio = fecha_fin - timedelta(days=dias)
    return await EstadisticasService.calcular_tiempo_alta(session, fecha_inicio, fecha_fin)


@router.get("/tiempos/fallecido", response_model=TiempoEstadisticaResponse)
async def obtener_tiempo_fallecido(
    dias: int = Query(7, description="Días hacia atrás"),
    session: Session = Depends(get_session)
):
    """Obtiene estadísticas de tiempo de egreso de fallecido."""
    fecha_fin = datetime.utcnow()
    fecha_inicio = fecha_fin - timedelta(days=dias)
    return await EstadisticasService.calcular_tiempo_fallecido(session, fecha_inicio, fecha_fin)


@router.get("/tiempos/hospitalizacion", response_model=TiempoEstadisticaResponse)
async def obtener_tiempo_hospitalizacion(
    hospital_id: Optional[str] = Query(None, description="ID del hospital (None para toda la red)"),
    solo_casos_especiales: Optional[bool] = Query(None, description="True para solo casos especiales, False para sin casos especiales, None para todos"),
    dias: int = Query(30, description="Días hacia atrás"),
    session: Session = Depends(get_session)
):
    """Obtiene estadísticas de tiempo de hospitalización."""
    fecha_fin = datetime.utcnow()
    fecha_inicio = fecha_fin - timedelta(days=dias)
    return await EstadisticasService.calcular_tiempo_hospitalizacion(
        session, hospital_id, solo_casos_especiales, fecha_inicio, fecha_fin
    )


@router.get("/ocupacion/red", response_model=TasaOcupacionResponse)
async def obtener_tasa_ocupacion_red(session: Session = Depends(get_session)):
    """Obtiene la tasa de ocupación de toda la red."""
    return await EstadisticasService.calcular_tasa_ocupacion_red(session)


@router.get("/ocupacion/hospital/{hospital_id}", response_model=TasaOcupacionResponse)
async def obtener_tasa_ocupacion_hospital(
    hospital_id: str,
    session: Session = Depends(get_session)
):
    """Obtiene la tasa de ocupación de un hospital."""
    return await EstadisticasService.calcular_tasa_ocupacion_hospital(session, hospital_id)


@router.get("/ocupacion/servicio/{servicio_id}", response_model=TasaOcupacionResponse)
async def obtener_tasa_ocupacion_servicio(
    servicio_id: str,
    session: Session = Depends(get_session)
):
    """Obtiene la tasa de ocupación de un servicio."""
    return await EstadisticasService.calcular_tasa_ocupacion_servicio(session, servicio_id)


@router.get("/flujos/mas-repetidos")
async def obtener_flujos_mas_repetidos(
    dias: int = Query(30, description="Días hacia atrás"),
    limite: int = Query(10, description="Número de flujos a retornar"),
    session: Session = Depends(get_session)
):
    """Obtiene los flujos (traslados y derivaciones) más repetidos."""
    fecha_fin = datetime.utcnow()
    fecha_inicio = fecha_fin - timedelta(days=dias)
    return await EstadisticasService.calcular_flujos_mas_repetidos(session, fecha_inicio, fecha_fin, limite)


@router.get("/demanda/servicios")
async def obtener_servicios_mayor_demanda(session: Session = Depends(get_session)):
    """Obtiene los servicios con mayor demanda."""
    return await EstadisticasService.calcular_servicios_mayor_demanda(session)


@router.get("/casos-especiales")
async def obtener_casos_especiales(
    hospital_id: Optional[str] = Query(None, description="ID del hospital (None para todos)"),
    session: Session = Depends(get_session)
):
    """Obtiene estadísticas de casos especiales."""
    return await EstadisticasService.calcular_casos_especiales(session, hospital_id)


@router.get("/subutilizacion/camas")
async def obtener_camas_subutilizadas(
    hospital_id: Optional[str] = Query(None, description="ID del hospital (None para todos)"),
    dias: int = Query(1, description="Días mínimos libre"),
    session: Session = Depends(get_session)
):
    """Obtiene las camas subutilizadas."""
    return await EstadisticasService.calcular_camas_subutilizadas(session, hospital_id, dias)


@router.get("/subutilizacion/servicios")
async def obtener_servicios_subutilizados(
    hospital_id: Optional[str] = Query(None, description="ID del hospital (None para todos)"),
    session: Session = Depends(get_session)
):
    """Obtiene los servicios subutilizados."""
    return await EstadisticasService.calcular_servicios_subutilizados(session, hospital_id)


@router.get("/trazabilidad/paciente/{paciente_id}", response_model=List[TrazabilidadServicioResponse])
async def obtener_trazabilidad_paciente(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """Obtiene la trazabilidad completa de un paciente."""
    return await EstadisticasService.obtener_trazabilidad_paciente(session, paciente_id)
