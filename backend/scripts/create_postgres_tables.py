#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear las tablas en PostgreSQL.
Importa todos los modelos antes de crear las tablas.
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

# IMPORTANTE: Importar TODOS los modelos ANTES de crear las tablas
# SQLModel necesita que los modelos estén importados para saber qué tablas crear
from app.models.usuario import Usuario, RefreshToken
from app.models.hospital import Hospital
from app.models.servicio import Servicio
from app.models.sala import Sala
from app.models.cama import Cama
from app.models.paciente import Paciente
from app.models.configuracion import ConfiguracionSistema, LogActividad

# Ahora importar la función para crear tablas
from app.core.database import create_db_and_tables

print("=" * 60)
print("Creando tablas en PostgreSQL...")
print("=" * 60)
print("")
print("Modelos importados:")
print("  - Usuario, RefreshToken")
print("  - Hospital")
print("  - Servicio")
print("  - Sala")
print("  - Cama")
print("  - Paciente")
print("  - ConfiguracionSistema, LogActividad")
print("")
print("Creando tablas...")

try:
    create_db_and_tables()
    print("")
    print("=" * 60)
    print("✅ Tablas creadas exitosamente en PostgreSQL")
    print("=" * 60)
    print("")
    print("Próximo paso:")
    print("  python scripts/migrate_sqlite_to_postgres.py")
    print("")
except Exception as e:
    print("")
    print("=" * 60)
    print(f"❌ Error al crear tablas: {e}")
    print("=" * 60)
    import traceback
    traceback.print_exc()
    sys.exit(1)
