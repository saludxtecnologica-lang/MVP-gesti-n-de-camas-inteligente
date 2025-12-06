"""
Configuración de Base de Datos para el Sistema de Gestión de Camas.
"""

from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import os

# Configuración de la base de datos
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gestion_camas.db")

# Crear engine
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)


def create_db_and_tables():
    """Crea todas las tablas en la base de datos"""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Generador de sesiones para dependency injection"""
    with Session(engine) as session:
        yield session


def get_session_direct() -> Session:
    """Obtiene una sesión directa (no generator)"""
    return Session(engine)