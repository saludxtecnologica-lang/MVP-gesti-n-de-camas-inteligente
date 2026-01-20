"""
Endpoint temporal para inicializar usuarios.
Solo para desarrollo - ELIMINAR EN PRODUCCIÓN
"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select, text
from passlib.context import CryptContext
import uuid

from app.core.database import get_session

router = APIRouter(prefix="/dev", tags=["dev"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Usuarios básicos para pruebas
USUARIOS_BASICOS = [
    {
        "username": "programador",
        "email": "programador@hospital.cl",
        "password": "Programador123!",
        "nombre_completo": "Equipo Programador",
        "rol": "PROGRAMADOR",
    },
    {
        "username": "gestor_camas",
        "email": "gestor.camas@hospital.cl",
        "password": "GestorCamas123!",
        "nombre_completo": "Gestor de Camas",
        "rol": "GESTOR_CAMAS",
    },
    {
        "username": "directivo_red",
        "email": "directivo.red@hospital.cl",
        "password": "Director123!",
        "nombre_completo": "Director de Red",
        "rol": "DIRECTIVO_RED",
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
    """Lógica común para crear usuarios usando SQL directo."""
    created_users = []
    errors = []

    try:
        # Verificar usuarios existentes
        try:
            result = session.exec(text("SELECT username FROM usuarios"))
            existing_usernames = [row[0] for row in result]
            existing_count = len(existing_usernames)
        except Exception as e:
            return {
                "status": "error",
                "message": "No se puede leer de la tabla usuarios.",
                "error": str(e),
                "solution": "Verifica RLS o DATABASE_URL"
            }

        # Insertar usuarios con SQL directo (evita validación del modelo)
        for user_data in USUARIOS_BASICOS:
            try:
                # Verificar si ya existe
                if user_data["username"] in existing_usernames:
                    continue

                # Generar ID y hash de contraseña
                user_id = str(uuid.uuid4())
                # Truncar contraseña a 72 bytes (límite de bcrypt)
                password = user_data["password"][:72]
                hashed_pwd = pwd_context.hash(password)

                # INSERT directo con SQL
                sql = text("""
                    INSERT INTO usuarios
                    (id, username, email, hashed_password, nombre_completo, rol, is_active, is_verified, created_at, updated_at)
                    VALUES
                    (:id, :username, :email, :password, :nombre, :rol, true, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """)

                # Usar execute() en lugar de exec() para pasar parámetros
                session.execute(
                    sql,
                    {
                        "id": user_id,
                        "username": user_data["username"],
                        "email": user_data["email"],
                        "password": hashed_pwd,
                        "nombre": user_data["nombre_completo"],
                        "rol": user_data["rol"]
                    }
                )

                created_users.append(user_data["username"])

            except Exception as e:
                errors.append({
                    "username": user_data["username"],
                    "error": str(e)
                })

        # Commit si hay usuarios creados
        if created_users:
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                return {
                    "status": "error",
                    "message": "No se pudo hacer commit.",
                    "error": str(e),
                    "solution": "Verifica RLS en Supabase"
                }

        return {
            "status": "success" if not errors else "partial",
            "created_users": created_users,
            "existing_users": existing_usernames,
            "total_users_in_db": existing_count + len(created_users),
            "errors": errors if errors else None,
            "message": f"✅ Creados {len(created_users)} usuarios. Total: {existing_count + len(created_users)}"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "Error general al crear usuarios",
            "error": str(e),
            "hint": "Verifica RLS, políticas de seguridad, o DATABASE_URL"
        }
