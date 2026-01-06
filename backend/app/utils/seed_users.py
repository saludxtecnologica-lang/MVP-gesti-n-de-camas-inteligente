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

USUARIOS_PRUEBA = [
    {
        "username": "superadmin",
        "email": "superadmin@hospital.cl",
        "password": "SuperAdmin123!",
        "nombre_completo": "Super Administrador",
        "rol": RolEnum.SUPER_ADMIN,
    },
    {
        "username": "admin",
        "email": "admin@hospital.cl",
        "password": "Admin123!",
        "nombre_completo": "Administrador Sistema",
        "rol": RolEnum.ADMIN,
    },
    {
        "username": "gestor",
        "email": "gestor@hospital.cl",
        "password": "Gestor123!",
        "nombre_completo": "María González Pérez",
        "rol": RolEnum.GESTOR_CAMAS,
    },
    {
        "username": "coordinador",
        "email": "coordinador@hospital.cl",
        "password": "Coord123!",
        "nombre_completo": "Carlos Muñoz Silva",
        "rol": RolEnum.COORDINADOR_CAMAS,
    },
    {
        "username": "medico",
        "email": "medico@hospital.cl",
        "password": "Medico123!",
        "nombre_completo": "Dr. Roberto Sánchez",
        "rol": RolEnum.MEDICO,
    },
    {
        "username": "jefe_medicina",
        "email": "jefe.medicina@hospital.cl",
        "password": "JefeServ123!",
        "nombre_completo": "Dra. Patricia Vera",
        "rol": RolEnum.JEFE_SERVICIO,
    },
    {
        "username": "enfermera",
        "email": "enfermera@hospital.cl",
        "password": "Enfermera123!",
        "nombre_completo": "Ana María López",
        "rol": RolEnum.ENFERMERA,
    },
    {
        "username": "supervisora",
        "email": "supervisora@hospital.cl",
        "password": "Superv123!",
        "nombre_completo": "Carmen Díaz Rojas",
        "rol": RolEnum.SUPERVISORA_ENFERMERIA,
    },
    {
        "username": "urgencias",
        "email": "urgencias@hospital.cl",
        "password": "Urgencias123!",
        "nombre_completo": "Pedro Martínez",
        "rol": RolEnum.URGENCIAS,
    },
    {
        "username": "jefe_urgencias",
        "email": "jefe.urgencias@hospital.cl",
        "password": "JefeUrg123!",
        "nombre_completo": "Dr. Luis Fernández",
        "rol": RolEnum.JEFE_URGENCIAS,
    },
    {
        "username": "derivaciones",
        "email": "derivaciones@hospital.cl",
        "password": "Deriv123!",
        "nombre_completo": "Sofía Ramírez",
        "rol": RolEnum.DERIVACIONES,
    },
    {
        "username": "coordinador_red",
        "email": "coordinador.red@hospital.cl",
        "password": "CoordRed123!",
        "nombre_completo": "Miguel Torres",
        "rol": RolEnum.COORDINADOR_RED,
    },
    {
        "username": "ambulatorio",
        "email": "ambulatorio@hospital.cl",
        "password": "Ambul123!",
        "nombre_completo": "Claudia Herrera",
        "rol": RolEnum.AMBULATORIO,
    },
    {
        "username": "estadisticas",
        "email": "estadisticas@hospital.cl",
        "password": "Stats123!",
        "nombre_completo": "Felipe Castro",
        "rol": RolEnum.ESTADISTICAS,
    },
    {
        "username": "visualizador",
        "email": "visualizador@hospital.cl",
        "password": "View123!",
        "nombre_completo": "Usuario Visualizador",
        "rol": RolEnum.VISUALIZADOR,
    },
    {
        "username": "operador",
        "email": "operador@hospital.cl",
        "password": "Operador123!",
        "nombre_completo": "Operador Sistema",
        "rol": RolEnum.OPERADOR,
    },
    {
        "username": "limpieza",
        "email": "limpieza@hospital.cl",
        "password": "Limpieza123!",
        "nombre_completo": "Personal Limpieza",
        "rol": RolEnum.LIMPIEZA,
    },
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
