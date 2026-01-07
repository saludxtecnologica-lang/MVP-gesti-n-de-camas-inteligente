"""
Modelo de Paciente.
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime
import uuid
import json

from app.models.enums import (
    TipoPacienteEnum,
    SexoEnum,
    EdadCategoriaEnum,
    TipoEnfermedadEnum,
    TipoAislamientoEnum,
    ComplejidadEnum,
    EstadoListaEsperaEnum,
)

if TYPE_CHECKING:
    from app.models.hospital import Hospital
    from app.models.cama import Cama


class Paciente(SQLModel, table=True):
    """
    Modelo de Paciente.
    
    Representa un paciente en el sistema de gestión de camas.
    Contiene toda la información clínica y de asignación.
    """
    __tablename__ = "paciente"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), 
        primary_key=True
    )
    
    # ============================================
    # DATOS PERSONALES
    # ============================================
    nombre: str
    run: str = Field(index=True)
    sexo: SexoEnum
    edad: int
    edad_categoria: EdadCategoriaEnum
    es_embarazada: bool = Field(default=False)
    
    # ============================================
    # DATOS CLÍNICOS
    # ============================================
    diagnostico: str
    tipo_enfermedad: TipoEnfermedadEnum
    tipo_aislamiento: TipoAislamientoEnum = Field(default=TipoAislamientoEnum.NINGUNO)
    notas_adicionales: Optional[str] = Field(default=None)
    documento_adjunto: Optional[str] = Field(default=None)
    
    # ============================================
    # REQUERIMIENTOS CLÍNICOS (JSON como string)
    # ============================================
    requerimientos_no_definen: Optional[str] = Field(default=None)
    requerimientos_baja: Optional[str] = Field(default=None)
    requerimientos_uti: Optional[str] = Field(default=None)
    requerimientos_uci: Optional[str] = Field(default=None)
    casos_especiales: Optional[str] = Field(default=None)
    
    # Campos especiales para observación clínica
    motivo_observacion: Optional[str] = Field(default=None)
    justificacion_observacion: Optional[str] = Field(default=None)
    
    # Campos especiales para monitorización
    motivo_monitorizacion: Optional[str] = Field(default=None)
    justificacion_monitorizacion: Optional[str] = Field(default=None)
    
    # Procedimiento invasivo
    procedimiento_invasivo: Optional[str] = Field(default=None, max_length=500)
    preparacion_quirurgica_detalle: Optional[str] = Field(default=None, max_length=500)  # AGREGAR

    # Timer de observación
    observacion_tiempo_horas: Optional[int] = Field(default=None)
    observacion_inicio: Optional[datetime] = Field(default=None)

    # Timer de monitorización
    monitorizacion_tiempo_horas: Optional[int] = Field(default=None)
    monitorizacion_inicio: Optional[datetime] = Field(default=None)

    # Motivo ambulatorio
    motivo_ingreso_ambulatorio: Optional[str] = Field(default=None)
    
    # ============================================
    # COMPLEJIDAD Y TIPO
    # ============================================
    complejidad_requerida: ComplejidadEnum = Field(default=ComplejidadEnum.BAJA)
    tipo_paciente: TipoPacienteEnum
    hospital_id: str = Field(foreign_key="hospital.id", index=True)
    
    # ============================================
    # ASIGNACIÓN DE CAMAS
    # ============================================
    cama_id: Optional[str] = Field(default=None, foreign_key="cama.id", index=True)
    cama_destino_id: Optional[str] = Field(default=None, foreign_key="cama.id")
    cama_origen_derivacion_id: Optional[str] = Field(default=None)
    cama_reservada_derivacion_id: Optional[str] = Field(default=None, foreign_key="cama.id")  # Cama reservada para derivación
    
     # ============================================
    # ORIGEN Y DESTINO (para priorización)
    # ============================================
    origen_servicio_nombre: Optional[str] = Field(default=None)
    servicio_destino: Optional[str] = Field(default=None)
    
    # ============================================
    # LISTA DE ESPERA
    # ============================================
    en_lista_espera: bool = Field(default=False, index=True)
    estado_lista_espera: EstadoListaEsperaEnum = Field(default=EstadoListaEsperaEnum.ESPERANDO)
    prioridad_calculada: float = Field(default=0.0)
    timestamp_lista_espera: Optional[datetime] = Field(default=None)
    
    # ============================================
    # ESTADOS ESPECIALES
    # ============================================
    requiere_nueva_cama: bool = Field(default=False)
    en_espera: bool = Field(default=False)
    
    # Espera por evaluación de oxígeno
    oxigeno_desactivado_at: Optional[datetime] = Field(default=None)
    requerimientos_oxigeno_previos: Optional[str] = Field(default=None)
    esperando_evaluacion_oxigeno: bool = Field(default=False)
    
    # ============================================
    # DERIVACIÓN
    # ============================================
    derivacion_hospital_destino_id: Optional[str] = Field(default=None)
    derivacion_motivo: Optional[str] = Field(default=None)
    derivacion_estado: Optional[str] = Field(default=None, index=True)
    derivacion_motivo_rechazo: Optional[str] = Field(default=None)
    
    # ============================================
    # ALTA
    # ============================================
    alta_solicitada: bool = Field(default=False)
    alta_motivo: Optional[str] = Field(default=None)
    
    # ============================================
    # FALLECIMIENTO
    # ============================================
    fallecido: bool = Field(default=False, index=True)
    causa_fallecimiento: Optional[str] = Field(default=None)
    fallecido_at: Optional[datetime] = Field(default=None)
    estado_cama_anterior_fallecimiento: Optional[str] = Field(default=None)

    # ============================================
    # TIMESTAMPS
    # ============================================
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # ============================================
    # RELACIONES
    # ============================================
    hospital: "Hospital" = Relationship(back_populates="pacientes")
    
    cama: Optional["Cama"] = Relationship(
        back_populates="paciente_actual",
        sa_relationship_kwargs={"foreign_keys": "[Paciente.cama_id]"}
    )
    
    cama_destino: Optional["Cama"] = Relationship(
        back_populates="pacientes_destino",
        sa_relationship_kwargs={"foreign_keys": "[Paciente.cama_destino_id]"}
    )
    
    # ============================================
    # PROPIEDADES CALCULADAS
    # ============================================
    
    @property
    def tiempo_espera_min(self) -> int:
        """Calcula minutos en lista de espera."""
        if self.timestamp_lista_espera:
            delta = datetime.utcnow() - self.timestamp_lista_espera
            return int(delta.total_seconds() / 60)
        return 0
    
    @property
    def es_adulto_mayor(self) -> bool:
        """Verifica si es adulto mayor."""
        return self.edad_categoria == EdadCategoriaEnum.ADULTO_MAYOR
    
    @property
    def es_pediatrico(self) -> bool:
        """Verifica si es pediátrico."""
        return self.edad_categoria == EdadCategoriaEnum.PEDIATRICO
    
    @property
    def requiere_aislamiento_individual(self) -> bool:
        """Verifica si requiere sala individual por aislamiento."""
        return self.tipo_aislamiento in [
            TipoAislamientoEnum.AEREO,
            TipoAislamientoEnum.AMBIENTE_PROTEGIDO,
            TipoAislamientoEnum.ESPECIAL
        ]
    
    @property
    def es_derivado(self) -> bool:
        """Verifica si es un paciente derivado."""
        return (
            self.tipo_paciente == TipoPacienteEnum.DERIVADO or
            self.derivacion_estado == "aceptada"
        )
    
    @property
    def esta_fallecido(self) -> bool:
        """Verifica si el paciente está marcado como fallecido."""
        return self.fallecido
    
    # ============================================
    # MÉTODOS DE UTILIDAD
    # ============================================
    
    def get_requerimientos_lista(self, campo: str) -> list:
        """
        Obtiene los requerimientos como lista.
        
        Args:
            campo: Nombre del campo de requerimientos
        
        Returns:
            Lista de requerimientos
        """
        valor = getattr(self, campo, None)
        if not valor:
            return []
        if isinstance(valor, list):
            return valor
        try:
            parsed = json.loads(valor)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    def tiene_requerimientos(self) -> bool:
        """Verifica si tiene algún requerimiento de hospitalización."""
        return bool(
            self.get_requerimientos_lista("requerimientos_uci") or
            self.get_requerimientos_lista("requerimientos_uti") or
            self.get_requerimientos_lista("requerimientos_baja")
        )
    
    def tiene_casos_especiales(self) -> bool:
        """Verifica si tiene casos especiales."""
        return bool(self.get_requerimientos_lista("casos_especiales"))
    
    def __repr__(self) -> str:
        return f"Paciente(id={self.id}, nombre={self.nombre}, run={self.run})"