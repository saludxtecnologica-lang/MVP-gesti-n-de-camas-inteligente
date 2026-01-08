"""
Modelo de Usuario para autenticación.
"""

from typing import Optional, List
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field


# ============================================
# ENUMS
# ============================================

class RolEnum(str, Enum):
    """
    Roles disponibles en el sistema - Sistema RBAC Multinivel.

    Capa 1 - Administración y Red (Nivel Global):
        - PROGRAMADOR: Equipo técnico con acceso total
        - DIRECTIVO_RED: Equipo directivo con visión de toda la red (solo lectura)

    Capa 2 - Gestión Local (Nivel Hospitalario):
        - DIRECTIVO_HOSPITAL: Directivos del hospital (solo lectura de su hospital)
        - GESTOR_CAMAS: Equipo de gestión de camas (Puerto Montt)

    Capa 3 - Clínica (Nivel Servicio):
        - MEDICO: Médico por servicio
        - ENFERMERA: Enfermero/a o Matrón/a por servicio
        - TENS: Técnico de enfermería de nivel superior
    """
    # Capa 1: Administración y Red
    PROGRAMADOR = "programador"
    DIRECTIVO_RED = "directivo_red"

    # Capa 2: Gestión Local
    DIRECTIVO_HOSPITAL = "directivo_hospital"
    GESTOR_CAMAS = "gestor_camas"

    # Capa 3: Clínica
    MEDICO = "medico"
    ENFERMERA = "enfermera"
    TENS = "tens"

    # Roles de servicio específicos
    JEFE_SERVICIO = "jefe_servicio"
    SUPERVISORA_ENFERMERIA = "supervisora_enfermeria"
    URGENCIAS = "urgencias"
    JEFE_URGENCIAS = "jefe_urgencias"
    AMBULATORIO = "ambulatorio"

    # Roles especializados
    DERIVACIONES = "derivaciones"
    ESTADISTICAS = "estadisticas"
    VISUALIZADOR = "visualizador"
    LIMPIEZA = "limpieza"

    # Aliases para compatibilidad
    SUPER_ADMIN = "programador"
    ADMIN = "gestor_camas"
    COORDINADOR_RED = "directivo_red"
    COORDINADOR_CAMAS = "gestor_camas"
    OPERADOR = "visualizador"


