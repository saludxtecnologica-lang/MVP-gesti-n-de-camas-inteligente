"""
Configuración del entorno de Alembic para migraciones.
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar modelos para que Alembic los detecte
from sqlmodel import SQLModel
from app.models import (
    Hospital,
    Servicio,
    Sala,
    Cama,
    Paciente,
    ConfiguracionSistema,
    LogActividad,
)
from app.config import settings

# Configuración de Alembic
config = context.config

# Configurar logging desde alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata de los modelos para autogenerate
target_metadata = SQLModel.metadata

# URL de la base de datos
def get_url():
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """
    Ejecuta migraciones en modo 'offline'.
    
    Genera scripts SQL sin conectar a la base de datos.
    Útil para generar scripts de migración para revisar.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Ejecuta migraciones en modo 'online'.
    
    Se conecta a la base de datos y aplica las migraciones.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            # Para SQLite, usar batch mode
            render_as_batch=True if "sqlite" in get_url() else False,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
