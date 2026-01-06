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
    """Roles disponibles en el sistema."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    GESTOR_CAMAS = "gestor_camas"
    COORDINADOR_CAMAS = "coordinador_camas"
    MEDICO = "medico"
    JEFE_SERVICIO = "jefe_servicio"
    ENFERMERA = "enfermera"
    SUPERVISORA_ENFERMERIA = "supervisora_enfermeria"
    URGENCIAS = "urgencias"
    JEFE_URGENCIAS = "jefe_urgencias"
    DERIVACIONES = "derivaciones"
    COORDINADOR_RED = "coordinador_red"
    AMBULATORIO = "ambulatorio"
    ESTADISTICAS = "estadisticas"
    VISUALIZADOR = "visualizador"
    OPERADOR = "operador"
    LIMPIEZA = "limpieza"


class PermisoEnum(str, Enum):
    """Permisos granulares del sistema."""
    # Pacientes
    PACIENTE_CREAR = "paciente:crear"
    PACIENTE_VER = "paciente:ver"
    PACIENTE_EDITAR = "paciente:editar"
    PACIENTE_ELIMINAR = "paciente:eliminar"
    
    # Camas
    CAMA_VER = "cama:ver"
    CAMA_BLOQUEAR = "cama:bloquear"
    CAMA_DESBLOQUEAR = "cama:desbloquear"
    CAMA_ASIGNAR = "cama:asignar"
    
    # Lista de Espera
    LISTA_ESPERA_VER = "lista_espera:ver"
    LISTA_ESPERA_GESTIONAR = "lista_espera:gestionar"
    LISTA_ESPERA_PRIORIZAR = "lista_espera:priorizar"
    
    # Traslados
    TRASLADO_INICIAR = "traslado:iniciar"
    TRASLADO_CONFIRMAR = "traslado:confirmar"
    TRASLADO_CANCELAR = "traslado:cancelar"
    TRASLADO_VER = "traslado:ver"
    
    # Derivaciones
    DERIVACION_SOLICITAR = "derivacion:solicitar"
    DERIVACION_ACEPTAR = "derivacion:aceptar"
    DERIVACION_RECHAZAR = "derivacion:rechazar"
    DERIVACION_VER = "derivacion:ver"
    DERIVACION_CANCELAR = "derivacion:cancelar"
    
    # Altas
    ALTA_SOLICITAR = "alta:solicitar"
    ALTA_EJECUTAR = "alta:ejecutar"
    ALTA_CANCELAR = "alta:cancelar"
    
    # Modo Manual
    MODO_MANUAL_ASIGNAR = "modo_manual:asignar"
    MODO_MANUAL_INTERCAMBIAR = "modo_manual:intercambiar"
    
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


# ============================================
# PERMISOS POR ROL
# ============================================

PERMISOS_POR_ROL: dict[RolEnum, set[PermisoEnum]] = {
    RolEnum.SUPER_ADMIN: set(PermisoEnum),  # Todos los permisos
    
    RolEnum.ADMIN: {
        PermisoEnum.PACIENTE_CREAR, PermisoEnum.PACIENTE_VER, PermisoEnum.PACIENTE_EDITAR, PermisoEnum.PACIENTE_ELIMINAR,
        PermisoEnum.CAMA_VER, PermisoEnum.CAMA_BLOQUEAR, PermisoEnum.CAMA_DESBLOQUEAR, PermisoEnum.CAMA_ASIGNAR,
        PermisoEnum.LISTA_ESPERA_VER, PermisoEnum.LISTA_ESPERA_GESTIONAR, PermisoEnum.LISTA_ESPERA_PRIORIZAR,
        PermisoEnum.TRASLADO_INICIAR, PermisoEnum.TRASLADO_CONFIRMAR, PermisoEnum.TRASLADO_CANCELAR, PermisoEnum.TRASLADO_VER,
        PermisoEnum.DERIVACION_SOLICITAR, PermisoEnum.DERIVACION_ACEPTAR, PermisoEnum.DERIVACION_RECHAZAR, 
        PermisoEnum.DERIVACION_VER, PermisoEnum.DERIVACION_CANCELAR,
        PermisoEnum.ALTA_SOLICITAR, PermisoEnum.ALTA_EJECUTAR, PermisoEnum.ALTA_CANCELAR,
        PermisoEnum.MODO_MANUAL_ASIGNAR, PermisoEnum.MODO_MANUAL_INTERCAMBIAR,
        PermisoEnum.CONFIGURACION_VER, PermisoEnum.CONFIGURACION_EDITAR,
        PermisoEnum.ESTADISTICAS_VER, PermisoEnum.ESTADISTICAS_EXPORTAR,
        PermisoEnum.USUARIOS_VER, PermisoEnum.USUARIOS_CREAR, PermisoEnum.USUARIOS_EDITAR, PermisoEnum.USUARIOS_ELIMINAR,
        PermisoEnum.HOSPITAL_VER, PermisoEnum.HOSPITAL_EDITAR, PermisoEnum.HOSPITAL_TELEFONOS,
        PermisoEnum.FALLECIMIENTO_REGISTRAR, PermisoEnum.FALLECIMIENTO_CANCELAR,
        PermisoEnum.LIMPIEZA_MARCAR, PermisoEnum.LIMPIEZA_COMPLETAR,
    },
    
    RolEnum.GESTOR_CAMAS: {
        PermisoEnum.PACIENTE_CREAR, PermisoEnum.PACIENTE_VER, PermisoEnum.PACIENTE_EDITAR,
        PermisoEnum.CAMA_VER, PermisoEnum.CAMA_BLOQUEAR, PermisoEnum.CAMA_DESBLOQUEAR, PermisoEnum.CAMA_ASIGNAR,
        PermisoEnum.LISTA_ESPERA_VER, PermisoEnum.LISTA_ESPERA_GESTIONAR, PermisoEnum.LISTA_ESPERA_PRIORIZAR,
        PermisoEnum.TRASLADO_INICIAR, PermisoEnum.TRASLADO_CONFIRMAR, PermisoEnum.TRASLADO_CANCELAR, PermisoEnum.TRASLADO_VER,
        PermisoEnum.DERIVACION_SOLICITAR, PermisoEnum.DERIVACION_ACEPTAR, PermisoEnum.DERIVACION_RECHAZAR, 
        PermisoEnum.DERIVACION_VER, PermisoEnum.DERIVACION_CANCELAR,
        PermisoEnum.ALTA_SOLICITAR, PermisoEnum.ALTA_EJECUTAR, PermisoEnum.ALTA_CANCELAR,
        PermisoEnum.MODO_MANUAL_ASIGNAR, PermisoEnum.MODO_MANUAL_INTERCAMBIAR,
        PermisoEnum.CONFIGURACION_VER,
        PermisoEnum.ESTADISTICAS_VER,
        PermisoEnum.HOSPITAL_VER, PermisoEnum.HOSPITAL_TELEFONOS,
        PermisoEnum.FALLECIMIENTO_REGISTRAR, PermisoEnum.FALLECIMIENTO_CANCELAR,
        PermisoEnum.LIMPIEZA_MARCAR, PermisoEnum.LIMPIEZA_COMPLETAR,
    },
    
    RolEnum.COORDINADOR_CAMAS: {
        PermisoEnum.PACIENTE_VER, PermisoEnum.PACIENTE_EDITAR,
        PermisoEnum.CAMA_VER, PermisoEnum.CAMA_ASIGNAR,
        PermisoEnum.LISTA_ESPERA_VER, PermisoEnum.LISTA_ESPERA_GESTIONAR,
        PermisoEnum.TRASLADO_INICIAR, PermisoEnum.TRASLADO_CONFIRMAR, PermisoEnum.TRASLADO_VER,
        PermisoEnum.DERIVACION_VER,
        PermisoEnum.ALTA_SOLICITAR, PermisoEnum.ALTA_EJECUTAR,
        PermisoEnum.ESTADISTICAS_VER,
        PermisoEnum.HOSPITAL_VER,
    },
    
    RolEnum.MEDICO: {
        PermisoEnum.PACIENTE_CREAR, PermisoEnum.PACIENTE_VER, PermisoEnum.PACIENTE_EDITAR,
        PermisoEnum.CAMA_VER,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.TRASLADO_INICIAR, PermisoEnum.TRASLADO_VER,
        PermisoEnum.DERIVACION_SOLICITAR, PermisoEnum.DERIVACION_VER,
        PermisoEnum.ALTA_SOLICITAR,
        PermisoEnum.ESTADISTICAS_VER,
        PermisoEnum.HOSPITAL_VER,
        PermisoEnum.FALLECIMIENTO_REGISTRAR,
    },
    
    RolEnum.JEFE_SERVICIO: {
        PermisoEnum.PACIENTE_CREAR, PermisoEnum.PACIENTE_VER, PermisoEnum.PACIENTE_EDITAR,
        PermisoEnum.CAMA_VER, PermisoEnum.CAMA_BLOQUEAR, PermisoEnum.CAMA_DESBLOQUEAR,
        PermisoEnum.LISTA_ESPERA_VER, PermisoEnum.LISTA_ESPERA_GESTIONAR,
        PermisoEnum.TRASLADO_INICIAR, PermisoEnum.TRASLADO_CONFIRMAR, PermisoEnum.TRASLADO_VER,
        PermisoEnum.DERIVACION_SOLICITAR, PermisoEnum.DERIVACION_VER,
        PermisoEnum.ALTA_SOLICITAR, PermisoEnum.ALTA_EJECUTAR,
        PermisoEnum.ESTADISTICAS_VER,
        PermisoEnum.HOSPITAL_VER, PermisoEnum.HOSPITAL_TELEFONOS,
        PermisoEnum.FALLECIMIENTO_REGISTRAR, PermisoEnum.FALLECIMIENTO_CANCELAR,
    },
    
    RolEnum.ENFERMERA: {
        PermisoEnum.PACIENTE_VER, PermisoEnum.PACIENTE_EDITAR,
        PermisoEnum.CAMA_VER,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.TRASLADO_CONFIRMAR, PermisoEnum.TRASLADO_VER,
        PermisoEnum.ALTA_EJECUTAR,
        PermisoEnum.HOSPITAL_VER,
        PermisoEnum.LIMPIEZA_MARCAR,
    },
    
    RolEnum.SUPERVISORA_ENFERMERIA: {
        PermisoEnum.PACIENTE_VER, PermisoEnum.PACIENTE_EDITAR,
        PermisoEnum.CAMA_VER, PermisoEnum.CAMA_BLOQUEAR, PermisoEnum.CAMA_DESBLOQUEAR,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.TRASLADO_CONFIRMAR, PermisoEnum.TRASLADO_VER,
        PermisoEnum.ALTA_EJECUTAR,
        PermisoEnum.ESTADISTICAS_VER,
        PermisoEnum.HOSPITAL_VER,
        PermisoEnum.LIMPIEZA_MARCAR, PermisoEnum.LIMPIEZA_COMPLETAR,
    },
    
    RolEnum.URGENCIAS: {
        PermisoEnum.PACIENTE_CREAR, PermisoEnum.PACIENTE_VER, PermisoEnum.PACIENTE_EDITAR,
        PermisoEnum.CAMA_VER,
        PermisoEnum.LISTA_ESPERA_VER, PermisoEnum.LISTA_ESPERA_GESTIONAR,
        PermisoEnum.TRASLADO_VER,
        PermisoEnum.DERIVACION_SOLICITAR, PermisoEnum.DERIVACION_VER,
        PermisoEnum.HOSPITAL_VER,
    },
    
    RolEnum.JEFE_URGENCIAS: {
        PermisoEnum.PACIENTE_CREAR, PermisoEnum.PACIENTE_VER, PermisoEnum.PACIENTE_EDITAR,
        PermisoEnum.CAMA_VER, PermisoEnum.CAMA_BLOQUEAR,
        PermisoEnum.LISTA_ESPERA_VER, PermisoEnum.LISTA_ESPERA_GESTIONAR, PermisoEnum.LISTA_ESPERA_PRIORIZAR,
        PermisoEnum.TRASLADO_INICIAR, PermisoEnum.TRASLADO_VER,
        PermisoEnum.DERIVACION_SOLICITAR, PermisoEnum.DERIVACION_VER, PermisoEnum.DERIVACION_CANCELAR,
        PermisoEnum.ESTADISTICAS_VER,
        PermisoEnum.HOSPITAL_VER, PermisoEnum.HOSPITAL_TELEFONOS,
    },
    
    RolEnum.DERIVACIONES: {
        PermisoEnum.PACIENTE_VER,
        PermisoEnum.CAMA_VER,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.DERIVACION_SOLICITAR, PermisoEnum.DERIVACION_ACEPTAR, PermisoEnum.DERIVACION_RECHAZAR,
        PermisoEnum.DERIVACION_VER, PermisoEnum.DERIVACION_CANCELAR,
        PermisoEnum.HOSPITAL_VER,
    },
    
    RolEnum.COORDINADOR_RED: {
        PermisoEnum.PACIENTE_VER,
        PermisoEnum.CAMA_VER,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.TRASLADO_VER,
        PermisoEnum.DERIVACION_SOLICITAR, PermisoEnum.DERIVACION_ACEPTAR, PermisoEnum.DERIVACION_RECHAZAR,
        PermisoEnum.DERIVACION_VER, PermisoEnum.DERIVACION_CANCELAR,
        PermisoEnum.ESTADISTICAS_VER, PermisoEnum.ESTADISTICAS_EXPORTAR,
        PermisoEnum.HOSPITAL_VER,
    },
    
    RolEnum.AMBULATORIO: {
        PermisoEnum.PACIENTE_CREAR, PermisoEnum.PACIENTE_VER, PermisoEnum.PACIENTE_EDITAR,
        PermisoEnum.CAMA_VER,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.HOSPITAL_VER,
    },
    
    RolEnum.ESTADISTICAS: {
        PermisoEnum.PACIENTE_VER,
        PermisoEnum.CAMA_VER,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.TRASLADO_VER,
        PermisoEnum.DERIVACION_VER,
        PermisoEnum.ESTADISTICAS_VER, PermisoEnum.ESTADISTICAS_EXPORTAR,
        PermisoEnum.HOSPITAL_VER,
    },
    
    RolEnum.VISUALIZADOR: {
        PermisoEnum.PACIENTE_VER,
        PermisoEnum.CAMA_VER,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.TRASLADO_VER,
        PermisoEnum.DERIVACION_VER,
        PermisoEnum.ESTADISTICAS_VER,
        PermisoEnum.HOSPITAL_VER,
    },
    
    RolEnum.OPERADOR: {
        PermisoEnum.PACIENTE_VER,
        PermisoEnum.CAMA_VER,
        PermisoEnum.LISTA_ESPERA_VER,
        PermisoEnum.TRASLADO_VER,
        PermisoEnum.HOSPITAL_VER,
    },
    
    RolEnum.LIMPIEZA: {
        PermisoEnum.CAMA_VER,
        PermisoEnum.LIMPIEZA_MARCAR, PermisoEnum.LIMPIEZA_COMPLETAR,
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