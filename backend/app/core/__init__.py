"""
Módulo core: funcionalidades centrales del sistema.
"""
from app.core.database import create_db_and_tables, get_session, get_session_direct, engine
from app.core.websocket_manager import manager, ConnectionManager
from app.core.exceptions import (
    BaseAppException,
    ValidationError,
    NotFoundError,
    PacienteNotFoundError,
    CamaNotFoundError,
    CamaNoDisponibleError,
    EstadoInvalidoError,
    HospitalNotFoundError
)

__all__ = [
    "create_db_and_tables",
    "get_session",
    "get_session_direct",
    "engine",
    "manager",
    "ConnectionManager",
    "BaseAppException",
    "ValidationError",
    "NotFoundError",
    "PacienteNotFoundError",
    "CamaNotFoundError",
    "CamaNoDisponibleError",
    "EstadoInvalidoError",
    "HospitalNotFoundError",
]