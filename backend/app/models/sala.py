"""
Modelo de Sala.
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
import uuid

from app.models.enums import SexoEnum

if TYPE_CHECKING:
    from app.models.servicio import Servicio
    from app.models.cama import Cama


class Sala(SQLModel, table=True):
    """
    Modelo de Sala.
    
    Representa una sala física dentro de un servicio.
    Puede ser individual o compartida.
    """
    __tablename__ = "sala"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    numero: int                                    # Número de la sala
    servicio_id: str = Field(foreign_key="servicio.id", index=True)
    es_individual: bool = Field(default=False)    # Si es sala individual (UCI/UTI/Aislamiento)
    sexo_asignado: Optional[str] = Field(default=None)  # 'hombre' o 'mujer' o None
    
    # Relaciones
    servicio: Optional["Servicio"] = Relationship(back_populates="salas")
    camas: List["Cama"] = Relationship(back_populates="sala")
    
    @property
    def nombre(self) -> str:
        """Genera el nombre de la sala dinámicamente."""
        return f"Sala {self.numero}"
    
    def __repr__(self) -> str:
        return f"Sala(id={self.id}, numero={self.numero}, es_individual={self.es_individual})"