"""
Schemas de Prioridad v3.1

Schemas Pydantic para las respuestas del sistema de priorización.
Incluye los nuevos campos de IVC y FRC.

"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


class DesglosePrioridadResponse(BaseModel):
    """
    Desglose detallado del cálculo de prioridad v3.1.
    
    Incluye todos los componentes del sistema:
    - Base por tipo de paciente
    - Servicio de origen
    - IVC (Índice de Vulnerabilidad Clínica)
    - FRC (Factor de Requerimientos Críticos)
    - Tiempo no lineal
    - Estado de rescate
    """
    # Componentes principales
    tipo_paciente: float = Field(..., description="Puntaje por tipo de paciente (base)")
    servicio_origen: float = Field(0, description="Puntaje por servicio de origen (solo hospitalizados)")
    ivc: float = Field(0, description="Índice de Vulnerabilidad Clínica")
    frc: float = Field(0, description="Factor de Requerimientos Críticos")
    tiempo: float = Field(0, description="Puntaje por tiempo de espera (no lineal)")
    
    # Desglose del IVC (para transparencia)
    ivc_desglose: Optional[Dict[str, float]] = Field(
        None, 
        description="Desglose del IVC: edad, monitorizacion, observacion, complejidad, aislamiento, embarazo, casos_especiales"
    )
    
    # Desglose del FRC (para transparencia)
    frc_desglose: Optional[Dict[str, float]] = Field(
        None,
        description="Desglose del FRC: drogas_vasoactivas, sedacion, oxigeno, procedimiento, aspiracion"
    )
    
    # Campos legacy (para compatibilidad)
    complejidad: float = Field(0, description="[Legacy] Puntaje por complejidad (incluido en IVC)")
    edad: float = Field(0, description="[Legacy] Puntaje por edad (incluido en IVC)")
    aislamiento: float = Field(0, description="[Legacy] Puntaje por aislamiento (incluido en IVC)")
    tiempo_espera: float = Field(0, description="[Legacy] Alias de tiempo")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tipo_paciente": 100,
                "servicio_origen": 0,
                "ivc": 55,
                "frc": 37,
                "tiempo": 22,
                "ivc_desglose": {
                    "edad": 20,
                    "monitorizacion": 20,
                    "complejidad": 15,
                    "aislamiento": 0,
                    "embarazo": 0,
                    "casos_especiales": 0
                },
                "frc_desglose": {
                    "drogas_vasoactivas": 15,
                    "sedacion": 12,
                    "oxigeno": 10,
                    "procedimiento": 0,
                    "aspiracion": 0
                },
                "complejidad": 15,
                "edad": 20,
                "aislamiento": 0,
                "tiempo_espera": 22
            }
        }


class PrioridadPacienteResponse(BaseModel):
    """
    Respuesta completa del endpoint de prioridad de un paciente.
    """
    paciente_id: str = Field(..., description="ID del paciente")
    nombre: str = Field(..., description="Nombre del paciente")
    prioridad_total: float = Field(..., description="Puntaje total de prioridad")
    posicion_cola: Optional[int] = Field(None, description="Posición en la cola de espera")
    
    # Tipo efectivo (puede diferir del original)
    tipo_original: str = Field(..., description="Tipo de paciente original")
    tipo_efectivo: str = Field(..., description="Tipo efectivo para priorización")
    
    # Estado especial
    es_rescate: bool = Field(False, description="Indica si el paciente está en modo rescate")
    tiempo_espera_horas: float = Field(0, description="Horas en lista de espera")
    
    # Desglose
    desglose: DesglosePrioridadResponse = Field(..., description="Desglose del cálculo")
    
    # Detalles textuales
    detalles: List[str] = Field(default_factory=list, description="Lista de detalles del cálculo")
    
    class Config:
        json_schema_extra = {
            "example": {
                "paciente_id": "abc123",
                "nombre": "Juan Pérez",
                "prioridad_total": 214,
                "posicion_cola": 3,
                "tipo_original": "urgencia",
                "tipo_efectivo": "urgencia",
                "es_rescate": False,
                "tiempo_espera_horas": 6.5,
                "desglose": {
                    "tipo_paciente": 100,
                    "servicio_origen": 0,
                    "ivc": 55,
                    "frc": 37,
                    "tiempo": 22
                },
                "detalles": [
                    "Tipo urgencia: +100",
                    "IVC Edad 70-79: +20",
                    "IVC Monitorización activa: +20",
                    "IVC Complejidad UTI: +15",
                    "FRC Drogas vasoactivas: +15",
                    "FRC Sedación: +12",
                    "FRC Oxígeno: +10",
                    "Tiempo urgencia 6.5h: +22"
                ]
            }
        }


class EstadisticasColaResponse(BaseModel):
    """
    Estadísticas de la cola de espera de un hospital.
    """
    hospital_id: str = Field(..., description="ID del hospital")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Fecha/hora de la consulta")
    
    total_pacientes: int = Field(0, description="Total de pacientes en cola")
    
    por_tipo: Dict[str, int] = Field(
        default_factory=dict,
        description="Conteo por tipo de paciente"
    )
    
    en_rescate: int = Field(0, description="Pacientes en modo rescate")
    
    prioridad_promedio: float = Field(0, description="Prioridad promedio")
    prioridad_maxima: float = Field(0, description="Prioridad máxima")
    prioridad_minima: float = Field(0, description="Prioridad mínima")
    
    # Alertas
    alertas: List[str] = Field(default_factory=list, description="Alertas del sistema")
    
    class Config:
        json_schema_extra = {
            "example": {
                "hospital_id": "hosp123",
                "timestamp": "2024-01-15T10:30:00Z",
                "total_pacientes": 25,
                "por_tipo": {
                    "hospitalizado": 5,
                    "urgencia": 12,
                    "derivado": 3,
                    "ambulatorio": 5
                },
                "en_rescate": 2,
                "prioridad_promedio": 145.5,
                "prioridad_maxima": 500,
                "prioridad_minima": 65,
                "alertas": [
                    "⚠️ 2 pacientes en modo RESCATE",
                    "⚠️ 3 pacientes con >12h de espera"
                ]
            }
        }


class ComparacionPrioridadResponse(BaseModel):
    """
    Respuesta para comparar prioridades entre dos pacientes.
    Útil para debugging y validación del sistema.
    """
    paciente_a: PrioridadPacienteResponse
    paciente_b: PrioridadPacienteResponse
    
    diferencia_total: float = Field(..., description="Diferencia de prioridad (A - B)")
    paciente_prioritario: str = Field(..., description="ID del paciente con mayor prioridad")
    
    comparacion_componentes: Dict[str, Dict[str, float]] = Field(
        ...,
        description="Comparación componente por componente"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "paciente_a": {"paciente_id": "abc", "prioridad_total": 200},
                "paciente_b": {"paciente_id": "xyz", "prioridad_total": 150},
                "diferencia_total": 50,
                "paciente_prioritario": "abc",
                "comparacion_componentes": {
                    "tipo_paciente": {"a": 100, "b": 100, "diferencia": 0},
                    "ivc": {"a": 50, "b": 30, "diferencia": 20},
                    "frc": {"a": 37, "b": 0, "diferencia": 37},
                    "tiempo": {"a": 13, "b": 20, "diferencia": -7}
                }
            }
        }


class SimulacionPrioridadRequest(BaseModel):
    """
    Request para simular el cálculo de prioridad sin crear paciente.
    Útil para testing y capacitación.
    """
    tipo_paciente: str = Field(..., description="Tipo de paciente")
    motivo_ingreso_ambulatorio: Optional[str] = Field(None, description="Motivo si es ambulatorio")
    edad: int = Field(..., description="Edad del paciente")
    complejidad: str = Field("ninguna", description="Complejidad requerida")
    tipo_aislamiento: Optional[str] = Field(None, description="Tipo de aislamiento")
    tiempo_espera_minutos: int = Field(0, description="Minutos en espera")
    es_embarazada: bool = Field(False, description="Si está embarazada")
    tiene_casos_especiales: bool = Field(False, description="Si tiene casos especiales")
    tiene_monitorizacion: bool = Field(False, description="Si tiene monitorización activa")
    tiene_observacion: bool = Field(False, description="Si tiene observación activa")
    tiene_cama: bool = Field(False, description="Si tiene cama asignada")
    servicio_origen: Optional[str] = Field(None, description="Servicio de origen si hospitalizado")
    
    # Requerimientos críticos
    tiene_drogas_vasoactivas: bool = Field(False)
    tiene_sedacion: bool = Field(False)
    tiene_oxigeno: bool = Field(False)
    tiene_procedimiento_invasivo: bool = Field(False)
    tiene_aspiracion_secreciones: bool = Field(False)


class SimulacionPrioridadResponse(BaseModel):
    """
    Respuesta de simulación de prioridad.
    """
    prioridad_total: float
    tipo_efectivo: str
    es_rescate: bool
    desglose: DesglosePrioridadResponse
    detalles: List[str]
    
    # Comparación con v2.2 (para validación)
    prioridad_v22_estimada: Optional[float] = Field(
        None, 
        description="Estimación de prioridad con sistema v2.2 (para comparación)"
    )
    diferencia_vs_v22: Optional[float] = Field(
        None,
        description="Diferencia con sistema v2.2"
    )