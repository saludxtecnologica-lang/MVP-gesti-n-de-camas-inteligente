"""
Endpoints de Altas.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.database import get_session
from app.core.websocket_manager import manager
from app.core.exceptions import PacienteNotFoundError, ValidationError
from app.schemas.responses import MessageResponse
from app.services.alta_service import AltaService
from app.services.Limpieza_service import OxigenoService

router = APIRouter()


@router.post("/{paciente_id}/iniciar", response_model=MessageResponse)
async def iniciar_alta(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """Inicia el proceso de alta de un paciente."""
    service = AltaService(session)
    
    try:
        resultado = service.iniciar_alta(paciente_id)
        
        await manager.broadcast({
            "tipo": "alta_iniciada",
            "paciente_id": paciente_id,
            "cama_id": resultado.cama_id
        })
        
        return MessageResponse(success=True, message=resultado.mensaje)
        
    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{paciente_id}/ejecutar", response_model=MessageResponse)
async def ejecutar_alta(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """Ejecuta el alta y libera la cama."""
    service = AltaService(session)
    
    try:
        resultado = service.ejecutar_alta(paciente_id)
        
        await manager.send_notification(
            {
                "tipo": "alta_completada",
                "paciente_id": paciente_id,
                "cama_id": resultado.cama_id
            },
            notification_type="success"
        )
        
        return MessageResponse(success=True, message=resultado.mensaje)
        
    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{paciente_id}/cancelar", response_model=MessageResponse)
async def cancelar_alta(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """Cancela el proceso de alta."""
    service = AltaService(session)
    
    try:
        resultado = service.cancelar_alta(paciente_id)
        
        await manager.broadcast({
            "tipo": "alta_cancelada",
            "paciente_id": paciente_id
        })
        
        return MessageResponse(success=True, message=resultado.mensaje)
        
    except PacienteNotFoundError:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{paciente_id}/omitir-pausa-oxigeno", response_model=MessageResponse)
async def omitir_pausa_oxigeno(
    paciente_id: str,
    session: Session = Depends(get_session)
):
    """Omite la pausa de espera por oxígeno."""
    service = OxigenoService(session)
    
    try:
        paciente = service.omitir_espera_oxigeno(paciente_id)
        
        await manager.broadcast({
            "tipo": "pausa_oxigeno_omitida",
            "paciente_id": paciente_id
        })
        
        return MessageResponse(
            success=True,
            message="Pausa de oxígeno omitida"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))