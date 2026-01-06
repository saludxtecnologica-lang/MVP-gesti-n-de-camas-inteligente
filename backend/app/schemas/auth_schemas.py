"""
Schemas de autenticación.
Validación de datos para login, registro y tokens.
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re

from app.models.usuario import RolEnum, PermisoEnum


# ============================================
# REQUEST SCHEMAS
# ============================================

class LoginRequest(BaseModel):
    """Schema para login."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1)
    remember_me: bool = Field(default=False)  # Para refresh token más largo


class RegisterRequest(BaseModel):
    """Schema para registro de usuario (solo admin puede usar)."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    nombre_completo: str = Field(..., min_length=2, max_length=100)
    rol: RolEnum = Field(default=RolEnum.VISUALIZADOR)
    hospital_id: Optional[str] = None
    servicio_id: Optional[str] = None
    
    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username solo puede contener letras, números y guiones bajos')
        return v.lower()
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v


class PasswordChangeRequest(BaseModel):
    """Schema para cambio de contraseña."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v


class UserUpdateRequest(BaseModel):
    """Schema para actualización de usuario (admin)."""
    email: Optional[EmailStr] = None
    nombre_completo: Optional[str] = Field(None, min_length=2, max_length=100)
    rol: Optional[RolEnum] = None
    hospital_id: Optional[str] = None
    servicio_id: Optional[str] = None
    is_active: Optional[bool] = None


class RefreshTokenRequest(BaseModel):
    """Schema para refresh de token."""
    refresh_token: str


# ============================================
# RESPONSE SCHEMAS
# ============================================

