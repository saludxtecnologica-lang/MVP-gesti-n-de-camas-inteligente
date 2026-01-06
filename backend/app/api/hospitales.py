"""
Endpoints de Hospitales con restricciones RBAC.

CORREGIDO: Lista de espera ahora incluye pacientes con cama_destino_id asignada
que están pendientes de completar el traslado físico.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import Optional, List
from datetime import datetime, timezone

from app.core.database import get_session
from app.core.auth_dependencies import get_current_user, require_not_readonly
from app.core.rbac_service import rbac_service
from app.models.usuario import Usuario, PermisoEnum
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
from app.services.prioridad_service import gestor_colas_global, PrioridadService
from app.utils.helpers import calcular_estadisticas_camas, crear_paciente_response
from pydantic import BaseModel

router = APIRouter()


@router.get("", response_model=List[HospitalResponse])
def obtener_hospitales(
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Obtiene todos los hospitales con estadísticas. Filtrado por permisos del usuario."""
    repo = HospitalRepository(session)
    hospitales_todos = repo.obtener_todos()

    # Filtrar hospitales según permisos del usuario
    hospitales_permitidos = rbac_service.obtener_hospitales_permitidos(current_user)
    if hospitales_permitidos is None:
        # None significa acceso a todos los hospitales (PROGRAMADOR, DIRECTIVO_RED)
        hospitales = hospitales_todos
    else:
        # Filtrar por los hospitales permitidos
        hospitales = [h for h in hospitales_todos if h.id in hospitales_permitidos]

    resultado = []
    
    for hospital in hospitales:
        camas = repo.obtener_camas_hospital(hospital.id)
        stats = calcular_estadisticas_camas(camas)
        
        # Contar pacientes en espera (incluye los que tienen cama destino asignada)
        cola = gestor_colas_global.obtener_cola(hospital.id)
        pacientes_en_cola = cola.tamano()
        
        # También contar pacientes con cama_destino_id que podrían no estar en la cola
        query_pendientes_traslado = select(Paciente).where(
            Paciente.hospital_id == hospital.id,
            Paciente.en_lista_espera == True,
            Paciente.cama_destino_id != None
        )
        pendientes_traslado = len(session.exec(query_pendientes_traslado).all())
        
        # El total es el máximo entre ambos (evitar doble conteo)
        pacientes_espera = max(pacientes_en_cola, pendientes_traslado) if pendientes_traslado > 0 else pacientes_en_cola
  
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
            pacientes_derivados=derivados,
            telefono_urgencias=hospital.telefono_urgencias,  
            telefono_ambulatorio=hospital.telefono_ambulatorio  
        ))
    
    return resultado


