"""
Router de Autenticación.
Endpoints para login, logout, refresh y gestión de usuarios.
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.usuario import Usuario, RolEnum, PermisoEnum, PERMISOS_POR_ROL
from app.services.auth_service import auth_service
from app.core.auth_dependencies import (
    get_current_user,
    get_current_user_optional,
    require_permissions,
    require_roles,
    can_manage_user
)
from app.schemas.auth_schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    UserListResponse,
    UserUpdateRequest,
    PasswordChangeRequest,
    MessageResponse,
    RolPermisos,
    ROLES_INFO
)


router = APIRouter(prefix="/auth", tags=["Autenticación"])


# ============================================
# ENDPOINTS PÚBLICOS
# ============================================

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    data: LoginRequest,
    session: Session = Depends(get_session)
):
    """
    Inicia sesión con username/email y contraseña.
    Retorna access_token y refresh_token.
    """
    user = auth_service.authenticate_user(data.username, data.password, session)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )
    
    # Crear tokens
    access_token = auth_service.create_access_token(user)
    refresh_token = auth_service.create_refresh_token(
        user, 
        session,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
        remember_me=data.remember_me
    )
    
    # Construir respuesta
    return LoginResponse(
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            nombre_completo=user.nombre_completo,
            rol=user.rol,
            hospital_id=user.hospital_id,
            servicio_id=user.servicio_id,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            last_login=user.last_login,
            permisos=[p.value for p in user.permisos]
        ),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=30 * 60  # 30 minutos en segundos
        )
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    session: Session = Depends(get_session)
):
    """
    Refresca el access_token usando un refresh_token válido.
    """
    # Verificar refresh token
    token_record = auth_service.verify_refresh_token(data.refresh_token, session)
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado"
        )
    
    # Obtener usuario
    user = auth_service.get_user_by_id(token_record.usuario_id, session)
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o desactivado"
        )
    
    # Crear nuevo access token
    access_token = auth_service.create_access_token(user)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=data.refresh_token,  # El refresh token sigue siendo el mismo
        expires_in=30 * 60
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    data: RefreshTokenRequest,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Cierra sesión revocando el refresh_token.
    """
    revoked = auth_service.revoke_refresh_token(data.refresh_token, session)
    
    return MessageResponse(
        success=True,
        message="Sesión cerrada correctamente"
    )


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all_sessions(
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Cierra todas las sesiones del usuario actual.
    """
    count = auth_service.revoke_all_user_tokens(current_user.id, session)
    
    return MessageResponse(
        success=True,
        message=f"Se cerraron {count} sesiones"
    )


# ============================================
# ENDPOINTS DE USUARIO ACTUAL
# ============================================

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene la información del usuario actual.
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        nombre_completo=current_user.nombre_completo,
        rol=current_user.rol,
        hospital_id=current_user.hospital_id,
        servicio_id=current_user.servicio_id,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
        permisos=[p.value for p in current_user.permisos]
    )


@router.put("/me/password", response_model=MessageResponse)
async def change_password(
    data: PasswordChangeRequest,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Cambia la contraseña del usuario actual.
    """
    # Verificar contraseña actual
    if not auth_service.verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta"
        )
    
    # Verificar que la nueva sea diferente
    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe ser diferente a la actual"
        )
    
    # Actualizar contraseña
    auth_service.update_password(current_user, data.new_password, session)
    
    # Revocar todos los tokens (forzar re-login)
    auth_service.revoke_all_user_tokens(current_user.id, session)
    
    return MessageResponse(
        success=True,
        message="Contraseña actualizada. Por favor, inicia sesión nuevamente."
    )


