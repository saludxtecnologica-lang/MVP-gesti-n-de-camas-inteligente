"""
Modelos de datos del sistema.
Re-exporta todos los modelos para imports simplificados.
"""
from app.models.enums import (
    TipoPacienteEnum,
    SexoEnum,
    EdadCategoriaEnum,
    TipoEnfermedadEnum,
    TipoAislamientoEnum,
    ComplejidadEnum,
    TipoServicioEnum,
    EstadoCamaEnum,
    EstadoListaEsperaEnum,
    TipoEventoEnum,
)

from app.models.hospital import Hospital
from app.models.servicio import Servicio
from app.models.sala import Sala
from app.models.cama import Cama
from app.models.paciente import Paciente
from app.models.evento_paciente import EventoPaciente
from app.models.configuracion import ConfiguracionSistema, LogActividad
from app.models.usuario import Usuario, RefreshToken, RolEnum, PermisoEnum

__all__ = [
    # Enums
    "TipoPacienteEnum",
    "SexoEnum",
    "EdadCategoriaEnum",
    "TipoEnfermedadEnum",
    "TipoAislamientoEnum",
    "ComplejidadEnum",
    "TipoServicioEnum",
    "EstadoCamaEnum",
    "EstadoListaEsperaEnum",
    "TipoEventoEnum",
    # Models
    "Hospital",
    "Servicio",
    "Sala",
    "Cama",
    "Paciente",
    "EventoPaciente",
    "ConfiguracionSistema",
    "LogActividad",
]