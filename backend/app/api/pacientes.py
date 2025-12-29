"""
Endpoints de Pacientes.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session
from typing import Optional, List
from datetime import datetime
import os
import uuid
import json
import logging

from app.config import settings
from app.core.database import get_session
from app.core.websocket_manager import manager
from app.core.exceptions import PacienteNotFoundError, ValidationError
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
    session: Session = Depends(get_session)
):
    """
    Crea un nuevo paciente y lo agrega a la cola de espera.
    
    Si se especifica derivacion_hospital_destino_id, se solicita la derivación
    automáticamente después de crear el paciente.
    """
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
        tipo_paciente=paciente_data.tipo_paciente,
        hospital_id=paciente_data.hospital_id,
        en_lista_espera=True,
        timestamp_lista_espera=datetime.utcnow(),
    )
    
    paciente.complejidad_requerida = service.calcular_complejidad(paciente)
    
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
def obtener_paciente(paciente_id: str, session: Session = Depends(get_session)):
    """Obtiene un paciente por ID."""
    repo = PacienteRepository(session)
    paciente = repo.obtener_por_id(paciente_id)
    
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    return crear_paciente_response(paciente)


@router.put("/{paciente_id}", response_model=PacienteResponse)
async def actualizar_paciente(
    paciente_id: str,
    paciente_data: PacienteUpdate,
    session: Session = Depends(get_session)
):
    """
    Actualiza un paciente (reevaluación).
    
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
    repo = PacienteRepository(session)
    cama_repo = CamaRepository(session)
    service = AsignacionService(session)
    
    paciente = repo.obtener_por_id(paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
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
    
    if paciente_data.alta_solicitada is not None:
        paciente.alta_solicitada = paciente_data.alta_solicitada
    if paciente_data.alta_motivo is not None:
        paciente.alta_motivo = paciente_data.alta_motivo
    
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
    
    mensaje_broadcast = "Paciente actualizado"
    tiempo_espera = obtener_tiempo_espera_oxigeno(session)
    
    # Si el paciente tiene cama asignada
    if paciente.cama_id:
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
    session: Session = Depends(get_session)
):
    """
    Inicia búsqueda de nueva cama para paciente hospitalizado.
    
    IMPORTANTE: No permite iniciar búsqueda si el paciente está en pausa de oxígeno.
    """
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
    
    Se usa antes de iniciar búsqueda de cama para determinar si es necesario
    buscar en otros hospitales.
    """
    repo = PacienteRepository(session)
    service = AsignacionService(session)
    
    paciente = repo.obtener_por_id(paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    tiene_tipo, mensaje = service.verificar_disponibilidad_tipo_cama_hospital(
        paciente, 
        paciente.hospital_id
    )
    
    return {
        "tiene_tipo_cama": tiene_tipo,
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
    session: Session = Depends(get_session)
):
    """Cancela búsqueda de cama."""
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