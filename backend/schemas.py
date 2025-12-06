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
    
    # Requerimientos clínicos como listas
    requerimientos_no_definen: List[str] = []
    requerimientos_baja: List[str] = []
    requerimientos_uti: List[str] = []
    requerimientos_uci: List[str] = []
    casos_especiales: List[str] = []
    
    # Campos especiales
    motivo_observacion: Optional[str] = None
    justificacion_observacion: Optional[str] = None
    procedimiento_invasivo: Optional[str] = None
    
    # Tipo de paciente
    tipo_paciente: TipoPacienteEnum
    hospital_id: str
    
    # Derivación
    derivacion_hospital_destino_id: Optional[str] = None
    derivacion_motivo: Optional[str] = None
    
    # Alta
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
    
    # Requerimientos
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


# ============================================
# SCHEMAS DE CAMA
# ============================================

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
    """Schema para bloquear/desbloquear cama"""
    bloquear: bool


# ============================================
# SCHEMAS DE HOSPITAL
# ============================================

class HospitalResponse(BaseModel):
    """Schema de respuesta para hospital"""
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
    """Schema de respuesta para servicio"""
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
    """Schema de respuesta para sala"""
    id: str
    numero: int
    es_individual: bool
    servicio_id: str
    sexo_asignado: Optional[SexoEnum]
    camas: List[CamaResponse] = []
    
    class Config:
        from_attributes = True


# ============================================
# SCHEMAS DE LISTA DE ESPERA
# ============================================

class PacienteListaEsperaResponse(BaseModel):
    """Schema para paciente en lista de espera"""
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


class ListaEsperaResponse(BaseModel):
    """Schema de respuesta para lista de espera"""
    hospital_id: str
    total_pacientes: int
    pacientes: List[PacienteListaEsperaResponse]


# ============================================
# SCHEMAS DE DERIVACIÓN
# ============================================

class DerivacionRequest(BaseModel):
    """Schema para solicitar derivación"""
    hospital_destino_id: str
    motivo: str


class DerivacionAccionRequest(BaseModel):
    """Schema para aceptar/rechazar derivación"""
    accion: str = Field(..., pattern='^(aceptar|rechazar)$')
    motivo_rechazo: Optional[str] = None


class PacienteDerivadoResponse(BaseModel):
    """Schema para paciente en lista de derivados"""
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


# ============================================
# SCHEMAS DE TRASLADO
# ============================================

class TrasladoManualRequest(BaseModel):
    """Schema para traslado manual"""
    paciente_id: str
    cama_destino_id: str


class IntercambioRequest(BaseModel):
    """Schema para intercambio de pacientes"""
    paciente_a_id: str
    paciente_b_id: str


# ============================================
# SCHEMAS DE CONFIGURACIÓN
# ============================================

class ConfiguracionResponse(BaseModel):
    """Schema de respuesta para configuración"""
    modo_manual: bool
    tiempo_limpieza_segundos: int


class ConfiguracionUpdate(BaseModel):
    """Schema para actualizar configuración"""
    modo_manual: Optional[bool] = None
    tiempo_limpieza_segundos: Optional[int] = None


# ============================================
# SCHEMAS DE ESTADÍSTICAS
# ============================================

class EstadisticasHospitalResponse(BaseModel):
    """Schema de estadísticas por hospital"""
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
    """Schema de estadísticas globales"""
    hospitales: List[EstadisticasHospitalResponse]
    total_camas_sistema: int
    total_pacientes_sistema: int
    ocupacion_promedio: float


# ============================================
# SCHEMAS DE RESPUESTA GENÉRICA
# ============================================

class MessageResponse(BaseModel):
    """Schema de respuesta genérica"""
    success: bool
    message: str
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Schema de error"""
    error: str
    detail: Optional[str] = None