@router.get("/me/permisos", response_model=List[str])
async def get_my_permissions(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene la lista de permisos del usuario actual.
    """
    return [p.value for p in current_user.permisos]


# ============================================
# ENDPOINTS DE GESTIÓN DE USUARIOS (ADMIN)
# ============================================

@router.get(
    "/usuarios",
    response_model=List[UserListResponse],
    dependencies=[Depends(require_permissions(PermisoEnum.USUARIOS_VER))]
)
async def list_users(
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
    hospital_id: Optional[str] = None,
    rol: Optional[RolEnum] = None,
    is_active: Optional[bool] = None
):
    """
    Lista todos los usuarios (solo admin).
    """
    statement = select(Usuario)
    
    # Filtros
    if hospital_id:
        statement = statement.where(Usuario.hospital_id == hospital_id)
    if rol:
        statement = statement.where(Usuario.rol == rol)
    if is_active is not None:
        statement = statement.where(Usuario.is_active == is_active)
    
    # No mostrar super_admins a usuarios normales
    if current_user.rol != RolEnum.SUPER_ADMIN:
        statement = statement.where(Usuario.rol != RolEnum.SUPER_ADMIN)
    
    users = session.exec(statement.order_by(Usuario.created_at.desc())).all()
    
    return [
        UserListResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            nombre_completo=u.nombre_completo,
            rol=u.rol,
            hospital_id=u.hospital_id,
            is_active=u.is_active,
            last_login=u.last_login
        )
        for u in users
    ]


@router.post(
    "/usuarios",
    response_model=UserResponse,
    dependencies=[Depends(require_permissions(PermisoEnum.USUARIOS_CREAR))]
)
async def create_user(
    data: RegisterRequest,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Crea un nuevo usuario (solo admin).
    """
    # Verificar que no se cree super_admin sin ser super_admin
    if data.rol == RolEnum.SUPER_ADMIN and current_user.rol != RolEnum.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un super administrador puede crear otros super administradores"
        )
    
    # Verificar username único
    if auth_service.get_user_by_username(data.username, session):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El username ya está en uso"
        )
    
    # Verificar email único
    if auth_service.get_user_by_email(data.email, session):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está en uso"
        )
    
    # Crear usuario
    user = auth_service.create_user(
        username=data.username,
        email=data.email,
        password=data.password,
        nombre_completo=data.nombre_completo,
        rol=data.rol,
        hospital_id=data.hospital_id,
        servicio_id=data.servicio_id,
        session=session,
        created_by=current_user.id
    )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        nombre_completo=user.nombre_completo,
        rol=user.rol,
        hospital_id=user.hospital_id,
        servicio_id=user.servicio_id,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        last_login=user.last_login,
        permisos=[p.value for p in user.permisos]
    )


@router.get(
    "/usuarios/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permissions(PermisoEnum.USUARIOS_VER))]
)
async def get_user(
    user_id: str,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene un usuario por ID (solo admin).
    """
    user = session.get(Usuario, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # No mostrar super_admins a usuarios normales
    if user.rol == RolEnum.SUPER_ADMIN and current_user.rol != RolEnum.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        nombre_completo=user.nombre_completo,
        rol=user.rol,
        hospital_id=user.hospital_id,
        servicio_id=user.servicio_id,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        last_login=user.last_login,
        permisos=[p.value for p in user.permisos]
    )


@router.put(
    "/usuarios/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permissions(PermisoEnum.USUARIOS_EDITAR))]
)
async def update_user(
    user_id: str,
    data: UserUpdateRequest,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Actualiza un usuario (solo admin).
    """
    user = session.get(Usuario, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Verificar permisos de gestión
    if not can_manage_user(current_user, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para gestionar este usuario"
        )
    
    # No permitir cambio a super_admin sin ser super_admin
    if data.rol == RolEnum.SUPER_ADMIN and current_user.rol != RolEnum.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes asignar el rol de super administrador"
        )
    
    # Actualizar campos
    if data.email is not None:
        # Verificar email único
        existing = auth_service.get_user_by_email(data.email, session)
        if existing and existing.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está en uso"
            )
        user.email = data.email.lower()
    
    if data.nombre_completo is not None:
        user.nombre_completo = data.nombre_completo
    
    if data.rol is not None:
        user.rol = data.rol
    
    if data.hospital_id is not None:
        user.hospital_id = data.hospital_id or None
    
    if data.servicio_id is not None:
        user.servicio_id = data.servicio_id or None
    
    if data.is_active is not None:
        user.is_active = data.is_active
        # Si se desactiva, revocar todos los tokens
        if not data.is_active:
            auth_service.revoke_all_user_tokens(user.id, session)
    
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        nombre_completo=user.nombre_completo,
        rol=user.rol,
        hospital_id=user.hospital_id,
        servicio_id=user.servicio_id,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        last_login=user.last_login,
        permisos=[p.value for p in user.permisos]
    )


