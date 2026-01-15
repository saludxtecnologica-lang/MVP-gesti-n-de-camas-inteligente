"""
Configuración centralizada de la aplicación.
Todas las configuraciones en un solo lugar para fácil mantenimiento.
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Configuración principal del sistema."""

    # ============================================
    # APLICACIÓN
    # ============================================
    APP_TITLE: str = "Sistema de Gestión de Camas Hospitalarias"
    APP_DESCRIPTION: str = "MVP de gestión automatizada de camas hospitalarias"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"  # development, staging, production
    DEBUG: bool = False

    # ============================================
    # BASE DE DATOS - PostgreSQL
    # ============================================
    # URL principal (escritura)
    DATABASE_URL: str = "postgresql://gestion_camas:changeme_in_production@localhost:5432/gestion_camas_db"

    # URL de réplica (lectura - opcional)
    DATABASE_READ_REPLICA_URL: Optional[str] = None

    # Pool de conexiones
    DB_POOL_SIZE: int = 20  # Número de conexiones permanentes
    DB_MAX_OVERFLOW: int = 10  # Conexiones adicionales en picos
    DB_POOL_TIMEOUT: int = 30  # Segundos para obtener conexión
    DB_POOL_RECYCLE: int = 3600  # Reciclar conexiones cada hora
    DB_POOL_PRE_PING: bool = True  # Verificar conexiones antes de usar
    DB_ECHO: bool = False  # Log de queries SQL (solo desarrollo)

    # ============================================
    # REDIS - Caché y Sesiones
    # ============================================
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300  # 5 minutos por defecto
    REDIS_ENABLED: bool = True  # Permitir deshabilitar en desarrollo
    
    # ============================================
    # MULTI-TENANCY (Preparación para múltiples hospitales/redes)
    # ============================================
    ENABLE_MULTI_TENANCY: bool = True  # Habilitar aislamiento por hospital
    DEFAULT_TENANT_ID: Optional[str] = None  # Hospital por defecto
    TENANT_HEADER_NAME: str = "X-Hospital-ID"  # Header para identificar tenant

    # ============================================
    # API GATEWAY - Comunicación entre Microservicios
    # ============================================
    # API Keys para autenticación entre servicios
    INTERNAL_API_KEYS: List[str] = []  # Cargar desde .env
    API_KEY_HEADER_NAME: str = "X-API-Key"

    # URLs de otros microservicios (para futuro)
    HIS_API_URL: Optional[str] = None  # Sistema HIS del hospital
    LABORATORIO_API_URL: Optional[str] = None
    IMAGENOLOGIA_API_URL: Optional[str] = None
    FARMACIA_API_URL: Optional[str] = None

    # Timeouts para APIs externas (segundos)
    EXTERNAL_API_TIMEOUT: int = 10
    EXTERNAL_API_RETRIES: int = 3

    # ============================================
    # CORS - Configuración más segura
    # ============================================
    # En producción, especificar dominios exactos
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",  # Frontend desarrollo
        "http://localhost:3000",  # Frontend alternativo
        "https://gestion-camas.hospital.cl"  # Producción
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # ============================================
    # ARCHIVOS
    # ============================================
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]
    
    # ============================================
    # PROCESOS AUTOMÁTICOS
    # ============================================
    PROCESO_AUTOMATICO_INTERVALO: int = 5  # segundos
    TIEMPO_LIMPIEZA_DEFAULT: int = 60  # segundos
    TIEMPO_ESPERA_OXIGENO_DEFAULT: int = 120  # segundos (2 minutos)
    
    # ============================================
    # WEBSOCKET
    # ============================================
    WS_RECONNECT_INTERVAL: int = 3  # segundos
    WS_MAX_RECONNECT_ATTEMPTS: int = 10
    
    # ============================================
    # LOGGING
    # ============================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    # ============================================
    # JWT
    # ============================================
    JWT_SECRET_KEY: str = "tu-clave-secreta-muy-larga-y-segura-cambiar-en-produccion-12345"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutos
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7     # 7 días
    
    # ============================================
    # SEGURIDAD
    # ============================================
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = False

    # Intentos de login
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # Rate Limiting (peticiones por minuto)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 100  # Peticiones generales
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 5  # Login
    RATE_LIMIT_API_PUBLIC_PER_MINUTE: int = 20  # APIs públicas

    # HTTPS/SSL
    FORCE_HTTPS: bool = False  # True en producción
    SSL_CERT_PATH: Optional[str] = None
    SSL_KEY_PATH: Optional[str] = None
    
    # ============================================
    # COOKIES (opcional, para httpOnly cookies)
    # ============================================
    COOKIE_SECURE: bool = False  # True en producción con HTTPS
    COOKIE_HTTPONLY: bool = True
    COOKIE_SAMESITE: str = "lax"  # "strict", "lax", o "none"
    COOKIE_DOMAIN: str = ""  # Vacío para localhost
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Instancia global de configuración
settings = Settings()

# Crear directorio de uploads si no existe
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)