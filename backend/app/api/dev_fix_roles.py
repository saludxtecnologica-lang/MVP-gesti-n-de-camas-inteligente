"""
Endpoint temporal para corregir roles en minúsculas.
Solo para desarrollo - ELIMINAR EN PRODUCCIÓN
"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, text

from app.core.database import get_session

router = APIRouter(prefix="/dev/fix", tags=["dev-fix"])


# Mapeo de roles minúsculas -> MAYÚSCULAS
ROLE_MAPPING = {
    "programador": "PROGRAMADOR",
    "gestor_camas": "GESTOR_CAMAS",
    "directivo_red": "DIRECTIVO_RED",
    "directivo_hospital": "DIRECTIVO_HOSPITAL",
    "médico": "MEDICO",
    "enfermera": "ENFERMERA",
    "tens": "TENS",
    "administrativo": "ADMINISTRATIVO",
    "visualizador": "VISUALIZADOR",
    "farmacia": "FARMACIA",
    "laboratorio": "LABORATORIO",
    "imagenologia": "IMAGENOLOGIA",
    "kinesiologia": "KINESIOLOGIA",
    "nutricion": "NUTRICION",
    "trabajo_social": "TRABAJO_SOCIAL",
    "limpieza": "LIMPIEZA",
}


@router.get("/update-roles-to-uppercase")
@router.post("/update-roles-to-uppercase")
def update_roles_to_uppercase(session: Session = Depends(get_session)):
    """
    Actualiza todos los roles de minúsculas a MAYÚSCULAS.
    ⚠️ SOLO PARA DESARROLLO - EJECUTAR UNA SOLA VEZ

    Disponible como GET y POST para facilitar ejecución desde navegador.
    """
    updated_users = []
    errors = []

    try:
        # Obtener todos los usuarios con sus roles actuales
        result = session.exec(text("SELECT id, username, rol FROM usuarios"))
        users = [(row[0], row[1], row[2]) for row in result]

        for user_id, username, current_rol in users:
            try:
                # Buscar el mapeo correcto
                new_rol = ROLE_MAPPING.get(current_rol)

                if not new_rol:
                    # Si el rol ya está en mayúsculas o no está en el mapeo, omitir
                    continue

                # Actualizar el rol usando SQL directo
                update_sql = text("""
                    UPDATE usuarios
                    SET rol = :new_rol, updated_at = CURRENT_TIMESTAMP
                    WHERE id = :user_id
                """)

                session.exec(update_sql, {"new_rol": new_rol, "user_id": user_id})

                updated_users.append({
                    "username": username,
                    "old_rol": current_rol,
                    "new_rol": new_rol
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
            "message": f"✅ Actualizados {len(updated_users)} roles a MAYÚSCULAS"
        }

    except Exception as e:
        session.rollback()
        return {
            "status": "error",
            "message": "Error al actualizar roles",
            "error": str(e)
        }


@router.get("/check-roles-status")
def check_roles_status(session: Session = Depends(get_session)):
    """
    Verifica el estado de los roles en la BD.
    ⚠️ SOLO PARA DESARROLLO
    """
    try:
        result = session.exec(text("SELECT username, rol FROM usuarios ORDER BY username"))
        users = [{"username": row[0], "rol": row[1]} for row in result]

        # Contar roles en minúsculas vs mayúsculas
        lowercase_count = sum(1 for u in users if u["rol"] and u["rol"].islower())
        uppercase_count = sum(1 for u in users if u["rol"] and u["rol"].isupper())
        mixed_count = len(users) - lowercase_count - uppercase_count

        return {
            "status": "success",
            "total_users": len(users),
            "lowercase_roles": lowercase_count,
            "uppercase_roles": uppercase_count,
            "mixed_case_roles": mixed_count,
            "users": users,
            "needs_update": lowercase_count > 0 or mixed_count > 0
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
