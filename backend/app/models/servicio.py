"""
Modelo de Servicio.
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
    Modelo de Servicio hospitalario.
    
    Representa un servicio dentro de un hospital (UCI, UTI, Medicina, etc.)
    """
    __tablename__ = "servicio"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), 
        primary_key=True
    )
    nombre: str = Field(index=True)
    codigo: str
    tipo: TipoServicioEnum
    hospital_id: str = Field(foreign_key="hospital.id", index=True)
    
    # ============================================
    # NUEVO CAMPO: Teléfono de contacto del servicio
    # ============================================
    telefono: Optional[str] = Field(default=None, max_length=50)
    
    # Relaciones
    hospital: "Hospital" = Relationship(back_populates="servicios")
    salas: List["Sala"] = Relationship(back_populates="servicio")
    
    def __repr__(self) -> str:
        return f"Servicio(id={self.id}, nombre={self.nombre}, tipo={self.tipo})"