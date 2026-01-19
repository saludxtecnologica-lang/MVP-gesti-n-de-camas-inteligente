"""
Script para crear usuarios de prueba.
Ejecutar con: python -m app.utils.seed_users

O importar la función e incluirla en init_data.py
"""

import uuid
from datetime import datetime
from typing import Optional

# Importar desde el módulo existente
from app.core.database import get_session
from app.models.usuario import Usuario, RolEnum


# ============================================
# USUARIOS DE PRUEBA
# ============================================
# IMPORTANTE: Estas son credenciales de desarrollo/demo
# En producción, crear usuarios con credenciales seguras

USUARIOS_PRUEBA = [
    {
        "username": "admin",
        "email": "admin@hospital.cl",
        "password": "Admin123!",
        "nombre_completo": "Administrador Sistema",
        "rol": RolEnum.ADMINISTRADOR
    },
    {
        "username": "gestor",
        "email": "gestor@hospital.cl",
        "password": "Gestor123!",
        "nombre_completo": "Gestor Camas",
        "rol": RolEnum.GESTOR_CAMAS
    },
    {
        "username": "medico",
        "email": "medico@hospital.cl",
        "password": "Medico123!",
        "nombre_completo": "Dr. Juan Pérez",
        "rol": RolEnum.MEDICO
    },
    {
        "username": "enfermera",
        "email": "enfermera@hospital.cl",
        "password": "Enfermera123!",
        "nombre_completo": "Enf. María González",
        "rol": RolEnum.ENFERMERA
    }
]


def hash_password(password: str) -> str:
    """Hash de contraseña usando passlib."""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)


def crear_usuarios_prueba(session) -> list[Usuario]:
    """
    Crea usuarios de prueba en la base de datos.
    Si el usuario ya existe (por username), lo omite.
    """
    usuarios_creados = []
    
    for data in USUARIOS_PRUEBA:
        # Verificar si ya existe
        from sqlmodel import select
        existing = session.exec(
            select(Usuario).where(Usuario.username == data["username"])
        ).first()
        
        if existing:
            print(f"  Usuario '{data['username']}' ya existe, omitiendo...")
            continue
        
        # Crear usuario
        usuario = Usuario(
            id=str(uuid.uuid4()),
            username=data["username"],
            email=data["email"],
            hashed_password=hash_password(data["password"]),
            nombre_completo=data["nombre_completo"],
            rol=data["rol"],
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        session.add(usuario)
        usuarios_creados.append(usuario)
        print(f"  ✓ Usuario '{data['username']}' creado")
    
    session.commit()
    return usuarios_creados


def inicializar_usuarios(session) -> None:
    """
    Función para llamar desde init_data.py
    """
    print("\n📦 Inicializando usuarios de prueba...")
    usuarios = crear_usuarios_prueba(session)
    print(f"   {len(usuarios)} usuarios creados")


def imprimir_credenciales():
    """Imprime tabla de credenciales."""
    print("\n" + "="*60)
    print("CREDENCIALES DE USUARIOS DE PRUEBA")
    print("="*60)
    print(f"{'ROL':<20} {'USUARIO':<15} {'CONTRASEÑA':<15}")
    print("-"*60)
    for u in USUARIOS_PRUEBA:
        print(f"{u['rol'].value:<20} {u['username']:<15} {u['password']:<15}")
    print("="*60 + "\n")


# ============================================
# EJECUCIÓN DIRECTA
# ============================================

if __name__ == "__main__":
    print("Creando usuarios de prueba...")
    
    # Obtener sesión
    with next(get_session()) as session:
        crear_usuarios_prueba(session)
    
    imprimir_credenciales()
    print("¡Usuarios creados exitosamente!")
