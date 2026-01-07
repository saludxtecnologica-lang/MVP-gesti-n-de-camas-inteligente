"""
Endpoints de Pacientes.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session
from typing import Optional, List
from datetime import datetime
from fastapi import HTTPException, status
import os
import uuid
import json
import logging

from app.config import settings
from app.core.database import get_session
from app.core.auth_dependencies import get_current_user, require_not_readonly
from app.core.rbac_service import rbac_service
from app.core.websocket_manager import manager
from app.core.exceptions import PacienteNotFoundError, ValidationError
from app.models.usuario import Usuario, PermisoEnum, RolEnum
from app.models.paciente import Paciente
from app.models.cama import Cama
from app.models.configuracion import ConfiguracionSistema
from app.models.enums import (
    EdadCategoriaEnum, 
    TipoPacienteEnum,
    EstadoCamaEnum,
    NIVEL_COMPLEJIDAD_OXIGENO,
    TODOS_REQUERIMIENTOS_OXIGENO,
)
from app.schemas.paciente import (
    PacienteCreate, 
    PacienteUpdate, 
    PacienteResponse,
    ListaEsperaResponse,
    PacienteListaEsperaResponse,
)
from app.schemas.responses import MessageResponse
from app.repositories.paciente_repo import PacienteRepository
from app.repositories.cama_repo import CamaRepository
from app.repositories.hospital_repo import HospitalRepository
from app.services.asignacion_service import AsignacionService
from app.services.prioridad_service import PrioridadService
from app.services.derivacion_service import DerivacionService
from app.utils.helpers import crear_paciente_response
from sqlmodel import select

router = APIRouter()
logger = logging.getLogger("gestion_camas.pacientes")


def determinar_edad_categoria(edad: int) -> EdadCategoriaEnum:
    """Determina la categoría de edad."""
    if edad < 15:
        return EdadCategoriaEnum.PEDIATRICO
    elif edad < 60:
        return EdadCategoriaEnum.ADULTO
    else:
        return EdadCategoriaEnum.ADULTO_MAYOR


def obtener_nivel_oxigeno_maximo(requerimientos: List[str]) -> int:
    """
    Obtiene el nivel máximo de oxígeno de una lista de requerimientos.
    
    Niveles:
    - 0: Sin oxígeno
    - 1: Baja complejidad (naricera, multiventuri)
    - 2: UTI (reservorio, CNAF, VMNI)
    - 3: UCI (VMI)
    """
    if not requerimientos:
        return 0
    
    nivel_maximo = 0
    for req in requerimientos:
        nivel = NIVEL_COMPLEJIDAD_OXIGENO.get(req, 0)
        if nivel > nivel_maximo:
            nivel_maximo = nivel
    
    return nivel_maximo


def extraer_requerimientos_oxigeno(paciente: Paciente) -> List[str]:
    """Extrae todos los requerimientos de oxígeno de un paciente."""
    requerimientos_oxigeno = []
    
    for campo in ['requerimientos_baja', 'requerimientos_uti', 'requerimientos_uci']:
        reqs = paciente.get_requerimientos_lista(campo)
        for req in reqs:
            if req in TODOS_REQUERIMIENTOS_OXIGENO:
                requerimientos_oxigeno.append(req)
    
    return requerimientos_oxigeno


def detectar_descalaje_oxigeno(
    requerimientos_anteriores: List[str],
    requerimientos_nuevos: List[str]
) -> dict:
    """Detecta si hubo un descalaje (bajada) en el nivel de oxígeno."""
    nivel_anterior = obtener_nivel_oxigeno_maximo(requerimientos_anteriores)
    nivel_nuevo = obtener_nivel_oxigeno_maximo(requerimientos_nuevos)
    
    hubo_descalaje = nivel_anterior > nivel_nuevo
    
    niveles_nombre = {
        0: "Sin oxígeno",
        1: "Baja complejidad (naricera/multiventuri)",
        2: "UTI (reservorio/CNAF/VMNI)",
        3: "UCI (VMI)"
    }
    
    descripcion = ""
    if hubo_descalaje:
        descripcion = f"Descalaje de {niveles_nombre[nivel_anterior]} a {niveles_nombre[nivel_nuevo]}"
    
    return {
        "hubo_descalaje": hubo_descalaje,
        "nivel_anterior": nivel_anterior,
        "nivel_nuevo": nivel_nuevo,
        "descripcion": descripcion
    }


def obtener_tiempo_espera_oxigeno(session: Session) -> int:
    """Obtiene el tiempo de espera de oxígeno configurado."""
    config = session.exec(select(ConfiguracionSistema)).first()
    if config and hasattr(config, 'tiempo_espera_oxigeno_segundos'):
        return config.tiempo_espera_oxigeno_segundos
    return getattr(settings, 'TIEMPO_ESPERA_OXIGENO_DEFAULT', 120)


def calcular_tiempo_restante_pausa(paciente: Paciente, tiempo_espera_total: int) -> int:
    """
    Calcula el tiempo restante de la pausa de oxígeno.
    
    Returns:
        Segundos restantes (0 si no hay pausa activa o ya terminó)
    """
    if not paciente.esperando_evaluacion_oxigeno or not paciente.oxigeno_desactivado_at:
        return 0
    
    tiempo_transcurrido = (datetime.utcnow() - paciente.oxigeno_desactivado_at).total_seconds()
    tiempo_restante = tiempo_espera_total - tiempo_transcurrido
    
    return max(0, int(tiempo_restante))


@router.post("", response_model=PacienteResponse)
async def crear_paciente(
    paciente_data: PacienteCreate,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Crea un nuevo paciente y lo agrega a la cola de espera.
    Solo MEDICO puede crear pacientes.

    Si se especifica derivacion_hospital_destino_id, se solicita la derivación
    automáticamente después de crear el paciente.
    """
    # Verificar que solo MEDICO puede crear pacientes
    if current_user.rol != RolEnum.MEDICO and current_user.rol != RolEnum.PROGRAMADOR:
        raise HTTPException(
            status_code=403,
            detail="Solo los médicos pueden registrar nuevos pacientes"
        )

    # Verificar permiso PACIENTE_CREAR
    if not current_user.tiene_permiso(PermisoEnum.PACIENTE_CREAR):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para crear pacientes"
        )

    # Verificar acceso al hospital
    if not rbac_service.puede_acceder_hospital(current_user, paciente_data.hospital_id):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para registrar pacientes en este hospital"
        )
    repo = PacienteRepository(session)
    service = AsignacionService(session)
    
    # Solo permitir urgencia o ambulatorio como origen
    if paciente_data.tipo_paciente not in [TipoPacienteEnum.URGENCIA, TipoPacienteEnum.AMBULATORIO]:
        raise HTTPException(
            status_code=400,
            detail="Solo se permite registrar pacientes de tipo Urgencia o Ambulatorio"
        )
    
    edad_categoria = determinar_edad_categoria(paciente_data.edad)
    
    paciente = Paciente(
        nombre=paciente_data.nombre,
        run=paciente_data.run,
        sexo=paciente_data.sexo,
        edad=paciente_data.edad,
        edad_categoria=edad_categoria,
        es_embarazada=paciente_data.es_embarazada,
        diagnostico=paciente_data.diagnostico,
        tipo_enfermedad=paciente_data.tipo_enfermedad,
        tipo_aislamiento=paciente_data.tipo_aislamiento,
        notas_adicionales=paciente_data.notas_adicionales,
        requerimientos_no_definen=json.dumps(paciente_data.requerimientos_no_definen),
        requerimientos_baja=json.dumps(paciente_data.requerimientos_baja),
        requerimientos_uti=json.dumps(paciente_data.requerimientos_uti),
        requerimientos_uci=json.dumps(paciente_data.requerimientos_uci),
        casos_especiales=json.dumps(paciente_data.casos_especiales),
        motivo_observacion=paciente_data.motivo_observacion,
        justificacion_observacion=paciente_data.justificacion_observacion,
        motivo_monitorizacion=paciente_data.motivo_monitorizacion,
        justificacion_monitorizacion=paciente_data.justificacion_monitorizacion,
        procedimiento_invasivo=paciente_data.procedimiento_invasivo,
        preparacion_quirurgica_detalle=paciente_data.preparacion_quirurgica_detalle,
        tipo_paciente=paciente_data.tipo_paciente,
        hospital_id=paciente_data.hospital_id,
        en_lista_espera=True,
        timestamp_lista_espera=datetime.utcnow(),
        observacion_tiempo_horas=paciente_data.observacion_tiempo_horas,
        monitorizacion_tiempo_horas=paciente_data.monitorizacion_tiempo_horas,
        motivo_ingreso_ambulatorio=paciente_data.motivo_ingreso_ambulatorio,
    )
    
    paciente.complejidad_requerida = service.calcular_complejidad(paciente)
    
    # ============================================
    # INICIAR TIMERS SI SE ESPECIFICARON
    # ============================================
    
    # Timer de observación clínica
    if paciente_data.observacion_tiempo_horas and paciente_data.observacion_tiempo_horas > 0:
        paciente.observacion_tiempo_horas = paciente_data.observacion_tiempo_horas
        paciente.observacion_inicio = datetime.utcnow()
        logger.info(
            f"Timer de observación iniciado para {paciente.nombre}: "
            f"{paciente_data.observacion_tiempo_horas} horas"
        )
    
    # Timer de monitorización
    if paciente_data.monitorizacion_tiempo_horas and paciente_data.monitorizacion_tiempo_horas > 0:
        paciente.monitorizacion_tiempo_horas = paciente_data.monitorizacion_tiempo_horas
        paciente.monitorizacion_inicio = datetime.utcnow()
        logger.info(
            f"Timer de monitorización iniciado para {paciente.nombre}: "
            f"{paciente_data.monitorizacion_tiempo_horas} horas"
        )
    
    session.add(paciente)
    session.commit()
    session.refresh(paciente)
    
    # Agregar a cola de prioridad
    service.agregar_a_cola(paciente)
    
    # Si se solicitó derivación, procesarla
    if paciente_data.derivacion_hospital_destino_id:
        try:
            derivacion_service = DerivacionService(session)
            resultado = derivacion_service.solicitar_derivacion(
                paciente.id,
                paciente_data.derivacion_hospital_destino_id,
                paciente_data.derivacion_motivo or "Derivación solicitada al registrar paciente"
            )
            
            # Notificar al hospital destino
            await manager.send_notification(
                {
                    "tipo": "derivacion_solicitada",
                    "paciente_id": paciente.id,
                    "paciente_nombre": paciente.nombre,
                    "hospital_destino_id": paciente_data.derivacion_hospital_destino_id,
                },
                notification_type="info",
                hospital_id=paciente_data.derivacion_hospital_destino_id
            )
            
            logger.info(f"Derivación solicitada para paciente {paciente.nombre}: {resultado.mensaje}")
            
        except Exception as e:
            logger.error(f"Error al solicitar derivación para {paciente.nombre}: {e}")
            # No fallar la creación del paciente por error en derivación
    
    await manager.broadcast({
        "tipo": "paciente_creado",
        "hospital_id": paciente.hospital_id,
        "reload": True
    })
    
    return crear_paciente_response(paciente)


