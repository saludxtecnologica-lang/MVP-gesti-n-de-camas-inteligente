"""
Schemas Pydantic para validación y serialización.
"""
from app.schemas.paciente import (
    PacienteCreate,
    PacienteUpdate,
    PacienteResponse,
    PacienteListaEsperaResponse,
    ListaEsperaResponse,
    PacienteDerivadoResponse,
)

from app.schemas.cama import (
    CamaResponse,
    CamaBloquearRequest,
)

from app.schemas.hospital import (
    HospitalResponse,
    ServicioResponse,
    SalaResponse,
)

from app.schemas.traslado import (
    TrasladoManualRequest,
    IntercambioRequest,
)

from app.schemas.derivacion import (
    DerivacionRequest,
    DerivacionAccionRequest,
)

from app.schemas.responses import (
    MessageResponse,
    ErrorResponse,
    ConfiguracionResponse,
    ConfiguracionUpdate,
    EstadisticasHospitalResponse,
    EstadisticasGlobalesResponse,
)

__all__ = [
    # Paciente
    "PacienteCreate",
    "PacienteUpdate",
    "PacienteResponse",
    "PacienteListaEsperaResponse",
    "ListaEsperaResponse",
    "PacienteDerivadoResponse",
    # Cama
    "CamaResponse",
    "CamaBloquearRequest",
    # Hospital
    "HospitalResponse",
    "ServicioResponse",
    "SalaResponse",
    # Traslado
    "TrasladoManualRequest",
    "IntercambioRequest",
    # Derivacion
    "DerivacionRequest",
    "DerivacionAccionRequest",
    # Responses
    "MessageResponse",
    "ErrorResponse",
    "ConfiguracionResponse",
    "ConfiguracionUpdate",
    "EstadisticasHospitalResponse",
    "EstadisticasGlobalesResponse",
]