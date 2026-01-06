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


# Descripciones de roles para el frontend
ROLES_INFO = {
    RolEnum.SUPER_ADMIN: {
        "nombre": "Super Administrador",
        "descripcion": "Acceso total al sistema, gestión de usuarios y configuración global"
    },
    RolEnum.ADMIN: {
        "nombre": "Administrador",
        "descripcion": "Administración del sistema sin gestión de super admins"
    },
    RolEnum.GESTOR_CAMAS: {
        "nombre": "Gestor de Camas",
        "descripcion": "Gestión completa de camas, traslados y asignaciones"
    },
    RolEnum.COORDINADOR_CAMAS: {
        "nombre": "Coordinador de Camas",
        "descripcion": "Coordinación de traslados entre servicios"
    },
    RolEnum.MEDICO: {
        "nombre": "Médico",
        "descripcion": "Ver pacientes, solicitar altas y derivaciones"
    },
    RolEnum.JEFE_SERVICIO: {
        "nombre": "Jefe de Servicio",
        "descripcion": "Gestión de su servicio específico"
    },
    RolEnum.ENFERMERA: {
        "nombre": "Enfermera/o",
        "descripcion": "Ver camas y actualizar estados básicos"
    },
    RolEnum.SUPERVISORA_ENFERMERIA: {
        "nombre": "Supervisora de Enfermería",
        "descripcion": "Supervisión de enfermería"
    },
    RolEnum.URGENCIAS: {
        "nombre": "Urgencias",
        "descripcion": "Crear pacientes de urgencia"
    },
    RolEnum.JEFE_URGENCIAS: {
        "nombre": "Jefe de Urgencias",
        "descripcion": "Gestión completa de urgencias"
    },
    RolEnum.DERIVACIONES: {
        "nombre": "Derivaciones",
        "descripcion": "Gestionar derivaciones entrantes y salientes"
    },
    RolEnum.COORDINADOR_RED: {
        "nombre": "Coordinador de Red",
        "descripcion": "Coordinación entre hospitales de la red"
    },
    RolEnum.AMBULATORIO: {
        "nombre": "Ambulatorio",
        "descripcion": "Crear pacientes ambulatorios"
    },
    RolEnum.ESTADISTICAS: {
        "nombre": "Estadísticas",
        "descripcion": "Solo ver y exportar estadísticas"
    },
    RolEnum.VISUALIZADOR: {
        "nombre": "Visualizador",
        "descripcion": "Solo ver dashboard sin realizar acciones"
    },
    RolEnum.OPERADOR: {
        "nombre": "Operador",
        "descripcion": "Operaciones básicas del día a día"
    },
    RolEnum.LIMPIEZA: {
        "nombre": "Limpieza",
        "descripcion": "Solo marcar limpieza de camas"
    },
}
