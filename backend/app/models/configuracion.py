"""
Modelos de Configuración y Logs.
"""
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid


class ConfiguracionSistema(SQLModel, table=True):
    """
    Configuración global del sistema.
    
    Almacena configuraciones que afectan el comportamiento
    del sistema de asignación de camas.
    """
    __tablename__ = "configuracionsistema"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), 
        primary_key=True
    )
    
    # Modo de operación
    modo_manual: bool = Field(default=False)
    
    # Tiempos de procesos automáticos (en segundos)
    tiempo_limpieza_segundos: int = Field(default=60)
    tiempo_espera_oxigeno_segundos: int = Field(default=120)
    
    # Timestamp de última actualización
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"ConfiguracionSistema(modo_manual={self.modo_manual})"


class LogActividad(SQLModel, table=True):
    """
    Log de actividades del sistema.
    
    Registra todas las acciones importantes para auditoría.
    """
    __tablename__ = "logactividad"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), 
        primary_key=True
    )
    
    # Tipo de actividad
    tipo: str  # asignacion, traslado, alta, derivacion, etc.
    descripcion: str
    
    # Referencias opcionales
    hospital_id: Optional[str] = Field(default=None, index=True)
    paciente_id: Optional[str] = Field(default=None, index=True)
    cama_id: Optional[str] = Field(default=None)
    
    # Datos adicionales en JSON
    datos_extra: Optional[str] = Field(default=None)
    
    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    def __repr__(self) -> str:
        return f"LogActividad(tipo={self.tipo}, descripcion={self.descripcion[:50]}...)"