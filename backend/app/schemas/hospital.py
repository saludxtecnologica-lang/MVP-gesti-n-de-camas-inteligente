"""
Schemas de Hospital, Servicio y Sala.
ACTUALIZADO: HospitalResponse incluye teléfonos de urgencias y ambulatorio.
             ServicioResponse incluye campo telefono.

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
    # ============================================
    # NUEVOS CAMPOS: Teléfonos del hospital
    # ============================================
    telefono_urgencias: Optional[str] = None
    telefono_ambulatorio: Optional[str] = None
    
    class Config:
        from_attributes = True


class HospitalTelefonosUpdate(BaseModel):
    """Schema para actualizar teléfonos de un hospital."""
    telefono_urgencias: Optional[str] = None
    telefono_ambulatorio: Optional[str] = None


class ServicioResponse(BaseModel):
    """Schema de respuesta para servicio."""
    
    id: str
    nombre: str
    codigo: str
    tipo: TipoServicioEnum
    hospital_id: str
    total_camas: int = 0
    camas_libres: int = 0
    # ============================================
    # Teléfono de contacto del servicio
    # ============================================
    telefono: Optional[str] = None
    
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