"""
Endpoints de Modo Manual.
Operaciones manuales que omiten el flujo automático.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from datetime import datetime
import logging

from app.core.database import get_session
from app.core.auth_dependencies import get_current_user
from app.core.rbac_service import rbac_service
from app.core.websocket_manager import manager
from app.core.exceptions import PacienteNotFoundError, ValidationError, CamaNotFoundError
from app.models.usuario import Usuario, PermisoEnum, RolEnum
from app.schemas.traslado import TrasladoManualRequest, IntercambioRequest
from app.schemas.responses import MessageResponse
from app.services.traslado_service import TrasladoService
from app.services.alta_service import AltaService
from app.services.asignacion_service import AsignacionService
from app.services.derivacion_service import DerivacionService
from app.services.Limpieza_service import LimpiezaService  
from app.repositories.paciente_repo import PacienteRepository
from app.repositories.cama_repo import CamaRepository
from app.models.enums import EstadoCamaEnum, EstadoListaEsperaEnum

router = APIRouter()
logger = logging.getLogger("gestion_camas.manual")


@router.post("/asignar-desde-cama", response_model=MessageResponse)
async def asignar_manual_desde_cama(
    request: TrasladoManualRequest,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Asigna manualmente un paciente a una cama desde otra cama.
    Solo GESTOR_CAMAS de Puerto Montt tiene acceso a modo manual.
    """
    # Verificar acceso a modo manual
    if not rbac_service.puede_usar_modo_manual(current_user, request.paciente_id):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para usar el modo manual (solo GESTOR_CAMAS de Puerto Montt)"
        )
    service = TrasladoService(session)
    
    try:
        resultado = service.traslado_manual(
            request.paciente_id,
            request.cama_destino_id
        )
        
        await manager.send_notification(
            {
                "tipo": "asignacion_manual",
                "paciente_id": request.paciente_id,
                "cama_id": request.cama_destino_id
            },
            notification_type="asignacion",
            play_sound=True
        )
        
        return MessageResponse(success=True, message=resultado.mensaje)
        
    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    except CamaNotFoundError:
        raise HTTPException(status_code=404, detail="Cama no encontrada")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/asignar-desde-lista", response_model=MessageResponse)
