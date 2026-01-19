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


@router.get("/init-users")
def init_users_get(session: Session = Depends(get_session)):
    """
    Crea usuarios de prueba si no existen.
    ⚠️ SOLO PARA DESARROLLO - ELIMINAR EN PRODUCCIÓN

    GET endpoint para facilitar pruebas desde navegador.
    """
    return _create_users(session)


@router.post("/init-users")
def init_users_post(session: Session = Depends(get_session)):
    """
    Crea usuarios de prueba si no existen.
    ⚠️ SOLO PARA DESARROLLO - ELIMINAR EN PRODUCCIÓN
    """
    return _create_users(session)


def _create_users(session: Session):
    """Lógica común para crear usuarios."""
    created_users = []
    errors = []

    try:
        # Primero verificar si podemos leer de la tabla
        try:
            existing_users = session.exec(select(Usuario)).all()
            existing_count = len(existing_users)
            existing_usernames = [u.username for u in existing_users]
        except Exception as e:
            return {
                "status": "error",
                "message": "No se puede leer de la tabla usuarios. Probablemente RLS está bloqueando.",
                "error": str(e),
                "solution": "Verifica que RLS esté deshabilitado en Supabase o que uses SUPABASE_SERVICE_ROLE_KEY"
            }

        for user_data in USUARIOS_BASICOS:
            try:
                # Verificar si ya existe
                if user_data["username"] in existing_usernames:
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

            except Exception as e:
                errors.append({
                    "username": user_data["username"],
                    "error": str(e)
                })

        if created_users:
            try:
                session.commit()
            except Exception as e:
                return {
                    "status": "error",
                    "message": "No se pudo hacer commit. Probablemente RLS está bloqueando INSERT.",
                    "error": str(e),
                    "solution": "Deshabilita RLS en la tabla 'usuarios' en Supabase Dashboard"
                }

        return {
            "status": "success" if not errors else "partial",
            "created_users": created_users,
            "existing_users": existing_usernames,
            "total_users_in_db": existing_count + len(created_users),
            "errors": errors if errors else None,
            "message": f"✅ Creados {len(created_users)} usuarios nuevos. Total en DB: {existing_count + len(created_users)}"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "Error general al crear usuarios",
            "error": str(e),
            "hint": "Verifica RLS en Supabase, políticas de seguridad, o la configuración de DATABASE_URL"
        }
