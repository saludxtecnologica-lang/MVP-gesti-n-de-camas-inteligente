"""
Configuración de Base de Datos.
Gestión de conexiones y sesiones SQLModel.
"""
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
from app.config import settings


# Crear engine con configuración según tipo de base de datos
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=connect_args
)


def create_db_and_tables() -> None:
    """
    Crea todas las tablas en la base de datos.
    Se llama al inicio de la aplicación.
    """
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """
    Generador de sesiones para dependency injection en FastAPI.
    
    Uso:
        @app.get("/endpoint")
        def endpoint(session: Session = Depends(get_session)):
            ...
    """
    with Session(engine) as session:
        yield session


def get_session_direct() -> Session:
    """
    Obtiene una sesión directa (no generator).
    Útil para tareas en background y scripts.
    
    IMPORTANTE: El caller es responsable de cerrar la sesión.
    
    Uso:
        session = get_session_direct()
        try:
            # operaciones
        finally:
            session.close()
    """
    return Session(engine)