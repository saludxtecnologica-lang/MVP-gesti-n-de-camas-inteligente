"""
Modelos de datos para el Sistema de Gestión de Camas Hospitalarias.
Usa SQLModel para ORM y validación con Pydantic.
"""

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid


# ============================================
# ENUMS
# ============================================

class TipoPacienteEnum(str, Enum):
    URGENCIA = "urgencia"
    AMBULATORIO = "ambulatorio"
    HOSPITALIZADO = "hospitalizado"
    DERIVADO = "derivado"


class SexoEnum(str, Enum):
    HOMBRE = "hombre"
    MUJER = "mujer"


class EdadCategoriaEnum(str, Enum):
    PEDIATRICO = "pediatrico"  # 0-14 años
    ADULTO = "adulto"          # 15-59 años
    ADULTO_MAYOR = "adulto_mayor"  # 60+ años


class TipoEnfermedadEnum(str, Enum):
    MEDICA = "medica"
    QUIRURGICA = "quirurgica"
    TRAUMATOLOGICA = "traumatologica"
    NEUROLOGICA = "neurologica"
    UROLOGICA = "urologica"
    GERIATRICA = "geriatrica"
    GINECOLOGICA = "ginecologica"
    OBSTETRICA = "obstetrica"


class TipoAislamientoEnum(str, Enum):
    NINGUNO = "ninguno"
    CONTACTO = "contacto"
    GOTITAS = "gotitas"
    AEREO = "aereo"
    AMBIENTE_PROTEGIDO = "ambiente_protegido"
    ESPECIAL = "especial"


class ComplejidadEnum(str, Enum):
    NINGUNA = "ninguna"
    BAJA = "baja"
    MEDIA = "media"  # UTI
    ALTA = "alta"    # UCI


class TipoServicioEnum(str, Enum):
    UCI = "uci"
    UTI = "uti"
    MEDICINA = "medicina"
    AISLAMIENTO = "aislamiento"
    CIRUGIA = "cirugia"
    OBSTETRICIA = "obstetricia"
    PEDIATRIA = "pediatria"
    MEDICO_QUIRURGICO = "medico_quirurgico"


class EstadoCamaEnum(str, Enum):
    LIBRE = "libre"
    OCUPADA = "ocupada"
    TRASLADO_ENTRANTE = "traslado_entrante"
    CAMA_EN_ESPERA = "cama_en_espera"
    TRASLADO_SALIENTE = "traslado_saliente"
    TRASLADO_CONFIRMADO = "traslado_confirmado"
    ALTA_SUGERIDA = "alta_sugerida"
    CAMA_ALTA = "cama_alta"
    EN_LIMPIEZA = "en_limpieza"
    BLOQUEADA = "bloqueada"
    ESPERA_DERIVACION = "espera_derivacion"
    DERIVACION_CONFIRMADA = "derivacion_confirmada"


class EstadoListaEsperaEnum(str, Enum):
    ESPERANDO = "esperando"
    BUSCANDO = "buscando"
    ASIGNADO = "asignado"


# ============================================
# MODELOS
# ============================================

class Hospital(SQLModel, table=True):
    """Modelo de Hospital"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    nombre: str = Field(index=True)
    codigo: str = Field(unique=True)  # PM, LL, CA
    es_central: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relaciones
    servicios: List["Servicio"] = Relationship(back_populates="hospital")
    pacientes: List["Paciente"] = Relationship(back_populates="hospital")


class Servicio(SQLModel, table=True):
    """Modelo de Servicio Hospitalario"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    nombre: str
    codigo: str  # UCI, UTI, MED, etc.
    tipo: TipoServicioEnum
    hospital_id: str = Field(foreign_key="hospital.id")
    numero_inicio_camas: int = Field(default=100)
    
    # Relaciones
    hospital: Hospital = Relationship(back_populates="servicios")
    salas: List["Sala"] = Relationship(back_populates="servicio")


class Sala(SQLModel, table=True):
    """Modelo de Sala"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    numero: int
    es_individual: bool = Field(default=False)
    servicio_id: str = Field(foreign_key="servicio.id")
    sexo_asignado: Optional[SexoEnum] = Field(default=None)
    
    # Relaciones
    servicio: Servicio = Relationship(back_populates="salas")
    camas: List["Cama"] = Relationship(back_populates="sala")


class Cama(SQLModel, table=True):
    """Modelo de Cama"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    numero: int
    letra: Optional[str] = Field(default=None)  # A, B, C para camas compartidas
    identificador: str = Field(index=True)  # MED-501-A
    sala_id: str = Field(foreign_key="sala.id")
    estado: EstadoCamaEnum = Field(default=EstadoCamaEnum.LIBRE)
    
    # Timestamps para estados
    estado_updated_at: datetime = Field(default_factory=datetime.utcnow)
    limpieza_inicio: Optional[datetime] = Field(default=None)
    
    # Mensaje de estado
    mensaje_estado: Optional[str] = Field(default=None)
    cama_asignada_destino: Optional[str] = Field(default=None)
    
    # Relaciones
    sala: Sala = Relationship(back_populates="camas")
    paciente_actual: Optional["Paciente"] = Relationship(
        back_populates="cama",
        sa_relationship_kwargs={"foreign_keys": "[Paciente.cama_id]"}
    )
    pacientes_destino: List["Paciente"] = Relationship(
        back_populates="cama_destino",
        sa_relationship_kwargs={"foreign_keys": "[Paciente.cama_destino_id]"}
    )


