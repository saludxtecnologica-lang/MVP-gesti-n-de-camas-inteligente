"""
Endpoints de Hospitales.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from datetime import datetime, timezone

from app.core.database import get_session
from app.models.hospital import Hospital
from app.models.servicio import Servicio
from app.models.sala import Sala
from app.models.cama import Cama
from app.models.paciente import Paciente
from app.models.enums import EstadoCamaEnum, TipoPacienteEnum
from app.schemas.hospital import HospitalResponse, ServicioResponse
from app.schemas.cama import CamaResponse
from app.repositories.hospital_repo import HospitalRepository
from app.repositories.cama_repo import CamaRepository
from app.services.prioridad_service import gestor_colas_global
from app.utils.helpers import calcular_estadisticas_camas, crear_paciente_response

router = APIRouter()


@router.get("", response_model=List[HospitalResponse])
def obtener_hospitales(session: Session = Depends(get_session)):
    """Obtiene todos los hospitales con estadísticas."""
    repo = HospitalRepository(session)
    hospitales = repo.obtener_todos()
    resultado = []
    
    for hospital in hospitales:
        camas = repo.obtener_camas_hospital(hospital.id)
        stats = calcular_estadisticas_camas(camas)
        
        # Contar pacientes en espera
        cola = gestor_colas_global.obtener_cola(hospital.id)
        pacientes_espera = cola.tamano()
        
        # Contar derivados pendientes
        query_derivados = select(Paciente).where(
            Paciente.derivacion_hospital_destino_id == hospital.id,
            Paciente.derivacion_estado == "pendiente"
        )
        derivados = len(session.exec(query_derivados).all())
        
        resultado.append(HospitalResponse(
            id=hospital.id,
            nombre=hospital.nombre,
            codigo=hospital.codigo,
            es_central=hospital.es_central,
            total_camas=stats["total"],
            camas_libres=stats["libres"],
            camas_ocupadas=stats["ocupadas"],
            pacientes_en_espera=pacientes_espera,
            pacientes_derivados=derivados
        ))
    
    return resultado


@router.get("/{hospital_id}", response_model=HospitalResponse)
def obtener_hospital(hospital_id: str, session: Session = Depends(get_session)):
    """Obtiene un hospital específico."""
    repo = HospitalRepository(session)
    hospital = repo.obtener_por_id(hospital_id)
    
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital no encontrado")
    
    camas = repo.obtener_camas_hospital(hospital.id)
    stats = calcular_estadisticas_camas(camas)
    cola = gestor_colas_global.obtener_cola(hospital.id)
    
    return HospitalResponse(
        id=hospital.id,
        nombre=hospital.nombre,
        codigo=hospital.codigo,
        es_central=hospital.es_central,
        total_camas=stats["total"],
        camas_libres=stats["libres"],
        camas_ocupadas=stats["ocupadas"],
        pacientes_en_espera=cola.tamano(),
        pacientes_derivados=0
    )


@router.get("/{hospital_id}/servicios", response_model=List[ServicioResponse])
def obtener_servicios(hospital_id: str, session: Session = Depends(get_session)):
    """Obtiene los servicios de un hospital."""
    repo = HospitalRepository(session)
    cama_repo = CamaRepository(session)
    
    servicios = repo.obtener_servicios_hospital(hospital_id)
    resultado = []
    
    for servicio in servicios:
        camas = cama_repo.obtener_por_servicio(servicio.id)
        camas_libres = len([c for c in camas if c.estado == EstadoCamaEnum.LIBRE])
        
        resultado.append(ServicioResponse(
            id=servicio.id,
            nombre=servicio.nombre,
            codigo=servicio.codigo,
            tipo=servicio.tipo,
            hospital_id=servicio.hospital_id,
            total_camas=len(camas),
            camas_libres=camas_libres
        ))
    
    return resultado


@router.get("/{hospital_id}/camas", response_model=List[CamaResponse])
def obtener_camas_hospital(hospital_id: str, session: Session = Depends(get_session)):
    """Obtiene todas las camas de un hospital con información completa."""
    repo = HospitalRepository(session)
    camas = repo.obtener_camas_hospital(hospital_id)
    
    resultado = []
    for cama in camas:
        sala = cama.sala
        servicio = sala.servicio if sala else None
        
        # Obtener paciente actual
        paciente = None
        paciente_entrante = None
        
        if cama.estado not in [EstadoCamaEnum.LIBRE, EstadoCamaEnum.BLOQUEADA, 
                                EstadoCamaEnum.EN_LIMPIEZA, EstadoCamaEnum.TRASLADO_ENTRANTE]:
            query_paciente = select(Paciente).where(Paciente.cama_id == cama.id)
            paciente_db = session.exec(query_paciente).first()
            if paciente_db:
                paciente = crear_paciente_response(paciente_db)
            elif cama.estado in [EstadoCamaEnum.DERIVACION_CONFIRMADA, 
                                  EstadoCamaEnum.ESPERA_DERIVACION] and cama.paciente_derivado_id:
                paciente_derivado = session.get(Paciente, cama.paciente_derivado_id)
                if paciente_derivado:
                    paciente = crear_paciente_response(paciente_derivado)
        
        # Obtener paciente entrante
        if cama.estado == EstadoCamaEnum.TRASLADO_ENTRANTE:
            query_entrante = select(Paciente).where(Paciente.cama_destino_id == cama.id)
            paciente_entrante_db = session.exec(query_entrante).first()
            if paciente_entrante_db:
                paciente_entrante = crear_paciente_response(paciente_entrante_db)
        
        resultado.append(CamaResponse(
            id=cama.id,
            numero=cama.numero,
            letra=cama.letra,
            identificador=cama.identificador,
            estado=cama.estado,
            mensaje_estado=cama.mensaje_estado,
            cama_asignada_destino=cama.cama_asignada_destino,
            sala_id=cama.sala_id,
            servicio_nombre=servicio.nombre if servicio else None,
            servicio_tipo=servicio.tipo if servicio else None,
            sala_nombre=sala.nombre if sala else None,  
            sala_es_individual=sala.es_individual if sala else None,
            sala_sexo_asignado=sala.sexo_asignado if sala else None,
            paciente=paciente,
            paciente_entrante=paciente_entrante
        ))
    
    return resultado


# ============================================
# ENDPOINT: LISTA DE ESPERA (CORREGIDO)
# ============================================
@router.get("/{hospital_id}/lista-espera")
def obtener_lista_espera(hospital_id: str, session: Session = Depends(get_session)):
    """
    Obtiene la lista de espera de un hospital.
    
    Retorna pacientes ordenados por prioridad (mayor a menor) con información de:
    - Origen del paciente (urgencias, ambulatorio, derivado, hospitalizado)
    - Estado en la lista (esperando, buscando, asignado)
    - Tiempo de espera
    - Datos clínicos relevantes
    """
    repo = HospitalRepository(session)
    hospital = repo.obtener_por_id(hospital_id)
    
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital no encontrado")
    
    # Obtener cola de prioridad
    cola = gestor_colas_global.obtener_cola(hospital_id)
    
    # obtener_todos_ordenados() retorna List[Tuple[paciente_id, prioridad]]
    pacientes_ordenados = cola.obtener_todos_ordenados()
    
    pacientes_response = []
    for posicion, (paciente_id, prioridad) in enumerate(pacientes_ordenados, 1):
        paciente = session.get(Paciente, paciente_id)
        if not paciente:
            continue
        
        # Calcular tiempo de espera
        tiempo_espera_min = 0
        if paciente.timestamp_lista_espera:
            try:
                # Manejar timestamps con y sin timezone
                ts = paciente.timestamp_lista_espera
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                delta = datetime.now(timezone.utc) - ts
                tiempo_espera_min = int(delta.total_seconds() / 60)
            except Exception:
                tiempo_espera_min = 0
        
        # ============================================
        # DETERMINAR ORIGEN DEL PACIENTE (CORREGIDO)
        # ============================================
        origen_tipo = None
        origen_hospital_nombre = None
        origen_hospital_codigo = None
        origen_servicio_nombre = None
        origen_cama_identificador = None
        
        # Caso 1: Paciente derivado (aceptado de otro hospital)
        if paciente.derivacion_estado == "aceptada":
            origen_tipo = "derivado"
            # El hospital_id original está en cama_origen_derivacion
            if paciente.cama_origen_derivacion_id:
                from app.repositories.cama_repo import CamaRepository
                cama_repo = CamaRepository(session)
                cama_origen = cama_repo.obtener_por_id(paciente.cama_origen_derivacion_id)
                if cama_origen and cama_origen.sala and cama_origen.sala.servicio:
                    hospital_origen = repo.obtener_por_id(cama_origen.sala.servicio.hospital_id)
                    if hospital_origen:
                        origen_hospital_nombre = hospital_origen.nombre
                        origen_hospital_codigo = hospital_origen.codigo
                    origen_servicio_nombre = cama_origen.sala.servicio.nombre
                    origen_cama_identificador = cama_origen.identificador
        
        # Caso 2: Paciente hospitalizado (tiene cama actual en este hospital)
        elif paciente.cama_id:
            cama_origen = session.get(Cama, paciente.cama_id)
            if cama_origen and cama_origen.sala and cama_origen.sala.servicio:
                origen_tipo = "hospitalizado"
                origen_servicio_nombre = cama_origen.sala.servicio.nombre
                origen_cama_identificador = cama_origen.identificador
        
        # Caso 3: Paciente sin cama - determinar por tipo_paciente
        else:
            if paciente.tipo_paciente == TipoPacienteEnum.URGENCIA:
                origen_tipo = "urgencias"
            elif paciente.tipo_paciente == TipoPacienteEnum.AMBULATORIO:
                origen_tipo = "ambulatorio"
            elif paciente.tipo_paciente == TipoPacienteEnum.DERIVADO:
                origen_tipo = "derivado"
            else:
                origen_tipo = paciente.tipo_paciente.value if paciente.tipo_paciente else "desconocido"
        
        # ============================================
        # OBTENER VALORES SEGUROS DE ENUMS
        # ============================================
        estado_lista = "esperando"
        if hasattr(paciente, 'estado_lista_espera') and paciente.estado_lista_espera:
            estado_lista = paciente.estado_lista_espera.value if hasattr(paciente.estado_lista_espera, 'value') else str(paciente.estado_lista_espera)
        
        tipo_paciente = "medico"
        if paciente.tipo_paciente:
            tipo_paciente = paciente.tipo_paciente.value if hasattr(paciente.tipo_paciente, 'value') else str(paciente.tipo_paciente)
        
        complejidad = "baja"
        if paciente.complejidad_requerida:
            complejidad = paciente.complejidad_requerida.value if hasattr(paciente.complejidad_requerida, 'value') else str(paciente.complejidad_requerida)
        
        sexo = "masculino"
        if paciente.sexo:
            sexo = paciente.sexo.value if hasattr(paciente.sexo, 'value') else str(paciente.sexo)
        
        tipo_enfermedad = "agudo"
        if paciente.tipo_enfermedad:
            tipo_enfermedad = paciente.tipo_enfermedad.value if hasattr(paciente.tipo_enfermedad, 'value') else str(paciente.tipo_enfermedad)
        
        tipo_aislamiento = "sin_aislamiento"
        if paciente.tipo_aislamiento:
            tipo_aislamiento = paciente.tipo_aislamiento.value if hasattr(paciente.tipo_aislamiento, 'value') else str(paciente.tipo_aislamiento)
        
        pacientes_response.append({
            "paciente_id": paciente.id,
            "nombre": paciente.nombre,
            "run": paciente.run,
            "prioridad": prioridad,
            "posicion": posicion,
            "tiempo_espera_min": tiempo_espera_min,
            "estado_lista": estado_lista,
            "tipo_paciente": tipo_paciente,
            "complejidad": complejidad,
            "sexo": sexo,
            "edad": paciente.edad or 0,
            "tipo_enfermedad": tipo_enfermedad,
            "tipo_aislamiento": tipo_aislamiento,
            "tiene_cama_actual": paciente.cama_id is not None,
            "cama_actual_id": paciente.cama_id,
            "cama_destino_id": paciente.cama_destino_id,
            "timestamp": paciente.timestamp_lista_espera.isoformat() if paciente.timestamp_lista_espera else None,
            "origen_tipo": origen_tipo,
            "origen_hospital_nombre": origen_hospital_nombre,
            "origen_hospital_codigo": origen_hospital_codigo,
            "origen_servicio_nombre": origen_servicio_nombre,
            "origen_cama_identificador": origen_cama_identificador,
            "servicio_destino": getattr(paciente, 'servicio_destino', None),
            # Campos adicionales para el frontend
            "es_derivado": paciente.derivacion_estado == "aceptada",
            "derivacion_estado": paciente.derivacion_estado,
            "diagnostico": paciente.diagnostico
        })
    
    return {
        "hospital_id": hospital_id,
        "total_pacientes": len(pacientes_response),
        "pacientes": pacientes_response
    }


# ============================================
# ENDPOINT: DERIVADOS PENDIENTES
# ============================================
@router.get("/{hospital_id}/derivados")
def obtener_derivados_hospital(hospital_id: str, session: Session = Depends(get_session)):
    """
    Obtiene pacientes derivados pendientes hacia un hospital.
    
    Estos son pacientes que han sido presentados desde otros hospitales
    y están esperando ser aceptados o rechazados.
    """
    repo = HospitalRepository(session)
    hospital = repo.obtener_por_id(hospital_id)
    
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital no encontrado")
    
    # Buscar pacientes con derivación pendiente hacia este hospital
    query = select(Paciente).where(
        Paciente.derivacion_hospital_destino_id == hospital_id,
        Paciente.derivacion_estado == "pendiente"
    )
    pacientes = session.exec(query).all()
    
    resultado = []
    for paciente in pacientes:
        # Obtener hospital de origen desde la cama origen de derivación
        hospital_origen = None
        cama_origen_identificador = None
        servicio_origen_nombre = None
        
        if paciente.cama_origen_derivacion_id:
            from app.repositories.cama_repo import CamaRepository
            cama_repo = CamaRepository(session)
            cama_origen = cama_repo.obtener_por_id(paciente.cama_origen_derivacion_id)
            if cama_origen:
                cama_origen_identificador = cama_origen.identificador
                if cama_origen.sala and cama_origen.sala.servicio:
                    servicio_origen_nombre = cama_origen.sala.servicio.nombre
                    hospital_origen = repo.obtener_por_id(cama_origen.sala.servicio.hospital_id)
        
        # Fallback al hospital_id del paciente si no encontramos cama origen
        if not hospital_origen and paciente.hospital_id:
            hospital_origen = repo.obtener_por_id(paciente.hospital_id)
        
        # Calcular tiempo en lista
        tiempo_en_lista_min = 0
        if paciente.timestamp_lista_espera:
            try:
                ts = paciente.timestamp_lista_espera
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                delta = datetime.now(timezone.utc) - ts
                tiempo_en_lista_min = int(delta.total_seconds() / 60)
            except Exception:
                tiempo_en_lista_min = 0
        
        # Obtener valores seguros
        tipo_paciente = "medico"
        if paciente.tipo_paciente:
            tipo_paciente = paciente.tipo_paciente.value if hasattr(paciente.tipo_paciente, 'value') else str(paciente.tipo_paciente)
        
        complejidad = "baja"
        if paciente.complejidad_requerida:
            complejidad = paciente.complejidad_requerida.value if hasattr(paciente.complejidad_requerida, 'value') else str(paciente.complejidad_requerida)
        
        resultado.append({
            "paciente_id": paciente.id,
            "nombre": paciente.nombre,
            "run": paciente.run,
            "prioridad": paciente.prioridad_calculada or 0,
            "tiempo_en_lista_min": tiempo_en_lista_min,
            "hospital_origen_id": hospital_origen.id if hospital_origen else "",
            "hospital_origen_nombre": hospital_origen.nombre if hospital_origen else "Desconocido",
            "hospital_origen_codigo": hospital_origen.codigo if hospital_origen else "",
            "cama_origen_identificador": cama_origen_identificador,
            "servicio_origen_nombre": servicio_origen_nombre,
            "motivo_derivacion": paciente.derivacion_motivo or "",
            "tipo_paciente": tipo_paciente,
            "complejidad": complejidad,
            "diagnostico": paciente.diagnostico or "",
            "edad": paciente.edad or 0,
            "sexo": paciente.sexo.value if paciente.sexo else "desconocido"
        })
    
    return resultado