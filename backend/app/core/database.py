"""
Configuración de Base de Datos con PostgreSQL.
Gestión de conexiones, pool, réplicas y caché con Redis.
"""
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import QueuePool
from typing import Generator, Optional
from contextlib import contextmanager
import redis
import logging

from app.config import settings

logger = logging.getLogger("gestion_camas.database")


# ============================================
# POSTGRESQL - ENGINE PRINCIPAL (ESCRITURA)
# ============================================

# Configuración del pool de conexiones
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,  # Conexiones permanentes
    max_overflow=settings.DB_MAX_OVERFLOW,  # Conexiones adicionales en picos
    pool_timeout=settings.DB_POOL_TIMEOUT,  # Timeout para obtener conexión
    pool_recycle=settings.DB_POOL_RECYCLE,  # Reciclar conexiones cada hora
    pool_pre_ping=settings.DB_POOL_PRE_PING,  # Verificar conexiones antes de usar
    # Configuración específica para PostgreSQL
    connect_args={
        "application_name": "gestion_camas_app",
        "connect_timeout": 10,
        # Para mejor performance con PostgreSQL
        "options": "-c timezone=America/Santiago"
    }
)

logger.info(f"✅ Engine de base de datos creado: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'database'}")
logger.info(f"📊 Pool configurado: size={settings.DB_POOL_SIZE}, max_overflow={settings.DB_MAX_OVERFLOW}")


# ============================================
# POSTGRESQL - ENGINE DE RÉPLICA (LECTURA)
# ============================================

engine_read: Optional[object] = None

if settings.DATABASE_READ_REPLICA_URL:
    engine_read = create_engine(
        settings.DATABASE_READ_REPLICA_URL,
        echo=settings.DB_ECHO,
        poolclass=QueuePool,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
        connect_args={
            "application_name": "gestion_camas_app_read",
            "connect_timeout": 10,
            "options": "-c timezone=America/Santiago -c default_transaction_read_only=on"
        }
    )
    logger.info("✅ Engine de réplica (lectura) creado")
else:
    logger.info("ℹ️  No se configuró réplica de lectura, usando engine principal")


# ============================================
# REDIS - CACHÉ
# ============================================

redis_client: Optional[redis.Redis] = None

if settings.REDIS_ENABLED:
    try:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
        # Verificar conexión
        redis_client.ping()
        logger.info("✅ Redis conectado correctamente")
    except Exception as e:
        logger.warning(f"⚠️  No se pudo conectar a Redis: {e}")
        redis_client = None
else:
    logger.info("ℹ️  Redis deshabilitado")


# ============================================
# FUNCIONES DE GESTIÓN DE BD
# ============================================

def create_db_and_tables() -> None:
    """
    Crea todas las tablas en la base de datos.
    Se llama al inicio de la aplicación.

    IMPORTANTE: En producción, usar Alembic migrations en lugar de esto.
    """
    logger.info("🔨 Creando tablas en base de datos...")
    SQLModel.metadata.create_all(engine)
    logger.info("✅ Tablas creadas correctamente")


def get_session(read_only: bool = False) -> Generator[Session, None, None]:
    """
    Generador de sesiones para dependency injection en FastAPI.

    Args:
        read_only: Si True, usa la réplica de lectura (si está configurada)

    Uso en FastAPI:
        @app.get("/endpoint")
        def endpoint(session: Session = Depends(get_session)):
            ...

        # Para operaciones de solo lectura (usa réplica si existe)
        @app.get("/endpoint-lectura")
        def endpoint_lectura(session: Session = Depends(lambda: get_session(read_only=True))):
            ...
    """
    # Seleccionar engine apropiado
    selected_engine = engine
    if read_only and engine_read is not None:
        selected_engine = engine_read
        logger.debug("🔍 Usando réplica de lectura")

    with Session(selected_engine) as session:
        try:
            yield session
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error en sesión de base de datos: {e}")
            raise
        finally:
            session.close()


def get_session_direct(read_only: bool = False) -> Session:
    """
    Obtiene una sesión directa (no generator).
    Útil para tareas en background y scripts.

    IMPORTANTE: El caller es responsable de cerrar la sesión.

    Args:
        read_only: Si True, usa la réplica de lectura (si está configurada)

    Uso:
        session = get_session_direct()
        try:
            # operaciones
        finally:
            session.close()
    """
    selected_engine = engine
    if read_only and engine_read is not None:
        selected_engine = engine_read

    return Session(selected_engine)