async def asignar_manual_desde_lista(
    request: TrasladoManualRequest,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Asigna manualmente un paciente de la lista de espera a una cama.
    Solo GESTOR_CAMAS de Puerto Montt tiene acceso a modo manual.

    CORREGIDO: Usa el método correcto asignar_cama() del AsignacionService.
    """
    # Verificar acceso a modo manual
    if not rbac_service.puede_usar_modo_manual(current_user, request.paciente_id):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para usar el modo manual (solo GESTOR_CAMAS de Puerto Montt)"
        )
    paciente_repo = PacienteRepository(session)
    cama_repo = CamaRepository(session)
    service = AsignacionService(session)
    
    paciente = paciente_repo.obtener_por_id(request.paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    if not paciente.en_lista_espera:
        raise HTTPException(status_code=400, detail="El paciente no está en la lista de espera")
    
    cama = cama_repo.obtener_por_id(request.cama_destino_id)
    if not cama:
        raise HTTPException(status_code=404, detail="Cama no encontrada")
    
    if cama.estado != EstadoCamaEnum.LIBRE:
        raise HTTPException(status_code=400, detail=f"La cama {cama.identificador} no está libre")
    
    try:
        # CORRECCIÓN: Usar asignar_cama con los IDs correctos
        resultado = service.asignar_cama(request.paciente_id, request.cama_destino_id)
        
        if not resultado.exito:
            raise HTTPException(status_code=400, detail=resultado.mensaje)
        
        await manager.send_notification(
            {
                "tipo": "asignacion_manual_lista",
                "paciente_id": request.paciente_id,
                "cama_id": request.cama_destino_id,
                "reload": True
            },
            notification_type="asignacion",
            play_sound=True
        )
        
        return MessageResponse(success=True, message=resultado.mensaje)
        
    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    except CamaNotFoundError:
        raise HTTPException(status_code=404, detail="Cama no encontrada")
    except Exception as e:
        logger.error(f"Error en asignar_manual_desde_lista: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/traslado", response_model=MessageResponse)
async def traslado_manual(
    request: TrasladoManualRequest,
    session: Session = Depends(get_session)
):
    """Realiza un traslado manual inmediato."""
    service = TrasladoService(session)
    
    try:
        resultado = service.traslado_manual(
            request.paciente_id,
            request.cama_destino_id
        )
        
        await manager.send_notification(
            {
                "tipo": "traslado_manual",
                "paciente_id": request.paciente_id,
                "cama_id": request.cama_destino_id
            },
            notification_type="success"
        )
        
        return MessageResponse(success=True, message=resultado.mensaje)
        
    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    except CamaNotFoundError:
        raise HTTPException(status_code=404, detail="Cama no encontrada")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/intercambiar", response_model=MessageResponse)
async def intercambiar_pacientes(
    request: IntercambioRequest,
    session: Session = Depends(get_session)
):
    """Intercambia las camas de dos pacientes."""
    service = TrasladoService(session)
    
    try:
        resultado = service.intercambiar_pacientes(
            request.paciente_a_id,
            request.paciente_b_id
        )
        
        await manager.broadcast({
            "tipo": "intercambio_completado",
            "paciente_a_id": request.paciente_a_id,
            "paciente_b_id": request.paciente_b_id
        })
        
        return MessageResponse(success=True, message=resultado.mensaje)
        
    except PacienteNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/egresar/{paciente_id}", response_model=MessageResponse)
async def egresar_manual(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """Egresa un paciente manualmente (sin proceso de alta)."""
    service = AltaService(session)
    
    try:
        resultado = service.egreso_manual(paciente_id)
        
        await manager.broadcast({
            "tipo": "egreso_manual",
            "paciente_id": paciente_id
        })
        
        return MessageResponse(success=True, message=resultado.mensaje)
        
    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")


@router.delete("/egresar-de-lista/{paciente_id}", response_model=MessageResponse)
async def egresar_de_lista(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """
    Elimina un paciente de la lista de espera.
    
    Flujo según documento:
    
    1. Si paciente DERIVADO (derivacion_estado == "aceptada"):
       - Vuelve a lista de derivados (derivacion_estado = "pendiente")
       - Cama origen pasa a ESPERA_DERIVACION
    
    2. Si paciente HOSPITALIZADO (tiene cama_id):
       - Vuelve a su cama con estado CAMA_EN_ESPERA
       - Se remueve de lista de espera
    
    3. Si paciente SIN CAMA (urgencia/ambulatorio):
       - Se elimina de lista de espera
       - Queda inactivo en el sistema (para trazabilidad)
    """
    paciente_repo = PacienteRepository(session)
    cama_repo = CamaRepository(session)
    service = AsignacionService(session)
    
    paciente = paciente_repo.obtener_por_id(paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    if not paciente.en_lista_espera:
        raise HTTPException(
            status_code=400,
            detail="El paciente no está en la lista de espera"
        )
    
    hospital_id = paciente.hospital_id
    es_derivado = paciente.derivacion_estado == "aceptada"
    tiene_cama = paciente.cama_id is not None
    
    # Liberar cama destino si existe
    if paciente.cama_destino_id:
        cama_destino = cama_repo.obtener_por_id(paciente.cama_destino_id)
        if cama_destino:
            cama_destino.estado = EstadoCamaEnum.LIBRE
            cama_destino.mensaje_estado = None
            cama_destino.estado_updated_at = datetime.utcnow()
            session.add(cama_destino)
        paciente.cama_destino_id = None
    
    if es_derivado:
        # FLUJO DERIVADO: Volver a lista de derivados pendientes
        resultado = service.cancelar_derivacion_desde_lista_espera(paciente_id)
        mensaje = resultado.mensaje
        
    elif tiene_cama:
        # FLUJO HOSPITALIZADO: Volver a cama en espera
        cama_origen = cama_repo.obtener_por_id(paciente.cama_id)
        if cama_origen:
            cama_origen.estado = EstadoCamaEnum.CAMA_EN_ESPERA
            cama_origen.mensaje_estado = "Paciente requiere nueva cama"
            cama_origen.cama_asignada_destino = None
            session.add(cama_origen)
        
        paciente.en_lista_espera = False
        paciente.timestamp_lista_espera = None
        paciente.prioridad_calculada = 0.0
        paciente.requiere_nueva_cama = True
        session.add(paciente)
        session.commit()
        mensaje = "Paciente removido de lista - puede buscar nueva cama"
        
    else:
        # FLUJO SIN CAMA: Eliminar de lista
        paciente.en_lista_espera = False
        paciente.timestamp_lista_espera = None
        paciente.prioridad_calculada = 0.0
        session.add(paciente)
        session.commit()
        mensaje = "Paciente removido de la lista de espera"
    
    await manager.broadcast({
        "tipo": "paciente_removido_lista",
        "paciente_id": paciente_id,
        "hospital_id": hospital_id
    })
    
    return MessageResponse(
        success=True,
        message=mensaje
    )


# ============================================
# ENDPOINT CORREGIDO: Completar egreso fallecido
# ============================================
@router.post("/fallecido/{paciente_id}/completar-egreso", response_model=MessageResponse)
async def completar_egreso_fallecido(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """
    Completa el egreso de un paciente fallecido e inicia limpieza de la cama.
    
    FLUJO CORREGIDO:
    1. Verifica que el paciente está marcado como fallecido
    2. Verifica que la cama está en estado FALLECIDO
    3. Desvincula al paciente de la cama
    4. USA LimpiezaService.iniciar_limpieza() para establecer correctamente:
       - estado = EN_LIMPIEZA
       - limpieza_inicio = datetime.utcnow()
       - mensaje_estado = "En limpieza"
    5. Elimina el paciente de la base de datos
    """
    # NOTA: LimpiezaService ya está importado arriba con L mayúscula
    # NO hacer import aquí para evitar el error de módulo no encontrado
    
    paciente_repo = PacienteRepository(session)
    cama_repo = CamaRepository(session)
    limpieza_service = LimpiezaService(session)  # Usar el import del inicio del archivo
    
    # Obtener paciente
    paciente = paciente_repo.obtener_por_id(paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    # Verificar que está fallecido
    if not paciente.fallecido:
        raise HTTPException(
            status_code=400, 
            detail="El paciente no está marcado como fallecido"
        )
    
    # Verificar que tiene cama asignada
    if not paciente.cama_id:
        raise HTTPException(
            status_code=400,
            detail="El paciente no tiene cama asignada"
        )
    
    # Obtener la cama
    cama = cama_repo.obtener_por_id(paciente.cama_id)
    if not cama:
        raise HTTPException(status_code=404, detail="Cama no encontrada")
    
    # Verificar que la cama está en estado FALLECIDO
    if cama.estado != EstadoCamaEnum.FALLECIDO:
        raise HTTPException(
            status_code=400,
            detail=f"La cama no está en estado fallecido (estado actual: {cama.estado.value})"
        )
    
    # Guardar identificador para el log
    cama_identificador = cama.identificador
    nombre_paciente = paciente.nombre
    cama_id = cama.id
    
    # Desvincular paciente de la cama
    paciente.cama_id = None
    session.add(paciente)
    session.commit()  # Commit para desvincular antes de eliminar
    
    # ============================================
    # CORRECCIÓN CRÍTICA: Usar el servicio de limpieza
    # Esto garantiza que limpieza_inicio se establezca
    # ============================================
    try:
        limpieza_service.iniciar_limpieza(cama_id)
        logger.info(
            f"Egreso fallecido completado: Paciente {nombre_paciente}, "
            f"Cama {cama_identificador} en limpieza"
        )
    except Exception as e:
        logger.error(f"Error al iniciar limpieza: {e}")
        # Fallback manual si el servicio falla
        cama.estado = EstadoCamaEnum.EN_LIMPIEZA
        cama.limpieza_inicio = datetime.utcnow()  # CRÍTICO: Establecer esto
        cama.mensaje_estado = "En limpieza"
        cama.estado_updated_at = datetime.utcnow()
        session.add(cama)
        session.commit()
    
    # Eliminar el paciente
    session.delete(paciente)
    session.commit()
    
    # Notificar via WebSocket
    await manager.broadcast({
        "tipo": "egreso_fallecido_completado",
        "cama_id": cama_id,
        "cama_identificador": cama_identificador,
        "reload": True
    })
    
    return MessageResponse(
        success=True,
        message=f"Egreso completado. Cama {cama_identificador} en proceso de limpieza.",
        data={
            "cama_id": cama_id,
            "paciente_nombre": nombre_paciente
        }
    )


@router.post("/fallecido/{paciente_id}/cancelar", response_model=MessageResponse)
async def cancelar_fallecimiento(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """
    Cancela el registro de fallecimiento de un paciente (SOLO MODO MANUAL).
    
    Revierte el estado del paciente y la cama al estado anterior.
    Este endpoint solo debe usarse en casos excepcionales de error en el registro.
    """
    paciente_repo = PacienteRepository(session)
    cama_repo = CamaRepository(session)
    
    # Verificar que el modo manual está activo
    from app.models.configuracion import ConfiguracionSistema
    from sqlmodel import select
    
    config = session.exec(select(ConfiguracionSistema)).first()
    if not config or not config.modo_manual:
        raise HTTPException(
            status_code=403,
            detail="Esta acción solo está disponible en modo manual"
        )
    
    paciente = paciente_repo.obtener_por_id(paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    if not paciente.fallecido:
        raise HTTPException(
            status_code=400,
            detail="El paciente no está marcado como fallecido"
        )
    
    # Restaurar estado de la cama
    if paciente.cama_id:
        cama = cama_repo.obtener_por_id(paciente.cama_id)
        if cama:
            # Restaurar al estado anterior guardado, o OCUPADA por defecto
            estado_anterior = paciente.estado_cama_anterior_fallecimiento
            if estado_anterior:
                try:
                    cama.estado = EstadoCamaEnum(estado_anterior)
                except ValueError:
                    cama.estado = EstadoCamaEnum.OCUPADA
            else:
                cama.estado = EstadoCamaEnum.OCUPADA
            
            cama.mensaje_estado = None
            cama.estado_updated_at = datetime.utcnow()
            session.add(cama)
    
    # Limpiar datos de fallecimiento
    hospital_id = paciente.hospital_id
    paciente.fallecido = False
    paciente.causa_fallecimiento = None
    paciente.fallecido_at = None
    paciente.estado_cama_anterior_fallecimiento = None
    paciente.updated_at = datetime.utcnow()
    session.add(paciente)
    session.commit()
    
    await manager.broadcast({
        "tipo": "fallecimiento_cancelado",
        "paciente_id": paciente_id,
        "hospital_id": hospital_id
    })
    
    return MessageResponse(
        success=True,
        message="Registro de fallecimiento cancelado. Paciente restaurado a estado anterior."
    )


# ============================================
# CORREGIDO: Cancelar asignación desde lista de espera
# ============================================

@router.post("/cancelar-asignacion-lista/{paciente_id}", response_model=MessageResponse)
async def cancelar_asignacion_desde_lista(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """
    Cancela la asignación de cama destino manteniendo al paciente en lista de espera.
    
    Este endpoint se usa cuando un paciente tiene una cama asignada (cama_destino_id)
    pero se quiere cancelar esa asignación sin sacarlo de la lista de espera.
    
    Flujo:
    1. Liberar la cama destino (estado = LIBRE)
    2. Si tiene cama de origen (cama_id):
       - Cama origen pasa a TRASLADO_SALIENTE
    3. Si NO tiene cama de origen:
       - Solo permanece en lista de espera
       - Puede ser reevaluado o derivado
    4. Paciente se mantiene en lista de espera con estado "esperando"
    
    Args:
        paciente_id: ID del paciente
    
    Returns:
        MessageResponse con resultado de la operación
    """
    paciente_repo = PacienteRepository(session)
    cama_repo = CamaRepository(session)
    
    # Obtener paciente
    paciente = paciente_repo.obtener_por_id(paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    # Verificar que está en lista de espera
    if not paciente.en_lista_espera:
        raise HTTPException(
            status_code=400,
            detail="El paciente no está en la lista de espera"
        )
    
    # Verificar que tiene cama destino asignada
    if not paciente.cama_destino_id:
        raise HTTPException(
            status_code=400,
            detail="El paciente no tiene cama destino asignada"
        )
    
    hospital_id = paciente.hospital_id
    tiene_cama_origen = paciente.cama_id is not None
    cama_destino_id = paciente.cama_destino_id
    
    # 1. Liberar la cama destino
    cama_destino = cama_repo.obtener_por_id(paciente.cama_destino_id)
    if cama_destino:
        cama_destino.estado = EstadoCamaEnum.LIBRE
        cama_destino.mensaje_estado = None
        # CORRECCIÓN: Eliminado paciente_entrante_id que no existe en el modelo
        cama_destino.estado_updated_at = datetime.utcnow()
        session.add(cama_destino)
        logger.info(f"Cama destino {cama_destino.identificador} liberada")
    
    # 2. Manejar cama de origen si existe
    if tiene_cama_origen:
        cama_origen = cama_repo.obtener_por_id(paciente.cama_id)
        if cama_origen:
            # Cama origen vuelve a TRASLADO_SALIENTE para seguir buscando
            cama_origen.estado = EstadoCamaEnum.TRASLADO_SALIENTE
            cama_origen.mensaje_estado = "Paciente buscando nueva cama"
            cama_origen.cama_asignada_destino = None
            cama_origen.estado_updated_at = datetime.utcnow()
            session.add(cama_origen)
            logger.info(f"Cama origen {cama_origen.identificador} cambiada a TRASLADO_SALIENTE")
    
    # 3. Actualizar estado del paciente - mantener en lista pero sin asignación
    paciente.cama_destino_id = None
    paciente.estado_lista_espera = EstadoListaEsperaEnum.ESPERANDO
    paciente.servicio_destino = None
    paciente.updated_at = datetime.utcnow()
    session.add(paciente)
    
    session.commit()
    
    # Mensaje según el caso
    if tiene_cama_origen:
        mensaje = "Asignación cancelada. Paciente permanece en lista de espera buscando nueva cama."
    else:
        mensaje = "Asignación cancelada. Paciente permanece en lista de espera."
    
    logger.info(
        f"Asignación cancelada para {paciente.nombre}: "
        f"cama destino {cama_destino_id} liberada, "
        f"tiene_cama_origen={tiene_cama_origen}"
    )
    
    # Notificar via WebSocket
    await manager.broadcast({
        "tipo": "asignacion_cancelada",
        "paciente_id": paciente_id,
        "hospital_id": hospital_id,
        "cama_destino_id": cama_destino_id,
        "reload": True
    })
    
    return MessageResponse(
        success=True,
        message=mensaje,
        data={
            "paciente_id": paciente_id,
            "cama_destino_liberada": cama_destino_id,
            "tiene_cama_origen": tiene_cama_origen
        }
    )