class PermisoEnum(str, Enum):
    """Permisos granulares del sistema según especificación RBAC."""

    # Pacientes
    PACIENTE_CREAR = "paciente:crear"
    PACIENTE_VER = "paciente:ver"
    PACIENTE_EDITAR = "paciente:editar"
    PACIENTE_ELIMINAR = "paciente:eliminar"
    PACIENTE_REEVALUAR = "paciente:reevaluar"  # Médico, Enfermera

    # Camas
    CAMA_VER = "cama:ver"
    CAMA_BLOQUEAR = "cama:bloquear"
    CAMA_DESBLOQUEAR = "cama:desbloquear"
    CAMA_ASIGNAR = "cama:asignar"

    # Lista de Espera y Búsqueda de Cama
    LISTA_ESPERA_VER = "lista_espera:ver"
    LISTA_ESPERA_GESTIONAR = "lista_espera:gestionar"
    LISTA_ESPERA_PRIORIZAR = "lista_espera:priorizar"
    BUSQUEDA_CAMA_INICIAR = "busqueda_cama:iniciar"  # Solo Médico

    # Traslados
    TRASLADO_INICIAR = "traslado:iniciar"  # Médico
    TRASLADO_ACEPTAR = "traslado:aceptar"  # Enfermera
    TRASLADO_CONFIRMAR = "traslado:confirmar"  # Enfermera (mismo que aceptar)
    TRASLADO_COMPLETAR = "traslado:completar"  # Médico, Enfermera, TENS
    TRASLADO_CANCELAR = "traslado:cancelar"  # Médico, Enfermera
    TRASLADO_VER = "traslado:ver"

    # Derivaciones
    DERIVACION_SOLICITAR = "derivacion:solicitar"  # Médico
    DERIVACION_REALIZAR = "derivacion:realizar"  # Médico (realizar/aceptar/rechazar)
    DERIVACION_ACEPTAR = "derivacion:aceptar"  # Médico
    DERIVACION_RECHAZAR = "derivacion:rechazar"  # Médico
    DERIVACION_VER = "derivacion:ver"
    DERIVACION_CANCELAR = "derivacion:cancelar"  # Médico

    # Altas y Egresos
    ALTA_SUGERIR = "alta:sugerir"  # Médico (seleccionar "Dar Alta")
    ALTA_EJECUTAR = "alta:ejecutar"  # Enfermera (estado "Cama Alta")
    ALTA_CANCELAR = "alta:cancelar"
    EGRESO_REGISTRAR = "egreso:registrar"  # Enfermera (Fallecido/Derivación Confirmada)

    # Modo Manual
    MODO_MANUAL_ASIGNAR = "modo_manual:asignar"
    MODO_MANUAL_INTERCAMBIAR = "modo_manual:intercambiar"

    # Pausas de Oxígeno
    PAUSA_OXIGENO_OMITIR = "pausa_oxigeno:omitir"  # Médico, Enfermera

    # Registros
    REGISTRO_ELIMINAR = "registro:eliminar"  # Médico, Enfermera

    # Configuración
    CONFIGURACION_VER = "configuracion:ver"
    CONFIGURACION_EDITAR = "configuracion:editar"

    # Estadísticas
    ESTADISTICAS_VER = "estadisticas:ver"
    ESTADISTICAS_EXPORTAR = "estadisticas:exportar"

    # Usuarios
    USUARIOS_VER = "usuarios:ver"
    USUARIOS_CREAR = "usuarios:crear"
    USUARIOS_EDITAR = "usuarios:editar"
    USUARIOS_ELIMINAR = "usuarios:eliminar"

    # Hospitales
    HOSPITAL_VER = "hospital:ver"
    HOSPITAL_EDITAR = "hospital:editar"
    HOSPITAL_TELEFONOS = "hospital:telefonos"

    # Fallecimiento
    FALLECIMIENTO_REGISTRAR = "fallecimiento:registrar"
    FALLECIMIENTO_CANCELAR = "fallecimiento:cancelar"

    # Limpieza
    LIMPIEZA_MARCAR = "limpieza:marcar"
    LIMPIEZA_COMPLETAR = "limpieza:completar"

    # Dashboard
    DASHBOARD_VER = "dashboard:ver"  # No disponible para Urgencias y Ambulatorio

    # Adjuntos y Resumen
    RESUMEN_VER = "resumen:ver"  # Médico, Enfermera (ver documentos adjuntos)


# ============================================
# PERMISOS POR ROL
# ============================================

