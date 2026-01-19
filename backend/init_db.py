#!/usr/bin/env python3
"""
Script para inicializar la base de datos con datos de prueba.
Ejecutar con: python init_db.py
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import get_session_direct
from app.utils.init_data import inicializar_datos

def main():
    """Inicializar base de datos con datos de prueba."""
    print("=" * 60)
    print("INICIALIZANDO BASE DE DATOS")
    print("=" * 60)

    session = get_session_direct()
    try:
        print("\n📦 Creando datos iniciales...")
        inicializar_datos(session)
        print("\n✅ ¡Base de datos inicializada exitosamente!")
        print("\n" + "=" * 60)
        print("CREDENCIALES DE ACCESO")
        print("=" * 60)
        print("\nAdministrador:")
        print("  Usuario: admin")
        print("  Contraseña: Admin123!")
        print("\nGestor de Camas:")
        print("  Usuario: gestor")
        print("  Contraseña: Gestor123!")
        print("\nMédico:")
        print("  Usuario: medico")
        print("  Contraseña: Medico123!")
        print("\nEnfermera:")
        print("  Usuario: enfermera")
        print("  Contraseña: Enfermera123!")
        print("\n" + "=" * 60)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    main()
