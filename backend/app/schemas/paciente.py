"""
Schemas de Paciente.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime

from app.models.enums import (
    SexoEnum,
    EdadCategoriaEnum,
    TipoEnfermedadEnum,
    TipoAislamientoEnum,
    ComplejidadEnum,
    TipoPacienteEnum,
    EstadoListaEsperaEnum,
)


class PacienteCreate(BaseModel):
    """Schema para crear un nuevo paciente."""
    
    # Datos personales
    nombre: str = Field(..., min_length=1, max_length=200)
    run: str = Field(..., pattern=r'^\d{7,8}-[\dkK]$')
    sexo: SexoEnum
    edad: int = Field(..., ge=0, le=120)
    es_embarazada: bool = False
    
    # Datos clínicos
    diagnostico: str
    tipo_enfermedad: TipoEnfermedadEnum
    tipo_aislamiento: TipoAislamientoEnum = TipoAislamientoEnum.NINGUNO
    notas_adicionales: Optional[str] = None
    
    # Requerimientos clínicos
    requerimientos_no_definen: List[str] = []
    requerimientos_baja: List[str] = []
    requerimientos_uti: List[str] = []
    requerimientos_uci: List[str] = []
    casos_especiales: List[str] = []
    
    # Campos para observación clínica
    motivo_observacion: Optional[str] = None
    justificacion_observacion: Optional[str] = None
    
    # Campos para monitorización
    motivo_monitorizacion: Optional[str] = None
    justificacion_monitorizacion: Optional[str] = None
    
    # Procedimiento invasivo
    procedimiento_invasivo: Optional[str] = None
    
    # Tipo y hospital
    tipo_paciente: TipoPacienteEnum
    hospital_id: str
    
    # Derivación (opcional)
    derivacion_hospital_destino_id: Optional[str] = None
    derivacion_motivo: Optional[str] = None
    
    # Alta (opcional)
    alta_solicitada: bool = False
    alta_motivo: Optional[str] = None

    @field_validator('edad')
    @classmethod
    def validar_edad(cls, v):
        if v < 0 or v > 120:
            raise ValueError('Edad debe estar entre 0 y 120')
        return v
    
    @field_validator('es_embarazada')
    @classmethod
    def validar_embarazo(cls, v, info):
        if v and info.data.get('sexo') == SexoEnum.HOMBRE:
            raise ValueError('Solo las mujeres pueden estar embarazadas')
        return v


class PacienteUpdate(BaseModel):
    """Schema para actualizar un paciente (reevaluación)."""
    
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
    motivo_monitorizacion: Optional[str] = None
    justificacion_monitorizacion: Optional[str] = None
    procedimiento_invasivo: Optional[str] = None
    
    derivacion_hospital_destino_id: Optional[str] = None
    derivacion_motivo: Optional[str] = None
    
    alta_solicitada: Optional[bool] = None
    alta_motivo: Optional[str] = None


class PacienteResponse(BaseModel):
    """Schema de respuesta para paciente."""
    
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
    tiempo_espera_min: Optional[int] = 0
    requiere_nueva_cama: bool
    
    # Derivación
    derivacion_hospital_destino_id: Optional[str]
    derivacion_motivo: Optional[str]
    derivacion_estado: Optional[str]
    
    # Alta
    alta_solicitada: bool
    
    # Origen y destino (para priorización)
    origen_servicio_nombre: Optional[str] = None
    servicio_destino: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Requerimientos
    requerimientos_no_definen: List[str] = []
    requerimientos_baja: List[str] = []
    requerimientos_uti: List[str] = []
    requerimientos_uci: List[str] = []
    casos_especiales: List[str] = []
    
    # Campos especiales
    motivo_observacion: Optional[str] = None
    justificacion_observacion: Optional[str] = None
    motivo_monitorizacion: Optional[str] = None
    justificacion_monitorizacion: Optional[str] = None
    procedimiento_invasivo: Optional[str] = None
    documento_adjunto: Optional[str] = None
    
    # Estado oxígeno
    esperando_evaluacion_oxigeno: bool = False
    
    class Config:
        from_attributes = True


class PacienteListaEsperaResponse(BaseModel):
    """Schema para paciente en lista de espera."""
    
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
    
    # Campos para filtros de origen y destino
    origen_tipo: Optional[str] = None
    origen_hospital_nombre: Optional[str] = None
    origen_hospital_codigo: Optional[str] = None
    origen_servicio_nombre: Optional[str] = None
    origen_cama_identificador: Optional[str] = None
    servicio_destino: Optional[str] = None


class ListaEsperaResponse(BaseModel):
    """Schema de respuesta para lista de espera."""
    
    hospital_id: str
    total_pacientes: int
    pacientes: List[PacienteListaEsperaResponse]


class PacienteDerivadoResponse(BaseModel):
    """Schema para paciente derivado."""
    
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