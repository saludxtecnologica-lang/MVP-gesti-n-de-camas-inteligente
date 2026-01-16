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


# ============================================
# NUEVOS SCHEMAS PARA ESTADÍSTICAS AVANZADAS
# ============================================

class TiempoEstadisticaResponse(BaseModel):
    """Estadísticas de tiempo (promedio, máximo, mínimo)."""
    promedio: float
    maximo: float
    minimo: float
    cantidad: int


class IngresosEgresosResponse(BaseModel):
    """Respuesta de ingresos y egresos."""
    total: int
    desglose: Optional[dict] = None


class TasaOcupacionResponse(BaseModel):
    """Respuesta de tasa de ocupación."""
    tasa_ocupacion: float
    camas_ocupadas: int
    camas_totales: int


class FlujoResponse(BaseModel):
    """Respuesta de flujo (traslado o derivación)."""
    flujo: str
    cantidad: int


class ServicioDemandaResponse(BaseModel):
    """Respuesta de servicio con demanda."""
    servicio_id: str
    servicio_nombre: str
    hospital_id: str
    tasa_ocupacion: float
    pacientes_en_espera: int
    demanda_score: float


class CasosEspecialesResponse(BaseModel):
    """Respuesta de casos especiales."""
    total: int
    cardiocirugia: int
    caso_social: int
    caso_socio_judicial: int


class CamaSubutilizadaResponse(BaseModel):
    """Respuesta de cama subutilizada."""
    cama_id: str
    identificador: str
    servicio_nombre: str
    tiempo_libre_horas: float


class ServicioSubutilizadoResponse(BaseModel):
    """Respuesta de servicio subutilizado."""
    servicio_id: str
    servicio_nombre: str
    hospital_id: str
    tasa_libre: float
    camas_libres: int
    camas_totales: int


class TrazabilidadServicioResponse(BaseModel):
    """Respuesta de trazabilidad por servicio."""
    servicio_nombre: str
    entrada: str
    salida: str
    duracion_dias: int
    duracion_horas: int
    duracion_total_segundos: int


class EstadisticasCompletasResponse(BaseModel):
    """Respuesta completa de todas las estadísticas."""
    # Ingresos y Egresos
    ingresos_red: Optional[IngresosEgresosResponse] = None
    egresos_red: Optional[IngresosEgresosResponse] = None
    ingresos_por_hospital: Optional[List[dict]] = None
    egresos_por_hospital: Optional[List[dict]] = None

    # Tiempos
    tiempo_espera_cama: Optional[TiempoEstadisticaResponse] = None
    tiempo_derivacion_pendiente: Optional[TiempoEstadisticaResponse] = None
    tiempo_traslado_saliente: Optional[TiempoEstadisticaResponse] = None
    tiempo_confirmacion_traslado: Optional[TiempoEstadisticaResponse] = None
    tiempo_alta: Optional[dict] = None
    tiempo_fallecido: Optional[TiempoEstadisticaResponse] = None
    tiempo_hospitalizacion_hospital: Optional[TiempoEstadisticaResponse] = None
    tiempo_hospitalizacion_red: Optional[TiempoEstadisticaResponse] = None

    # Tasas de Ocupación
    tasa_ocupacion_red: Optional[TasaOcupacionResponse] = None
    tasas_ocupacion_hospitales: Optional[List[dict]] = None
    tasas_ocupacion_servicios: Optional[List[dict]] = None

    # Flujos y Demanda
    flujos_mas_repetidos: Optional[List[FlujoResponse]] = None
    servicios_mayor_demanda: Optional[List[ServicioDemandaResponse]] = None

    # Casos Especiales
    casos_especiales: Optional[CasosEspecialesResponse] = None

    # Subutilización
    camas_subutilizadas: Optional[List[CamaSubutilizadaResponse]] = None
    servicios_subutilizados: Optional[List[ServicioSubutilizadoResponse]] = None