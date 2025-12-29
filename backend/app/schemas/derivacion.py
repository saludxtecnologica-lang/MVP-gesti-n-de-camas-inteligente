"""
Schemas de Derivación.
"""
from pydantic import BaseModel, Field
from typing import Optional


class DerivacionRequest(BaseModel):
    """Request para solicitar derivación."""
    hospital_destino_id: str
    motivo: str


class DerivacionAccionRequest(BaseModel):
    """Request para aceptar/rechazar derivación."""
    accion: str = Field(..., pattern='^(aceptar|rechazar)$')
    motivo_rechazo: Optional[str] = None