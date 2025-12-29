"""
Modelo de Servicio Hospitalario.
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
import uuid

from app.models.enums import TipoServicioEnum

if TYPE_CHECKING:
    from app.models.hospital import Hospital
    from app.models.sala import Sala


class Servicio(SQLModel, table=True):
    """
    Modelo de Servicio Hospitalario.
    
    Representa un servicio clínico dentro de un hospital.
    Ejemplos: UCI, UTI, Medicina, Cirugía, etc.
    """
    __tablename__ = "servicio"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), 
        primary_key=True
    )
    nombre: str
    codigo: str  # UCI, UTI, MED, etc.
    tipo: TipoServicioEnum
    hospital_id: str = Field(foreign_key="hospital.id", index=True)
    numero_inicio_camas: int = Field(default=100)
    
    # Configuración del servicio
    es_uci: bool = Field(default=False)
    es_uti: bool = Field(default=False)
    permite_pediatria: bool = Field(default=False)
    
    # Relaciones
    hospital: "Hospital" = Relationship(back_populates="servicios")
    salas: List["Sala"] = Relationship(back_populates="servicio")
    
    def __repr__(self) -> str:
        return f"Servicio(id={self.id}, nombre={self.nombre}, tipo={self.tipo})"