@router.delete(
    "/usuarios/{user_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_permissions(PermisoEnum.USUARIOS_ELIMINAR))]
)
async def delete_user(
    user_id: str,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Elimina (desactiva) un usuario (solo admin).
    """
    user = session.get(Usuario, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Verificar permisos de gestión
    if not can_manage_user(current_user, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para eliminar este usuario"
        )
    
    # No permitir eliminarse a sí mismo
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminarte a ti mismo"
        )
    
    # Soft delete - desactivar en lugar de eliminar
    user.is_active = False
    user.updated_at = datetime.utcnow()
    session.add(user)
    
    # Revocar todos los tokens
    auth_service.revoke_all_user_tokens(user.id, session)
    
    session.commit()
    
    return MessageResponse(
        success=True,
        message="Usuario desactivado correctamente"
    )


@router.put(
    "/usuarios/{user_id}/reset-password",
    response_model=MessageResponse,
    dependencies=[Depends(require_permissions(PermisoEnum.USUARIOS_EDITAR))]
)
async def reset_user_password(
    user_id: str,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Resetea la contraseña de un usuario a una temporal (solo admin).
    La nueva contraseña es el username + "123"
    """
    user = session.get(Usuario, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Verificar permisos de gestión
    if not can_manage_user(current_user, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para resetear la contraseña de este usuario"
        )
    
    # Nueva contraseña temporal
    temp_password = f"{user.username}123"
    
    auth_service.update_password(user, temp_password, session)
    auth_service.revoke_all_user_tokens(user.id, session)
    
    return MessageResponse(
        success=True,
        message=f"Contraseña reseteada. Nueva contraseña temporal: {temp_password}",
        data={"temp_password": temp_password}
    )


# ============================================
# ENDPOINTS DE INFORMACIÓN DE ROLES
# ============================================

@router.get("/roles", response_model=List[RolPermisos])
async def list_roles(
    current_user: Optional[Usuario] = Depends(get_current_user_optional)
):
    """
    Lista todos los roles disponibles con sus permisos.
    Endpoint público para mostrar info en login.
    """
    roles_list = []
    
    for rol in RolEnum:
        # No mostrar super_admin a usuarios no autenticados o no-admin
        if rol == RolEnum.SUPER_ADMIN:
            if not current_user or current_user.rol != RolEnum.SUPER_ADMIN:
                continue
        
        info = ROLES_INFO.get(rol, {"nombre": rol.value, "descripcion": ""})
        permisos = PERMISOS_POR_ROL.get(rol, [])
        
        roles_list.append(RolPermisos(
            rol=rol,
            nombre=info["nombre"],
            descripcion=info["descripcion"],
            permisos=[p.value for p in permisos]
        ))
    
    return roles_list


@router.get("/roles/{rol}", response_model=RolPermisos)
async def get_role_info(
    rol: RolEnum
):
    """
    Obtiene información de un rol específico.
    """
    info = ROLES_INFO.get(rol, {"nombre": rol.value, "descripcion": ""})
    permisos = PERMISOS_POR_ROL.get(rol, [])
    
    return RolPermisos(
        rol=rol,
        nombre=info["nombre"],
        descripcion=info["descripcion"],
        permisos=[p.value for p in permisos]
    )


# ============================================
# ENDPOINT DE VERIFICACIÓN DE PERMISOS
# ============================================

@router.post("/check-permission", response_model=MessageResponse)
async def check_permission(
    permiso: str,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Verifica si el usuario actual tiene un permiso específico.
    Útil para el frontend.
    """
    try:
        permiso_enum = PermisoEnum(permiso)
        has_permission = current_user.tiene_permiso(permiso_enum)
        
        return MessageResponse(
            success=has_permission,
            message="Permiso verificado",
            data={"permiso": permiso, "tiene_permiso": has_permission}
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Permiso inválido: {permiso}"
        )
