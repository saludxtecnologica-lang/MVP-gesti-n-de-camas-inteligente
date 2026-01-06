"""
Servicio de Autenticación.
Manejo de JWT, hashing de contraseñas y validación de tokens.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select
import secrets

from app.config import settings
from app.models.usuario import Usuario, RefreshToken, RolEnum
from app.schemas.auth_schemas import TokenPayload


# Contexto de hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Servicio de autenticación."""
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        self.refresh_token_expire = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    # ============================================
    # HASHING DE CONTRASEÑAS
    # ============================================
    
    def hash_password(self, password: str) -> str:
        """Hashea una contraseña."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica una contraseña contra su hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    # ============================================
    # JWT TOKENS
    # ============================================
    
    def create_access_token(
        self, 
        user: Usuario,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Crea un access token JWT."""
        expire = datetime.utcnow() + (expires_delta or self.access_token_expire)
        
        payload = {
            "sub": user.id,
            "username": user.username,
            "rol": user.rol.value,
            "hospital_id": user.hospital_id,
            "servicio_id": user.servicio_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(
        self,
        user: Usuario,
        session: Session,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        remember_me: bool = False
    ) -> str:
        """Crea un refresh token y lo guarda en la BD."""
        # Token más largo si "remember me"
        expire_delta = timedelta(days=30) if remember_me else self.refresh_token_expire
        expire = datetime.utcnow() + expire_delta
        
        # Generar token único
        token_value = secrets.token_urlsafe(64)
        
        # Guardar en BD - CORREGIDO: usar user_id en lugar de usuario_id
        refresh_token = RefreshToken(
            token=token_value,
            user_id=user.id,  # ✅ CORREGIDO
            expires_at=expire,
            user_agent=user_agent,
            ip_address=ip_address
        )
        session.add(refresh_token)
        session.commit()
        
        return token_value
    
    def decode_token(self, token: str) -> Optional[TokenPayload]:
        """Decodifica y valida un JWT token."""
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            return TokenPayload(**payload)
        except JWTError:
            return None
    
    def verify_refresh_token(
        self, 
        token: str, 
        session: Session
    ) -> Optional[RefreshToken]:
        """Verifica un refresh token en la BD."""
        statement = select(RefreshToken).where(
            RefreshToken.token == token,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        )
        return session.exec(statement).first()
    
    def revoke_refresh_token(self, token: str, session: Session) -> bool:
        """Revoca un refresh token."""
        statement = select(RefreshToken).where(RefreshToken.token == token)
        refresh_token = session.exec(statement).first()
        
        if refresh_token:
            refresh_token.revoked = True
            refresh_token.revoked_at = datetime.utcnow()
            session.add(refresh_token)
            session.commit()
            return True
        return False
    
    def revoke_all_user_tokens(self, user_id: str, session: Session) -> int:
        """Revoca todos los refresh tokens de un usuario."""
        # CORREGIDO: usar user_id en lugar de usuario_id
        statement = select(RefreshToken).where(
            RefreshToken.user_id == user_id,  # ✅ CORREGIDO
            RefreshToken.revoked == False
        )
        tokens = session.exec(statement).all()
        
        count = 0
        for token in tokens:
            token.revoked = True
            token.revoked_at = datetime.utcnow()
            session.add(token)
            count += 1
        
        session.commit()
        return count
    
    # ============================================
    # AUTENTICACIÓN
    # ============================================
    
    def authenticate_user(
        self, 
        username: str, 
        password: str, 
        session: Session
    ) -> Optional[Usuario]:
        """Autentica un usuario por username/password."""
        # Buscar por username o email
        statement = select(Usuario).where(
            (Usuario.username == username.lower()) | 
            (Usuario.email == username.lower())
        )
        user = session.exec(statement).first()
        
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        if not self.verify_password(password, user.hashed_password):
            return None
        
        # Actualizar último login
        user.last_login = datetime.utcnow()
        session.add(user)
        session.commit()
        
        return user
    
    def get_user_by_id(self, user_id: str, session: Session) -> Optional[Usuario]:
        """Obtiene un usuario por ID."""
        return session.get(Usuario, user_id)
    
    def get_user_by_username(self, username: str, session: Session) -> Optional[Usuario]:
        """Obtiene un usuario por username."""
        statement = select(Usuario).where(Usuario.username == username.lower())
        return session.exec(statement).first()
    
    def get_user_by_email(self, email: str, session: Session) -> Optional[Usuario]:
        """Obtiene un usuario por email."""
        statement = select(Usuario).where(Usuario.email == email.lower())
        return session.exec(statement).first()
    
    # ============================================
    # REGISTRO (solo admin)
    # ============================================
    
    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        nombre_completo: str,
        rol: RolEnum,
        session: Session,
        hospital_id: Optional[str] = None,
        servicio_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Usuario:
        """Crea un nuevo usuario."""
        user = Usuario(
            username=username.lower(),
            email=email.lower(),
            hashed_password=self.hash_password(password),
            nombre_completo=nombre_completo,
            rol=rol,
            hospital_id=hospital_id,
            servicio_id=servicio_id,
            is_verified=True  # Auto-verificado cuando lo crea admin
        )
        
        session.add(user)
        session.commit()
        session.refresh(user)
        
        return user
    
    def update_password(
        self,
        user: Usuario,
        new_password: str,
        session: Session
    ) -> bool:
        """Actualiza la contraseña de un usuario."""
        user.hashed_password = self.hash_password(new_password)
        user.updated_at = datetime.utcnow()
        session.add(user)
        session.commit()
        return True
    
    # ============================================
    # LIMPIEZA
    # ============================================
    
    def cleanup_expired_tokens(self, session: Session) -> int:
        """Elimina tokens expirados (ejecutar periódicamente)."""
        statement = select(RefreshToken).where(
            RefreshToken.expires_at < datetime.utcnow()
        )
        expired_tokens = session.exec(statement).all()
        
        count = 0
        for token in expired_tokens:
            session.delete(token)
            count += 1
        
        session.commit()
        return count


# Instancia global del servicio
auth_service = AuthService()