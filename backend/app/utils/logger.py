"""
Configuración de logging del sistema.
"""
import logging
from app.config import settings


def configurar_logging(nivel: str = None) -> logging.Logger:
    """
    Configura y retorna el logger principal del sistema.
    
    Args:
        nivel: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Logger configurado
    """
    if nivel is None:
        nivel = settings.LOG_LEVEL
    
    # Convertir string a nivel
    nivel_num = getattr(logging, nivel.upper(), logging.INFO)
    
    # Formato del log
    formato = logging.Formatter(
        settings.LOG_FORMAT,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formato)
    
    # Logger principal
    logger = logging.getLogger('gestion_camas')
    logger.setLevel(nivel_num)
    
    # Evitar duplicación de handlers
    if not logger.handlers:
        logger.addHandler(console_handler)
    
    return logger


# Logger global
logger = configurar_logging()


def get_logger(nombre: str) -> logging.Logger:
    """
    Obtiene un logger para un módulo específico.
    
    Args:
        nombre: Nombre del módulo
    
    Returns:
        Logger configurado
    """
    return logging.getLogger(f'gestion_camas.{nombre}')