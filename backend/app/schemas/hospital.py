"""
Schemas de Hospital, Servicio y Sala.
"""
from pydantic import BaseModel
from typing import Optional, List

from app.models.enums import TipoServicioEnum, SexoEnum
from app.schemas.cama import CamaResponse


class HospitalResponse(BaseModel):
    """Schema de respuesta para hospital."""
    
    id: str
    nombre: str
    codigo: str
    es_central: bool
    total_camas: int = 0
    camas_libres: int = 0
    camas_ocupadas: int = 0
    pacientes_en_espera: int = 0
    pacientes_derivados: int = 0
    
    class Config:
        from_attributes = True


class ServicioResponse(BaseModel):
    """Schema de respuesta para servicio."""
    
    id: str
    nombre: str
    codigo: str
    tipo: TipoServicioEnum
    hospital_id: str
    total_camas: int = 0
    camas_libres: int = 0
    
    class Config:
        from_attributes = True


class SalaResponse(BaseModel):
    """Schema de respuesta para sala."""
    
    id: str
    numero: int
    es_individual: bool
    servicio_id: str
    sexo_asignado: Optional[SexoEnum]
    camas: List[CamaResponse] = []
    
    class Config:
        from_attributes = True