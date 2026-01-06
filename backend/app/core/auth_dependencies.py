"""
Dependencies de autenticación para FastAPI.
Provee decoradores y dependencies para proteger endpoints.
"""
from typing import List, Optional, Callable
from functools import wraps
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from app.core.database import get_session
from app.models.usuario import Usuario, PermisoEnum, RolEnum
from app.services.auth_service import auth_service
from app.core.rbac_service import rbac_service


# Esquema de seguridad Bearer
security = HTTPBearer(auto_error=False)


class AuthError(HTTPException):
    """Excepción personalizada de autenticación."""
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(status_code=status_code, detail=detail)


class PermissionError(HTTPException):
    """Excepción de permisos insuficientes."""
    def __init__(self, detail: str = "No tienes permisos para realizar esta acción"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


# ============================================
# DEPENDENCIES BÁSICAS
# ============================================

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: Session = Depends(get_session)
) -> Optional[Usuario]:
    """
    Obtiene el usuario actual si está autenticado.
    No lanza error si no hay token (para endpoints públicos con contenido extra para autenticados).
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = auth_service.decode_token(token)
    
    if not payload or payload.type != "access":
        return None
    
    user = auth_service.get_user_by_id(payload.sub, session)
    
    if not user or not user.is_active:
        return None
    
    return user


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: Session = Depends(get_session)
) -> Usuario:
    """
    Obtiene el usuario actual autenticado.
    Lanza error 401 si no está autenticado.
    """
    if not credentials:
        raise AuthError("No se proporcionó token de autenticación")
    
    token = credentials.credentials
    payload = auth_service.decode_token(token)
    
    if not payload:
        raise AuthError("Token inválido o expirado")
    
    if payload.type != "access":
        raise AuthError("Tipo de token inválido")
    
    user = auth_service.get_user_by_id(payload.sub, session)
    
    if not user:
        raise AuthError("Usuario no encontrado")
    
    if not user.is_active:
        raise AuthError("Usuario desactivado")
    
    return user


async def get_current_active_user(
    current_user: Usuario = Depends(get_current_user)
) -> Usuario:
    """Alias de get_current_user que verifica que esté activo."""
    return current_user


# ============================================
# DEPENDENCY FACTORIES PARA PERMISOS
# ============================================

def require_permissions(*permisos: PermisoEnum):
    """
    Factory que crea una dependency que requiere ciertos permisos.
    El usuario debe tener TODOS los permisos especificados.
    
    Uso:
        @router.get("/admin", dependencies=[Depends(require_permissions(PermisoEnum.USUARIOS_VER))])
        def admin_endpoint():
            ...
    """
    async def permission_checker(
        current_user: Usuario = Depends(get_current_user)
    ) -> Usuario:
        if not current_user.tiene_todos_permisos(list(permisos)):
            raise PermissionError(
                f"Permisos requeridos: {', '.join(p.value for p in permisos)}"
            )
        return current_user
    
    return permission_checker


def require_any_permission(*permisos: PermisoEnum):
    """
    Factory que crea una dependency que requiere AL MENOS UNO de los permisos.
    
    Uso:
        @router.get("/camas", dependencies=[Depends(require_any_permission(PermisoEnum.CAMA_VER, PermisoEnum.CAMA_ASIGNAR))])
        def camas_endpoint():
            ...
    """
    async def permission_checker(
        current_user: Usuario = Depends(get_current_user)
    ) -> Usuario:
        if not current_user.tiene_algun_permiso(list(permisos)):
            raise PermissionError(
                f"Se requiere al menos uno de: {', '.join(p.value for p in permisos)}"
            )
        return current_user
    
    return permission_checker


def require_roles(*roles: RolEnum):
    """
    Factory que crea una dependency que requiere uno de los roles especificados.
    
    Uso:
        @router.post("/usuarios", dependencies=[Depends(require_roles(RolEnum.ADMIN, RolEnum.SUPER_ADMIN))])
        def create_user():
            ...
    """
    async def role_checker(
        current_user: Usuario = Depends(get_current_user)
    ) -> Usuario:
        if current_user.rol not in roles:
            raise PermissionError(
                f"Roles permitidos: {', '.join(r.value for r in roles)}"
            )
        return current_user
    
    return role_checker


# ============================================
# DEPENDENCY CON VERIFICACIÓN DE HOSPITAL
# ============================================

def require_same_hospital():
    """
    Verifica que el usuario pertenezca al mismo hospital que el recurso.
    Usado para endpoints que filtran por hospital_id.
    Los admins y super_admins tienen acceso a todos los hospitales.
    """
    async def hospital_checker(
        hospital_id: str,
        current_user: Usuario = Depends(get_current_user)
    ) -> Usuario:
        # Admins tienen acceso a todo
        if current_user.rol in [RolEnum.SUPER_ADMIN, RolEnum.ADMIN, RolEnum.COORDINADOR_RED]:
            return current_user
        
        # Verificar mismo hospital
        if current_user.hospital_id and current_user.hospital_id != hospital_id:
            raise PermissionError("No tienes acceso a este hospital")
        
        return current_user
    
    return hospital_checker


# ============================================
# DECORADORES PARA PROTEGER FUNCIONES
# ============================================

def protected(
    permisos: Optional[List[PermisoEnum]] = None,
    roles: Optional[List[RolEnum]] = None,
    require_all_permisos: bool = True
):
    """
    Decorador para proteger funciones de servicio (no endpoints).
    
    Uso:
        @protected(permisos=[PermisoEnum.PACIENTE_CREAR])
        def crear_paciente(user: Usuario, data: dict):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Buscar el usuario en los argumentos
            user = kwargs.get('user') or kwargs.get('current_user')
            
            if not user:
                for arg in args:
                    if isinstance(arg, Usuario):
                        user = arg
                        break
            
            if not user:
                raise AuthError("Usuario no proporcionado")
            
            # Verificar rol
            if roles and user.rol not in roles:
                raise PermissionError(
                    f"Roles permitidos: {', '.join(r.value for r in roles)}"
                )
            
            # Verificar permisos
            if permisos:
                if require_all_permisos:
                    if not user.tiene_todos_permisos(permisos):
                        raise PermissionError(
                            f"Permisos requeridos: {', '.join(p.value for p in permisos)}"
                        )
                else:
                    if not user.tiene_algun_permiso(permisos):
                        raise PermissionError(
                            f"Se requiere al menos uno de: {', '.join(p.value for p in permisos)}"
                        )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================================
