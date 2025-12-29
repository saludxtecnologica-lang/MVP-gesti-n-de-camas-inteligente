"""
Schemas de Traslado.
"""
from pydantic import BaseModel


class TrasladoManualRequest(BaseModel):
    """Request para traslado manual."""
    paciente_id: str
    cama_destino_id: str


class IntercambioRequest(BaseModel):
    """Request para intercambio de pacientes."""
    paciente_a_id: str
    paciente_b_id: str