PERMISOS_POR_ROL: dict[RolEnum, set[PermisoEnum]] = {
    # ================================================
    # CAPA 1: ADMINISTRACIÓN Y RED (NIVEL GLOBAL)
    # ================================================

    # Equipo Programador: Acceso irrestricto a todas las funciones
    RolEnum.PROGRAMADOR: set(PermisoEnum),  # Todos los permisos

    # Equipo Directivo de Red: Solo lectura de todos los hospitales
    # BLOQUEO TOTAL DE ESCRITURA - No pueden registrar, reevaluar, derivar, dar altas, modificar tiempos
    RolEnum.DIRECTIVO_RED: {
        # Visualización
        PermisoEnum.PACIENTE_VER,
        PermisoEnum.CAMA_VER,
        PermisoEnum.DASHBOARD_VER,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.TRASLADO_VER,
        PermisoEnum.DERIVACION_VER,
        PermisoEnum.RESUMEN_VER,  # Ver resúmenes de paciente con documentos adjuntos
        PermisoEnum.ESTADISTICAS_VER,
        PermisoEnum.ESTADISTICAS_EXPORTAR,
        PermisoEnum.HOSPITAL_VER,
    },

    # ================================================
    # CAPA 2: GESTIÓN LOCAL (NIVEL HOSPITALARIO)
    # ================================================

    # Equipo Directivo Hospital: Solo lectura de su hospital específico
    RolEnum.DIRECTIVO_HOSPITAL: {
        PermisoEnum.PACIENTE_VER,
        PermisoEnum.CAMA_VER,
        PermisoEnum.DASHBOARD_VER,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.RESUMEN_VER,
        PermisoEnum.ESTADISTICAS_VER,
        PermisoEnum.HOSPITAL_VER,
    },

    # Equipo Gestión de Camas (Exclusivo Hospital Puerto Montt)
    # Funciones Operativas: derivaciones, traslados, omitir pausas, eliminar registros, altas, egresos
    # Funciones de Sistema: bloquear camas, modo manual
    # Limitaciones: NO pueden reevaluar clínicamente ni registrar pacientes inicialmente
    RolEnum.GESTOR_CAMAS: {
        # Visualización
        PermisoEnum.PACIENTE_VER,
        PermisoEnum.PACIENTE_EDITAR,  # Pero NO PACIENTE_CREAR ni PACIENTE_REEVALUAR
        PermisoEnum.CAMA_VER,
        PermisoEnum.DASHBOARD_VER,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.LISTA_ESPERA_GESTIONAR,
        PermisoEnum.RESUMEN_VER,

        # Camas - Sistema
        PermisoEnum.CAMA_BLOQUEAR,
        PermisoEnum.CAMA_DESBLOQUEAR,
        PermisoEnum.CAMA_ASIGNAR,

        # Traslados
        PermisoEnum.TRASLADO_INICIAR,
        PermisoEnum.TRASLADO_ACEPTAR,
        PermisoEnum.TRASLADO_CONFIRMAR,
        PermisoEnum.TRASLADO_COMPLETAR,
        PermisoEnum.TRASLADO_CANCELAR,
        PermisoEnum.TRASLADO_VER,

        # Derivaciones
        PermisoEnum.DERIVACION_SOLICITAR,
        PermisoEnum.DERIVACION_REALIZAR,
        PermisoEnum.DERIVACION_ACEPTAR,
        PermisoEnum.DERIVACION_RECHAZAR,
        PermisoEnum.DERIVACION_VER,
        PermisoEnum.DERIVACION_CANCELAR,

        # Altas y Egresos
        PermisoEnum.ALTA_SUGERIR,
        PermisoEnum.ALTA_EJECUTAR,
        PermisoEnum.ALTA_CANCELAR,
        PermisoEnum.EGRESO_REGISTRAR,

        # Modo Manual
        PermisoEnum.MODO_MANUAL_ASIGNAR,
        PermisoEnum.MODO_MANUAL_INTERCAMBIAR,

        # Operaciones especiales
        PermisoEnum.PAUSA_OXIGENO_OMITIR,
        PermisoEnum.REGISTRO_ELIMINAR,

        # Fallecimiento
        PermisoEnum.FALLECIMIENTO_REGISTRAR,
        PermisoEnum.FALLECIMIENTO_CANCELAR,

        # Estadísticas y Configuración
        PermisoEnum.ESTADISTICAS_VER,
        PermisoEnum.CONFIGURACION_VER,
        PermisoEnum.HOSPITAL_VER,
        PermisoEnum.HOSPITAL_TELEFONOS,

        # Limpieza
        PermisoEnum.LIMPIEZA_MARCAR,
        PermisoEnum.LIMPIEZA_COMPLETAR,
    },

    # ================================================
    # CAPA 3: CLÍNICA (NIVEL SERVICIO + ROL PROFESIONAL)
    # ================================================

    # MÉDICO - Por servicio
    # Funciones según tabla: Reevaluación, Ver resumen/adjuntos, Realizar/Aceptar/Rechazar Derivación,
    # Iniciar búsqueda de cama, Cancelar Traslado, Seleccionar "Dar Alta" (Sugerida),
    # Completar Traslado, Omitir pausas de oxígeno / Eliminar
    RolEnum.MEDICO: {
        # Visualización
        PermisoEnum.PACIENTE_VER,
        PermisoEnum.CAMA_VER,
        PermisoEnum.DASHBOARD_VER,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.RESUMEN_VER,  # Ver resumen e información con adjuntos

        # Reevaluación de paciente
        PermisoEnum.PACIENTE_REEVALUAR,

        # Derivaciones (Realizar, Aceptar, Rechazar)
        PermisoEnum.DERIVACION_SOLICITAR,
        PermisoEnum.DERIVACION_REALIZAR,
        PermisoEnum.DERIVACION_ACEPTAR,
        PermisoEnum.DERIVACION_RECHAZAR,
        PermisoEnum.DERIVACION_VER,
        PermisoEnum.DERIVACION_CANCELAR,

        # Búsqueda de cama
        PermisoEnum.BUSQUEDA_CAMA_INICIAR,

        # Traslados
        PermisoEnum.TRASLADO_INICIAR,
        PermisoEnum.TRASLADO_COMPLETAR,
        PermisoEnum.TRASLADO_CANCELAR,
        PermisoEnum.TRASLADO_VER,

        # Altas
        PermisoEnum.ALTA_SUGERIR,  # Seleccionar "Dar Alta" (Sugerida)

        # Operaciones especiales
        PermisoEnum.PAUSA_OXIGENO_OMITIR,
        PermisoEnum.REGISTRO_ELIMINAR,

        # Fallecimiento
        PermisoEnum.FALLECIMIENTO_REGISTRAR,

        # Información
        PermisoEnum.HOSPITAL_VER,
    },

    # ENFERMERA/MATRONA - Por servicio
    # Funciones según tabla: Registro de pacientes, Reevaluación, Ver resumen/adjuntos, Aceptar Traslado de cama,
    # Cancelar Traslado, Dar Alta (Estado "Cama Alta"), Egreso (Fallecido/Derivación Confirmada),
    # Completar Traslado, Omitir pausas de oxígeno / Eliminar
    RolEnum.ENFERMERA: {
        # Visualización
        PermisoEnum.PACIENTE_VER,
        PermisoEnum.CAMA_VER,
        PermisoEnum.DASHBOARD_VER,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.RESUMEN_VER,  # Ver resumen e información con adjuntos

        # Registro y Reevaluación de paciente
        PermisoEnum.PACIENTE_CREAR,  # Registro de pacientes nuevos
        PermisoEnum.PACIENTE_REEVALUAR,

        # Traslados
        PermisoEnum.TRASLADO_ACEPTAR,  # Aceptar Traslado de cama
        PermisoEnum.TRASLADO_CONFIRMAR,
        PermisoEnum.TRASLADO_COMPLETAR,
        PermisoEnum.TRASLADO_CANCELAR,
        PermisoEnum.TRASLADO_VER,

        # Altas y Egresos
        PermisoEnum.ALTA_EJECUTAR,  # Dar Alta (Estado "Cama Alta")
        PermisoEnum.EGRESO_REGISTRAR,  # Egreso (Fallecido/Derivación Confirmada)

        # Operaciones especiales
        PermisoEnum.PAUSA_OXIGENO_OMITIR,
        PermisoEnum.REGISTRO_ELIMINAR,

        # Fallecimiento
        PermisoEnum.FALLECIMIENTO_REGISTRAR,
        PermisoEnum.FALLECIMIENTO_CANCELAR,

        # Limpieza
        PermisoEnum.LIMPIEZA_MARCAR,

        # Información
        PermisoEnum.HOSPITAL_VER,
    },

    # TENS - Técnico de Enfermería de Nivel Superior
    # Funciones según tabla: SOLO Completar Traslado (Botón)
    # Perfil operativo enfocado al movimiento físico del paciente
    # NO accede a documentos clínicos confidenciales (reevaluación/adjuntos)
    RolEnum.TENS: {
        # Visualización básica
        PermisoEnum.PACIENTE_VER,  # Información básica, sin reevaluación ni adjuntos
        PermisoEnum.CAMA_VER,
        PermisoEnum.DASHBOARD_VER,

        # Traslados - Solo completar
        PermisoEnum.TRASLADO_COMPLETAR,  # Actualizar estado de cama tras movimiento físico
        PermisoEnum.TRASLADO_VER,

        # Información
        PermisoEnum.HOSPITAL_VER,
    },

    # ================================================
    # ROLES ADICIONALES (SERVICIOS Y ESPECIALIZADOS)
    # ================================================

    # Jefe de Servicio - Gestión de su servicio específico
    RolEnum.JEFE_SERVICIO: {
        PermisoEnum.PACIENTE_VER,
        PermisoEnum.PACIENTE_REEVALUAR,
        PermisoEnum.CAMA_VER,
        PermisoEnum.CAMA_BLOQUEAR,
        PermisoEnum.CAMA_DESBLOQUEAR,
        PermisoEnum.DASHBOARD_VER,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.LISTA_ESPERA_GESTIONAR,
        PermisoEnum.RESUMEN_VER,
        PermisoEnum.TRASLADO_INICIAR,
        PermisoEnum.TRASLADO_ACEPTAR,
        PermisoEnum.TRASLADO_CONFIRMAR,
        PermisoEnum.TRASLADO_COMPLETAR,
        PermisoEnum.TRASLADO_VER,
        PermisoEnum.DERIVACION_SOLICITAR,
        PermisoEnum.DERIVACION_VER,
        PermisoEnum.ALTA_SUGERIR,
        PermisoEnum.ALTA_EJECUTAR,
        PermisoEnum.FALLECIMIENTO_REGISTRAR,
        PermisoEnum.FALLECIMIENTO_CANCELAR,
        PermisoEnum.ESTADISTICAS_VER,
        PermisoEnum.HOSPITAL_VER,
        PermisoEnum.HOSPITAL_TELEFONOS,
        PermisoEnum.MODO_MANUAL_ASIGNAR,  # Llanquihue/Calbuco
        PermisoEnum.CAMA_BLOQUEAR,  # Llanquihue/Calbuco
    },

    # Supervisora de Enfermería
    RolEnum.SUPERVISORA_ENFERMERIA: {
        PermisoEnum.PACIENTE_VER,
        PermisoEnum.PACIENTE_REEVALUAR,
        PermisoEnum.CAMA_VER,
        PermisoEnum.CAMA_BLOQUEAR,
        PermisoEnum.CAMA_DESBLOQUEAR,
        PermisoEnum.DASHBOARD_VER,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.RESUMEN_VER,
        PermisoEnum.TRASLADO_ACEPTAR,
        PermisoEnum.TRASLADO_CONFIRMAR,
        PermisoEnum.TRASLADO_COMPLETAR,
        PermisoEnum.TRASLADO_VER,
        PermisoEnum.ALTA_EJECUTAR,
        PermisoEnum.EGRESO_REGISTRAR,
        PermisoEnum.ESTADISTICAS_VER,
        PermisoEnum.HOSPITAL_VER,
        PermisoEnum.LIMPIEZA_MARCAR,
        PermisoEnum.LIMPIEZA_COMPLETAR,
    },

    # Urgencias - Sin dashboard de camas, solo registro y derivación
    RolEnum.URGENCIAS: {
        PermisoEnum.PACIENTE_CREAR,
        PermisoEnum.PACIENTE_VER,
        PermisoEnum.PACIENTE_EDITAR,
        PermisoEnum.PACIENTE_REEVALUAR,
        PermisoEnum.CAMA_VER,
        # NO DASHBOARD_VER - Sin visión de dashboard de camas
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.LISTA_ESPERA_GESTIONAR,
        PermisoEnum.TRASLADO_VER,
        PermisoEnum.DERIVACION_SOLICITAR,
        PermisoEnum.DERIVACION_VER,
        PermisoEnum.RESUMEN_VER,
        PermisoEnum.HOSPITAL_VER,
    },

    # Jefe de Urgencias
    RolEnum.JEFE_URGENCIAS: {
        PermisoEnum.PACIENTE_CREAR,
        PermisoEnum.PACIENTE_VER,
        PermisoEnum.PACIENTE_EDITAR,
        PermisoEnum.PACIENTE_REEVALUAR,
        PermisoEnum.CAMA_VER,
        PermisoEnum.CAMA_BLOQUEAR,
        # NO DASHBOARD_VER - Sin visión de dashboard de camas
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.LISTA_ESPERA_GESTIONAR,
        PermisoEnum.LISTA_ESPERA_PRIORIZAR,
        PermisoEnum.TRASLADO_INICIAR,
        PermisoEnum.TRASLADO_VER,
        PermisoEnum.DERIVACION_SOLICITAR,
        PermisoEnum.DERIVACION_VER,
        PermisoEnum.DERIVACION_CANCELAR,
        PermisoEnum.RESUMEN_VER,
        PermisoEnum.ESTADISTICAS_VER,
        PermisoEnum.HOSPITAL_VER,
        PermisoEnum.HOSPITAL_TELEFONOS,
    },

    # Ambulatorio - Sin dashboard, solo reevaluación y eliminación
    RolEnum.AMBULATORIO: {
        PermisoEnum.PACIENTE_CREAR,
        PermisoEnum.PACIENTE_VER,
        PermisoEnum.PACIENTE_EDITAR,
        PermisoEnum.PACIENTE_REEVALUAR,
        PermisoEnum.CAMA_VER,
        # NO DASHBOARD_VER - Sin visión de dashboard de camas
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.REGISTRO_ELIMINAR,
        PermisoEnum.HOSPITAL_VER,
    },

    # Derivaciones - Gestión de derivaciones
    RolEnum.DERIVACIONES: {
        PermisoEnum.PACIENTE_VER,
        PermisoEnum.CAMA_VER,
        PermisoEnum.DASHBOARD_VER,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.RESUMEN_VER,
        PermisoEnum.DERIVACION_SOLICITAR,
        PermisoEnum.DERIVACION_ACEPTAR,
        PermisoEnum.DERIVACION_RECHAZAR,
        PermisoEnum.DERIVACION_VER,
        PermisoEnum.DERIVACION_CANCELAR,
        PermisoEnum.HOSPITAL_VER,
    },

    # Estadísticas - Solo visualización y exportación
    RolEnum.ESTADISTICAS: {
        PermisoEnum.PACIENTE_VER,
        PermisoEnum.CAMA_VER,
        PermisoEnum.DASHBOARD_VER,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.TRASLADO_VER,
        PermisoEnum.DERIVACION_VER,
        PermisoEnum.ESTADISTICAS_VER,
        PermisoEnum.ESTADISTICAS_EXPORTAR,
        PermisoEnum.HOSPITAL_VER,
    },

    # Visualizador - Solo ver dashboard sin realizar acciones
    RolEnum.VISUALIZADOR: {
        PermisoEnum.PACIENTE_VER,
        PermisoEnum.CAMA_VER,
        PermisoEnum.DASHBOARD_VER,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.TRASLADO_VER,
        PermisoEnum.DERIVACION_VER,
        PermisoEnum.ESTADISTICAS_VER,
        PermisoEnum.HOSPITAL_VER,
    },

    # Limpieza - Solo marcar limpieza de camas
    RolEnum.LIMPIEZA: {
        PermisoEnum.CAMA_VER,
        PermisoEnum.LIMPIEZA_MARCAR,
        PermisoEnum.LIMPIEZA_COMPLETAR,
        PermisoEnum.HOSPITAL_VER,
    },
}