@router.get("/{hospital_id}", response_model=HospitalResponse)
def obtener_hospital(
    hospital_id: str,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Obtiene un hospital específico. Requiere acceso al hospital."""
    # Verificar acceso al hospital
    if not rbac_service.puede_acceder_hospital(current_user, hospital_id):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para acceder a este hospital"
        )

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
def obtener_servicios(
    hospital_id: str,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Obtiene los servicios de un hospital. Filtrado por permisos del usuario."""
    # Verificar acceso al hospital
    if not rbac_service.puede_acceder_hospital(current_user, hospital_id):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para acceder a este hospital"
        )

    repo = HospitalRepository(session)
    cama_repo = CamaRepository(session)
    
    servicios = repo.obtener_servicios_hospital(hospital_id)
    resultado = []
    
    for servicio in servicios:
        # Filtrar por servicio si el usuario tiene restricción de servicio
        if current_user.servicio_id and current_user.servicio_id != servicio.id:
            continue

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
def obtener_camas_hospital(
    hospital_id: str,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Obtiene todas las camas de un hospital. Filtrado por permisos del usuario."""
    # Verificar acceso al hospital
    if not rbac_service.puede_acceder_hospital(current_user, hospital_id):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para acceder a este hospital"
        )

    repo = HospitalRepository(session)
    camas = repo.obtener_camas_hospital(hospital_id)
    
    resultado = []
    for cama in camas:
        sala = cama.sala
        servicio = sala.servicio if sala else None

        # Filtrar por servicio si el usuario tiene restricción de servicio
        if servicio and current_user.servicio_id and current_user.servicio_id != servicio.id:
            continue
        
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
# ENDPOINT: LISTA DE ESPERA 
# ============================================
# incluye pacientes con cama_destino_id asignada
# que están pendientes de completar el traslado físico.
# ============================================
@router.get("/{hospital_id}/lista-espera")
def obtener_lista_espera(
    hospital_id: str,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Obtiene la lista de espera de un hospital. Filtrado por permisos del usuario.
    
    ncluye pacientes que:
    1. Están en la cola de prioridad (esperando asignación)
    2. Tienen cama_destino_id asignada (pendientes de traslado físico)
    
    Retorna pacientes ordenados por prioridad (mayor a menor) con información de:
    - Origen del paciente (urgencias, ambulatorio, derivado, hospitalizado)
    - Estado en la lista (esperando, buscando, asignado)
    - Tiempo de espera
    - Datos clínicos relevantes
    """
    # Verificar acceso al hospital
    if not rbac_service.puede_acceder_hospital(current_user, hospital_id):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para acceder a este hospital"
        )

    repo = HospitalRepository(session)
    hospital = repo.obtener_por_id(hospital_id)

    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital no encontrado")
    
    # ============================================
    # OBTENER PACIENTES DE MÚLTIPLES FUENTES
    # ============================================
    
    # Fuente 1: Cola de prioridad (pacientes esperando asignación)
    cola = gestor_colas_global.obtener_cola(hospital_id)
    pacientes_en_cola = cola.obtener_todos_ordenados()  # List[Tuple[paciente_id, prioridad]]
    pacientes_ids_en_cola = {pid for pid, _ in pacientes_en_cola}
    
    # Fuente 2: Pacientes con cama_destino_id asignada (pendientes de traslado)
    # Estos pueden no estar en la cola pero deben mostrarse
    query_pendientes_traslado = select(Paciente).where(
        Paciente.hospital_id == hospital_id,
        Paciente.en_lista_espera == True,
        Paciente.cama_destino_id != None
    )
    pacientes_pendientes_traslado = session.exec(query_pendientes_traslado).all()
    
    # Fuente 3: Pacientes derivados aceptados que están en lista de espera
    query_derivados_aceptados = select(Paciente).where(
        Paciente.hospital_id == hospital_id,
        Paciente.en_lista_espera == True,
        Paciente.derivacion_estado == "aceptada"
    )
    pacientes_derivados = session.exec(query_derivados_aceptados).all()
    
    # ============================================
    # COMBINAR Y ORDENAR PACIENTES
    # ============================================
    prioridad_service = PrioridadService(session)
    pacientes_dict = {}  # Usar dict para evitar duplicados
    
    # Agregar pacientes de la cola con su prioridad
    for paciente_id, prioridad in pacientes_en_cola:
        paciente = session.get(Paciente, paciente_id)
        if paciente:
            pacientes_dict[paciente_id] = (paciente, prioridad)
    
    # Agregar pacientes pendientes de traslado (si no están ya)
    for paciente in pacientes_pendientes_traslado:
        if paciente.id not in pacientes_dict:
            prioridad = prioridad_service.calcular_prioridad(paciente)
            pacientes_dict[paciente.id] = (paciente, prioridad)
    
    # Agregar pacientes derivados aceptados (si no están ya)
    for paciente in pacientes_derivados:
        if paciente.id not in pacientes_dict:
            prioridad = prioridad_service.calcular_prioridad(paciente)
            pacientes_dict[paciente.id] = (paciente, prioridad)
    
    # Ordenar por prioridad descendente
    pacientes_ordenados = sorted(
        pacientes_dict.values(),
        key=lambda x: x[1],
        reverse=True
    )
    
    # ============================================
    # CONSTRUIR RESPUESTA
    # ============================================
    pacientes_response = []
    cama_repo = CamaRepository(session)

    for posicion, (paciente, prioridad) in enumerate(pacientes_ordenados, 1):
        # Filtrar pacientes según acceso del usuario
        # Si el usuario tiene servicio asignado, solo ver pacientes de ese servicio
        if current_user.servicio_id:
            # El usuario puede ver el paciente si:
            # - El servicio del paciente coincide con el del usuario (origen o destino)
            paciente_servicio_origen = None
            paciente_servicio_destino = getattr(paciente, 'servicio_destino', None)

            # Obtener servicio origen desde cama_id si existe
            if paciente.cama_id:
                cama_origen = cama_repo.obtener_por_id(paciente.cama_id)
                if cama_origen and cama_origen.sala and cama_origen.sala.servicio:
                    paciente_servicio_origen = cama_origen.sala.servicio.id

            # Si no coincide con el servicio del usuario, saltar
            if (current_user.servicio_id != paciente_servicio_origen and
                current_user.servicio_id != paciente_servicio_destino):
                continue
        # Calcular tiempo de espera
        tiempo_espera_min = 0
        if paciente.timestamp_lista_espera:
            try:
                ts = paciente.timestamp_lista_espera
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                delta = datetime.now(timezone.utc) - ts
                tiempo_espera_min = int(delta.total_seconds() / 60)
            except Exception:
                tiempo_espera_min = 0
        
        # ============================================
        # DETERMINAR ORIGEN DEL PACIENTE
        # ============================================
        origen_tipo = None
        origen_hospital_nombre = None
        origen_hospital_codigo = None
        origen_servicio_nombre = None
        origen_cama_identificador = None
        
        # Caso 1: Paciente derivado (aceptado de otro hospital)
        if paciente.derivacion_estado == "aceptada":
            origen_tipo = "derivado"
            if paciente.cama_origen_derivacion_id:
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
def obtener_derivados_hospital(
    hospital_id: str,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Obtiene pacientes derivados pendientes hacia un hospital. Filtrado por permisos.
    
    Estos son pacientes que han sido presentados desde otros hospitales
    y están esperando ser aceptados o rechazados.
    """
    # Verificar acceso al hospital
    if not rbac_service.puede_acceder_hospital(current_user, hospital_id):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para acceder a este hospital"
        )

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

# ============================================
# SCHEMAS PARA TELÉFONOS
# ============================================

class HospitalTelefonosUpdate(BaseModel):
    """Schema para actualizar teléfonos de un hospital."""
    telefono_urgencias: Optional[str] = None
    telefono_ambulatorio: Optional[str] = None


class ServicioTelefonoUpdate(BaseModel):
    """Schema para actualizar el teléfono de un servicio."""
    telefono: Optional[str] = None


class ServicioConTelefonoResponse(BaseModel):
    """Schema de respuesta para servicio con teléfono."""
    id: str
    nombre: str
    codigo: str
    tipo: str
    hospital_id: str
    telefono: Optional[str] = None
    total_camas: int = 0
    camas_libres: int = 0
    
    class Config:
        from_attributes = True


class HospitalConTelefonosResponse(BaseModel):
    """Schema de respuesta para hospital con todos sus teléfonos."""
    id: str
    nombre: str
    codigo: str
    es_central: bool
    telefono_urgencias: Optional[str] = None
    telefono_ambulatorio: Optional[str] = None
    servicios: List[ServicioConTelefonoResponse] = []
    
    class Config:
        from_attributes = True

        # ============================================
# ENDPOINT: Obtener teléfonos de un hospital
# ============================================

@router.get("/{hospital_id}/telefonos", response_model=HospitalConTelefonosResponse)
def obtener_telefonos_hospital(hospital_id: str, session: Session = Depends(get_session)):
    """
    Obtiene todos los teléfonos de un hospital:
    - Teléfono de urgencias del hospital
    - Teléfono de ambulatorio del hospital
    - Teléfonos de cada servicio
    """
    repo = HospitalRepository(session)
    cama_repo = CamaRepository(session)
    
    hospital = repo.obtener_por_id(hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital no encontrado")
    
    # Obtener servicios con sus teléfonos
    servicios = repo.obtener_servicios_hospital(hospital_id)
    servicios_response = []
    
    for servicio in servicios:
        camas = cama_repo.obtener_por_servicio(servicio.id)
        camas_libres = len([c for c in camas if c.estado == EstadoCamaEnum.LIBRE])
        
        servicios_response.append(ServicioConTelefonoResponse(
            id=servicio.id,
            nombre=servicio.nombre,
            codigo=servicio.codigo,
            tipo=servicio.tipo.value if hasattr(servicio.tipo, 'value') else str(servicio.tipo),
            hospital_id=servicio.hospital_id,
            telefono=servicio.telefono,
            total_camas=len(camas),
            camas_libres=camas_libres
        ))
    
    return HospitalConTelefonosResponse(
        id=hospital.id,
        nombre=hospital.nombre,
        codigo=hospital.codigo,
        es_central=hospital.es_central,
        telefono_urgencias=hospital.telefono_urgencias,
        telefono_ambulatorio=hospital.telefono_ambulatorio,
        servicios=servicios_response
    )


# ============================================
# ENDPOINT: Actualizar teléfonos del hospital (urgencias/ambulatorio)
# ============================================

@router.put("/{hospital_id}/telefonos")
async def actualizar_telefonos_hospital(
    hospital_id: str,
    data: HospitalTelefonosUpdate,
    current_user: Usuario = Depends(require_not_readonly()),
    session: Session = Depends(get_session)
):
    """
    Actualiza los teléfonos de urgencias y ambulatorio de un hospital.
    Requiere permisos de escritura.
    """
    # Verificar acceso al hospital
    if not rbac_service.puede_acceder_hospital(current_user, hospital_id):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para modificar este hospital"
        )
    repo = HospitalRepository(session)
    hospital = repo.obtener_por_id(hospital_id)
    
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital no encontrado")
    
    # Actualizar teléfonos
    if data.telefono_urgencias is not None:
        hospital.telefono_urgencias = data.telefono_urgencias.strip() if data.telefono_urgencias.strip() else None
    
    if data.telefono_ambulatorio is not None:
        hospital.telefono_ambulatorio = data.telefono_ambulatorio.strip() if data.telefono_ambulatorio.strip() else None
    
    session.add(hospital)
    session.commit()
    session.refresh(hospital)
    
    # Notificar cambio
    await manager.broadcast({
        "tipo": "hospital_telefonos_actualizados",
        "hospital_id": hospital_id
    })
    
    return {
        "success": True,
        "message": "Teléfonos del hospital actualizados",
        "data": {
            "telefono_urgencias": hospital.telefono_urgencias,
            "telefono_ambulatorio": hospital.telefono_ambulatorio
        }
    }


# ============================================
# ENDPOINT: Obtener servicios con teléfonos
# ============================================

@router.get("/{hospital_id}/servicios-telefonos", response_model=List[ServicioConTelefonoResponse])
def obtener_servicios_con_telefonos(hospital_id: str, session: Session = Depends(get_session)):
    """
    Obtiene los servicios de un hospital con sus teléfonos.
    Útil para la configuración de teléfonos.
    """
    repo = HospitalRepository(session)
    cama_repo = CamaRepository(session)
    
    servicios = repo.obtener_servicios_hospital(hospital_id)
    resultado = []
    
    for servicio in servicios:
        camas = cama_repo.obtener_por_servicio(servicio.id)
        camas_libres = len([c for c in camas if c.estado == EstadoCamaEnum.LIBRE])
        
        resultado.append(ServicioConTelefonoResponse(
            id=servicio.id,
            nombre=servicio.nombre,
            codigo=servicio.codigo,
            tipo=servicio.tipo.value if hasattr(servicio.tipo, 'value') else str(servicio.tipo),
            hospital_id=servicio.hospital_id,
            telefono=servicio.telefono,
            total_camas=len(camas),
            camas_libres=camas_libres
        ))
    
    return resultado


# ============================================
# ENDPOINT: Actualizar teléfono de un servicio
# ============================================

@router.put("/{hospital_id}/servicios/{servicio_id}/telefono", response_model=ServicioConTelefonoResponse)
async def actualizar_telefono_servicio(
    hospital_id: str,
    servicio_id: str,
    data: ServicioTelefonoUpdate,
    current_user: Usuario = Depends(require_not_readonly()),
    session: Session = Depends(get_session)
):
    """
    Actualiza el teléfono de contacto de un servicio.
    Requiere permisos de escritura.
    """
    # Verificar acceso al hospital
    if not rbac_service.puede_acceder_hospital(current_user, hospital_id):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para modificar este hospital"
        )
    servicio = session.get(Servicio, servicio_id)
    
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    if servicio.hospital_id != hospital_id:
        raise HTTPException(status_code=400, detail="El servicio no pertenece a este hospital")
    
    # Actualizar teléfono
    servicio.telefono = data.telefono.strip() if data.telefono and data.telefono.strip() else None
    
    session.add(servicio)
    session.commit()
    session.refresh(servicio)
    
    # Obtener estadísticas de camas
    cama_repo = CamaRepository(session)
    camas = cama_repo.obtener_por_servicio(servicio.id)
    camas_libres = len([c for c in camas if c.estado == EstadoCamaEnum.LIBRE])
    
    # Notificar cambio
    await manager.broadcast({
        "tipo": "servicio_actualizado",
        "servicio_id": servicio_id,
        "hospital_id": hospital_id
    })
    
    return ServicioConTelefonoResponse(
        id=servicio.id,
        nombre=servicio.nombre,
        codigo=servicio.codigo,
        tipo=servicio.tipo.value if hasattr(servicio.tipo, 'value') else str(servicio.tipo),
        hospital_id=servicio.hospital_id,
        telefono=servicio.telefono,
        total_camas=len(camas),
        camas_libres=camas_libres
    )


# ============================================
# ENDPOINT: Actualizar múltiples teléfonos (batch)
# ============================================

@router.put("/{hospital_id}/telefonos-batch")
async def actualizar_telefonos_batch(
    hospital_id: str,
    data: dict,  # {"hospital": {...}, "servicios": {...}}
    current_user: Usuario = Depends(require_not_readonly()),
    session: Session = Depends(get_session)
):
    """
    Actualiza todos los teléfonos de un hospital en una sola llamada.
    Requiere permisos de escritura.
    
    Body esperado:
    {
        "hospital": {
            "telefono_urgencias": "123456",
            "telefono_ambulatorio": "789012"
        },
        "servicios": {
            "servicio_id_1": "111222",
            "servicio_id_2": "333444"
        }
    }
    """
    repo = HospitalRepository(session)
    hospital = repo.obtener_por_id(hospital_id)
    
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital no encontrado")
    
    actualizados = []
    errores = []
    
    # Actualizar teléfonos del hospital
    hospital_data = data.get("hospital", {})
    if "telefono_urgencias" in hospital_data:
        tel = hospital_data["telefono_urgencias"]
        hospital.telefono_urgencias = tel.strip() if tel and tel.strip() else None
        actualizados.append("Urgencias del hospital")
    
    if "telefono_ambulatorio" in hospital_data:
        tel = hospital_data["telefono_ambulatorio"]
        hospital.telefono_ambulatorio = tel.strip() if tel and tel.strip() else None
        actualizados.append("Ambulatorio del hospital")
    
    session.add(hospital)
    
    # Actualizar teléfonos de servicios
    servicios_data = data.get("servicios", {})
    for servicio_id, telefono in servicios_data.items():
        servicio = session.get(Servicio, servicio_id)
        
        if not servicio:
            errores.append(f"Servicio {servicio_id} no encontrado")
            continue
            
        if servicio.hospital_id != hospital_id:
            errores.append(f"Servicio {servicio_id} no pertenece a este hospital")
            continue
        
        servicio.telefono = telefono.strip() if telefono and telefono.strip() else None
        session.add(servicio)
        actualizados.append(servicio.nombre)
    
    session.commit()
    
    # Notificar cambio
    await manager.broadcast({
        "tipo": "telefonos_hospital_actualizados",
        "hospital_id": hospital_id
    })
    
    return {
        "success": True,
        "message": f"Teléfonos actualizados: {len(actualizados)}",
        "actualizados": actualizados,
        "errores": errores if errores else None
    }
