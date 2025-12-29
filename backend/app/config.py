"""
Configuración centralizada de la aplicación.
Todas las configuraciones en un solo lugar para fácil mantenimiento.
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Configuración principal del sistema."""
    
    # ============================================
    # APLICACIÓN
    # ============================================
    APP_TITLE: str = "Sistema de Gestión de Camas Hospitalarias"
    APP_DESCRIPTION: str = "MVP de gestión automatizada de camas hospitalarias"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # ============================================
    # BASE DE DATOS
    # ============================================
    DATABASE_URL: str = "sqlite:///./gestion_camas.db"
    
    # ============================================
    # CORS
    # ============================================
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
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
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Instancia global de configuración
settings = Settings()

# Crear directorio de uploads si no existe
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)