"""
Endpoints de Modo Manual.
Operaciones manuales que omiten el flujo automático.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.database import get_session
from app.core.websocket_manager import manager
from app.core.exceptions import PacienteNotFoundError, ValidationError, CamaNotFoundError
from app.schemas.traslado import TrasladoManualRequest, IntercambioRequest
from app.schemas.responses import MessageResponse
from app.services.traslado_service import TrasladoService
from app.services.alta_service import AltaService
from app.services.asignacion_service import AsignacionService
from app.services.derivacion_service import DerivacionService
from app.repositories.paciente_repo import PacienteRepository
from app.repositories.cama_repo import CamaRepository
from app.models.enums import EstadoCamaEnum

router = APIRouter()


@router.post("/asignar-desde-cama", response_model=MessageResponse)
async def asignar_manual_desde_cama(
    request: TrasladoManualRequest,
    session: Session = Depends(get_session)
):
    """Asigna manualmente un paciente a una cama desde otra cama."""
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
    session: Session = Depends(get_session)
):
    """Asigna manualmente un paciente de la lista de espera a una cama."""
    paciente_repo = PacienteRepository(session)
    cama_repo = CamaRepository(session)
    service = AsignacionService(session)
    
    paciente = paciente_repo.obtener_por_id(request.paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    cama = cama_repo.obtener_por_id(request.cama_destino_id)
    if not cama:
        raise HTTPException(status_code=404, detail="Cama no encontrada")
    
    resultado = service.ejecutar_asignacion(paciente, cama)
    
    if not resultado.exito:
        raise HTTPException(status_code=400, detail=resultado.mensaje)
    
    await manager.send_notification(
        {
            "tipo": "asignacion_manual_lista",
            "paciente_id": request.paciente_id,
            "cama_id": request.cama_destino_id
        },
        notification_type="asignacion",
        play_sound=True
    )
    
    return MessageResponse(success=True, message=resultado.mensaje)


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
            session.add(cama_destino)
    
    paciente.cama_destino_id = None
    
    # Remover de cola de prioridad en memoria
    service.remover_de_cola(paciente)
    
    mensaje = ""
    
    if es_derivado:
        # FLUJO DERIVADO: Volver a lista de derivados
        derivacion_service = DerivacionService(session)
        resultado = derivacion_service.cancelar_derivacion_desde_lista_espera(paciente_id)
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