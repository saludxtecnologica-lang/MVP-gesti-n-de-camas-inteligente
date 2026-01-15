"""
Endpoints de Health Check.
Verificación de estado del sistema y sus componentes.
"""
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import Dict, Any

from app.config import settings
from app.core.database import check_database_health, check_redis_health, get_redis

router = APIRouter(
    prefix="/health",
    tags=["health"],
    responses={
        200: {"description": "Sistema saludable"},
        503: {"description": "Sistema no disponible"}
    }
)


@router.get(
    "",
    summary="Health Check General",
    description="Verifica el estado general de la aplicación",
    response_model=None
)
async def health_check() -> JSONResponse:
    """
    Health check básico.
    Retorna 200 si la aplicación está corriendo.

    Este endpoint es útil para:
    - Docker health checks
    - Load balancers
    - Monitoreo básico
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV
        }
    )


@router.get(
    "/liveness",
    summary="Liveness Probe",
    description="Verifica que la aplicación está viva",
    response_model=None
)
async def liveness_probe() -> JSONResponse:
    """
    Liveness probe para Kubernetes.

    Retorna 200 si la aplicación está corriendo.
    Si falla, Kubernetes reiniciará el pod.
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "alive",
            "timestamp": datetime.now().isoformat()
        }
    )


@router.get(
    "/readiness",
    summary="Readiness Probe",
    description="Verifica que la aplicación está lista para recibir tráfico",
    response_model=None
)
async def readiness_probe() -> JSONResponse:
    """
    Readiness probe para Kubernetes.

    Verifica que todos los componentes críticos están disponibles:
    - Base de datos
    - Redis (si está habilitado)

    Si falla, Kubernetes no enviará tráfico a este pod.
    """
    # Verificar base de datos
    db_health = check_database_health()

    # Verificar Redis
    redis_health = check_redis_health()

    # Determinar estado general
    all_healthy = (
        db_health.get("status") == "healthy" and
        (redis_health.get("status") in ["healthy", "disabled"])
    )

    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_healthy else "not_ready",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "database": db_health,
                "redis": redis_health
            }
        }
    )


@router.get(
    "/detailed",
    summary="Health Check Detallado",
    description="Información detallada del estado del sistema",
    response_model=None
)
async def detailed_health_check() -> JSONResponse:
    """
    Health check completo con información detallada.

    Incluye:
    - Estado de la base de datos
    - Estado de Redis
    - Configuración del pool de conexiones
    - Versión de la aplicación
    - Variables de entorno
    """
    # Verificar base de datos
    db_health = check_database_health()

    # Verificar Redis
    redis_health = check_redis_health()

    # Determinar estado general
    all_healthy = (
        db_health.get("status") == "healthy" and
        (redis_health.get("status") in ["healthy", "disabled"])
    )

    # Información adicional del sistema
    system_info = {
        "app_version": settings.APP_VERSION,
        "app_environment": settings.APP_ENV,
        "debug_mode": settings.DEBUG,
        "multi_tenancy_enabled": settings.ENABLE_MULTI_TENANCY,
        "rate_limiting_enabled": settings.RATE_LIMIT_ENABLED,
        "redis_enabled": settings.REDIS_ENABLED,
        "process_interval_seconds": settings.PROCESO_AUTOMATICO_INTERVALO,
    }

    # Pool de conexiones
    pool_info = {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_recycle": settings.DB_POOL_RECYCLE,
    }

    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "database": db_health,
                "redis": redis_health
            },
            "system": system_info,
            "database_pool": pool_info
        }
    )


@router.get(
    "/startup",
    summary="Startup Probe",
    description="Verifica que la aplicación completó el inicio",
    response_model=None
)
async def startup_probe() -> JSONResponse:
    """
    Startup probe para Kubernetes.

    Verifica que la aplicación terminó de inicializar.
    Útil para aplicaciones que tardan en iniciar.

    Si falla, Kubernetes esperará más tiempo antes de enviar tráfico.
    """
    # Verificar base de datos (componente crítico para el inicio)
    db_health = check_database_health()

    is_started = db_health.get("status") == "healthy"

    status_code = status.HTTP_200_OK if is_started else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "started" if is_started else "starting",
            "timestamp": datetime.now().isoformat(),
            "database": db_health
        }
    )


@router.get(
    "/metrics",
    summary="Métricas Básicas",
    description="Métricas básicas del sistema (formato simple)",
    response_model=None
)
async def metrics() -> Dict[str, Any]:
    """
    Métricas básicas del sistema.

    En el futuro, esto podría expandirse para incluir:
    - Número de pacientes activos
    - Número de camas ocupadas
    - Tiempo promedio de asignación
    - etc.
    """
    redis_client = get_redis()

    metrics_data = {
        "timestamp": datetime.now().isoformat(),
        "app_version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }

    # Si Redis está disponible, obtener estadísticas
    if redis_client:
        try:
            info = redis_client.info("stats")
            metrics_data["redis"] = {
                "total_connections": info.get("total_connections_received", 0),
                "commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
        except Exception:
            pass

    return metrics_data