# ============================================
# MODELO USUARIO
# ============================================

class Usuario(SQLModel, table=True):
    """Modelo de usuario del sistema."""
    
    __tablename__ = "usuarios"
    
    id: Optional[str] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    email: str = Field(unique=True, index=True, max_length=255)
    hashed_password: str = Field(max_length=255)
    nombre_completo: str = Field(max_length=255)
    rol: RolEnum = Field(default=RolEnum.VISUALIZADOR)
    
    # Relaciones opcionales (SIN FOREIGN KEY para evitar errores)
    # Si tu proyecto tiene tablas hospitales/servicios, puedes descomentar las FK
    hospital_id: Optional[str] = Field(default=None, index=True)
    # hospital_id: Optional[str] = Field(default=None, foreign_key="hospitales.id", index=True)
    
    servicio_id: Optional[str] = Field(default=None, index=True)
    # servicio_id: Optional[str] = Field(default=None, foreign_key="servicios.id", index=True)
    
    # Estado
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(default=None)
    
    def __init__(self, **data):
        super().__init__(**data)
        # Generar ID si no existe
        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())
    
    @property
    def permisos(self) -> set[PermisoEnum]:
        """Obtiene los permisos basados en el rol."""
        return PERMISOS_POR_ROL.get(self.rol, set())
    
    def tiene_permiso(self, permiso: PermisoEnum) -> bool:
        """Verifica si el usuario tiene un permiso específico."""
        return permiso in self.permisos
    
    def tiene_algun_permiso(self, permisos: List[PermisoEnum]) -> bool:
        """Verifica si el usuario tiene al menos uno de los permisos."""
        return bool(self.permisos & set(permisos))
    
    def tiene_todos_permisos(self, permisos: List[PermisoEnum]) -> bool:
        """Verifica si el usuario tiene todos los permisos."""
        return set(permisos).issubset(self.permisos)


# ============================================
# MODELO REFRESH TOKEN
# ============================================

class RefreshToken(SQLModel, table=True):
    """Modelo para almacenar refresh tokens."""
    
    __tablename__ = "refresh_tokens"
    
    id: Optional[str] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True)
    user_id: str = Field(index=True)
    # Si quieres foreign key, descomenta:
    # user_id: str = Field(foreign_key="usuarios.id", index=True)
    
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    revoked: bool = Field(default=False)
    revoked_at: Optional[datetime] = Field(default=None)
    
    # Información del dispositivo/sesión
    user_agent: Optional[str] = Field(default=None, max_length=500)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())
    
    @property
    def is_expired(self) -> bool:
        """Verifica si el token ha expirado."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Verifica si el token es válido (no revocado y no expirado)."""
        return not self.revoked and not self.is_expired