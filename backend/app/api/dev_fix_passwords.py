"""
Endpoint temporal para corregir contraseñas hasheadas incorrectamente.
Solo para desarrollo - ELIMINAR EN PRODUCCIÓN
"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, text
from passlib.context import CryptContext

from app.core.database import get_session

router = APIRouter(prefix="/dev/fix", tags=["dev-fix-passwords"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Credenciales originales de los usuarios de prueba
USUARIOS_PASSWORDS = {
    "programador": "Programador123!",
    "gestor_camas": "GestorCamas123!",
    "director_red": "Director123!",
    "dr_flores": "Medico123!",
    "enfermera_torres": "Enfermera123!",
    "tens_lopez": "Tens123!",
}


@router.get("/fix-passwords")
@router.post("/fix-passwords")
def fix_passwords(session: Session = Depends(get_session)):
    """
    Rehashea todas las contraseñas de los usuarios de prueba.
    ⚠️ SOLO PARA DESARROLLO - EJECUTAR UNA SOLA VEZ

    Disponible como GET y POST para facilitar ejecución desde navegador.
    """
    import bcrypt

    updated_users = []
    errors = []

    try:
        for username, plain_password in USUARIOS_PASSWORDS.items():
            try:
                # Generar hash correcto usando bcrypt directamente
                # Convertir a bytes y hashear
                password_bytes = plain_password.encode('utf-8')
                salt = bcrypt.gensalt()
                hashed_pwd = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

                # Actualizar contraseña usando SQL directo
                update_sql = text("""
                    UPDATE usuarios
                    SET hashed_password = :hashed_pwd, updated_at = CURRENT_TIMESTAMP
                    WHERE username = :username
                """)

                result = session.execute(update_sql, {
                    "hashed_pwd": hashed_pwd,
                    "username": username
                })

                if result.rowcount > 0:
                    updated_users.append({
                        "username": username,
                        "password": plain_password,
                        "hash_length": len(hashed_pwd),
                        "hash_prefix": hashed_pwd[:7]
                    })
                else:
                    errors.append({
                        "username": username,
                        "error": "Usuario no encontrado en BD"
                    })

            except Exception as e:
                errors.append({
                    "username": username,
                    "error": str(e)
                })

        # Commit de cambios
        if updated_users:
            session.commit()

        return {
            "status": "success" if not errors else "partial",
            "updated_count": len(updated_users),
            "updated_users": updated_users,
            "errors": errors if errors else None,
            "message": f"✅ Actualizados {len(updated_users)} usuarios con contraseñas correctas"
        }

    except Exception as e:
        session.rollback()
        return {
            "status": "error",
            "message": "Error al actualizar contraseñas",
            "error": str(e)
        }


@router.get("/check-password-hashes")
def check_password_hashes(session: Session = Depends(get_session)):
    """
    Verifica el estado de los hashes de contraseña.
    ⚠️ SOLO PARA DESARROLLO
    """
    try:
        result = session.exec(text("""
            SELECT username,
                   LENGTH(hashed_password) as hash_length,
                   SUBSTRING(hashed_password, 1, 7) as hash_prefix
            FROM usuarios
            ORDER BY username
        """))

        users = []
        for row in result:
            username, hash_length, hash_prefix = row[0], row[1], row[2]

            # Bcrypt hashes válidos empiezan con $2b$ o $2a$ y tienen ~60 chars
            is_valid_format = hash_prefix.startswith('$2') if hash_prefix else False

            users.append({
                "username": username,
                "hash_length": hash_length,
                "hash_prefix": hash_prefix,
                "looks_valid": is_valid_format and hash_length >= 59
            })

        invalid_count = sum(1 for u in users if not u["looks_valid"])

        return {
            "status": "success",
            "total_users": len(users),
            "invalid_hashes": invalid_count,
            "users": users,
            "needs_fix": invalid_count > 0
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