class Paciente(SQLModel, table=True):
    """Modelo de Paciente"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Datos personales
    nombre: str
    run: str = Field(index=True)
    sexo: SexoEnum
    edad: int
    edad_categoria: EdadCategoriaEnum
    es_embarazada: bool = Field(default=False)
    
    # Datos clínicos
    diagnostico: str
    tipo_enfermedad: TipoEnfermedadEnum
    tipo_aislamiento: TipoAislamientoEnum = Field(default=TipoAislamientoEnum.NINGUNO)
    notas_adicionales: Optional[str] = Field(default=None)
    documento_adjunto: Optional[str] = Field(default=None)
    
    # Requerimientos clínicos (JSON como string)
    requerimientos_no_definen: Optional[str] = Field(default=None)
    requerimientos_baja: Optional[str] = Field(default=None)
    requerimientos_uti: Optional[str] = Field(default=None)
    requerimientos_uci: Optional[str] = Field(default=None)
    casos_especiales: Optional[str] = Field(default=None)
    
    # Campos especiales para observación
    motivo_observacion: Optional[str] = Field(default=None)
    justificacion_observacion: Optional[str] = Field(default=None)
    procedimiento_invasivo: Optional[str] = Field(default=None)
    
    # Complejidad calculada
    complejidad_requerida: ComplejidadEnum = Field(default=ComplejidadEnum.BAJA)
    
    # Tipo y estado del paciente
    tipo_paciente: TipoPacienteEnum
    hospital_id: str = Field(foreign_key="hospital.id")
    
    # Cama actual y destino
    cama_id: Optional[str] = Field(default=None, foreign_key="cama.id")
    cama_destino_id: Optional[str] = Field(default=None, foreign_key="cama.id")
    
    # Estado en lista de espera
    en_lista_espera: bool = Field(default=False)
    estado_lista_espera: EstadoListaEsperaEnum = Field(default=EstadoListaEsperaEnum.ESPERANDO)
    prioridad_calculada: float = Field(default=0.0)
    timestamp_lista_espera: Optional[datetime] = Field(default=None)
    
    # Estados especiales
    requiere_nueva_cama: bool = Field(default=False)
    en_espera: bool = Field(default=False)
    
    # Derivación
    derivacion_hospital_destino_id: Optional[str] = Field(default=None)
    derivacion_motivo: Optional[str] = Field(default=None)
    derivacion_estado: Optional[str] = Field(default=None)  # pendiente, aceptado, rechazado
    derivacion_motivo_rechazo: Optional[str] = Field(default=None)
    
    # Alta
    alta_solicitada: bool = Field(default=False)
    alta_motivo: Optional[str] = Field(default=None)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relaciones
    hospital: Hospital = Relationship(back_populates="pacientes")
    cama: Optional[Cama] = Relationship(
        back_populates="paciente_actual",
        sa_relationship_kwargs={"foreign_keys": "[Paciente.cama_id]"}
    )
    cama_destino: Optional[Cama] = Relationship(
        back_populates="pacientes_destino",
        sa_relationship_kwargs={"foreign_keys": "[Paciente.cama_destino_id]"}
    )
    
    @property
    def tiempo_espera_min(self) -> int:
        """Calcula minutos en lista de espera"""
        if self.timestamp_lista_espera:
            delta = datetime.utcnow() - self.timestamp_lista_espera
            return int(delta.total_seconds() / 60)
        return 0
    
    @property
    def es_adulto_mayor(self) -> bool:
        return self.edad_categoria == EdadCategoriaEnum.ADULTO_MAYOR
    
    @property
    def es_pediatrico(self) -> bool:
        return self.edad_categoria == EdadCategoriaEnum.PEDIATRICO
    
    @property
    def requiere_aislamiento_individual(self) -> bool:
        return self.tipo_aislamiento in [
            TipoAislamientoEnum.AEREO,
            TipoAislamientoEnum.AMBIENTE_PROTEGIDO,
            TipoAislamientoEnum.ESPECIAL
        ]


class ConfiguracionSistema(SQLModel, table=True):
    """Configuración global del sistema"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    modo_manual: bool = Field(default=False)
    tiempo_limpieza_segundos: int = Field(default=60)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LogActividad(SQLModel, table=True):
    """Log de actividades del sistema"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tipo: str  # asignacion, traslado, alta, derivacion, etc.
    descripcion: str
    hospital_id: Optional[str] = Field(default=None)
    paciente_id: Optional[str] = Field(default=None)
    cama_id: Optional[str] = Field(default=None)
    datos_extra: Optional[str] = Field(default=None)  # JSON
    created_at: datetime = Field(default_factory=datetime.utcnow)