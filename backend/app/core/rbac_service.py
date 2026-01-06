"""
Servicio RBAC (Role-Based Access Control) Multinivel.
Implementa la lógica de filtrado por ubicación (servicio/hospital) + rol profesional.
"""
from typing import Optional, List
from sqlmodel import Session, select, or_, and_
from fastapi import HTTPException, status

from app.models.usuario import Usuario, RolEnum, PermisoEnum


# ============================================
# MAPEO DE CÓDIGOS
# ============================================

# Mapeo de códigos largos a códigos cortos de la BD
CODIGO_HOSPITAL_MAP = {
    "puerto_montt": "PM",
    "llanquihue": "LL",
    "calbuco": "CA",
}

CODIGO_SERVICIO_MAP = {
    "medicina": "Med",
    "cirugia": "Cirug",
    "uci": "UCI",
    "uti": "UTI",
    "pediatria": "Ped",
    "obstetricia": "Obst",
    "aislamiento": "Aisl",
    "medicoquirurgico": "MQ",
    "urgencias": "Urg",
    "ambulatorio": "Amb",
}


# ============================================
# MAPEO DE SERVICIOS POR ROL
# ============================================

# Roles que NO tienen acceso al dashboard de camas
ROLES_SIN_DASHBOARD = {
    RolEnum.URGENCIAS,
    RolEnum.JEFE_URGENCIAS,
    RolEnum.AMBULATORIO,
}

# Roles con acceso global a todos los hospitales (Capa 1)
ROLES_ACCESO_GLOBAL = {
    RolEnum.PROGRAMADOR,
    RolEnum.DIRECTIVO_RED,
}

# Roles con acceso solo a su hospital (Capa 2)
ROLES_ACCESO_HOSPITAL = {
    RolEnum.DIRECTIVO_HOSPITAL,
    RolEnum.GESTOR_CAMAS,
}

# Roles con acceso solo a su servicio (Capa 3)
ROLES_ACCESO_SERVICIO = {
    RolEnum.MEDICO,
    RolEnum.ENFERMERA,
    RolEnum.TENS,
    RolEnum.JEFE_SERVICIO,
    RolEnum.SUPERVISORA_ENFERMERIA,
    RolEnum.URGENCIAS,
    RolEnum.JEFE_URGENCIAS,
    RolEnum.AMBULATORIO,
}

# Roles de solo lectura (bloqueo total de escritura)
ROLES_SOLO_LECTURA = {
    RolEnum.DIRECTIVO_RED,
    RolEnum.DIRECTIVO_HOSPITAL,
    RolEnum.VISUALIZADOR,
    RolEnum.ESTADISTICAS,
}

# Servicios específicos para filtrado
SERVICIOS_HOSPITALARIOS = [
    "medicina",
    "cirugia",
    "uci",
    "uti",
    "pediatria",
    "obstetricia",
    "urgencias",
    "ambulatorio",
    "medicoquirurgico",
]

# Hospital Puerto Montt (único con Equipo de Gestión de Camas)
HOSPITAL_PUERTO_MONTT = "puerto_montt"


# ============================================
# FUNCIONES DE AUTORIZACIÓN
# ============================================

