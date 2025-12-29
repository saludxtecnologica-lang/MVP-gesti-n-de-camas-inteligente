"""
Modelo de Hospital.
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
import uuid

if TYPE_CHECKING:
    from app.models.servicio import Servicio
    from app.models.paciente import Paciente


class Hospital(SQLModel, table=True):
    """
    Modelo de Hospital.
    
    Representa un centro hospitalario en el sistema.
    Cada hospital tiene servicios, salas y camas.
    """
    __tablename__ = "hospital"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), 
        primary_key=True
    )
    nombre: str = Field(index=True)
    codigo: str = Field(unique=True)  # PM, LL, CA
    es_central: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relaciones
    servicios: List["Servicio"] = Relationship(back_populates="hospital")
    pacientes: List["Paciente"] = Relationship(back_populates="hospital")
    
    def __repr__(self) -> str:
        return f"Hospital(id={self.id}, nombre={self.nombre}, codigo={self.codigo})"