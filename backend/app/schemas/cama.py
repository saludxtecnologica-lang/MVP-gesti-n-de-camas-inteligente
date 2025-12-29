"""
Schemas de Cama.
"""
from pydantic import BaseModel
from typing import Optional

from app.models.enums import EstadoCamaEnum, TipoServicioEnum, SexoEnum
from app.schemas.paciente import PacienteResponse


class CamaResponse(BaseModel):
    """Schema de respuesta para cama."""
    
    id: str
    numero: int
    letra: Optional[str]
    identificador: str
    estado: EstadoCamaEnum
    mensaje_estado: Optional[str]
    cama_asignada_destino: Optional[str]
    sala_id: str
    
    # Información del servicio y sala
    servicio_nombre: Optional[str] = None
    servicio_tipo: Optional[TipoServicioEnum] = None
    sala_nombre: Optional[str] = None  
    sala_es_individual: Optional[bool] = None
    sala_sexo_asignado: Optional[str] = None
    
    # Pacientes
    paciente: Optional[PacienteResponse] = None
    paciente_entrante: Optional[PacienteResponse] = None
    
    class Config:
        from_attributes = True


class CamaBloquearRequest(BaseModel):
    """Request para bloquear/desbloquear cama."""
    bloquear: bool


class CamaBusquedaRequest(BaseModel):
    """Request para buscar camas disponibles."""
    hospital_id: str
    complejidad: Optional[str] = None
    sexo: Optional[str] = None
    requiere_aislamiento: bool = False