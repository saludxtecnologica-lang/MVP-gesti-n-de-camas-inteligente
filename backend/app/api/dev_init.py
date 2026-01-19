"""
Endpoint temporal para inicializar usuarios.
Solo para desarrollo - ELIMINAR EN PRODUCCIÓN
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.usuario import Usuario, RolEnum
from passlib.context import CryptContext

router = APIRouter(prefix="/dev", tags=["dev"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Usuarios básicos para pruebas
USUARIOS_BASICOS = [
    {
        "username": "programador",
        "email": "programador@hospital.cl",
        "password": "Programador123!",
        "nombre_completo": "Equipo Programador",
        "rol": RolEnum.PROGRAMADOR,
    },
    {
        "username": "gestor_camas",
        "email": "gestor.camas@hospital.cl",
        "password": "GestorCamas123!",
        "nombre_completo": "Gestor de Camas",
        "rol": RolEnum.GESTOR_CAMAS,
    },
    {
        "username": "directivo_red",
        "email": "directivo.red@hospital.cl",
        "password": "DirectivoRed123!",
        "nombre_completo": "Director de Red",
        "rol": RolEnum.DIRECTIVO_RED,
    },
]


@router.post("/init-users")
def init_users(session: Session = Depends(get_session)):
    """
    Crea usuarios de prueba si no existen.
    ⚠️ SOLO PARA DESARROLLO - ELIMINAR EN PRODUCCIÓN
    """
    created_users = []

    for user_data in USUARIOS_BASICOS:
        # Verificar si ya existe
        existing = session.exec(
            select(Usuario).where(Usuario.username == user_data["username"])
        ).first()

        if existing:
            continue

        # Crear usuario
        usuario = Usuario(
            username=user_data["username"],
            email=user_data["email"],
            hashed_password=pwd_context.hash(user_data["password"]),
            nombre_completo=user_data["nombre_completo"],
            rol=user_data["rol"],
            is_active=True,
            is_verified=True,
        )

        session.add(usuario)
        created_users.append(user_data["username"])

    session.commit()

    return {
        "status": "success",
        "created_users": created_users,
        "message": f"Creados {len(created_users)} usuarios"
    }
