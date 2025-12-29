"""
Repositories para acceso a datos.
Abstraen las queries SQL y proporcionan una interfaz limpia.
"""
from app.repositories.base import BaseRepository
from app.repositories.hospital_repo import HospitalRepository
from app.repositories.cama_repo import CamaRepository
from app.repositories.paciente_repo import PacienteRepository
from app.repositories.configuracion_repo import ConfiguracionRepository

__all__ = [
    "BaseRepository",
    "HospitalRepository",
    "CamaRepository",
    "PacienteRepository",
    "ConfiguracionRepository",
]