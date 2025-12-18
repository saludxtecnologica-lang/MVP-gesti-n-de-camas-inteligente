"""
Schemas de Pydantic para validación de datos en la API.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

from models import (
    SexoEnum, EdadCategoriaEnum, TipoEnfermedadEnum, TipoAislamientoEnum,
    ComplejidadEnum, TipoPacienteEnum, EstadoCamaEnum, TipoServicioEnum,
    EstadoListaEsperaEnum
)


# ============================================
# SCHEMAS DE PACIENTE
# ============================================

class PacienteCreate(BaseModel):
    """Schema para crear un nuevo paciente"""
    nombre: str = Field(..., min_length=1, max_length=200)
    run: str = Field(..., pattern=r'^\d{7,8}-[\dkK]$')
    sexo: SexoEnum
    edad: int = Field(..., ge=0, le=120)
    es_embarazada: bool = False
    diagnostico: str
    tipo_enfermedad: TipoEnfermedadEnum
    tipo_aislamiento: TipoAislamientoEnum = TipoAislamientoEnum.NINGUNO
    notas_adicionales: Optional[str] = None
    
    requerimientos_no_definen: List[str] = []
    requerimientos_baja: List[str] = []
    requerimientos_uti: List[str] = []
    requerimientos_uci: List[str] = []
    casos_especiales: List[str] = []
    
    motivo_observacion: Optional[str] = None
    justificacion_observacion: Optional[str] = None
    procedimiento_invasivo: Optional[str] = None
    
    tipo_paciente: TipoPacienteEnum
    hospital_id: str
    
    derivacion_hospital_destino_id: Optional[str] = None
    derivacion_motivo: Optional[str] = None
    
    alta_solicitada: bool = False
    alta_motivo: Optional[str] = None

    @validator('edad')
    def validar_edad(cls, v):
        if v < 0 or v > 120:
            raise ValueError('Edad debe estar entre 0 y 120')
        return v
    
    @validator('es_embarazada')
    def validar_embarazo(cls, v, values):
        if v and values.get('sexo') == SexoEnum.HOMBRE:
            raise ValueError('Solo las mujeres pueden estar embarazadas')
        return v


class PacienteUpdate(BaseModel):
    """Schema para actualizar un paciente (reevaluación)"""
    diagnostico: Optional[str] = None
    tipo_enfermedad: Optional[TipoEnfermedadEnum] = None
    tipo_aislamiento: Optional[TipoAislamientoEnum] = None
    notas_adicionales: Optional[str] = None
    es_embarazada: Optional[bool] = None
    
    requerimientos_no_definen: Optional[List[str]] = None
    requerimientos_baja: Optional[List[str]] = None
    requerimientos_uti: Optional[List[str]] = None
    requerimientos_uci: Optional[List[str]] = None
    casos_especiales: Optional[List[str]] = None
    
    motivo_observacion: Optional[str] = None
    justificacion_observacion: Optional[str] = None
    procedimiento_invasivo: Optional[str] = None
    
    derivacion_hospital_destino_id: Optional[str] = None
    derivacion_motivo: Optional[str] = None
    
    alta_solicitada: Optional[bool] = None
    alta_motivo: Optional[str] = None


class PacienteResponse(BaseModel):
    """Schema de respuesta para paciente"""
    id: str
    nombre: str
    run: str
    sexo: SexoEnum
    edad: int
    edad_categoria: EdadCategoriaEnum
    es_embarazada: bool
    diagnostico: str
    tipo_enfermedad: TipoEnfermedadEnum
    tipo_aislamiento: TipoAislamientoEnum
    notas_adicionales: Optional[str]
    complejidad_requerida: ComplejidadEnum
    tipo_paciente: TipoPacienteEnum
    hospital_id: str
    cama_id: Optional[str]
    cama_destino_id: Optional[str]
    en_lista_espera: bool
    estado_lista_espera: EstadoListaEsperaEnum
    prioridad_calculada: float
    tiempo_espera_min: Optional[int]
    requiere_nueva_cama: bool
    derivacion_hospital_destino_id: Optional[str]
    derivacion_motivo: Optional[str]
    derivacion_estado: Optional[str]
    alta_solicitada: bool
    created_at: datetime
    updated_at: datetime
    
    requerimientos_no_definen: List[str] = []
    requerimientos_baja: List[str] = []
    requerimientos_uti: List[str] = []
    requerimientos_uci: List[str] = []
    casos_especiales: List[str] = []
    
    motivo_observacion: Optional[str] = None
    justificacion_observacion: Optional[str] = None
    procedimiento_invasivo: Optional[str] = None
    
    class Config:
        from_attributes = True


class CamaResponse(BaseModel):
    """Schema de respuesta para cama"""
    id: str
    numero: int
    letra: Optional[str]
    identificador: str
    estado: EstadoCamaEnum
    mensaje_estado: Optional[str]
    cama_asignada_destino: Optional[str]
    sala_id: str
    servicio_nombre: Optional[str] = None
    servicio_tipo: Optional[TipoServicioEnum] = None
    sala_es_individual: Optional[bool] = None
    sala_sexo_asignado: Optional[SexoEnum] = None
    paciente: Optional[PacienteResponse] = None
    paciente_entrante: Optional[PacienteResponse] = None
    
    class Config:
        from_attributes = True


class CamaBloquearRequest(BaseModel):
    bloquear: bool


class HospitalResponse(BaseModel):
    id: str
    nombre: str
    codigo: str
    es_central: bool
    total_camas: int = 0
    camas_libres: int = 0
    camas_ocupadas: int = 0
    pacientes_en_espera: int = 0
    pacientes_derivados: int = 0
    
    class Config:
        from_attributes = True


class ServicioResponse(BaseModel):
    id: str
    nombre: str
    codigo: str
    tipo: TipoServicioEnum
    hospital_id: str
    total_camas: int = 0
    camas_libres: int = 0
    
    class Config:
        from_attributes = True


class SalaResponse(BaseModel):
    id: str
    numero: int
    es_individual: bool
    servicio_id: str
    sexo_asignado: Optional[SexoEnum]
    camas: List[CamaResponse] = []
    
    class Config:
        from_attributes = True


class PacienteListaEsperaResponse(BaseModel):
    paciente_id: str
    nombre: str
    run: str
    prioridad: float
    posicion: int
    tiempo_espera_min: int
    estado_lista: str
    tipo_paciente: str
    complejidad: str
    sexo: str
    edad: int
    tipo_enfermedad: str
    tipo_aislamiento: str
    tiene_cama_actual: bool
    cama_actual_id: Optional[str]
    timestamp: str
    # CAMPOS para filtros de origen y destino
    origen_tipo: Optional[str] = None  # "derivado", "hospitalizado", "urgencia", "ambulatorio"
    origen_hospital_nombre: Optional[str] = None  # Para derivados
    origen_hospital_codigo: Optional[str] = None  # Para derivados
    origen_servicio_nombre: Optional[str] = None  # Para hospitalizados y derivados
    origen_cama_identificador: Optional[str] = None  # Para hospitalizados y derivados
    servicio_destino: Optional[str] = None  # UCI, UTI, Medicina, etc.

class ListaEsperaResponse(BaseModel):
    hospital_id: str
    total_pacientes: int
    pacientes: List[PacienteListaEsperaResponse]


class DerivacionRequest(BaseModel):
    hospital_destino_id: str
    motivo: str


class DerivacionAccionRequest(BaseModel):
    accion: str = Field(..., pattern='^(aceptar|rechazar)$')
    motivo_rechazo: Optional[str] = None


class PacienteDerivadoResponse(BaseModel):
    paciente_id: str
    nombre: str
    run: str
    prioridad: float
    tiempo_en_lista_min: int
    hospital_origen_id: str
    hospital_origen_nombre: str
    motivo_derivacion: str
    tipo_paciente: str
    complejidad: str
    diagnostico: str


class TrasladoManualRequest(BaseModel):
    paciente_id: str
    cama_destino_id: str


class IntercambioRequest(BaseModel):
    paciente_a_id: str
    paciente_b_id: str


class ConfiguracionResponse(BaseModel):
    modo_manual: bool
    tiempo_limpieza_segundos: int
    # CORRECCIÓN: Agregar campo para tiempo de espera de oxígeno
    tiempo_espera_oxigeno_segundos: Optional[int] = 120


class ConfiguracionUpdate(BaseModel):
    modo_manual: Optional[bool] = None
    tiempo_limpieza_segundos: Optional[int] = None
    # CORRECCIÓN: Agregar campo para tiempo de espera de oxígeno
    tiempo_espera_oxigeno_segundos: Optional[int] = None


class EstadisticasHospitalResponse(BaseModel):
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
    hospitales: List[EstadisticasHospitalResponse]
    total_camas_sistema: int
    total_pacientes_sistema: int
    ocupacion_promedio: float


class MessageResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None