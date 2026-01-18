#!/usr/bin/env python3
"""
Script para crear las tablas en PostgreSQL
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import create_db_and_tables
from app.utils.logger import logger

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Creando tablas en PostgreSQL...")
    logger.info("=" * 60)
    
    try:
        create_db_and_tables()
        logger.info("=" * 60)
        logger.info("? Tablas creadas exitosamente")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"? Error al crear tablas: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