# UTILITIES
# ============================================

def get_user_permisos(user: Usuario) -> List[str]:
    """Obtiene la lista de permisos de un usuario como strings."""
    return [p.value for p in user.permisos]


def check_permission(user: Usuario, permiso: PermisoEnum) -> bool:
    """Verifica si un usuario tiene un permiso específico."""
    return user.tiene_permiso(permiso)


def check_any_permission(user: Usuario, permisos: List[PermisoEnum]) -> bool:
    """Verifica si un usuario tiene al menos uno de los permisos."""
    return user.tiene_algun_permiso(permisos)


def can_access_hospital(user: Usuario, hospital_id: str) -> bool:
    """Verifica si un usuario puede acceder a un hospital específico."""
    if user.rol in [RolEnum.SUPER_ADMIN, RolEnum.ADMIN, RolEnum.COORDINADOR_RED]:
        return True
    
    if not user.hospital_id:
        return True  # Sin hospital asignado = acceso global
    
    return user.hospital_id == hospital_id


def can_manage_user(current_user: Usuario, target_user: Usuario) -> bool:
    """Verifica si un usuario puede gestionar a otro usuario."""
    # Solo super_admin puede gestionar otros super_admin
    if target_user.rol == RolEnum.SUPER_ADMIN:
        return current_user.rol == RolEnum.SUPER_ADMIN

    # Admin puede gestionar usuarios no-super_admin
    if current_user.rol in [RolEnum.SUPER_ADMIN, RolEnum.ADMIN]:
        return True

    return False


# ============================================
# DEPENDENCIES RBAC AVANZADOS (CAPA DE SEGURIDAD)
# ============================================

def require_not_readonly():
    """
    Dependency que verifica que el usuario NO sea de solo lectura.
    Lanza excepción si tiene perfil de solo lectura.
    """
    async def readonly_checker(
        current_user: Usuario = Depends(get_current_user)
    ) -> Usuario:
        rbac_service.verificar_restriccion_escritura(current_user, "operaciones de escritura")
        return current_user

    return readonly_checker


def require_hospital_access(hospital_id: str):
    """
    Dependency que verifica acceso a un hospital específico.

    Uso:
        @router.get("/hospitales/{hospital_id}", dependencies=[Depends(require_hospital_access)])
    """
    async def hospital_checker(
        current_user: Usuario = Depends(get_current_user)
    ) -> Usuario:
        if not rbac_service.puede_acceder_hospital(current_user, hospital_id):
            raise PermissionError(
                f"No tienes acceso al hospital: {hospital_id}"
            )
        return current_user

    return hospital_checker


def require_servicio_access(servicio_id: str):
    """
    Dependency que verifica acceso a un servicio específico.

    Uso:
        @router.get("/servicios/{servicio_id}", dependencies=[Depends(require_servicio_access)])
    """
    async def servicio_checker(
        current_user: Usuario = Depends(get_current_user)
    ) -> Usuario:
        if not rbac_service.puede_acceder_servicio(current_user, servicio_id):
            raise PermissionError(
                f"No tienes acceso al servicio: {servicio_id}"
            )
        return current_user

    return servicio_checker


def require_dashboard_access():
    """
    Dependency que verifica acceso al dashboard de camas.
    Urgencias y Ambulatorio NO tienen acceso.
    """
    async def dashboard_checker(
        current_user: Usuario = Depends(get_current_user)
    ) -> Usuario:
        if not rbac_service.tiene_acceso_dashboard(current_user):
            raise PermissionError(
                f"Tu rol ({current_user.rol.value}) no tiene acceso al dashboard de camas"
            )
        return current_user

    return dashboard_checker


def require_modo_manual_access(hospital_id: str):
    """
    Dependency que verifica acceso al modo manual según hospital.
    """
    async def modo_manual_checker(
        current_user: Usuario = Depends(get_current_user)
    ) -> Usuario:
        if not rbac_service.puede_usar_modo_manual(current_user, hospital_id):
            raise PermissionError(
                "No tienes permisos para usar el modo manual en este hospital"
            )
        return current_user

    return modo_manual_checker


async def get_user_hospitales_permitidos(
    current_user: Usuario = Depends(get_current_user)
) -> Optional[List[str]]:
    """
    Obtiene la lista de hospitales permitidos para el usuario.
    Returns None si tiene acceso a todos.
    """
    return rbac_service.obtener_hospitales_permitidos(current_user)


async def get_user_servicios_permitidos(
    current_user: Usuario = Depends(get_current_user)
) -> Optional[List[str]]:
    """
    Obtiene la lista de servicios permitidos para el usuario.
    Returns None si tiene acceso a todos.
    """
    return rbac_service.obtener_servicios_permitidos(current_user)