class RBACService:
    """Servicio de autorización RBAC con lógica de capas."""

    @staticmethod
    def puede_acceder_hospital(user: Usuario, hospital_id: str) -> bool:
        """
        Verifica si un usuario puede acceder a un hospital específico.
        Soporta comparación por UUID o código (largo o corto).

        Lógica:
        - Capa 1 (Global): Acceso a todos los hospitales
        - Capa 2 (Hospital): Solo su hospital
        - Capa 3 (Servicio): Solo su hospital
        """
        # Capa 1: Acceso global
        if user.rol in ROLES_ACCESO_GLOBAL:
            return True

        # Sin hospital asignado = sin restricción (por compatibilidad)
        if not user.hospital_id:
            return True

        # Normalizar código del usuario (convertir formato largo a corto si aplica)
        user_hospital_codigo = CODIGO_HOSPITAL_MAP.get(user.hospital_id, user.hospital_id)

        # Normalizar código del hospital objetivo
        hospital_id_normalizado = CODIGO_HOSPITAL_MAP.get(hospital_id, hospital_id)

        # Verificar que coincida el hospital (comparar ambos formatos)
        return (user.hospital_id == hospital_id or
                user_hospital_codigo == hospital_id or
                user.hospital_id == hospital_id_normalizado or
                user_hospital_codigo == hospital_id_normalizado)

    @staticmethod
    def puede_acceder_servicio(user: Usuario, servicio_id: str) -> bool:
        """
        Verifica si un usuario puede acceder a un servicio específico.
        Soporta comparación por UUID o código (largo o corto).

        Lógica:
        - Capa 1 (Global): Acceso a todos los servicios
        - Capa 2 (Hospital): Acceso a todos los servicios de su hospital
        - Capa 3 (Servicio): Solo su servicio
        """
        # Capa 1: Acceso global
        if user.rol in ROLES_ACCESO_GLOBAL:
            return True

        # Capa 2: Acceso a todos los servicios del hospital
        if user.rol in ROLES_ACCESO_HOSPITAL:
            return True

        # Capa 3: Solo su servicio
        if user.rol in ROLES_ACCESO_SERVICIO:
            if not user.servicio_id:
                return True  # Sin servicio asignado = sin restricción

            # Normalizar códigos
            user_servicio_codigo = CODIGO_SERVICIO_MAP.get(user.servicio_id, user.servicio_id)
            servicio_id_normalizado = CODIGO_SERVICIO_MAP.get(servicio_id, servicio_id)

            return (user.servicio_id == servicio_id or
                    user_servicio_codigo == servicio_id or
                    user.servicio_id == servicio_id_normalizado or
                    user_servicio_codigo == servicio_id_normalizado)

        # Por defecto, sin restricción
        return True

    @staticmethod
    def puede_ver_paciente(user: Usuario, paciente_origen_servicio: Optional[str],
                          paciente_destino_servicio: Optional[str],
                          paciente_hospital_id: Optional[str]) -> bool:
        """
        Verifica si un usuario puede ver un paciente según su servicio de origen/destino.

        Reglas según especificación:
        - Medicina/Cirugía/UCI/UTI/Pedia: Solo pacientes con origen o destino en su servicio
        - Obstetricia: Solo pacientes de Obstetricia (Exclusivo Matrón/a)
        - Urgencias: Solo pacientes con origen en Urgencias
        - Ambulatorios: Solo pacientes con origen en Ambulatorio
        - Medicoquirúrgico: Solo pacientes con origen o destino en su servicio
        """
        # Capa 1: Ver todos los pacientes
        if user.rol in ROLES_ACCESO_GLOBAL:
            return True

        # Capa 2: Ver todos los pacientes del hospital
        if user.rol in ROLES_ACCESO_HOSPITAL:
            if user.hospital_id and paciente_hospital_id:
                return user.hospital_id == paciente_hospital_id
            return True

        # Capa 3: Filtrado por servicio
        if user.rol in ROLES_ACCESO_SERVICIO:
            # Sin servicio asignado = sin restricción
            if not user.servicio_id:
                return True

            # Casos especiales según especificación
            if user.servicio_id == "urgencias":
                # Urgencias: Solo pacientes con origen en Urgencias
                return paciente_origen_servicio == "urgencias"

            elif user.servicio_id == "ambulatorio":
                # Ambulatorios: Solo pacientes con origen en Ambulatorio
                return paciente_origen_servicio == "ambulatorio"

            elif user.servicio_id == "obstetricia":
                # Obstetricia: Solo pacientes de Obstetricia
                return (paciente_origen_servicio == "obstetricia" or
                        paciente_destino_servicio == "obstetricia")

            else:
                # Medicina/Cirugía/UCI/UTI/Pedia/Medicoquirúrgico:
                # Solo pacientes con origen o destino en su servicio
                return (paciente_origen_servicio == user.servicio_id or
                        paciente_destino_servicio == user.servicio_id)

        # Por defecto, permitir acceso
        return True

    @staticmethod
    def tiene_acceso_dashboard(user: Usuario) -> bool:
        """
        Verifica si un usuario tiene acceso al dashboard de camas.

        Según especificación:
        - Urgencias y Ambulatorios NO tienen visión de dashboard de camas
        """
        # Verificar permiso básico
        if not user.tiene_permiso(PermisoEnum.DASHBOARD_VER):
            return False

        # Roles explícitamente sin dashboard
        if user.rol in ROLES_SIN_DASHBOARD:
            return False

        return True

    @staticmethod
    def puede_usar_modo_manual(user: Usuario, hospital_id: str) -> bool:
        """
        Verifica si un usuario puede usar el modo manual.

        Según especificación:
        - Puerto Montt: Solo Equipo de Gestión de Camas
        - Llanquihue/Calbuco: Equipo clínico (Medicoquirúrgico) puede usar modo manual
        """
        # Verificar permiso básico
        if not user.tiene_permiso(PermisoEnum.MODO_MANUAL_ASIGNAR):
            return False

        # Gestor de Camas siempre puede (Puerto Montt)
        if user.rol == RolEnum.GESTOR_CAMAS:
            # Solo si es de Puerto Montt
            if user.hospital_id == HOSPITAL_PUERTO_MONTT:
                return True
            return False

        # Hospitales periféricos (Llanquihue/Calbuco)
        if hospital_id in ["llanquihue", "calbuco"]:
            # Equipo clínico de Medicoquirúrgico
            if user.servicio_id == "medicoquirurgico":
                return user.tiene_permiso(PermisoEnum.MODO_MANUAL_ASIGNAR)

        return False

    @staticmethod
    def puede_bloquear_camas(user: Usuario, hospital_id: str) -> bool:
        """
        Verifica si un usuario puede bloquear camas.

        Según especificación:
        - Puerto Montt: Equipo de Gestión de Camas
        - Llanquihue/Calbuco: Equipo clínico (Medicoquirúrgico)
        """
        # Verificar permiso básico
        if not user.tiene_permiso(PermisoEnum.CAMA_BLOQUEAR):
            return False

        # Gestor de Camas siempre puede (Puerto Montt)
        if user.rol == RolEnum.GESTOR_CAMAS:
            if user.hospital_id == HOSPITAL_PUERTO_MONTT:
                return True
            return False

        # Hospitales periféricos (Llanquihue/Calbuco)
        if hospital_id in ["llanquihue", "calbuco"]:
            if user.servicio_id == "medicoquirurgico":
                return True

        # Jefe de servicio siempre puede
        if user.rol == RolEnum.JEFE_SERVICIO:
            return True

        return True

    @staticmethod
    def es_solo_lectura(user: Usuario) -> bool:
        """
        Verifica si un usuario tiene perfil de solo lectura.

        Según especificación:
        - Equipo Directivo de Red: BLOQUEO TOTAL DE ESCRITURA
        - Equipo Directivo Hospital: Sin permisos de registro o cambios operativos
        """
        return user.rol in ROLES_SOLO_LECTURA

    @staticmethod
    def verificar_restriccion_escritura(user: Usuario, accion: str) -> None:
        """
        Lanza excepción si el usuario tiene perfil de solo lectura.

        Args:
            user: Usuario que intenta realizar la acción
            accion: Descripción de la acción (para el mensaje de error)

        Raises:
            HTTPException: Si el usuario es de solo lectura
        """
        if RBACService.es_solo_lectura(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tu perfil ({user.rol.value}) tiene acceso de solo lectura. No puedes realizar: {accion}"
            )

    @staticmethod
    def filtrar_query_por_hospital(user: Usuario, query):
        """
        Filtra una query SQLModel por hospital según el rol del usuario.

        Args:
            user: Usuario actual
            query: Query de SQLModel

        Returns:
            Query filtrada por hospital
        """
        # Capa 1: Sin filtro (acceso global)
        if user.rol in ROLES_ACCESO_GLOBAL:
            return query

        # Capa 2 y 3: Filtrar por hospital
        if user.hospital_id:
            # Asumir que la tabla tiene campo hospital_id
            return query.where(query.column_descriptions[0]['entity'].hospital_id == user.hospital_id)

        return query

    @staticmethod
    def filtrar_query_por_servicio(user: Usuario, query, tabla):
        """
        Filtra una query SQLModel por servicio según el rol del usuario.

        Args:
            user: Usuario actual
            query: Query de SQLModel
            tabla: Clase del modelo (para acceder a sus columnas)

        Returns:
            Query filtrada por servicio
        """
        # Capa 1: Sin filtro (acceso global)
        if user.rol in ROLES_ACCESO_GLOBAL:
            return query

        # Capa 2: Sin filtro por servicio (acceso a todo el hospital)
        if user.rol in ROLES_ACCESO_HOSPITAL:
            return query

        # Capa 3: Filtrar por servicio
        if user.rol in ROLES_ACCESO_SERVICIO and user.servicio_id:
            # Casos especiales según el servicio
            if user.servicio_id == "urgencias":
                # Solo pacientes con origen en Urgencias
                return query.where(tabla.servicio_origen == "urgencias")

            elif user.servicio_id == "ambulatorio":
                # Solo pacientes con origen en Ambulatorio
                return query.where(tabla.servicio_origen == "ambulatorio")

            else:
                # Pacientes con origen O destino en su servicio
                return query.where(
                    or_(
                        tabla.servicio_origen == user.servicio_id,
                        tabla.servicio_destino == user.servicio_id
                    )
                )

        return query

    @staticmethod
    def obtener_hospitales_permitidos(user: Usuario) -> Optional[List[str]]:
        """
        Obtiene la lista de hospitales a los que el usuario tiene acceso.

        Returns:
            None si tiene acceso a todos, o lista de hospital_ids permitidos
        """
        # Acceso global
        if user.rol in ROLES_ACCESO_GLOBAL:
            return None  # Todos los hospitales

        # Solo su hospital
        if user.hospital_id:
            return [user.hospital_id]

        # Sin restricción
        return None

    @staticmethod
    def obtener_servicios_permitidos(user: Usuario) -> Optional[List[str]]:
        """
        Obtiene la lista de servicios a los que el usuario tiene acceso.

        Returns:
            None si tiene acceso a todos, o lista de servicio_ids permitidos
        """
        # Acceso global o por hospital
        if user.rol in ROLES_ACCESO_GLOBAL or user.rol in ROLES_ACCESO_HOSPITAL:
            return None  # Todos los servicios

        # Solo su servicio
        if user.servicio_id:
            return [user.servicio_id]

        # Sin restricción
        return None


# ============================================
# INSTANCIA SINGLETON
# ============================================

rbac_service = RBACService()
