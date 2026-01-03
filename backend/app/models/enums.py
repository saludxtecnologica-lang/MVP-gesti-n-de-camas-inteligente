"""
Enumeraciones del sistema.
Centralizadas para evitar imports circulares.
"""
from enum import Enum


class TipoPacienteEnum(str, Enum):
    """Tipo de origen del paciente."""
    URGENCIA = "urgencia"
    AMBULATORIO = "ambulatorio"
    HOSPITALIZADO = "hospitalizado"
    DERIVADO = "derivado"


class SexoEnum(str, Enum):
    """Sexo biológico del paciente."""
    HOMBRE = "hombre"
    MUJER = "mujer"


class EdadCategoriaEnum(str, Enum):
    """Categoría de edad del paciente."""
    PEDIATRICO = "pediatrico"      # 0-14 años
    ADULTO = "adulto"              # 15-59 años
    ADULTO_MAYOR = "adulto_mayor"  # 60+ años


class TipoEnfermedadEnum(str, Enum):
    """Tipo de enfermedad principal."""
    MEDICA = "medica"
    QUIRURGICA = "quirurgica"
    TRAUMATOLOGICA = "traumatologica"
    NEUROLOGICA = "neurologica"
    UROLOGICA = "urologica"
    GERIATRICA = "geriatrica"
    GINECOLOGICA = "ginecologica"
    OBSTETRICA = "obstetrica"


class TipoAislamientoEnum(str, Enum):
    """Tipo de aislamiento requerido."""
    NINGUNO = "ninguno"
    CONTACTO = "contacto"
    GOTITAS = "gotitas"
    AEREO = "aereo"
    AMBIENTE_PROTEGIDO = "ambiente_protegido"
    ESPECIAL = "especial"


class ComplejidadEnum(str, Enum):
    """Nivel de complejidad asistencial requerida."""
    NINGUNA = "ninguna"
    BAJA = "baja"
    MEDIA = "media"  # UTI
    ALTA = "alta"    # UCI


class TipoServicioEnum(str, Enum):
    """Tipo de servicio hospitalario."""
    UCI = "uci"
    UTI = "uti"
    MEDICINA = "medicina"
    AISLAMIENTO = "aislamiento"
    CIRUGIA = "cirugia"
    OBSTETRICIA = "obstetricia"
    PEDIATRIA = "pediatria"
    MEDICO_QUIRURGICO = "medico_quirurgico"


class EstadoCamaEnum(str, Enum):
    """Estado de una cama hospitalaria."""
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
    # ============================================
    # NUEVO ESTADO: PACIENTE FALLECIDO
    # ============================================
    FALLECIDO = "fallecido"


class EstadoListaEsperaEnum(str, Enum):
    """Estado del paciente en lista de espera."""
    ESPERANDO = "esperando"
    BUSCANDO = "buscando"
    ASIGNADO = "asignado"


# ============================================
# CONSTANTES RELACIONADAS CON ENUMS
# ============================================

# Estados que cuentan como "cama ocupada" (paciente usando la cama)
ESTADOS_CAMA_OCUPADA = [
    EstadoCamaEnum.OCUPADA,
    EstadoCamaEnum.CAMA_EN_ESPERA,
    EstadoCamaEnum.TRASLADO_SALIENTE,
    EstadoCamaEnum.TRASLADO_CONFIRMADO,
    EstadoCamaEnum.ALTA_SUGERIDA,
    EstadoCamaEnum.CAMA_ALTA,
    EstadoCamaEnum.ESPERA_DERIVACION,
    EstadoCamaEnum.DERIVACION_CONFIRMADA,
    EstadoCamaEnum.FALLECIDO,  # AGREGADO: Fallecido también cuenta como ocupada
]

# Aislamientos que requieren sala individual
AISLAMIENTOS_SALA_INDIVIDUAL = [
    TipoAislamientoEnum.AEREO,
    TipoAislamientoEnum.AMBIENTE_PROTEGIDO,
    TipoAislamientoEnum.ESPECIAL,
]

# Aislamientos que pueden estar en sala compartida
AISLAMIENTOS_SALA_COMPARTIDA = [
    TipoAislamientoEnum.NINGUNO,
    TipoAislamientoEnum.CONTACTO,
    TipoAislamientoEnum.GOTITAS,
]

# ============================================
# CONSTANTES DE OXÍGENO Y COMPLEJIDAD
# ============================================

# Requerimientos de oxígeno por nivel de complejidad
OXIGENO_BAJA_COMPLEJIDAD = [
    "O2 por naricera",
    "O2 por Multiventuri",
]

OXIGENO_UTI_COMPLEJIDAD = [
    "O2 con reservorio",
    "CNAF",
    "VMNI",
]

OXIGENO_UCI_COMPLEJIDAD = [
    "VMI",
]

# Todos los requerimientos de oxígeno
TODOS_REQUERIMIENTOS_OXIGENO = (
    OXIGENO_BAJA_COMPLEJIDAD + 
    OXIGENO_UTI_COMPLEJIDAD + 
    OXIGENO_UCI_COMPLEJIDAD
)