@router.get("/{paciente_id}", response_model=PacienteResponse)
def obtener_paciente(
    paciente_id: str,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Obtiene un paciente por ID. Filtrado por permisos del usuario."""
    repo = PacienteRepository(session)
    paciente = repo.obtener_por_id(paciente_id)

    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # Verificar acceso al hospital del paciente
    # Obtener el hospital para comparar por código (paciente.hospital_id es UUID)
    hospital_repo = HospitalRepository(session)
    hospital_paciente = hospital_repo.obtener_por_id(paciente.hospital_id)

    if hospital_paciente:
        # Comparar usando el código del hospital en lugar del UUID
        if not rbac_service.puede_acceder_hospital(current_user, hospital_paciente.codigo):
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para ver este paciente"
            )
    else:
        # Fallback: usar UUID si no se encuentra el hospital
        if not rbac_service.puede_acceder_hospital(current_user, paciente.hospital_id):
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para ver este paciente"
            )

    # Verificar acceso por servicio (si el usuario tiene servicio asignado)
    if current_user.servicio_id:
        puede_ver = rbac_service.puede_ver_paciente(
            current_user,
            paciente.servicio_origen if hasattr(paciente, 'servicio_origen') else None,
            paciente.servicio_destino if hasattr(paciente, 'servicio_destino') else None,
            paciente.hospital_id
        )
        if not puede_ver:
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para ver este paciente (servicio no coincide)"
            )

    mensaje_broadcast = "Paciente actualizado"

    return crear_paciente_response(paciente)


@router.put("/{paciente_id}", response_model=PacienteResponse)
async def actualizar_paciente(
    paciente_id: str,
    paciente_data: PacienteUpdate,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Actualiza un paciente (reevaluación).
    Solo MEDICO puede hacer cambios clínicos (reevaluaciones).

    LÓGICA DE PAUSA DE OXÍGENO:
    
    1. Si hay descalaje Y NO hay pausa activa:
       - Activar nueva pausa (esperando_evaluacion_oxigeno=True, oxigeno_desactivado_at=now)
       
    2. Si hay descalaje Y YA hay pausa activa:
       - NO reiniciar el timer (mantener oxigeno_desactivado_at original)
       - Actualizar estado según nuevos requerimientos
       
    3. Durante la pausa:
       - Si requiere nueva cama → requiere_nueva_cama=True pero NO cambiar a CAMA_EN_ESPERA
       - El estado se mantiene OCUPADA hasta que termine la pausa
       - El botón "Buscar nueva cama" está deshabilitado
       
    4. Después de la pausa (manejado por background_tasks):
       - Si requiere_nueva_cama=True → CAMA_EN_ESPERA
       - Si puede_sugerir_alta() → ALTA_SUGERIDA
       - Si compatible → OCUPADA normal
       
    DERIVACIÓN:
    Si se especifica derivacion_hospital_destino_id, se solicita la derivación.
    """
    # Verificar que solo MEDICO puede reevaluar
    if current_user.rol not in [RolEnum.MEDICO, RolEnum.PROGRAMADOR]:
        raise HTTPException(
            status_code=403,
            detail="Solo los médicos pueden reevaluar pacientes"
        )

    # Verificar permiso PACIENTE_REEVALUAR
    if not current_user.tiene_permiso(PermisoEnum.PACIENTE_REEVALUAR):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para reevaluar pacientes"
        )

    repo = PacienteRepository(session)
    cama_repo = CamaRepository(session)
    service = AsignacionService(session)

    paciente = repo.obtener_por_id(paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # Verificar acceso al hospital del paciente
    # Obtener el hospital para comparar por código (paciente.hospital_id es UUID)
    hospital_repo = HospitalRepository(session)
    hospital_paciente = hospital_repo.obtener_por_id(paciente.hospital_id)

    if hospital_paciente:
        # Comparar usando el código del hospital en lugar del UUID
        if not rbac_service.puede_acceder_hospital(current_user, hospital_paciente.codigo):
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para modificar pacientes de este hospital"
            )
    else:
        # Fallback: usar UUID si no se encuentra el hospital
        if not rbac_service.puede_acceder_hospital(current_user, paciente.hospital_id):
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para modificar pacientes de este hospital"
            )

    # Verificar acceso por servicio
    if current_user.servicio_id:
        puede_ver = rbac_service.puede_ver_paciente(
            current_user,
            paciente.servicio_origen if hasattr(paciente, 'servicio_origen') else None,
            paciente.servicio_destino if hasattr(paciente, 'servicio_destino') else None,
            paciente.hospital_id
        )
        if not puede_ver:
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para modificar este paciente (servicio no coincide)"
            )

    # ============================================
    # GUARDAR ESTADO ANTERIOR
    # ============================================
    requerimientos_oxigeno_anteriores = extraer_requerimientos_oxigeno(paciente)
    ya_en_pausa_oxigeno = paciente.esperando_evaluacion_oxigeno
    timestamp_pausa_original = paciente.oxigeno_desactivado_at
    # Verificar si hay derivación ACTIVA (no solo si existe algún valor)
    derivacion_activa = paciente.derivacion_estado in ["pendiente", "aceptada"]
    
    logger.info(
        f"Paciente {paciente.nombre}: Reevaluando. "
        f"Ya en pausa: {ya_en_pausa_oxigeno}, "
        f"O₂ anterior: {requerimientos_oxigeno_anteriores}"
    )
    
    # ============================================
    # ACTUALIZAR CAMPOS
    # ============================================
    if paciente_data.diagnostico is not None:
        paciente.diagnostico = paciente_data.diagnostico
    if paciente_data.tipo_enfermedad is not None:
        paciente.tipo_enfermedad = paciente_data.tipo_enfermedad
    if paciente_data.tipo_aislamiento is not None:
        paciente.tipo_aislamiento = paciente_data.tipo_aislamiento
    if paciente_data.notas_adicionales is not None:
        paciente.notas_adicionales = paciente_data.notas_adicionales
    if paciente_data.es_embarazada is not None:
        paciente.es_embarazada = paciente_data.es_embarazada
    
    if paciente_data.requerimientos_no_definen is not None:
        paciente.requerimientos_no_definen = json.dumps(paciente_data.requerimientos_no_definen)
    if paciente_data.requerimientos_baja is not None:
        paciente.requerimientos_baja = json.dumps(paciente_data.requerimientos_baja)
    if paciente_data.requerimientos_uti is not None:
        paciente.requerimientos_uti = json.dumps(paciente_data.requerimientos_uti)
    if paciente_data.requerimientos_uci is not None:
        paciente.requerimientos_uci = json.dumps(paciente_data.requerimientos_uci)
    if paciente_data.casos_especiales is not None:
        paciente.casos_especiales = json.dumps(paciente_data.casos_especiales)
    
    if paciente_data.motivo_observacion is not None:
        paciente.motivo_observacion = paciente_data.motivo_observacion
    if paciente_data.justificacion_observacion is not None:
        paciente.justificacion_observacion = paciente_data.justificacion_observacion
    if paciente_data.motivo_monitorizacion is not None:
        paciente.motivo_monitorizacion = paciente_data.motivo_monitorizacion
    if paciente_data.justificacion_monitorizacion is not None:
        paciente.justificacion_monitorizacion = paciente_data.justificacion_monitorizacion
    if paciente_data.procedimiento_invasivo is not None:
        paciente.procedimiento_invasivo = paciente_data.procedimiento_invasivo
    if paciente_data.preparacion_quirurgica_detalle is not None:
        paciente.preparacion_quirurgica_detalle = paciente_data.preparacion_quirurgica_detalle

    
    # ============================================
    # Timer observación - LÓGICA CORREGIDA
    # ============================================
    
    # Obtener los requerimientos de baja complejidad finales
    req_baja_finales = []
    if paciente_data.requerimientos_baja is not None:
        req_baja_finales = paciente_data.requerimientos_baja
    else:
        req_baja_finales = paciente.get_requerimientos_lista('requerimientos_baja')
    
    # Verificar si tiene el requerimiento "Observación clínica" marcado
    tiene_observacion_clinica = 'Observación clínica' in req_baja_finales
    
    if tiene_observacion_clinica:
        # El requerimiento ESTÁ marcado
        if paciente_data.observacion_tiempo_horas is not None:
            if paciente_data.observacion_tiempo_horas > 0:
                # Hay un tiempo especificado (positivo)
                if paciente.observacion_tiempo_horas != paciente_data.observacion_tiempo_horas:
                    # El tiempo CAMBIÓ - reiniciar timer
                    paciente.observacion_tiempo_horas = paciente_data.observacion_tiempo_horas
                    paciente.observacion_inicio = datetime.utcnow()
                    logger.info(
                        f"Timer de observación reiniciado para {paciente.nombre}: "
                        f"{paciente_data.observacion_tiempo_horas} horas"
                    )
                elif paciente.observacion_inicio is None:
                    # El tiempo es el mismo pero NO hay inicio - iniciar ahora
                    paciente.observacion_inicio = datetime.utcnow()
                    logger.info(
                        f"Timer de observación iniciado para {paciente.nombre}: "
                        f"{paciente.observacion_tiempo_horas} horas"
                    )
                else:
                    # El tiempo es el mismo Y ya hay inicio - mantener sin cambios
                    logger.debug(f"Timer de observación mantenido para {paciente.nombre}")
            elif paciente_data.observacion_tiempo_horas == 0:
                # Se envió tiempo = 0, esto significa que se desmarcó el requerimiento
                # o se quiere desactivar el timer manualmente
                paciente.observacion_tiempo_horas = None
                paciente.observacion_inicio = None
                logger.info(f"Timer de observación desactivado para {paciente.nombre} (tiempo=0)")
        # Si observacion_tiempo_horas es None en paciente_data, mantener el timer existente
    else:
        # El requerimiento NO está marcado - limpiar todo el timer
        if paciente.observacion_tiempo_horas is not None or paciente.observacion_inicio is not None:
            paciente.observacion_tiempo_horas = None
            paciente.observacion_inicio = None
            paciente.motivo_observacion = None
            paciente.justificacion_observacion = None
            logger.info(f"Timer de observación limpiado para {paciente.nombre} (requerimiento desmarcado)")

    # ============================================
    # Timer monitorización - LÓGICA CORREGIDA
    # ============================================
    
    # Obtener los requerimientos UTI finales
    req_uti_finales = []
    if paciente_data.requerimientos_uti is not None:
        req_uti_finales = paciente_data.requerimientos_uti
    else:
        req_uti_finales = paciente.get_requerimientos_lista('requerimientos_uti')
    
    # Verificar si tiene el requerimiento "Monitorización continua" marcado
    tiene_monitorizacion = 'Monitorización continua' in req_uti_finales
    
    if tiene_monitorizacion:
        # El requerimiento ESTÁ marcado
        if paciente_data.monitorizacion_tiempo_horas is not None:
            if paciente_data.monitorizacion_tiempo_horas > 0:
                # Hay un tiempo especificado (positivo)
                if paciente.monitorizacion_tiempo_horas != paciente_data.monitorizacion_tiempo_horas:
                    # El tiempo CAMBIÓ - reiniciar timer
                    paciente.monitorizacion_tiempo_horas = paciente_data.monitorizacion_tiempo_horas
                    paciente.monitorizacion_inicio = datetime.utcnow()
                    logger.info(
                        f"Timer de monitorización reiniciado para {paciente.nombre}: "
                        f"{paciente_data.monitorizacion_tiempo_horas} horas"
                    )
                elif paciente.monitorizacion_inicio is None:
                    # El tiempo es el mismo pero NO hay inicio - iniciar ahora
                    paciente.monitorizacion_inicio = datetime.utcnow()
                    logger.info(
                        f"Timer de monitorización iniciado para {paciente.nombre}: "
                        f"{paciente.monitorizacion_tiempo_horas} horas"
                    )
                else:
                    # El tiempo es el mismo Y ya hay inicio - mantener sin cambios
                    logger.debug(f"Timer de monitorización mantenido para {paciente.nombre}")
            elif paciente_data.monitorizacion_tiempo_horas == 0:
                # Se envió tiempo = 0, esto significa que se desmarcó el requerimiento
                paciente.monitorizacion_tiempo_horas = None
                paciente.monitorizacion_inicio = None
                logger.info(f"Timer de monitorización desactivado para {paciente.nombre} (tiempo=0)")
        # Si monitorizacion_tiempo_horas es None en paciente_data, mantener el timer existente
    else:
        # El requerimiento NO está marcado - limpiar todo el timer
        if paciente.monitorizacion_tiempo_horas is not None or paciente.monitorizacion_inicio is not None:
            paciente.monitorizacion_tiempo_horas = None
            paciente.monitorizacion_inicio = None
            paciente.motivo_monitorizacion = None
            paciente.justificacion_monitorizacion = None
            logger.info(f"Timer de monitorización limpiado para {paciente.nombre} (requerimiento desmarcado)")
    
    # ============================================
    # MANEJO DE FALLECIMIENTO
    # ============================================
    if paciente_data.fallecido is not None:
        if paciente_data.fallecido and not paciente.fallecido:
            # Registrar fallecimiento
            paciente.fallecido = True
            paciente.causa_fallecimiento = paciente_data.causa_fallecimiento
            paciente.fallecido_at = datetime.utcnow()
            
            # Guardar estado anterior de la cama para poder revertir
            if paciente.cama_id:
                cama = cama_repo.obtener_por_id(paciente.cama_id)
                if cama:
                    paciente.estado_cama_anterior_fallecimiento = cama.estado.value
                    cama.estado = EstadoCamaEnum.FALLECIDO
                    cama.mensaje_estado = "Paciente fallecido - Cuidados postmortem"
                    cama.estado_updated_at = datetime.utcnow()
                    session.add(cama)
            
            logger.info(f"Paciente {paciente.nombre} marcado como fallecido. Causa: {paciente_data.causa_fallecimiento}")
            mensaje_broadcast = "Paciente registrado como fallecido"
            
        elif not paciente_data.fallecido and paciente.fallecido:
            # Cancelar fallecimiento (solo desde modo manual)
            # Este caso se maneja en el endpoint específico de cancelar fallecimiento
            pass
    
    if paciente_data.causa_fallecimiento is not None and paciente.fallecido:
        paciente.causa_fallecimiento = paciente_data.causa_fallecimiento
        
    paciente.updated_at = datetime.utcnow()
    paciente.complejidad_requerida = service.calcular_complejidad(paciente)
    
    # ============================================
    # OBTENER REQUERIMIENTOS NUEVOS
    # ============================================
    requerimientos_oxigeno_nuevos = extraer_requerimientos_oxigeno(paciente)
    logger.info(f"Paciente {paciente.nombre}: O₂ nuevo: {requerimientos_oxigeno_nuevos}")
    
    # ============================================
    # DETECTAR DESCALAJE DE OXÍGENO
    # ============================================
    resultado_descalaje = detectar_descalaje_oxigeno(
        requerimientos_oxigeno_anteriores,
        requerimientos_oxigeno_nuevos
    )
    
    # Inicializar mensaje_broadcast
    mensaje_broadcast = "Paciente actualizado"
    if paciente.fallecido:
        mensaje_broadcast = "Paciente registrado como fallecido"

    tiempo_espera = obtener_tiempo_espera_oxigeno(session)
    
    # Si el paciente tiene cama asignada Y NO está fallecido
    if paciente.cama_id and not paciente.fallecido:
        cama = cama_repo.obtener_por_id(paciente.cama_id)
        
        if cama:
            # ============================================
            # CASO 1: Hay descalaje de oxígeno
            # ============================================
            if resultado_descalaje["hubo_descalaje"]:
                logger.info(f"Paciente {paciente.nombre}: {resultado_descalaje['descripcion']}")
                
                if not ya_en_pausa_oxigeno:
                    # NUEVA pausa: Activar timer
                    paciente.esperando_evaluacion_oxigeno = True
                    paciente.oxigeno_desactivado_at = datetime.utcnow()
                    paciente.requerimientos_oxigeno_previos = json.dumps(requerimientos_oxigeno_anteriores)
                    logger.info(f"  → Nueva pausa activada ({tiempo_espera}s)")
                else:
                    # YA en pausa: Mantener timer original
                    paciente.oxigeno_desactivado_at = timestamp_pausa_original
                    tiempo_restante = calcular_tiempo_restante_pausa(paciente, tiempo_espera)
                    logger.info(f"  → Pausa ya activa, tiempo restante: {tiempo_restante}s")
                
                # Evaluar si requiere nueva cama (para marcar el flag)
                if service.paciente_requiere_nueva_cama(paciente, cama):
                    paciente.requiere_nueva_cama = True
                    cama.mensaje_estado = f"Evaluando descalaje O₂ - Requiere nueva cama"
                    logger.info(f"  → Requiere nueva cama (marcado para después de pausa)")
                elif service.puede_sugerir_alta(paciente):
                    cama.mensaje_estado = f"Evaluando descalaje O₂ - Posible alta"
                    logger.info(f"  → Posible alta (después de pausa)")
                else:
                    cama.mensaje_estado = f"Evaluando descalaje O₂"
                    logger.info(f"  → Compatible con cama actual (verificar al terminar pausa)")
                
                # Estado siempre OCUPADA durante la pausa
                cama.estado = EstadoCamaEnum.OCUPADA
                cama.estado_updated_at = datetime.utcnow()
                session.add(cama)
                
                tiempo_restante = calcular_tiempo_restante_pausa(paciente, tiempo_espera)
                mensaje_broadcast = f"Evaluando descalaje de oxígeno ({tiempo_restante}s restantes)"
            
            # ============================================
            # CASO 2: Ya estaba en pausa (sin nuevo descalaje)
            # ============================================
            elif ya_en_pausa_oxigeno:
                # Mantener la pausa activa
                paciente.oxigeno_desactivado_at = timestamp_pausa_original
                tiempo_restante = calcular_tiempo_restante_pausa(paciente, tiempo_espera)
                
                # Reevaluar si ahora requiere nueva cama
                if service.paciente_requiere_nueva_cama(paciente, cama):
                    paciente.requiere_nueva_cama = True
                    cama.mensaje_estado = f"Evaluando descalaje O₂ - Requiere nueva cama"
                    logger.info(f"Paciente {paciente.nombre}: Ahora requiere nueva cama ({tiempo_restante}s restantes)")
                elif service.puede_sugerir_alta(paciente):
                    cama.mensaje_estado = f"Evaluando descalaje O₂ - Posible alta"
                    logger.info(f"Paciente {paciente.nombre}: Posible alta ({tiempo_restante}s restantes)")
                else:
                    cama.mensaje_estado = f"Evaluando descalaje O₂"
                    logger.info(f"Paciente {paciente.nombre}: Compatible ({tiempo_restante}s restantes)")
                
                cama.estado = EstadoCamaEnum.OCUPADA
                cama.estado_updated_at = datetime.utcnow()
                session.add(cama)
                
                mensaje_broadcast = f"Reevaluación durante pausa de oxígeno ({tiempo_restante}s restantes)"
            
            # ============================================
            # CASO 3: Sin pausa activa, sin descalaje
            # ============================================
            else:
                # ============================================
                # VERIFICAR SI HAY DERIVACIÓN SOLICITADA
                # Si hay derivación, NO evaluar estado normalmente.
                # La derivación manejará el estado de la cama.
                # ============================================
                hay_derivacion_nueva = (
                    paciente_data.derivacion_hospital_destino_id 
                    and not derivacion_activa
                )
                
                if hay_derivacion_nueva:
                    # Hay derivación solicitada: NO cambiar el estado de la cama aquí
                    # El servicio de derivación lo pondrá en ESPERA_DERIVACION
                    logger.info(
                        f"Paciente {paciente.nombre}: Derivación solicitada a "
                        f"{paciente_data.derivacion_hospital_destino_id}, "
                        f"saltando evaluación de estado normal"
                    )
                else:
                    # NO hay derivación: evaluar estado normalmente
                    nuevo_estado, nuevo_mensaje = service.evaluar_estado_post_reevaluacion(paciente, cama)
                    
                    if nuevo_estado != cama.estado:
                        cama.estado = nuevo_estado
                        cama.mensaje_estado = nuevo_mensaje
                        cama.estado_updated_at = datetime.utcnow()
                        session.add(cama)
                        
                        logger.info(f"Paciente {paciente.nombre}: Estado actualizado a {nuevo_estado.value}")
    
    # ============================================
    # AGREGAR PACIENTE A LA SESIÓN ANTES DE DERIVACIÓN
    # Esto asegura que los cambios del paciente se incluyan
    # cuando el servicio de derivación haga commit
    # ============================================
    session.add(paciente)
    
    # ============================================
    # MANEJAR DERIVACIÓN SI SE SOLICITA
    # IMPORTANTE: Procesar ANTES del commit normal porque
    # el servicio de derivación hace su propio commit interno
    # que incluirá todos los cambios pendientes de la sesión
    # ============================================
    derivacion_procesada = False
    if paciente_data.derivacion_hospital_destino_id and not derivacion_activa:
        try:
            derivacion_service = DerivacionService(session)
            
            # El servicio de derivación:
            # 1. Cambia la cama a ESPERA_DERIVACION
            # 2. Actualiza el paciente con derivacion_estado, etc.
            # 3. Hace commit (que incluye TODOS los cambios pendientes)
            resultado = derivacion_service.solicitar_derivacion(
                paciente.id,
                paciente_data.derivacion_hospital_destino_id,
                paciente_data.derivacion_motivo or "Derivación solicitada en reevaluación"
            )
            
            derivacion_procesada = True
            mensaje_broadcast = f"Derivación solicitada a hospital destino"
            
            logger.info(f"Derivación procesada para paciente {paciente.nombre}: {resultado.mensaje}")
            
        except Exception as e:
            logger.error(f"Error al solicitar derivación para {paciente.nombre}: {e}")
            # Si falla la derivación, hacer commit de los cambios del paciente sin derivación
            session.commit()
            derivacion_procesada = False
    else:
        # No hay derivación: hacer commit normal
        session.commit()
    
    # Refrescar el paciente después del commit
    session.refresh(paciente)
    
    # ============================================
    # NOTIFICACIONES POST-COMMIT
    # ============================================
    if derivacion_procesada:
        try:
            await manager.send_notification(
                {
                    "tipo": "derivacion_solicitada",
                    "paciente_id": paciente.id,
                    "paciente_nombre": paciente.nombre,
                    "hospital_destino_id": paciente_data.derivacion_hospital_destino_id,
                },
                notification_type="info",
                hospital_id=paciente_data.derivacion_hospital_destino_id
            )
        except Exception as e:
            logger.error(f"Error al enviar notificación de derivación: {e}")
    
    await manager.broadcast({
        "tipo": "paciente_actualizado",
        "paciente_id": paciente_id,
        "hospital_id": paciente.hospital_id,
        "mensaje": mensaje_broadcast,
        "reload": True
    })
    
    return crear_paciente_response(paciente)


