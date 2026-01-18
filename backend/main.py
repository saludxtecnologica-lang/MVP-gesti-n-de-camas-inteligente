"""
Entry point de la aplicación.
Sistema de Gestión de Camas Hospitalarias.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import os

from app.config import settings
from app.api.router import api_router
from app.core.database import create_db_and_tables, get_session_direct
from app.core.background_tasks import proceso_automatico
from app.services.prioridad_service import sincronizar_colas_iniciales
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación."""
    logger.info("Iniciando aplicación...")

    # Startup
    # create_db_and_tables()  # COMENTADO: Las tablas ya existen en Supabase
    logger.info("Saltando creación de tablas (ya existen en Supabase)")

    # # Inicializar datos si es necesario
    # session = get_session_direct()
    # try:
    #     from app.utils.init_data import inicializar_datos
    #     inicializar_datos(session)
    #     logger.info("Datos iniciales cargados")
    #
    #     # Sincronizar colas de prioridad
    #     sincronizar_colas_iniciales(session)
    #     logger.info("Colas de prioridad sincronizadas")
    # finally:
    #     session.close()

    logger.info("Aplicación iniciada correctamente")

    # # Iniciar proceso automático en background
    # # COMENTADO: Causa errores de conexión IPv6 en Railway
    # task = asyncio.create_task(proceso_automatico())
    # logger.info("Proceso automático iniciado")

    yield

    # # Shutdown
    # task.cancel()
    # try:
    #     await task
    # except asyncio.CancelledError:
    #     pass
    logger.info("Aplicación detenida")


def create_app() -> FastAPI:
    """Factory para crear la aplicación FastAPI."""
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        lifespan=lifespan
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    
    # Montar directorio de uploads
    if os.path.exists(settings.UPLOAD_DIR):
        app.mount(
            "/uploads", 
            StaticFiles(directory=settings.UPLOAD_DIR), 
            name="uploads"
        )
    
    # Incluir routers
    app.include_router(api_router, prefix="/api")
    
    # Endpoint de health check
    @app.get("/health")
    def health_check():
        return {"status": "healthy", "version": settings.APP_VERSION}
    
    return app


# Crear instancia de la aplicación
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
