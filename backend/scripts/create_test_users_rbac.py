"""
Script para crear usuarios de prueba del sistema RBAC multinivel.

Crea usuarios para cada perfil con credenciales de prueba.
"""
import sys
import asyncio
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, create_engine, select
from app.models.usuario import Usuario, RolEnum
from app.services.auth_service import auth_service
from app.config import settings


# Configuración de usuarios de prueba
USUARIOS_PRUEBA = [
    # ========== CAPA 1: ADMINISTRACIÓN Y RED (NIVEL GLOBAL) ==========
    {
        "username": "programador",
        "email": "programador@hospital.cl",
        "password": "Programador123!",
        "nombre_completo": "Equipo Programador",
        "rol": RolEnum.PROGRAMADOR,
        "hospital_id": None,
        "servicio_id": None,
    },
    {
        "username": "directivo_red",
        "email": "directivo.red@hospital.cl",
        "password": "DirectivoRed123!",
        "nombre_completo": "Director de Red",
        "rol": RolEnum.DIRECTIVO_RED,
        "hospital_id": None,  # Acceso a todos los hospitales
        "servicio_id": None,
    },

    # ========== CAPA 2: GESTIÓN LOCAL (NIVEL HOSPITALARIO) ==========
    {
        "username": "directivo_hospital_pm",
        "email": "directivo.pm@hospital.cl",
        "password": "DirectivoPM123!",
        "nombre_completo": "Director Hospital Puerto Montt",
        "rol": RolEnum.DIRECTIVO_HOSPITAL,
        "hospital_id": "puerto_montt",
        "servicio_id": None,
    },
    {
        "username": "directivo_hospital_ll",
        "email": "directivo.ll@hospital.cl",
        "password": "DirectivoLL123!",
        "nombre_completo": "Director Hospital Llanquihue",
        "rol": RolEnum.DIRECTIVO_HOSPITAL,
        "hospital_id": "llanquihue",
        "servicio_id": None,
    },
    {
        "username": "directivo_hospital_cal",
        "email": "directivo.cal@hospital.cl",
        "password": "DirectivoCal123!",
        "nombre_completo": "Director Hospital Calbuco",
        "rol": RolEnum.DIRECTIVO_HOSPITAL,
        "hospital_id": "calbuco",
        "servicio_id": None,
    },
    {
        "username": "gestor_camas",
        "email": "gestor.camas@hospital.cl",
        "password": "GestorCamas123!",
        "nombre_completo": "Gestor de Camas Puerto Montt",
        "rol": RolEnum.GESTOR_CAMAS,
        "hospital_id": "puerto_montt",
        "servicio_id": None,  # Acceso a todos los servicios de Puerto Montt
    },

    # ========== CAPA 3: CLÍNICA (NIVEL SERVICIO + ROL PROFESIONAL) ==========
    # MÉDICOS por servicio
    {
        "username": "medico_medicina",
        "email": "medico.medicina@hospital.cl",
        "password": "MedicoMed123!",
        "nombre_completo": "Dr. Juan Pérez - Medicina",
        "rol": RolEnum.MEDICO,
        "hospital_id": "puerto_montt",
        "servicio_id": "medicina",
    },
    {
        "username": "medico_cirugia",
        "email": "medico.cirugia@hospital.cl",
        "password": "MedicoCir123!",
        "nombre_completo": "Dr. Carlos González - Cirugía",
        "rol": RolEnum.MEDICO,
        "hospital_id": "puerto_montt",
        "servicio_id": "cirugia",
    },
    {
        "username": "medico_uci",
        "email": "medico.uci@hospital.cl",
        "password": "MedicoUCI123!",
        "nombre_completo": "Dra. María López - UCI",
        "rol": RolEnum.MEDICO,
        "hospital_id": "puerto_montt",
        "servicio_id": "uci",
    },

    # ENFERMERAS/MATRONAS por servicio
    {
        "username": "enfermera_medicina",
        "email": "enfermera.medicina@hospital.cl",
        "password": "EnfermeraMed123!",
        "nombre_completo": "Enfermera Ana Martínez - Medicina",
        "rol": RolEnum.ENFERMERA,
        "hospital_id": "puerto_montt",
        "servicio_id": "medicina",
    },
    {
        "username": "matrona_obstetricia",
        "email": "matrona.obstetricia@hospital.cl",
        "password": "MatronaObs123!",
        "nombre_completo": "Matrona Laura Fernández - Obstetricia",
        "rol": RolEnum.ENFERMERA,  # Enfermera incluye matronas
        "hospital_id": "puerto_montt",
        "servicio_id": "obstetricia",
    },

    # TENS por servicio
    {
        "username": "tens_medicina",
        "email": "tens.medicina@hospital.cl",
        "password": "TensMed123!",
        "nombre_completo": "TENS Pedro Ramírez - Medicina",
        "rol": RolEnum.TENS,
        "hospital_id": "puerto_montt",
        "servicio_id": "medicina",
    },
    {
        "username": "tens_cirugia",
        "email": "tens.cirugia@hospital.cl",
        "password": "TensCir123!",
        "nombre_completo": "TENS Rosa Silva - Cirugía",
        "rol": RolEnum.TENS,
        "hospital_id": "puerto_montt",
        "servicio_id": "cirugia",
    },

    # ========== ROLES DE SERVICIO ESPECÍFICOS ==========
    {
        "username": "jefe_medicina",
        "email": "jefe.medicina@hospital.cl",
        "password": "JefeMed123!",
        "nombre_completo": "Dr. Roberto Sánchez - Jefe Medicina",
        "rol": RolEnum.JEFE_SERVICIO,
        "hospital_id": "puerto_montt",
        "servicio_id": "medicina",
    },
    {
        "username": "supervisora_enfermeria",
        "email": "supervisora.enfermeria@hospital.cl",
        "password": "SupervisoraEnf123!",
        "nombre_completo": "Supervisora Claudia Morales",
        "rol": RolEnum.SUPERVISORA_ENFERMERIA,
        "hospital_id": "puerto_montt",
        "servicio_id": "medicina",
    },
    {
        "username": "urgencias_pm",
        "email": "urgencias.pm@hospital.cl",
        "password": "UrgenciasPM123!",
        "nombre_completo": "Enfermera Urgencias Puerto Montt",
        "rol": RolEnum.URGENCIAS,
        "hospital_id": "puerto_montt",
        "servicio_id": "urgencias",
    },
    {
        "username": "jefe_urgencias",
        "email": "jefe.urgencias@hospital.cl",
        "password": "JefeUrg123!",
        "nombre_completo": "Dr. Luis Torres - Jefe Urgencias",
        "rol": RolEnum.JEFE_URGENCIAS,
        "hospital_id": "puerto_montt",
        "servicio_id": "urgencias",
    },
    {
        "username": "ambulatorio",
        "email": "ambulatorio@hospital.cl",
        "password": "Ambulatorio123!",
        "nombre_completo": "Enfermera Ambulatorio",
        "rol": RolEnum.AMBULATORIO,
        "hospital_id": "puerto_montt",
        "servicio_id": "ambulatorio",
    },

    # Medicoquirúrgico en hospitales periféricos (con modo manual y bloqueo de camas)
    {
        "username": "jefe_medicoquirurgico_ll",
        "email": "jefe.medquir.ll@hospital.cl",
        "password": "JefeMedQuirLL123!",
        "nombre_completo": "Dr. Andrés Rojas - Jefe Medicoquirúrgico Llanquihue",
        "rol": RolEnum.JEFE_SERVICIO,
        "hospital_id": "llanquihue",
        "servicio_id": "medicoquirurgico",
    },
    {
        "username": "jefe_medicoquirurgico_cal",
        "email": "jefe.medquir.cal@hospital.cl",
        "password": "JefeMedQuirCal123!",
        "nombre_completo": "Dra. Patricia Vega - Jefe Medicoquirúrgico Calbuco",
        "rol": RolEnum.JEFE_SERVICIO,
        "hospital_id": "calbuco",
        "servicio_id": "medicoquirurgico",
    },

    # ========== ROLES ESPECIALIZADOS ==========
    {
        "username": "derivaciones",
        "email": "derivaciones@hospital.cl",
        "password": "Derivaciones123!",
        "nombre_completo": "Equipo Derivaciones",
        "rol": RolEnum.DERIVACIONES,
        "hospital_id": "puerto_montt",
        "servicio_id": None,
    },
    {
        "username": "estadisticas",
        "email": "estadisticas@hospital.cl",
        "password": "Estadisticas123!",
        "nombre_completo": "Analista de Estadísticas",
        "rol": RolEnum.ESTADISTICAS,
        "hospital_id": None,  # Acceso a estadísticas de toda la red
        "servicio_id": None,
    },
    {
        "username": "visualizador",
        "email": "visualizador@hospital.cl",
        "password": "Visualizador123!",
        "nombre_completo": "Usuario Visualizador",
        "rol": RolEnum.VISUALIZADOR,
        "hospital_id": "puerto_montt",
        "servicio_id": None,
    },
    {
        "username": "limpieza",
        "email": "limpieza@hospital.cl",
        "password": "Limpieza123!",
        "nombre_completo": "Personal de Limpieza",
        "rol": RolEnum.LIMPIEZA,
        "hospital_id": "puerto_montt",
        "servicio_id": None,
    },
]