@router.post("/{paciente_id}/buscar-cama", response_model=MessageResponse)
async def buscar_cama_paciente(
    paciente_id: str,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Inicia búsqueda de nueva cama para paciente hospitalizado.
    Solo MEDICO puede iniciar búsqueda de cama.

    IMPORTANTE: No permite iniciar búsqueda si el paciente está en pausa de oxígeno.
    """
    # Verificar que solo MEDICO puede iniciar búsqueda
    if current_user.rol not in [RolEnum.MEDICO, RolEnum.PROGRAMADOR]:
        raise HTTPException(
            status_code=403,
            detail="Solo los médicos pueden iniciar búsqueda de cama"
        )

    # Verificar permiso
    if not current_user.tiene_permiso(PermisoEnum.BUSQUEDA_CAMA_INICIAR):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para iniciar búsqueda de cama"
        )
    repo = PacienteRepository(session)
    service = AsignacionService(session)
    
    paciente = repo.obtener_por_id(paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    # Verificar si está en pausa de oxígeno
    if paciente.esperando_evaluacion_oxigeno:
        tiempo_espera = obtener_tiempo_espera_oxigeno(session)
        tiempo_restante = calcular_tiempo_restante_pausa(paciente, tiempo_espera)
        
        if tiempo_restante > 0:
            raise HTTPException(
                status_code=400,
                detail=f"El paciente está en evaluación de oxígeno. Tiempo restante: {tiempo_restante} segundos. "
                       f"Puede omitir la espera si es clínicamente apropiado."
            )
    
    try:
        resultado = service.iniciar_busqueda_cama(paciente_id)
        
        await manager.broadcast({
            "tipo": "busqueda_iniciada",
            "paciente_id": paciente_id,
            "reload": True
        })
        
        return MessageResponse(success=True, message=resultado.mensaje)
        
    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{paciente_id}/verificar-disponibilidad-hospital")
def verificar_disponibilidad_tipo_cama(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """
    Verifica si el hospital actual del paciente tiene el tipo de cama requerido.

    ACTUALIZADO v4.0: Ahora distingue entre:
    - No tener el tipo de servicio (debe buscar en red)
    - Tener el servicio pero sin camas libres (solo lista de espera)

    Returns:
        - tiene_tipo_servicio: Si el hospital tiene el tipo de servicio requerido
        - tiene_camas_libres: Si hay camas libres disponibles en ese servicio
        - mensaje: Mensaje explicativo de la situación

    Casos de uso:
    - tiene_tipo_servicio=False → Buscar en otros hospitales
    - tiene_tipo_servicio=True, tiene_camas_libres=False → Lista de espera únicamente
    - tiene_tipo_servicio=True, tiene_camas_libres=True → Proceder con búsqueda normal
    """
    repo = PacienteRepository(session)
    service = AsignacionService(session)

    paciente = repo.obtener_por_id(paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    tiene_tipo_servicio, tiene_camas_libres, mensaje = service.verificar_disponibilidad_tipo_cama_hospital(
        paciente,
        paciente.hospital_id
    )

    return {
        "tiene_tipo_servicio": tiene_tipo_servicio,
        "tiene_camas_libres": tiene_camas_libres,
        "mensaje": mensaje,
        "paciente_id": paciente_id,
        "hospital_id": paciente.hospital_id
    }


@router.get("/{paciente_id}/buscar-camas-red")
def buscar_camas_en_red_hospitalaria(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """
    Busca camas compatibles para el paciente en TODA la red hospitalaria.
    
    Excluye el hospital actual del paciente de la búsqueda.
    Retorna todas las camas disponibles que cumplen con los requerimientos.
    """
    repo = PacienteRepository(session)
    service = AsignacionService(session)
    
    paciente = repo.obtener_por_id(paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    resultado = service.buscar_camas_en_red(paciente_id, paciente.hospital_id)
    
    # Serializar las camas
    camas_serializadas = []
    for cama in resultado.camas:
        camas_serializadas.append({
            "cama_id": cama.cama_id,
            "cama_identificador": cama.cama_identificador,
            "hospital_id": cama.hospital_id,
            "hospital_nombre": cama.hospital_nombre,
            "hospital_codigo": cama.hospital_codigo,
            "servicio_id": cama.servicio_id,
            "servicio_nombre": cama.servicio_nombre,
            "servicio_tipo": cama.servicio_tipo,
            "sala_id": cama.sala_id,
            "sala_numero": cama.sala_numero,
            "sala_es_individual": cama.sala_es_individual
        })
    
    return {
        "encontradas": resultado.encontradas,
        "cantidad": len(camas_serializadas),
        "camas": camas_serializadas,
        "mensaje": resultado.mensaje,
        "paciente_id": paciente_id,
        "hospital_origen_id": paciente.hospital_id
    }

@router.delete("/{paciente_id}/cancelar-busqueda", response_model=MessageResponse)
async def cancelar_busqueda(
    paciente_id: str,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Cancela búsqueda de cama. Solo MEDICO puede cancelar."""
    # Verificar que solo MEDICO puede cancelar búsqueda
    if current_user.rol not in [RolEnum.MEDICO, RolEnum.PROGRAMADOR]:
        raise HTTPException(
            status_code=403,
            detail="Solo los médicos pueden cancelar búsqueda de cama"
        )
    service = AsignacionService(session)
    
    try:
        resultado = service.cancelar_busqueda(paciente_id)
        
        await manager.broadcast({
            "tipo": "busqueda_cancelada",
            "paciente_id": paciente_id,
            "reload": True
        })
        
        return MessageResponse(success=True, message=resultado.mensaje)
        
    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

@router.post("/{paciente_id}/cancelar-y-volver", summary="Cancelar búsqueda y volver a cama")
async def cancelar_busqueda_y_volver_a_cama(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """
    Cancela la búsqueda de cama para un paciente y lo devuelve a su cama actual.
    
    Solo funciona si el paciente tiene una cama asignada (cama_id).
    - Remueve al paciente de la lista de espera
    - Cambia el estado de la cama de CAMA_EN_ESPERA a OCUPADA
    - Limpia cama_destino_id si existe
    
    Retorna error si el paciente no tiene cama asignada.
    """
    from sqlmodel import select
    
    # Buscar paciente
    paciente = session.exec(select(Paciente).where(Paciente.id == paciente_id)).first()
    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado"
        )
    
    # Verificar que tiene cama asignada
    if not paciente.cama_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El paciente no tiene cama asignada. Use el endpoint de eliminar en su lugar."
        )
    
    try:
        # Obtener la cama actual
        cama = session.exec(select(Cama).where(Cama.id == paciente.cama_id)).first()

        # Remover de lista de espera
        from app.services.prioridad_service import gestor_colas_global
        if paciente.hospital_id:
            cola = gestor_colas_global.obtener_cola(paciente.hospital_id)
            if cola.contiene(paciente_id):
                cola.remover(paciente_id)
                logger.info(f"Paciente {paciente_id} removido de lista de espera")
        
        # Si tenía cama destino asignada, liberarla
        if paciente.cama_destino_id:
            cama_destino = session.exec(select(Cama).where(Cama.id == paciente.cama_destino_id)).first()
            if cama_destino and cama_destino.estado == EstadoCamaEnum.TRASLADO_ENTRANTE:
                cama_destino.estado = EstadoCamaEnum.LIBRE
                cama_destino.paciente_entrante_id = None
                session.add(cama_destino)
                logger.info(f"Cama destino {cama_destino.identificador} liberada")
            paciente.cama_destino_id = None
        
        # Cambiar estado de la cama actual a OCUPADA
        if cama:
            cama.estado = EstadoCamaEnum.OCUPADA
            session.add(cama)
            logger.info(f"Cama {cama.identificador} cambiada a OCUPADA")
        
        # Actualizar estado del paciente
        paciente.en_lista_espera = False
        session.add(paciente)
        
        session.commit()
        
        # Notificar cambios via WebSocket
        try:
            await manager.broadcast({
                "tipo": "cama_actualizada",
                "cama_id": str(cama.id) if cama else None,
                "estado": "ocupada",
                "reload": True
            })
        except Exception as ws_error:
            logger.warning(f"Error al notificar WebSocket: {ws_error}")
        
        return {
            "message": f"Búsqueda cancelada. Paciente volvió a cama {cama.identificador if cama else 'anterior'}",
            "paciente_id": paciente_id,
            "cama_id": str(cama.id) if cama else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error al cancelar búsqueda: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar: {str(e)}"
        )