# Mapeo de requerimiento de oxígeno a nivel de complejidad
# Nivel 0 = Sin oxígeno
# Nivel 1 = Baja complejidad (naricera, multiventuri)
# Nivel 2 = UTI (reservorio, CNAF, VMNI)
# Nivel 3 = UCI (VMI)
NIVEL_COMPLEJIDAD_OXIGENO = {
    "O2 por naricera": 1,
    "O2 por Multiventuri": 1,
    "O2 con reservorio": 2,
    "CNAF": 2,
    "VMNI": 2,
    "VMI": 3,
}

# ============================================
# MAPEO DE COMPLEJIDAD A SERVICIOS
# CORREGIDO según reglas del documento:
# - UCI: SOLO pacientes con requerimientos UCI exclusivamente
# - UTI: SOLO pacientes con requerimientos UTI exclusivamente
# - BAJA/NINGUNA: Servicios de hospitalización básica
# ============================================

MAPEO_COMPLEJIDAD_SERVICIO = {
    # UCI solo recibe pacientes con requerimientos UCI
    ComplejidadEnum.ALTA: [
        TipoServicioEnum.UCI,
    ],
    # UTI solo recibe pacientes con requerimientos UTI
    # (NO va a UCI según documento: "UTI exclusivamente")
    ComplejidadEnum.MEDIA: [
        TipoServicioEnum.UTI,
    ],
    # Baja complejidad: servicios de hospitalización básica
    ComplejidadEnum.BAJA: [
        TipoServicioEnum.MEDICINA,
        TipoServicioEnum.CIRUGIA,
        TipoServicioEnum.AISLAMIENTO,
        TipoServicioEnum.OBSTETRICIA,
        TipoServicioEnum.PEDIATRIA,
        TipoServicioEnum.MEDICO_QUIRURGICO,
    ],
    # Sin complejidad: mismos servicios que baja
    ComplejidadEnum.NINGUNA: [
        TipoServicioEnum.MEDICINA,
        TipoServicioEnum.CIRUGIA,
        TipoServicioEnum.AISLAMIENTO,
        TipoServicioEnum.OBSTETRICIA,
        TipoServicioEnum.PEDIATRIA,
        TipoServicioEnum.MEDICO_QUIRURGICO,
    ],
}

# ============================================
# MAPEO DE TIPO DE ENFERMEDAD A SERVICIOS
# Según reglas del documento
# ============================================

MAPEO_ENFERMEDAD_SERVICIO = {
    # Medicina: prioridad para enfermedades médicas
    TipoEnfermedadEnum.MEDICA: [
        TipoServicioEnum.MEDICINA,
        TipoServicioEnum.MEDICO_QUIRURGICO,
        TipoServicioEnum.CIRUGIA,  # Solo si no hay médicas en lista
    ],
    # Cirugía: prioridad para quirúrgicas
    TipoEnfermedadEnum.QUIRURGICA: [
        TipoServicioEnum.CIRUGIA,
        TipoServicioEnum.MEDICO_QUIRURGICO,
    ],
    TipoEnfermedadEnum.TRAUMATOLOGICA: [
        TipoServicioEnum.CIRUGIA,
        TipoServicioEnum.MEDICO_QUIRURGICO,
    ],
    TipoEnfermedadEnum.NEUROLOGICA: [
        TipoServicioEnum.CIRUGIA,
        TipoServicioEnum.MEDICO_QUIRURGICO,
    ],
    TipoEnfermedadEnum.UROLOGICA: [
        TipoServicioEnum.CIRUGIA,
        TipoServicioEnum.MEDICO_QUIRURGICO,
    ],
    TipoEnfermedadEnum.GERIATRICA: [
        TipoServicioEnum.MEDICINA,
        TipoServicioEnum.MEDICO_QUIRURGICO,
    ],
    TipoEnfermedadEnum.GINECOLOGICA: [
        TipoServicioEnum.CIRUGIA,
        TipoServicioEnum.OBSTETRICIA,
        TipoServicioEnum.MEDICO_QUIRURGICO,
    ],
    # Obstétrica: SOLO obstetricia
    TipoEnfermedadEnum.OBSTETRICA: [
        TipoServicioEnum.OBSTETRICIA,
    ],
}

# ============================================
# SERVICIOS QUE ACEPTAN CADA TIPO DE PACIENTE
# ============================================

# Servicios que NO aceptan pediátricos
SERVICIOS_SOLO_ADULTOS = [
    TipoServicioEnum.UCI,
    TipoServicioEnum.UTI,
    TipoServicioEnum.MEDICINA,
    TipoServicioEnum.CIRUGIA,
    TipoServicioEnum.AISLAMIENTO,
    TipoServicioEnum.OBSTETRICIA,
    TipoServicioEnum.MEDICO_QUIRURGICO,
]

# Servicios que aceptan pediátricos
SERVICIOS_PEDIATRICOS = [
    TipoServicioEnum.PEDIATRIA,
]

# Servicios con salas individuales (para aislamientos)
SERVICIOS_SALA_INDIVIDUAL = [
    TipoServicioEnum.UCI,
    TipoServicioEnum.UTI,
    TipoServicioEnum.AISLAMIENTO,
]

# Servicios con salas compartidas
SERVICIOS_SALA_COMPARTIDA = [
    TipoServicioEnum.MEDICINA,
    TipoServicioEnum.CIRUGIA,
    TipoServicioEnum.OBSTETRICIA,
    TipoServicioEnum.PEDIATRIA,
    TipoServicioEnum.MEDICO_QUIRURGICO,
]