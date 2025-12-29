"""
Endpoints de Traslados.

ACTUALIZADO: Incluye endpoint para cancelar traslados confirmados.

Ubicación: app/api/traslados.py
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.database import get_session
from app.core.websocket_manager import manager
from app.core.exceptions import PacienteNotFoundError, ValidationError, CamaNotFoundError
from app.schemas.responses import MessageResponse
from app.services.traslado_service import TrasladoService

router = APIRouter()


@router.post("/{paciente_id}/completar", response_model=MessageResponse)
async def completar_traslado(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """Completa el traslado de un paciente a su cama destino."""
    service = TrasladoService(session)
    
    try:
        resultado = service.completar_traslado(paciente_id)
        
        await manager.send_notification(
            {
                "tipo": "traslado_completado",
                "paciente_id": paciente_id,
                "cama_destino_id": resultado.cama_destino_id,
                "reload": True,
            },
            notification_type="success"
        )
        
        return MessageResponse(
            success=True,
            message=resultado.mensaje,
            data={
                "cama_origen_id": resultado.cama_origen_id,
                "cama_destino_id": resultado.cama_destino_id
            }
        )
        
    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    except CamaNotFoundError:
        raise HTTPException(status_code=404, detail="Cama destino no encontrada")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{paciente_id}/cancelar", response_model=MessageResponse)
async def cancelar_traslado(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """Cancela un traslado pendiente."""
    service = TrasladoService(session)
    
    try:
        resultado = service.cancelar_traslado(paciente_id)
        
        await manager.broadcast({
            "tipo": "traslado_cancelado",
            "paciente_id": paciente_id,
            "reload": True
        })
        
        return MessageResponse(success=True, message=resultado.mensaje)
        
    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")


@router.post("/{paciente_id}/cancelar-desde-origen", response_model=MessageResponse)
async def cancelar_traslado_desde_origen(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """Cancela traslado desde la cama de origen."""
    service = TrasladoService(session)
    
    try:
        resultado = service.cancelar_traslado(paciente_id)
        
        await manager.broadcast({
            "tipo": "traslado_cancelado_origen",
            "paciente_id": paciente_id,
            "reload": True
        })
        
        return MessageResponse(success=True, message=resultado.mensaje)
        
    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")


@router.post("/{paciente_id}/cancelar-desde-destino", response_model=MessageResponse)
async def cancelar_traslado_desde_destino(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """Cancela traslado desde la cama de destino."""
    service = TrasladoService(session)
    
    try:
        resultado = service.cancelar_traslado(paciente_id)
        
        await manager.broadcast({
            "tipo": "traslado_cancelado_destino",
            "paciente_id": paciente_id,
            "reload": True
        })
        
        return MessageResponse(success=True, message=resultado.mensaje)
        
    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")


# ============================================
# NUEVO ENDPOINT: Cancelar traslado confirmado
# ============================================

@router.post("/{paciente_id}/cancelar-confirmado", response_model=MessageResponse)
async def cancelar_traslado_confirmado(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """
    Cancela un traslado que está en estado TRASLADO_CONFIRMADO.
    
    Flujo:
    1. Paciente elimina su asignación en la cama destino
    2. Paciente se sale de la lista de espera  
    3. Cama destino vuelve a LIBRE
    4. Cama origen vuelve a CAMA_EN_ESPERA
    
    Este endpoint se usa cuando se quiere cancelar un traslado que ya fue
    confirmado pero el paciente aún no ha sido movido físicamente.
    """
    service = TrasladoService(session)
    
    try:
        resultado = service.cancelar_traslado_confirmado(paciente_id)
        
        await manager.broadcast({
            "tipo": "traslado_confirmado_cancelado",
            "paciente_id": paciente_id,
            "reload": True,
            "play_sound": True
        })
        
        return MessageResponse(
            success=True, 
            message=resultado.mensaje,
            data={
                "cama_origen_id": resultado.cama_origen_id,
                "cama_destino_id": resultado.cama_destino_id
            }
        )
        
    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))