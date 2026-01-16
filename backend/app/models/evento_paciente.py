"""
Modelo de Evento de Paciente.
Registra todos los cambios de estado y eventos importantes del paciente.
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timedelta
import uuid
import json

from app.models.enums import TipoEventoEnum

if TYPE_CHECKING:
    from app.models.paciente import Paciente
    from app.models.hospital import Hospital
    from app.models.servicio import Servicio
    from app.models.cama import Cama


class EventoPaciente(SQLModel, table=True):
    """
    Modelo de Evento de Paciente.

    Registra todos los cambios de estado importantes del paciente
    para análisis estadístico y trazabilidad.
    """
    __tablename__ = "evento_paciente"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True
    )

    # ============================================
    # TIPO DE EVENTO Y TIMESTAMP
    # ============================================
    tipo_evento: TipoEventoEnum = Field(index=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)

    # ============================================
    # REFERENCIAS A ENTIDADES
    # ============================================
    paciente_id: str = Field(foreign_key="paciente.id", index=True)
    hospital_id: str = Field(foreign_key="hospital.id", index=True)

    # Servicios (origen y destino)
    servicio_origen_id: Optional[str] = Field(default=None, foreign_key="servicio.id")
    servicio_destino_id: Optional[str] = Field(default=None, foreign_key="servicio.id")

    # Camas (origen y destino)
    cama_origen_id: Optional[str] = Field(default=None, foreign_key="cama.id")
    cama_destino_id: Optional[str] = Field(default=None, foreign_key="cama.id")

    # Hospital destino (para derivaciones)
    hospital_destino_id: Optional[str] = Field(default=None, foreign_key="hospital.id")

    # ============================================
    # METADATA ADICIONAL
    # ============================================
    datos_adicionales: Optional[str] = Field(default=None)  # JSON con información adicional

    # ============================================
    # DATOS CALCULADOS (para optimización de consultas)
    # ============================================
    # Día clínico (para agrupación diaria)
    # Un día clínico inicia a las 8:00 AM
    dia_clinico: Optional[datetime] = Field(default=None, index=True)

    # Duración del evento (en segundos, para eventos que tienen duración)
    duracion_segundos: Optional[int] = Field(default=None)

    # ============================================
    # RELACIONES
    # ============================================
    paciente: "Paciente" = Relationship()
    hospital: "Hospital" = Relationship()

    # ============================================
    # MÉTODOS DE UTILIDAD
    # ============================================

    def set_metadata(self, data: dict) -> None:
        """
        Establece metadata como JSON.

        Args:
            data: Diccionario con metadata
        """
        self.datos_adicionales = json.dumps(data)

    def get_metadata(self) -> dict:
        """
        Obtiene metadata como diccionario.

        Returns:
            Diccionario con metadata
        """
        if not self.datos_adicionales:
            return {}
        try:
            return json.loads(self.datos_adicionales)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def calcular_dia_clinico(timestamp: datetime) -> datetime:
        """
        Calcula el día clínico para un timestamp dado.
        Un día clínico inicia a las 8:00 AM.

        Args:
            timestamp: Timestamp del evento

        Returns:
            Fecha del día clínico (8:00 AM)
        """
        # Si es antes de las 8 AM, pertenece al día clínico anterior
        if timestamp.hour < 8:
            dia_clinico = timestamp.replace(hour=8, minute=0, second=0, microsecond=0)
            dia_clinico = dia_clinico - timedelta(days=1)
        else:
            dia_clinico = timestamp.replace(hour=8, minute=0, second=0, microsecond=0)
        return dia_clinico

    def __repr__(self) -> str:
        return f"EventoPaciente(id={self.id}, tipo={self.tipo_evento}, paciente_id={self.paciente_id})"
