"""
Endpoints de Estadísticas.
"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import List

from app.core.database import get_session
from app.models.hospital import Hospital
from app.models.cama import Cama
from app.models.paciente import Paciente
from app.models.sala import Sala
from app.models.servicio import Servicio
from app.models.enums import EstadoCamaEnum, ESTADOS_CAMA_OCUPADA
from app.schemas.responses import EstadisticasHospitalResponse, EstadisticasGlobalesResponse
from app.schemas.paciente import ListaEsperaResponse, PacienteListaEsperaResponse
from app.repositories.hospital_repo import HospitalRepository
from app.repositories.paciente_repo import PacienteRepository
from app.services.prioridad_service import gestor_colas_global, PrioridadService
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