@router.delete("/{paciente_id}/eliminar", summary="Eliminar paciente sin cama del sistema")
async def eliminar_paciente_sin_cama(
    paciente_id: str,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Elimina un paciente que NO tiene cama asignada del sistema.
    Solo MEDICO puede eliminar pacientes.
    
    Solo funciona si el paciente NO tiene cama (cama_id es None).
    - Remueve al paciente de la lista de espera
    - Elimina el registro del paciente de la base de datos
    
    Retorna error si el paciente tiene cama asignada (usar cancelar-y-volver en su lugar).
    """
    # Verificar que solo MEDICO puede eliminar
    if current_user.rol not in [RolEnum.MEDICO, RolEnum.PROGRAMADOR]:
        raise HTTPException(
            status_code=403,
            detail="Solo los médicos pueden eliminar pacientes"
        )

    from sqlmodel import select

    # Buscar paciente
    paciente = session.exec(select(Paciente).where(Paciente.id == paciente_id)).first()
    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado"
        )

    # Verificar que NO tiene cama asignada
    if paciente.cama_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El paciente tiene cama asignada. Use el endpoint de cancelar-y-volver en su lugar."
        )
    
    nombre_paciente = paciente.nombre  # Guardar para el mensaje

    try:
        # Remover de lista de espera si está
        from app.services.prioridad_service import gestor_colas_global
        if paciente.hospital_id:
            cola = gestor_colas_global.obtener_cola(paciente.hospital_id)
            if cola.contiene(paciente_id):
                cola.remover(paciente_id)
                logger.info(f"Paciente {paciente_id} removido de lista de espera")
        
        # Si tenía cama destino asignada (aunque no debería), liberarla
        if paciente.cama_destino_id:
            cama_destino = session.exec(select(Cama).where(Cama.id == paciente.cama_destino_id)).first()
            if cama_destino:
                cama_destino.estado = EstadoCamaEnum.LIBRE
                cama_destino.paciente_entrante_id = None
                session.add(cama_destino)
        
        # Eliminar el paciente
        session.delete(paciente)
        session.commit()
        
        logger.info(f"Paciente {nombre_paciente} ({paciente_id}) eliminado del sistema")
        
        # Notificar cambios via WebSocket
        try:
            await manager.broadcast({
                "tipo": "paciente_eliminado",
                "paciente_id": paciente_id,
                "reload": True
            })
        except Exception as ws_error:
            logger.warning(f"Error al notificar WebSocket: {ws_error}")
        
        return {
            "message": f"Paciente {nombre_paciente} eliminado del sistema",
            "paciente_id": paciente_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error al eliminar paciente: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar: {str(e)}"
        )


@router.post("/{paciente_id}/omitir-pausa-oxigeno", response_model=MessageResponse)
async def omitir_pausa_oxigeno(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """
    Omite la pausa de evaluación de oxígeno y procede inmediatamente.
    
    Evalúa si el paciente:
    - Requiere nueva cama → CAMA_EN_ESPERA
    - Puede ser dado de alta → ALTA_SUGERIDA
    - Es compatible con cama actual → OCUPADA
    """
    repo = PacienteRepository(session)
    cama_repo = CamaRepository(session)
    service = AsignacionService(session)
    
    paciente = repo.obtener_por_id(paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    if not paciente.esperando_evaluacion_oxigeno:
        raise HTTPException(
            status_code=400, 
            detail="El paciente no está en espera de evaluación de oxígeno"
        )
    
    if not paciente.cama_id:
        raise HTTPException(
            status_code=400,
            detail="El paciente no tiene cama asignada"
        )
    
    cama = cama_repo.obtener_por_id(paciente.cama_id)
    if not cama:
        raise HTTPException(status_code=404, detail="Cama no encontrada")
    
    # Limpiar flags de espera de oxígeno
    paciente.esperando_evaluacion_oxigeno = False
    paciente.oxigeno_desactivado_at = None
    paciente.requerimientos_oxigeno_previos = None
    
    # Evaluar nuevo estado
    mensaje = ""
    
    if service.puede_sugerir_alta(paciente):
        cama.estado = EstadoCamaEnum.ALTA_SUGERIDA
        cama.mensaje_estado = "Se sugiere evaluar alta"
        paciente.requiere_nueva_cama = False
        mensaje = "Evaluación completada: Se sugiere dar de alta al paciente"
        logger.info(f"Paciente {paciente.nombre}: Pausa omitida → ALTA_SUGERIDA")
        
    elif service.paciente_requiere_nueva_cama(paciente, cama) or paciente.requiere_nueva_cama:
        cama.estado = EstadoCamaEnum.CAMA_EN_ESPERA
        cama.mensaje_estado = "Paciente requiere nueva cama"
        paciente.requiere_nueva_cama = True
        mensaje = "Evaluación completada: Paciente requiere nueva cama"
        logger.info(f"Paciente {paciente.nombre}: Pausa omitida → CAMA_EN_ESPERA")
        
    else:
        cama.estado = EstadoCamaEnum.OCUPADA
        cama.mensaje_estado = None
        paciente.requiere_nueva_cama = False
        mensaje = "Evaluación completada: Paciente compatible con cama actual"
        logger.info(f"Paciente {paciente.nombre}: Pausa omitida → OCUPADA (compatible)")
    
    cama.estado_updated_at = datetime.utcnow()
    paciente.updated_at = datetime.utcnow()
    
    session.add(cama)
    session.add(paciente)
    session.commit()
    
    await manager.broadcast({
        "tipo": "pausa_oxigeno_omitida",
        "paciente_id": paciente_id,
        "hospital_id": paciente.hospital_id,
        "nuevo_estado": cama.estado.value,
        "mensaje": mensaje,
        "reload": True,
        "play_sound": True
    })
    
    return MessageResponse(success=True, message=mensaje)


@router.get("/{paciente_id}/estado-pausa-oxigeno")
def obtener_estado_pausa_oxigeno(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """
    Obtiene el estado de la pausa de oxígeno de un paciente.
    
    Útil para el frontend para mostrar el timer y estado del botón.
    """
    repo = PacienteRepository(session)
    paciente = repo.obtener_por_id(paciente_id)
    
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    tiempo_espera = obtener_tiempo_espera_oxigeno(session)
    tiempo_restante = calcular_tiempo_restante_pausa(paciente, tiempo_espera)
    
    return {
        "paciente_id": paciente_id,
        "en_pausa": paciente.esperando_evaluacion_oxigeno,
        "tiempo_total_segundos": tiempo_espera,
        "tiempo_restante_segundos": tiempo_restante,
        "tiempo_transcurrido_segundos": tiempo_espera - tiempo_restante if paciente.esperando_evaluacion_oxigeno else 0,
        "requiere_nueva_cama": paciente.requiere_nueva_cama,
        "puede_buscar_cama": not paciente.esperando_evaluacion_oxigeno or tiempo_restante == 0,
        "inicio_pausa": paciente.oxigeno_desactivado_at.isoformat() if paciente.oxigeno_desactivado_at else None
    }


@router.get("/{paciente_id}/prioridad")
def obtener_prioridad_paciente(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """Obtiene la prioridad calculada de un paciente con desglose."""
    repo = PacienteRepository(session)
    prioridad_service = PrioridadService(session)
    
    paciente = repo.obtener_por_id(paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    explicacion = prioridad_service.explicar_prioridad(paciente)
    
    return {
        "paciente_id": paciente_id,
        "nombre": paciente.nombre,
        "prioridad_total": explicacion.puntaje_total,
        "desglose": {
            "tipo_paciente": explicacion.puntaje_tipo,
            "complejidad": explicacion.puntaje_complejidad,
            "edad": explicacion.puntaje_edad,
            "aislamiento": explicacion.puntaje_aislamiento,
            "tiempo_espera": explicacion.puntaje_tiempo,
        },
        "detalles": explicacion.detalles
    }


@router.post("/{paciente_id}/documento", response_model=MessageResponse)
async def subir_documento(
    paciente_id: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """Sube un documento adjunto para un paciente."""
    repo = PacienteRepository(session)
    paciente = repo.obtener_por_id(paciente_id)
    
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Solo se permiten archivos PDF"
        )
    
    filename = f"{uuid.uuid4()}_{file.filename}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)
    
    with open(filepath, "wb") as f:
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=400,
                detail="El archivo excede el tamaño máximo permitido"
            )
        f.write(content)
    
    # Eliminar documento anterior si existe
    if paciente.documento_adjunto:
        old_filepath = os.path.join(settings.UPLOAD_DIR, paciente.documento_adjunto)
        if os.path.exists(old_filepath):
            try:
                os.remove(old_filepath)
            except Exception as e:
                logger.warning(f"No se pudo eliminar documento anterior: {e}")
    
    paciente.documento_adjunto = filename
    session.add(paciente)
    session.commit()
    
    return MessageResponse(
        success=True,
        message="Documento subido correctamente",
        data={"filename": filename}
    )


@router.get("/{paciente_id}/documento")
def obtener_documento(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """Obtiene información del documento adjunto de un paciente."""
    repo = PacienteRepository(session)
    paciente = repo.obtener_por_id(paciente_id)
    
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    if not paciente.documento_adjunto:
        raise HTTPException(status_code=404, detail="El paciente no tiene documento adjunto")
    
    return {
        "paciente_id": paciente_id,
        "filename": paciente.documento_adjunto,
        "url": f"/uploads/{paciente.documento_adjunto}"
    }

@router.get("/{paciente_id}/estado-timers")
def obtener_estado_timers(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    '''
    Obtiene el estado de los timers de monitorización y observación de un paciente.
      
    Retorna tiempo total, tiempo transcurrido, tiempo restante y estado.
    '''
    repo = PacienteRepository(session)
    paciente = repo.obtener_por_id(paciente_id)
    
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    ahora = datetime.utcnow()
    
    # Calcular estado del timer de observación
    observacion_info = None
    if paciente.observacion_tiempo_horas and paciente.observacion_inicio:
        tiempo_total_seg = paciente.observacion_tiempo_horas * 3600
        tiempo_transcurrido = (ahora - paciente.observacion_inicio).total_seconds()
        tiempo_restante = max(0, tiempo_total_seg - tiempo_transcurrido)
        
        observacion_info = {
            "activo": True,
            "tiempo_total_horas": paciente.observacion_tiempo_horas,
            "tiempo_total_segundos": tiempo_total_seg,
            "tiempo_transcurrido_segundos": int(tiempo_transcurrido),
            "tiempo_restante_segundos": int(tiempo_restante),
            "porcentaje_completado": min(100, (tiempo_transcurrido / tiempo_total_seg) * 100),
            "inicio": paciente.observacion_inicio.isoformat(),
            "completado": tiempo_restante <= 0,
            "motivo": paciente.motivo_observacion,
            "justificacion": paciente.justificacion_observacion
        }
    else:
        observacion_info = {
            "activo": False,
            "tiempo_total_horas": None,
            "tiempo_restante_segundos": None,
            "completado": None
        }
    
    # Calcular estado del timer de monitorización
    monitorizacion_info = None
    if paciente.monitorizacion_tiempo_horas and paciente.monitorizacion_inicio:
        tiempo_total_seg = paciente.monitorizacion_tiempo_horas * 3600
        tiempo_transcurrido = (ahora - paciente.monitorizacion_inicio).total_seconds()
        tiempo_restante = max(0, tiempo_total_seg - tiempo_transcurrido)
        
        monitorizacion_info = {
            "activo": True,
            "tiempo_total_horas": paciente.monitorizacion_tiempo_horas,
            "tiempo_total_segundos": tiempo_total_seg,
            "tiempo_transcurrido_segundos": int(tiempo_transcurrido),
            "tiempo_restante_segundos": int(tiempo_restante),
            "porcentaje_completado": min(100, (tiempo_transcurrido / tiempo_total_seg) * 100),
            "inicio": paciente.monitorizacion_inicio.isoformat(),
            "completado": tiempo_restante <= 0,
            "motivo": paciente.motivo_monitorizacion,
            "justificacion": paciente.justificacion_monitorizacion
        }
    else:
        monitorizacion_info = {
            "activo": False,
            "tiempo_total_horas": None,
            "tiempo_restante_segundos": None,
            "completado": None
        }
    
    return {
        "paciente_id": paciente_id,
        "paciente_nombre": paciente.nombre,
        "observacion": observacion_info,
        "monitorizacion": monitorizacion_info
    }

"""
Endpoint de Información de Traslado de Paciente
AGREGAR A: app/api/pacientes.py (al final del archivo)

Este endpoint devuelve información completa del traslado
incluyendo teléfonos de servicios de origen y destino.

ACTUALIZADO: Los teléfonos de urgencias y ambulatorio se obtienen
del hospital correspondiente, no de una configuración global.
"""

from pydantic import BaseModel
from typing import Optional

# ============================================
# SCHEMA DE RESPUESTA
# ============================================
class InfoTrasladoResponse(BaseModel):
    """Información de traslado de un paciente con teléfonos."""
    # Origen
    origen_tipo: Optional[str] = None
    origen_hospital_nombre: Optional[str] = None
    origen_hospital_codigo: Optional[str] = None
    origen_servicio_nombre: Optional[str] = None
    origen_servicio_telefono: Optional[str] = None
    origen_cama_identificador: Optional[str] = None
    
    # Destino
    destino_servicio_nombre: Optional[str] = None
    destino_servicio_telefono: Optional[str] = None
    destino_cama_identificador: Optional[str] = None
    destino_hospital_nombre: Optional[str] = None
    
    # Estado
    tiene_cama_origen: bool = False
    tiene_cama_destino: bool = False
    en_traslado: bool = False


@router.get("/{paciente_id}/info-traslado", response_model=InfoTrasladoResponse)
def obtener_info_traslado(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """
    Obtiene información completa de traslado de un paciente,
    incluyendo teléfonos de servicios de origen y destino.
    
    Los teléfonos de urgencias y ambulatorio se obtienen del hospital
    correspondiente al paciente, ya que cada hospital tiene sus propios números.
    
    Para pacientes derivados, el teléfono de origen es del hospital de origen.
    """
    from app.repositories.hospital_repo import HospitalRepository
    
    # Obtener paciente
    paciente_repo = PacienteRepository(session)
    paciente = paciente_repo.obtener_por_id(paciente_id)
    
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    # Obtener hospital actual del paciente
    hospital_repo = HospitalRepository(session)
    hospital_actual = hospital_repo.obtener_por_id(paciente.hospital_id) if paciente.hospital_id else None
    
    # Inicializar respuesta
    info = InfoTrasladoResponse()
    
    # ============================================
    # DETERMINAR ORIGEN
    # ============================================
    
    # Caso 1: Paciente derivado de otro hospital
    if paciente.tipo_paciente == TipoPacienteEnum.DERIVADO or paciente.derivacion_estado == "aceptada":
        info.origen_tipo = "derivado"
        
        # Buscar información del hospital de origen desde la cama de derivación
        if paciente.cama_origen_derivacion_id:
            cama_repo = CamaRepository(session)
            cama_origen = cama_repo.obtener_por_id(paciente.cama_origen_derivacion_id)
            if cama_origen:
                info.origen_cama_identificador = cama_origen.identificador
                if cama_origen.sala and cama_origen.sala.servicio:
                    info.origen_servicio_nombre = cama_origen.sala.servicio.nombre
                    # Teléfono del servicio de origen
                    info.origen_servicio_telefono = cama_origen.sala.servicio.telefono
                    
                    # Hospital de origen (para derivados)
                    hospital_origen = hospital_repo.obtener_por_id(cama_origen.sala.servicio.hospital_id)
                    if hospital_origen:
                        info.origen_hospital_nombre = hospital_origen.nombre
                        info.origen_hospital_codigo = hospital_origen.codigo
                        # Si no hay teléfono de servicio, usar urgencias del hospital origen
                        if not info.origen_servicio_telefono:
                            info.origen_servicio_telefono = hospital_origen.telefono_urgencias
        
        # Fallback: buscar hospital origen si no lo encontramos por cama
        if not info.origen_hospital_nombre:
            # Intentar obtener el hospital de origen desde otros campos
            # El paciente derivado viene de un hospital diferente al actual
            pass
    
    # Caso 2: Paciente hospitalizado (tiene cama actual en este hospital)
    elif paciente.cama_id:
        info.origen_tipo = "hospitalizado"
        info.tiene_cama_origen = True
        
        cama_repo = CamaRepository(session)
        cama_origen = cama_repo.obtener_por_id(paciente.cama_id)
        if cama_origen:
            info.origen_cama_identificador = cama_origen.identificador
            if cama_origen.sala and cama_origen.sala.servicio:
                info.origen_servicio_nombre = cama_origen.sala.servicio.nombre
                info.origen_servicio_telefono = cama_origen.sala.servicio.telefono
    
    # Caso 3: Paciente de urgencias (sin cama asignada aún)
    elif paciente.tipo_paciente == TipoPacienteEnum.URGENCIA:
        info.origen_tipo = "urgencia"
        info.origen_servicio_nombre = "Urgencias"
        # Teléfono de urgencias del hospital del paciente
        if hospital_actual:
            info.origen_servicio_telefono = hospital_actual.telefono_urgencias
            info.origen_hospital_nombre = hospital_actual.nombre
    
    # Caso 4: Paciente ambulatorio (sin cama asignada aún)
    elif paciente.tipo_paciente == TipoPacienteEnum.AMBULATORIO:
        info.origen_tipo = "ambulatorio"
        info.origen_servicio_nombre = "Ambulatorio"
        # Teléfono de ambulatorio del hospital del paciente
        if hospital_actual:
            info.origen_servicio_telefono = hospital_actual.telefono_ambulatorio
            info.origen_hospital_nombre = hospital_actual.nombre
    
    # ============================================
    # DETERMINAR DESTINO
    # ============================================
    
    if paciente.cama_destino_id:
        info.tiene_cama_destino = True
        info.en_traslado = True
        
        cama_repo = CamaRepository(session)
        cama_destino = cama_repo.obtener_por_id(paciente.cama_destino_id)
        if cama_destino:
            info.destino_cama_identificador = cama_destino.identificador
            if cama_destino.sala and cama_destino.sala.servicio:
                info.destino_servicio_nombre = cama_destino.sala.servicio.nombre
                info.destino_servicio_telefono = cama_destino.sala.servicio.telefono
                
                # Hospital destino (puede ser diferente para derivaciones)
                hospital_destino = hospital_repo.obtener_por_id(cama_destino.sala.servicio.hospital_id)
                if hospital_destino:
                    info.destino_hospital_nombre = hospital_destino.nombre
    
    # Verificar si está en traslado por estado de cama
    if paciente.cama_id:
        cama_repo = CamaRepository(session)
        cama_actual = cama_repo.obtener_por_id(paciente.cama_id)
        if cama_actual and cama_actual.estado in [
            EstadoCamaEnum.TRASLADO_SALIENTE,
            EstadoCamaEnum.TRASLADO_CONFIRMADO,
            EstadoCamaEnum.CAMA_EN_ESPERA
        ]:
            info.en_traslado = True
    
    return info