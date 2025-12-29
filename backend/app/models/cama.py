"""
Modelo de Cama.
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
import uuid

from app.models.enums import EstadoCamaEnum

if TYPE_CHECKING:
    from app.models.sala import Sala
    from app.models.paciente import Paciente


class Cama(SQLModel, table=True):
    """
    Modelo de Cama hospitalaria.
    
    Representa una cama física dentro de una sala.
    Gestiona el estado y asignaciones de pacientes.
    """
    __tablename__ = "cama"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), 
        primary_key=True
    )
    numero: int
    letra: Optional[str] = Field(default=None)  # A, B, C para camas compartidas
    identificador: str = Field(index=True)  # MED-501-A
    sala_id: str = Field(foreign_key="sala.id", index=True)
    estado: EstadoCamaEnum = Field(default=EstadoCamaEnum.LIBRE, index=True)
    
    # Timestamps para estados
    estado_updated_at: datetime = Field(default_factory=datetime.utcnow)
    limpieza_inicio: Optional[datetime] = Field(default=None)
    
    # Mensaje de estado para UI
    mensaje_estado: Optional[str] = Field(default=None)
    
    # Referencia a cama destino cuando hay traslado confirmado
    cama_asignada_destino: Optional[str] = Field(default=None)
    
    # Campo para rastrear el paciente derivado asociado a esta cama
    paciente_derivado_id: Optional[str] = Field(default=None)
    
    # Relaciones
    sala: "Sala" = Relationship(back_populates="camas")
    
    paciente_actual: Optional["Paciente"] = Relationship(
        back_populates="cama",
        sa_relationship_kwargs={"foreign_keys": "[Paciente.cama_id]"}
    )
    
    pacientes_destino: List["Paciente"] = Relationship(
        back_populates="cama_destino",
        sa_relationship_kwargs={"foreign_keys": "[Paciente.cama_destino_id]"}
    )
    
    def __repr__(self) -> str:
        return f"Cama(id={self.id}, identificador={self.identificador}, estado={self.estado})"
    
    @property
    def esta_libre(self) -> bool:
        """Verifica si la cama está libre."""
        return self.estado == EstadoCamaEnum.LIBRE
    
    @property
    def esta_ocupada(self) -> bool:
        """Verifica si la cama tiene un paciente asignado."""
        from app.models.enums import ESTADOS_CAMA_OCUPADA
        return self.estado in ESTADOS_CAMA_OCUPADA
    
    @property
    def puede_recibir_paciente(self) -> bool:
        """Verifica si la cama puede recibir un nuevo paciente."""
        return self.estado == EstadoCamaEnum.LIBRE