@contextmanager
def get_session_context(read_only: bool = False):
    """
    Context manager para sesiones.
    Cierra automáticamente la sesión al salir del contexto.

    Args:
        read_only: Si True, usa la réplica de lectura (si está configurada)

    Uso:
        with get_session_context() as session:
            # operaciones
            pass
        # sesión cerrada automáticamente
    """
    session = get_session_direct(read_only=read_only)
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error en contexto de sesión: {e}")
        raise
    finally:
        session.close()


# ============================================
# FUNCIONES DE CACHÉ (REDIS)
# ============================================

def get_redis() -> Optional[redis.Redis]:
    """
    Obtiene el cliente de Redis.

    Returns:
        Cliente de Redis o None si no está disponible
    """
    return redis_client


def cache_get(key: str) -> Optional[str]:
    """
    Obtiene un valor del caché.

    Args:
        key: Clave del caché

    Returns:
        Valor del caché o None si no existe o Redis no disponible
    """
    if redis_client is None:
        return None

    try:
        return redis_client.get(key)
    except Exception as e:
        logger.warning(f"⚠️  Error al obtener del caché: {e}")
        return None


def cache_set(key: str, value: str, ttl: int = None) -> bool:
    """
    Guarda un valor en el caché.

    Args:
        key: Clave del caché
        value: Valor a guardar
        ttl: Tiempo de vida en segundos (None = usar default)

    Returns:
        True si se guardó correctamente, False en caso contrario
    """
    if redis_client is None:
        return False

    try:
        if ttl is None:
            ttl = settings.REDIS_CACHE_TTL
        redis_client.setex(key, ttl, value)
        return True
    except Exception as e:
        logger.warning(f"⚠️  Error al guardar en caché: {e}")
        return False


def cache_delete(key: str) -> bool:
    """
    Elimina un valor del caché.

    Args:
        key: Clave del caché

    Returns:
        True si se eliminó correctamente, False en caso contrario
    """
    if redis_client is None:
        return False

    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        logger.warning(f"⚠️  Error al eliminar del caché: {e}")
        return False


def cache_invalidate_pattern(pattern: str) -> int:
    """
    Invalida todas las claves que coincidan con un patrón.

    Args:
        pattern: Patrón de búsqueda (ej: "camas:*")

    Returns:
        Número de claves eliminadas
    """
    if redis_client is None:
        return 0

    try:
        keys = redis_client.keys(pattern)
        if keys:
            return redis_client.delete(*keys)
        return 0
    except Exception as e:
        logger.warning(f"⚠️  Error al invalidar patrón de caché: {e}")
        return 0


# ============================================
# HEALTH CHECKS
# ============================================

def check_database_health() -> dict:
    """
    Verifica el estado de la base de datos.

    Returns:
        Dict con información de salud
    """
    try:
        with get_session_context() as session:
            session.execute("SELECT 1")

        # Verificar réplica si existe
        replica_status = "not_configured"
        if engine_read is not None:
            try:
                with Session(engine_read) as session:
                    session.execute("SELECT 1")
                replica_status = "healthy"
            except Exception:
                replica_status = "unhealthy"

        return {
            "status": "healthy",
            "primary": "healthy",
            "replica": replica_status,
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW
        }
    except Exception as e:
        logger.error(f"❌ Database health check falló: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_redis_health() -> dict:
    """
    Verifica el estado de Redis.

    Returns:
        Dict con información de salud
    """
    if redis_client is None:
        return {
            "status": "disabled",
            "message": "Redis no configurado"
        }

    try:
        redis_client.ping()
        info = redis_client.info("stats")
        return {
            "status": "healthy",
            "total_connections": info.get("total_connections_received", 0),
            "commands_processed": info.get("total_commands_processed", 0)
        }
    except Exception as e:
        logger.error(f"❌ Redis health check falló: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# ============================================
# SHUTDOWN
# ============================================

def shutdown_database():
    """
    Cierra las conexiones a la base de datos y Redis al apagar la aplicación.
    """
    logger.info("🔄 Cerrando conexiones a base de datos...")

    try:
        engine.dispose()
        logger.info("✅ Engine principal cerrado")

        if engine_read is not None:
            engine_read.dispose()
            logger.info("✅ Engine de réplica cerrado")

        if redis_client is not None:
            redis_client.close()
            logger.info("✅ Redis cerrado")
    except Exception as e:
        logger.error(f"❌ Error al cerrar conexiones: {e}")
