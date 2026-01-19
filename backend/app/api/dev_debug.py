"""
Endpoint temporal para diagnosticar problemas de login.
Solo para desarrollo - ELIMINAR EN PRODUCCIÓN
"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select, text
from passlib.context import CryptContext

from app.core.database import get_session
from app.models.usuario import Usuario

router = APIRouter(prefix="/dev/debug", tags=["dev-debug"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/check-user/{username}")
def check_user(username: str, session: Session = Depends(get_session)):
    """
    Verifica si un usuario existe y puede ser encontrado.
    ⚠️ SOLO PARA DESARROLLO - ELIMINAR EN PRODUCCIÓN
    """
    try:
        # Buscar como lo hace auth_service
        statement = select(Usuario).where(
            (Usuario.username == username.lower()) |
            (Usuario.email == username.lower())
        )
        user = session.exec(statement).first()

        if not user:
            return {
                "status": "not_found",
                "message": f"Usuario '{username}' no encontrado",
                "searched_as": username.lower()
            }

        return {
            "status": "found",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "nombre_completo": user.nombre_completo,
                "rol": user.rol,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "has_password": bool(user.hashed_password),
                "password_length": len(user.hashed_password) if user.hashed_password else 0
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Error al buscar usuario"
        }


@router.post("/test-login")
def test_login(username: str, password: str, session: Session = Depends(get_session)):
    """
    Prueba el proceso de login paso a paso.
    ⚠️ SOLO PARA DESARROLLO - ELIMINAR EN PRODUCCIÓN
    """
    result = {
        "steps": []
    }

    try:
        # Paso 1: Buscar usuario
        result["steps"].append({"step": 1, "action": "Buscando usuario", "username": username.lower()})

        statement = select(Usuario).where(
            (Usuario.username == username.lower()) |
            (Usuario.email == username.lower())
        )
        user = session.exec(statement).first()

        if not user:
            result["steps"].append({"step": 2, "action": "Usuario no encontrado", "success": False})
            result["status"] = "user_not_found"
            return result

        result["steps"].append({
            "step": 2,
            "action": "Usuario encontrado",
            "success": True,
            "user": {
                "username": user.username,
                "email": user.email,
                "rol": user.rol,
                "is_active": user.is_active
            }
        })

        # Paso 2: Verificar is_active
        if not user.is_active:
            result["steps"].append({"step": 3, "action": "Usuario inactivo", "success": False})
            result["status"] = "user_inactive"
            return result

        result["steps"].append({"step": 3, "action": "Usuario activo", "success": True})

        # Paso 3: Verificar contraseña
        password_match = pwd_context.verify(password, user.hashed_password)

        result["steps"].append({
            "step": 4,
            "action": "Verificando contraseña",
            "success": password_match,
            "password_length": len(password),
            "hash_length": len(user.hashed_password) if user.hashed_password else 0
        })

        if not password_match:
            result["status"] = "password_mismatch"
            return result

        result["status"] = "success"
        result["message"] = "Login debería funcionar correctamente"

        return result

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        return result


@router.get("/list-all-users")
def list_all_users(session: Session = Depends(get_session)):
    """
    Lista todos los usuarios con información básica.
    ⚠️ SOLO PARA DESARROLLO - ELIMINAR EN PRODUCCIÓN
    """
    try:
        result = session.exec(text("SELECT username, email, rol, is_active FROM usuarios"))
        users = [
            {
                "username": row[0],
                "email": row[1],
                "rol": row[2],
                "is_active": row[3]
            }
            for row in result
        ]

        return {
            "status": "success",
            "total_users": len(users),
            "users": users
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
