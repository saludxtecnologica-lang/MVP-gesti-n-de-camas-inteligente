#!/usr/bin/env python3
"""
Script de Migración de SQLite a PostgreSQL
Sistema de Gestión de Camas Hospitalarias

Este script migra todos los datos de la base de datos SQLite existente
a la nueva base de datos PostgreSQL.

Uso:
    python scripts/migrate_sqlite_to_postgres.py

Requisitos:
    - Base de datos SQLite existente en gestion_camas.db
    - PostgreSQL configurado y corriendo
    - Variables de entorno configuradas (.env)
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz al PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import create_engine, Session, select
from sqlalchemy import inspect, text
import logging
from typing import List, Dict, Any
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)

# Importar configuración
from app.config import settings

# Importar todos los modelos
from app.models.usuario import Usuario, RefreshToken
from app.models.hospital import Hospital
from app.models.servicio import Servicio
from app.models.sala import Sala
from app.models.cama import Cama
from app.models.paciente import Paciente
from app.models.configuracion import ConfiguracionSistema, LogActividad


# ============================================
# CONFIGURACIÓN
# ============================================

# URL de la base de datos SQLite
SQLITE_URL = "sqlite:///./gestion_camas.db"

# URL de PostgreSQL (desde configuración)
POSTGRES_URL = settings.DATABASE_URL

# Orden de migración (respetando foreign keys)
MIGRATION_ORDER = [
    ("hospital", Hospital),
    ("servicio", Servicio),
    ("sala", Sala),
    ("cama", Cama),
    ("paciente", Paciente),
    ("usuario", Usuario),
    ("refreshtoken", RefreshToken),
    ("configuracionsistema", ConfiguracionSistema),
    ("logactividad", LogActividad),
]


# ============================================
# FUNCIONES DE MIGRACIÓN
# ============================================

def verificar_sqlite_existe() -> bool:
    """Verifica que la base de datos SQLite existe."""
    sqlite_path = Path("gestion_camas.db")
    if not sqlite_path.exists():
        logger.error(f"❌ No se encontró la base de datos SQLite en: {sqlite_path.absolute()}")
        return False
    logger.info(f"✅ Base de datos SQLite encontrada: {sqlite_path.absolute()}")
    return True


def conectar_bases_datos():
    """
    Crea conexiones a ambas bases de datos.

    Returns:
        tuple: (sqlite_engine, postgres_engine)
    """
    logger.info("🔌 Conectando a bases de datos...")

    # SQLite (origen)
    sqlite_engine = create_engine(
        SQLITE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )

    # PostgreSQL (destino)
    postgres_engine = create_engine(
        POSTGRES_URL,
        echo=False,
        pool_pre_ping=True
    )

    logger.info("✅ Conexiones establecidas")
    return sqlite_engine, postgres_engine


def obtener_estadisticas_sqlite(sqlite_engine) -> Dict[str, int]:
    """
    Obtiene estadísticas de la base de datos SQLite.

    Args:
        sqlite_engine: Engine de SQLite

    Returns:
        Dict con conteos por tabla
    """
    logger.info("📊 Obteniendo estadísticas de SQLite...")
    stats = {}

    with Session(sqlite_engine) as session:
        for table_name, model in MIGRATION_ORDER:
            try:
                count = session.exec(select(model)).all()
                stats[table_name] = len(count)
                logger.info(f"   {table_name}: {len(count)} registros")
            except Exception as e:
                logger.warning(f"   ⚠️  {table_name}: Error al contar - {e}")
                stats[table_name] = 0

    return stats


def migrar_tabla(
    table_name: str,
    model: Any,
    sqlite_session: Session,
    postgres_session: Session
) -> int:
    """
    Migra una tabla específica de SQLite a PostgreSQL.

    Args:
        table_name: Nombre de la tabla
        model: Modelo SQLModel
        sqlite_session: Sesión de SQLite
        postgres_session: Sesión de PostgreSQL

    Returns:
        Número de registros migrados
    """
    logger.info(f"🔄 Migrando tabla: {table_name}...")

    try:
        # Obtener todos los registros de SQLite
        registros = sqlite_session.exec(select(model)).all()

        if not registros:
            logger.info(f"   ℹ️  Tabla vacía, saltando")
            return 0

        # Insertar en PostgreSQL
        migrados = 0
        errores = 0

        for registro in registros:
            try:
                # Crear una copia del registro
                registro_dict = registro.dict()

                # Crear nuevo registro
                nuevo_registro = model(**registro_dict)

                # Agregar a PostgreSQL
                postgres_session.add(nuevo_registro)
                migrados += 1

                # Commit cada 100 registros para evitar transacciones muy grandes
                if migrados % 100 == 0:
                    postgres_session.commit()
                    logger.info(f"   ⏳ {migrados}/{len(registros)} migrados...")

            except Exception as e:
                errores += 1
                logger.warning(f"   ⚠️  Error al migrar registro: {e}")
                postgres_session.rollback()

        # Commit final
        postgres_session.commit()

        logger.info(f"   ✅ {migrados} registros migrados ({errores} errores)")
        return migrados

    except Exception as e:
        logger.error(f"   ❌ Error al migrar tabla {table_name}: {e}")
        postgres_session.rollback()
        return 0


def actualizar_secuencias_postgres(postgres_engine):
    """
    Actualiza las secuencias de PostgreSQL para que continúen desde el último ID.

    Args:
        postgres_engine: Engine de PostgreSQL
    """
    logger.info("🔢 Actualizando secuencias de PostgreSQL...")

    with Session(postgres_engine) as session:
        # Obtener todas las tablas
        inspector = inspect(postgres_engine)
        tablas = inspector.get_table_names()

        for tabla in tablas:
            try:
                # Intentar actualizar la secuencia
                # Esto funcionará para tablas con columnas id seriales/identity
                query = text(f"""
                    SELECT setval(
                        pg_get_serial_sequence('{tabla}', 'id'),
                        COALESCE((SELECT MAX(id) FROM {tabla}), 1),
                        false
                    )
                """)
                session.execute(query)
                logger.debug(f"   ✅ Secuencia actualizada: {tabla}")
            except Exception:
                # Ignorar tablas que no tienen secuencia
                pass

        session.commit()

    logger.info("✅ Secuencias actualizadas")


def verificar_integridad(sqlite_engine, postgres_engine) -> bool:
    """
    Verifica que los datos se migraron correctamente.

    Args:
        sqlite_engine: Engine de SQLite
        postgres_engine: Engine de PostgreSQL

    Returns:
        True si la verificación pasa, False en caso contrario
    """
    logger.info("🔍 Verificando integridad de datos migrados...")

    todo_ok = True

    with Session(sqlite_engine) as sqlite_session, Session(postgres_engine) as postgres_session:
        for table_name, model in MIGRATION_ORDER:
            try:
                count_sqlite = len(sqlite_session.exec(select(model)).all())
                count_postgres = len(postgres_session.exec(select(model)).all())

                if count_sqlite == count_postgres:
                    logger.info(f"   ✅ {table_name}: {count_sqlite} registros")
                else:
                    logger.error(
                        f"   ❌ {table_name}: SQLite={count_sqlite}, "
                        f"PostgreSQL={count_postgres}"
                    )
                    todo_ok = False

            except Exception as e:
                logger.error(f"   ❌ Error al verificar {table_name}: {e}")
                todo_ok = False

    return todo_ok


# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

def main():
    """Función principal del script de migración."""

    logger.info("=" * 60)
    logger.info("🏥 MIGRACIÓN DE SQLITE A POSTGRESQL")
    logger.info("Sistema de Gestión de Camas Hospitalarias")
    logger.info("=" * 60)
    logger.info("")

    # Paso 1: Verificar que SQLite existe
    if not verificar_sqlite_existe():
        logger.error("❌ Abortando migración")
        return 1

    # Paso 2: Conectar a bases de datos
    try:
        sqlite_engine, postgres_engine = conectar_bases_datos()
    except Exception as e:
        logger.error(f"❌ Error al conectar a bases de datos: {e}")
        return 1

    # Paso 3: Obtener estadísticas
    stats_sqlite = obtener_estadisticas_sqlite(sqlite_engine)
    total_registros = sum(stats_sqlite.values())

    if total_registros == 0:
        logger.warning("⚠️  La base de datos SQLite está vacía. Nada que migrar.")
        return 0

    logger.info(f"📊 Total de registros a migrar: {total_registros}")
    logger.info("")

    # Paso 4: Confirmar migración
    print("⚠️  IMPORTANTE: Esta operación insertará datos en PostgreSQL")
    print("   Asegúrate de que la base de datos PostgreSQL esté vacía o")
    print("   que no haya conflictos de IDs.")
    print("")
    respuesta = input("¿Deseas continuar con la migración? (si/no): ")

    if respuesta.lower() not in ['si', 's', 'yes', 'y']:
        logger.info("❌ Migración cancelada por el usuario")
        return 0

    logger.info("")
    logger.info("🚀 Iniciando migración...")
    logger.info("")

    # Paso 5: Migrar tablas
    inicio = datetime.now()
    total_migrados = 0

    with Session(sqlite_engine) as sqlite_session, Session(postgres_engine) as postgres_session:
        for table_name, model in MIGRATION_ORDER:
            migrados = migrar_tabla(table_name, model, sqlite_session, postgres_session)
            total_migrados += migrados
            logger.info("")

    # Paso 6: Actualizar secuencias
    actualizar_secuencias_postgres(postgres_engine)
    logger.info("")

    # Paso 7: Verificar integridad
    integridad_ok = verificar_integridad(sqlite_engine, postgres_engine)
    logger.info("")

    # Paso 8: Resultados finales
    fin = datetime.now()
    duracion = (fin - inicio).total_seconds()

    logger.info("=" * 60)
    logger.info("📊 RESUMEN DE MIGRACIÓN")
    logger.info("=" * 60)
    logger.info(f"Total de registros migrados: {total_migrados}")
    logger.info(f"Tiempo de migración: {duracion:.2f} segundos")
    logger.info(f"Integridad de datos: {'✅ OK' if integridad_ok else '❌ ERRORES'}")
    logger.info("=" * 60)

    if integridad_ok:
        logger.info("")
        logger.info("🎉 ¡Migración completada exitosamente!")
        logger.info("")
        logger.info("📝 Próximos pasos:")
        logger.info("   1. Verificar que la aplicación funciona con PostgreSQL")
        logger.info("   2. Hacer backup de la base de datos PostgreSQL")
        logger.info("   3. Considerar eliminar gestion_camas.db (después de verificar)")
        return 0
    else:
        logger.error("")
        logger.error("❌ La migración completó con errores")
        logger.error("   Revisa los logs anteriores para más detalles")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Migración interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
