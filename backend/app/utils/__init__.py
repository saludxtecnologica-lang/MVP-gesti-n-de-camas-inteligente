"""
Utilidades compartidas del sistema.
"""
from app.utils.helpers import (
    calcular_estadisticas_camas,
    crear_paciente_response,
    safe_json_loads,
    safe_json_dumps,
    formatear_tiempo_espera,
)
from app.utils.validators import validar_run_chileno, formatear_run
from app.utils.logger import configurar_logging, logger

__all__ = [
    "calcular_estadisticas_camas",
    "crear_paciente_response",
    "safe_json_loads",
    "safe_json_dumps",
    "formatear_tiempo_espera",
    "validar_run_chileno",
    "formatear_run",
    "configurar_logging",
    "logger",
]