def create_test_users():
    """Crea usuarios de prueba en la base de datos."""
    # Crear engine
    engine = create_engine(str(settings.DATABASE_URL))

    print("=" * 80)
    print("CREACIÓN DE USUARIOS DE PRUEBA - SISTEMA RBAC MULTINIVEL")
    print("=" * 80)
    print()

    with Session(engine) as session:
        usuarios_creados = 0
        usuarios_existentes = 0

        for user_data in USUARIOS_PRUEBA:
            # Verificar si el usuario ya existe
            existing_user = session.exec(
                select(Usuario).where(Usuario.username == user_data["username"])
            ).first()

            if existing_user:
                print(f"⚠️  Usuario '{user_data['username']}' ya existe. Omitiendo...")
                usuarios_existentes += 1
                continue

            # Crear usuario
            try:
                usuario = auth_service.create_user(
                    username=user_data["username"],
                    email=user_data["email"],
                    password=user_data["password"],
                    nombre_completo=user_data["nombre_completo"],
                    rol=user_data["rol"],
                    hospital_id=user_data["hospital_id"],
                    servicio_id=user_data["servicio_id"],
                    session=session,
                )
                session.commit()

                capa = ""
                if user_data["rol"] in [RolEnum.PROGRAMADOR, RolEnum.DIRECTIVO_RED]:
                    capa = "Capa 1: Admin/Red"
                elif user_data["rol"] in [RolEnum.DIRECTIVO_HOSPITAL, RolEnum.GESTOR_CAMAS]:
                    capa = "Capa 2: Gestión Local"
                elif user_data["rol"] in [RolEnum.MEDICO, RolEnum.ENFERMERA, RolEnum.TENS]:
                    capa = "Capa 3: Clínica"
                else:
                    capa = "Especializado"

                print(f"✅ Usuario creado: {user_data['username']}")
                print(f"   Nombre: {user_data['nombre_completo']}")
                print(f"   Rol: {user_data['rol'].value} ({capa})")
                print(f"   Hospital: {user_data['hospital_id'] or 'Todos'}")
                print(f"   Servicio: {user_data['servicio_id'] or 'Todos'}")
                print(f"   Email: {user_data['email']}")
                print(f"   Password: {user_data['password']}")
                print()

                usuarios_creados += 1

            except Exception as e:
                print(f"❌ Error creando usuario '{user_data['username']}': {e}")
                print()

    print("=" * 80)
    print(f"RESUMEN: {usuarios_creados} usuarios creados, {usuarios_existentes} ya existían")
    print("=" * 80)
    print()
    print("CREDENCIALES DE PRUEBA:")
    print()
    print("Capa 1 - Administración y Red:")
    print("  programador / Programador123! (Acceso total)")
    print("  directivo_red / DirectivoRed123! (Solo lectura - Todos los hospitales)")
    print()
    print("Capa 2 - Gestión Local:")
    print("  directivo_hospital_pm / DirectivoPM123! (Solo lectura - Puerto Montt)")
    print("  gestor_camas / GestorCamas123! (Gestión - Puerto Montt)")
    print()
    print("Capa 3 - Clínica:")
    print("  medico_medicina / MedicoMed123! (Médico - Medicina)")
    print("  enfermera_medicina / EnfermeraMed123! (Enfermera - Medicina)")
    print("  tens_medicina / TensMed123! (TENS - Medicina)")
    print()
    print("=" * 80)


if __name__ == "__main__":
    create_test_users()
