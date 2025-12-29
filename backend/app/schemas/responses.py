"""
Schemas de Respuestas Comunes.
"""
from pydantic import BaseModel
from typing import Optional, List


class MessageResponse(BaseModel):
    """Respuesta genérica con mensaje."""
    success: bool
    message: str
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Respuesta de error."""
    error: str
    detail: Optional[str] = None


class ConfiguracionResponse(BaseModel):
    """Schema de respuesta para configuración."""
    modo_manual: bool
    tiempo_limpieza_segundos: int
    tiempo_espera_oxigeno_segundos: Optional[int] = 120


class ConfiguracionUpdate(BaseModel):
    """Schema para actualizar configuración."""
    modo_manual: Optional[bool] = None
    tiempo_limpieza_segundos: Optional[int] = None
    tiempo_espera_oxigeno_segundos: Optional[int] = None


class EstadisticasHospitalResponse(BaseModel):
    """Estadísticas de un hospital."""
    hospital_id: str
    hospital_nombre: str
    total_camas: int
    camas_libres: int
    camas_ocupadas: int
    camas_traslado: int
    camas_limpieza: int
    camas_bloqueadas: int
    pacientes_en_espera: int
    pacientes_derivados_pendientes: int
    ocupacion_porcentaje: float


class EstadisticasGlobalesResponse(BaseModel):
    """Estadísticas globales del sistema."""
    hospitales: List[EstadisticasHospitalResponse]
    total_camas_sistema: int
    total_pacientes_sistema: int
    ocupacion_promedio: float