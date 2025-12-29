"""
Endpoints de Camas.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List

from app.core.database import get_session
from app.core.websocket_manager import manager
from app.models.enums import EstadoCamaEnum
from app.schemas.cama import CamaResponse, CamaBloquearRequest
from app.schemas.responses import MessageResponse
from app.repositories.cama_repo import CamaRepository

router = APIRouter()


@router.get("/{cama_id}", response_model=CamaResponse)
def obtener_cama(cama_id: str, session: Session = Depends(get_session)):
    """Obtiene una cama específica."""
    repo = CamaRepository(session)
    cama = repo.obtener_por_id(cama_id)
    
    if not cama:
        raise HTTPException(status_code=404, detail="Cama no encontrada")
    
    sala = cama.sala
    servicio = sala.servicio if sala else None
    
    return CamaResponse(
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
        sala_es_individual=sala.es_individual if sala else None,
        sala_sexo_asignado=sala.sexo_asignado if sala else None,
    )


@router.post("/{cama_id}/bloquear", response_model=MessageResponse)
async def bloquear_cama(
    cama_id: str,
    request: CamaBloquearRequest,
    session: Session = Depends(get_session)
):
    """Bloquea o desbloquea una cama."""
    repo = CamaRepository(session)
    cama = repo.obtener_por_id(cama_id)
    
    if not cama:
        raise HTTPException(status_code=404, detail="Cama no encontrada")
    
    if request.bloquear:
        if cama.estado != EstadoCamaEnum.LIBRE:
            raise HTTPException(
                status_code=400, 
                detail="Solo se pueden bloquear camas libres"
            )
        repo.cambiar_estado(cama, EstadoCamaEnum.BLOQUEADA, "Bloqueada")
        mensaje = "Cama bloqueada correctamente"
    else:
        if cama.estado != EstadoCamaEnum.BLOQUEADA:
            raise HTTPException(
                status_code=400, 
                detail="La cama no está bloqueada"
            )
        repo.cambiar_estado(cama, EstadoCamaEnum.LIBRE)
        mensaje = "Cama desbloqueada correctamente"
    
    await manager.broadcast({
        "tipo": "cama_actualizada",
        "cama_id": cama_id
    })
    
    return MessageResponse(success=True, message=mensaje)


@router.get("/{cama_id}/libres", response_model=List[CamaResponse])
def obtener_camas_libres_servicio(
    cama_id: str,
    session: Session = Depends(get_session)
):
    """Obtiene camas libres del mismo servicio que una cama dada."""
    repo = CamaRepository(session)
    cama = repo.obtener_por_id(cama_id)
    
    if not cama:
        raise HTTPException(status_code=404, detail="Cama no encontrada")
    
    sala = cama.sala
    if not sala:
        return []
    
    camas_libres = repo.obtener_por_servicio(sala.servicio_id, solo_libres=True)
    
    return [
        CamaResponse(
            id=c.id,
            numero=c.numero,
            letra=c.letra,
            identificador=c.identificador,
            estado=c.estado,
            mensaje_estado=c.mensaje_estado,
            cama_asignada_destino=c.cama_asignada_destino,
            sala_id=c.sala_id
        )
        for c in camas_libres
    ]