class TokenResponse(BaseModel):
    """Schema de respuesta con tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos hasta expiración


class UserResponse(BaseModel):
    """Schema de respuesta de usuario (sin password)."""
    id: str
    username: str
    email: str
    nombre_completo: str
    rol: RolEnum
    hospital_id: Optional[str] = None
    servicio_id: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    permisos: List[str]  # Lista de permisos como strings
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema para lista de usuarios."""
    id: str
    username: str
    email: str
    nombre_completo: str
    rol: RolEnum
    hospital_id: Optional[str] = None
    is_active: bool
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Schema de respuesta de login exitoso."""
    user: UserResponse
    tokens: TokenResponse
    message: str = "Login exitoso"


class MessageResponse(BaseModel):
    """Schema de respuesta genérica."""
    success: bool
    message: str
    data: Optional[dict] = None


# ============================================
# TOKEN PAYLOAD
# ============================================

class TokenPayload(BaseModel):
    """Payload del JWT token."""
    sub: str  # user_id
    username: str
    rol: str
    hospital_id: Optional[str] = None
    servicio_id: Optional[str] = None
    exp: datetime
    iat: datetime
    type: str = "access"  # "access" o "refresh"


# ============================================
# PERMISOS
# ============================================

class PermisoCheck(BaseModel):
    """Schema para verificar permisos."""
    permisos: List[str]
    usuario_id: Optional[str] = None


class RolPermisos(BaseModel):
    """Schema de rol con sus permisos."""
    rol: RolEnum
    nombre: str
    descripcion: str
    permisos: List[str]


# Descripciones de roles para el frontend (Sistema RBAC Multinivel)
ROLES_INFO = {
    # ========== CAPA 1: ADMINISTRACIÓN Y RED (NIVEL GLOBAL) ==========
    RolEnum.PROGRAMADOR: {
        "nombre": "Equipo Programador",
        "descripcion": "Acceso irrestricto a todas las funciones, configuraciones y bases de datos. Mantenimiento preventivo y soporte de nivel raíz.",
        "capa": "Administración y Red (Global)",
        "alcance": "Totalidad del sistema (Multi-hospital)",
        "solo_lectura": False,
    },
    RolEnum.DIRECTIVO_RED: {
        "nombre": "Equipo Directivo de Red",
        "descripcion": "Visualización de todos los hospitales (Puerto Montt, Llanquihue, Calbuco). Ver Dashboards, listas de espera, derivaciones y resúmenes de paciente. BLOQUEO TOTAL DE ESCRITURA.",
        "capa": "Administración y Red (Global)",
        "alcance": "Todos los hospitales de la red",
        "solo_lectura": True,
    },

    # ========== CAPA 2: GESTIÓN LOCAL (NIVEL HOSPITALARIO) ==========
    RolEnum.DIRECTIVO_HOSPITAL: {
        "nombre": "Equipo Directivo Hospital",
        "descripcion": "Visualización completa de su hospital específico. Dashboards, listas de espera y resúmenes de pacientes del recinto. Sin permisos de registro o cambios operativos.",
        "capa": "Gestión Local (Hospitalario)",
        "alcance": "Su hospital específico",
        "solo_lectura": True,
    },
    RolEnum.GESTOR_CAMAS: {
        "nombre": "Equipo Gestión de Camas (Puerto Montt)",
        "descripcion": "Realizar y aceptar derivaciones, traslados, omitir pausas de oxígeno, eliminar registros, dar altas y egresos. Bloquear camas y activar Modo Manual. NO pueden reevaluar clínicamente ni registrar pacientes inicialmente.",
        "capa": "Gestión Local (Hospitalario)",
        "alcance": "Todos los servicios del Hospital Puerto Montt",
        "solo_lectura": False,
    },

    # ========== CAPA 3: CLÍNICA (NIVEL SERVICIO + ROL PROFESIONAL) ==========
    RolEnum.MEDICO: {
        "nombre": "Médico",
        "descripcion": "Reevaluación de pacientes, realizar/aceptar/rechazar derivaciones, iniciar búsqueda de cama, cancelar traslados, sugerir altas, completar traslados, omitir pausas de oxígeno y eliminar registros.",
        "capa": "Clínica (Servicio)",
        "alcance": "Solo pacientes con origen o destino en su servicio",
        "solo_lectura": False,
    },
    RolEnum.ENFERMERA: {
        "nombre": "Enfermera/o o Matrón/a",
        "descripcion": "Reevaluación de pacientes, aceptar traslados de cama, dar altas (estado 'Cama Alta'), registrar egresos (fallecido/derivación confirmada), completar traslados, omitir pausas de oxígeno y eliminar registros.",
        "capa": "Clínica (Servicio)",
        "alcance": "Solo pacientes con origen o destino en su servicio",
        "solo_lectura": False,
    },
    RolEnum.TENS: {
        "nombre": "TENS (Técnico de Enfermería de Nivel Superior)",
        "descripcion": "Perfil operativo enfocado al movimiento físico del paciente. SOLO puede completar traslados. NO accede a documentos clínicos confidenciales (reevaluación/adjuntos).",
        "capa": "Clínica (Servicio)",
        "alcance": "Solo pacientes de su servicio",
        "solo_lectura": False,
    },

    # ========== ROLES DE SERVICIO ESPECÍFICOS ==========
    RolEnum.JEFE_SERVICIO: {
        "nombre": "Jefe de Servicio",
        "descripcion": "Gestión de su servicio específico. En hospitales periféricos (Llanquihue/Calbuco) puede usar Modo Manual y bloquear camas.",
        "capa": "Clínica (Servicio)",
        "alcance": "Su servicio específico",
        "solo_lectura": False,
    },
    RolEnum.SUPERVISORA_ENFERMERIA: {
        "nombre": "Supervisora de Enfermería",
        "descripcion": "Supervisión de enfermería del servicio",
        "capa": "Clínica (Servicio)",
        "alcance": "Su servicio específico",
        "solo_lectura": False,
    },
    RolEnum.URGENCIAS: {
        "nombre": "Urgencias",
        "descripcion": "Crear pacientes de urgencia y solicitar derivaciones. SIN acceso al dashboard de camas. Solo pacientes con origen en Urgencias.",
        "capa": "Clínica (Servicio)",
        "alcance": "Solo pacientes con origen en Urgencias",
        "solo_lectura": False,
    },
    RolEnum.JEFE_URGENCIAS: {
        "nombre": "Jefe de Urgencias",
        "descripcion": "Gestión completa de urgencias. SIN acceso al dashboard de camas.",
        "capa": "Clínica (Servicio)",
        "alcance": "Solo pacientes con origen en Urgencias",
        "solo_lectura": False,
    },
    RolEnum.AMBULATORIO: {
        "nombre": "Ambulatorio",
        "descripcion": "Crear pacientes ambulatorios, reevaluación y eliminación de registros. SIN acceso al dashboard de camas. Solo pacientes con origen en Ambulatorio.",
        "capa": "Clínica (Servicio)",
        "alcance": "Solo pacientes con origen en Ambulatorio",
        "solo_lectura": False,
    },

    # ========== ROLES ESPECIALIZADOS ==========
    RolEnum.DERIVACIONES: {
        "nombre": "Derivaciones",
        "descripcion": "Gestionar derivaciones entrantes y salientes",
        "capa": "Especializado",
        "alcance": "Derivaciones del hospital",
        "solo_lectura": False,
    },
    RolEnum.ESTADISTICAS: {
        "nombre": "Estadísticas",
        "descripcion": "Solo ver y exportar estadísticas",
        "capa": "Especializado",
        "alcance": "Estadísticas del hospital/red",
        "solo_lectura": True,
    },
    RolEnum.VISUALIZADOR: {
        "nombre": "Visualizador",
        "descripcion": "Solo ver dashboard sin realizar acciones",
        "capa": "Especializado",
        "alcance": "Visualización del hospital",
        "solo_lectura": True,
    },
    RolEnum.LIMPIEZA: {
        "nombre": "Limpieza",
        "descripcion": "Solo marcar limpieza de camas",
        "capa": "Especializado",
        "alcance": "Camas del hospital",
        "solo_lectura": False,
    },

    # ========== ALIASES (para compatibilidad) ==========
    RolEnum.SUPER_ADMIN: {
        "nombre": "Super Administrador (Alias)",
        "descripcion": "Alias de Programador",
        "capa": "Administración y Red (Global)",
        "alcance": "Totalidad del sistema",
        "solo_lectura": False,
    },
    RolEnum.ADMIN: {
        "nombre": "Administrador (Alias)",
        "descripcion": "Alias de Gestor de Camas",
        "capa": "Gestión Local (Hospitalario)",
        "alcance": "Hospital",
        "solo_lectura": False,
    },
    RolEnum.COORDINADOR_RED: {
        "nombre": "Coordinador de Red (Alias)",
        "descripcion": "Alias de Directivo de Red",
        "capa": "Administración y Red (Global)",
        "alcance": "Todos los hospitales",
        "solo_lectura": True,
    },
}
