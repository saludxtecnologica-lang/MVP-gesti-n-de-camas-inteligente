"""
Servicio de Compatibilidad de Camas.
Funciones para verificar compatibilidad de pacientes con camas/salas.

CORREGIDO: Ahora busca camas compartidas en TODOS los servicios compatibles,
no solo en el servicio actual.

CORREGIDO v2: Manejo robusto de sexo_asignado como str o Enum.

CORREGIDO v3: Agregada verificación de COMPLEJIDAD de cama vs paciente
al completar traslado.

Ubicación: app/services/compatibilidad_service.py
"""
from typing import Optional, Tuple, List, Union
from sqlmodel import Session, select
from datetime import datetime
import logging

from app.models.paciente import Paciente
from app.models.cama import Cama
from app.models.sala import Sala
from app.models.servicio import Servicio
from app.models.enums import (
    EstadoCamaEnum,
    TipoAislamientoEnum,
    TipoServicioEnum,
    SexoEnum,
    ComplejidadEnum,
    AISLAMIENTOS_SALA_INDIVIDUAL,
    ESTADOS_CAMA_OCUPADA,
    MAPEO_COMPLEJIDAD_SERVICIO,
)

logger = logging.getLogger("gestion_camas.compatibilidad")


# ============================================
# FUNCIONES HELPER PARA MANEJO DE SEXO
# ============================================

def _normalizar_sexo(sexo: Union[SexoEnum, str, None]) -> Optional[str]:
    """
    Normaliza el valor de sexo a string para comparaciones.
    
    Args:
        sexo: Puede ser SexoEnum, str o None
    
    Returns:
        String normalizado ('hombre', 'mujer') o None
    """
    if sexo is None:
        return None
    if hasattr(sexo, 'value'):
        return sexo.value
    return str(sexo).lower()


def _obtener_sexo_display(sexo: Union[SexoEnum, str, None]) -> str:
    """
    Obtiene el valor de sexo como string para mostrar en mensajes.
    
    Args:
        sexo: Puede ser SexoEnum, str o None
    
    Returns:
        String para mostrar
    """
    if sexo is None:
        return "no asignado"
    if hasattr(sexo, 'value'):
        return sexo.value
    return str(sexo)


# ============================================
# MAPEO DE NIVELES DE COMPLEJIDAD
# ============================================

# Niveles numéricos para comparación de complejidad
# Usando los valores correctos del enum: NINGUNA, BAJA, MEDIA (UTI), ALTA (UCI)
NIVEL_COMPLEJIDAD = {
    # Enum values
    ComplejidadEnum.NINGUNA: 0,
    ComplejidadEnum.BAJA: 1,
    ComplejidadEnum.MEDIA: 2,   # UTI
    ComplejidadEnum.ALTA: 3,    # UCI
    # Strings alternativos (por si acaso)
    'ninguna': 0,
    'baja': 1,
    'media': 2,
    'uti': 2,
    'alta': 3,
    'uci': 3,
}

# Mapeo de tipo de servicio a nivel de complejidad máximo que soporta
COMPLEJIDAD_MAXIMA_SERVICIO = {
    TipoServicioEnum.MEDICINA: ComplejidadEnum.BAJA,
    TipoServicioEnum.CIRUGIA: ComplejidadEnum.BAJA,
    TipoServicioEnum.MEDICO_QUIRURGICO: ComplejidadEnum.BAJA,
    TipoServicioEnum.UTI: ComplejidadEnum.MEDIA,
    TipoServicioEnum.UCI: ComplejidadEnum.ALTA,
    TipoServicioEnum.AISLAMIENTO: ComplejidadEnum.ALTA,  # Puede manejar cualquier complejidad
    TipoServicioEnum.PEDIATRIA: ComplejidadEnum.BAJA,
    TipoServicioEnum.OBSTETRICIA: ComplejidadEnum.BAJA,
}


def _obtener_nivel_complejidad(complejidad) -> int:
    """
    Obtiene el nivel numérico de una complejidad para comparaciones.
    
    Args:
        complejidad: ComplejidadEnum, string o None
    
    Returns:
        Nivel numérico (0-3)
    """
    if complejidad is None:
        return 0
    
    # Si ya es un número
    if isinstance(complejidad, int):
        return complejidad
    
    # Si es enum, intentar buscarlo directamente
    if complejidad in NIVEL_COMPLEJIDAD:
        return NIVEL_COMPLEJIDAD[complejidad]
    
    # Si es enum, obtener valor string
    if hasattr(complejidad, 'value'):
        key = str(complejidad.value).lower()
    else:
        key = str(complejidad).lower()
    
    return NIVEL_COMPLEJIDAD.get(key, 0)


def _obtener_complejidad_display(complejidad) -> str:
    """
    Obtiene el valor de complejidad como string para mostrar en mensajes.
    
    Args:
        complejidad: ComplejidadEnum, string o None
    
    Returns:
        String para mostrar
    """
    if complejidad is None:
        return "ninguna"
    if hasattr(complejidad, 'value'):
        return complejidad.value
    return str(complejidad)


class CompatibilidadService:
    """
    Servicio para verificar compatibilidad de pacientes con camas.
    
    Maneja:
    - Compatibilidad de sexo en salas compartidas
    - Compatibilidad de aislamiento
    - Compatibilidad de complejidad (NUEVO)
    - Actualización de sexo de sala
    - Verificación de si paciente debe buscar cama compartida
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    # ============================================
    # VERIFICACIÓN DE TIPO DE SALA
    # ============================================
    
    def es_sala_individual(self, sala: Sala) -> bool:
        """
        Verifica si una sala es individual (no requiere compatibilidad de sexo).
        
        Salas individuales incluyen:
        - Salas marcadas como es_individual=True
        - UCI, UTI
        - Salas de aislamiento
        """
        if sala.es_individual:
            return True
        
        # Verificar tipo de servicio
        if sala.servicio:
            servicio_tipo = sala.servicio.tipo
            if servicio_tipo in [TipoServicioEnum.UCI, TipoServicioEnum.UTI, TipoServicioEnum.AISLAMIENTO]:
                return True
        
        return False
    
    # ============================================
    # VERIFICACIÓN DE SEXO EN SALA
    # ============================================
    
    def obtener_sexo_actual_sala(self, sala: Sala) -> Optional[str]:
        """
        Obtiene el sexo actualmente asignado a una sala.
        
        Revisa:
        1. El campo sexo_asignado de la sala
        2. Los pacientes actualmente en las camas de la sala (cama_id)
        3. Los pacientes asignados a camas de la sala pero que aún no llegan (cama_destino_id)
        
        Returns:
            String con el sexo ('hombre', 'mujer') o None si la sala está vacía/sin asignaciones
        """
        # Si la sala ya tiene sexo asignado, retornarlo normalizado
        if sala.sexo_asignado:
            return _normalizar_sexo(sala.sexo_asignado)
        
        # Obtener IDs de todas las camas de esta sala
        ids_camas_sala = [cama.id for cama in sala.camas]
        
        if not ids_camas_sala:
            return None
        
        # Buscar pacientes que están físicamente en las camas (cama_id)
        for cama in sala.camas:
            if cama.estado in ESTADOS_CAMA_OCUPADA:
                query = select(Paciente).where(Paciente.cama_id == cama.id)
                paciente = self.session.exec(query).first()
                if paciente and paciente.sexo:
                    return _normalizar_sexo(paciente.sexo)
        
        # Buscar pacientes asignados pero que aún no llegan (cama_destino_id)
        # Esto cubre el caso de asignaciones pendientes (TRASLADO_ENTRANTE)
        query = select(Paciente).where(Paciente.cama_destino_id.in_(ids_camas_sala))
        pacientes_asignados = self.session.exec(query).all()
        
        if pacientes_asignados:
            # Retornar el sexo del primer paciente asignado encontrado
            for paciente in pacientes_asignados:
                if paciente.sexo:
                    return _normalizar_sexo(paciente.sexo)
        
        return None
    
    def verificar_compatibilidad_sexo(
        self, 
        paciente: Paciente, 
        cama: Cama
    ) -> Tuple[bool, str]:
        """
        Verifica si un paciente es compatible con una cama en términos de sexo.
        
        Args:
            paciente: Paciente a verificar
            cama: Cama destino
        
        Returns:
            Tuple (es_compatible, mensaje)
        """
        sala = cama.sala
        if not sala:
            return True, "Sin información de sala"
        
        # Las salas individuales aceptan cualquier sexo
        if self.es_sala_individual(sala):
            return True, "Sala individual - acepta cualquier sexo"
        
        # Obtener sexo actual de la sala (ya normalizado como string)
        sexo_sala = self.obtener_sexo_actual_sala(sala)
        
        # Si la sala no tiene sexo asignado, es compatible
        if not sexo_sala:
            return True, "Sala sin sexo asignado - disponible"
        
        # Normalizar sexo del paciente para comparación
        sexo_paciente = _normalizar_sexo(paciente.sexo)
        
        # Verificar compatibilidad
        if sexo_paciente == sexo_sala:
            return True, f"Sexo compatible con sala ({sexo_sala})"
        else:
            return False, f"Sexo incompatible: paciente {_obtener_sexo_display(paciente.sexo)}, sala {sexo_sala}"
    
    def actualizar_sexo_sala(self, sala: Sala) -> Optional[str]:
        """
        Actualiza el sexo asignado de una sala basándose en sus pacientes actuales
        y pacientes con asignación pendiente.
        
        Si la sala queda vacía y sin asignaciones pendientes, el sexo se limpia.
        Si hay pacientes (físicos o asignados), el sexo se asigna al del primer paciente encontrado.
        
        Returns:
            El nuevo sexo asignado (como string) o None si la sala quedó vacía
        """
        # Las salas individuales no necesitan sexo asignado
        if self.es_sala_individual(sala):
            sala.sexo_asignado = None
            self.session.add(sala)
            return None
        
        # Obtener IDs de todas las camas de esta sala
        ids_camas_sala = [cama.id for cama in sala.camas]
        
        sexo_encontrado = None
        
        # Buscar pacientes físicamente en las camas de la sala
        for cama in sala.camas:
            if cama.estado in ESTADOS_CAMA_OCUPADA:
                query = select(Paciente).where(Paciente.cama_id == cama.id)
                paciente = self.session.exec(query).first()
                if paciente and paciente.sexo:
                    sexo_encontrado = _normalizar_sexo(paciente.sexo)
                    break
        
        # NUEVO: Si no encontró pacientes físicos, buscar asignaciones pendientes
        if not sexo_encontrado and ids_camas_sala:
            query = select(Paciente).where(Paciente.cama_destino_id.in_(ids_camas_sala))
            pacientes_asignados = self.session.exec(query).all()
            
            for paciente in pacientes_asignados:
                if paciente.sexo:
                    sexo_encontrado = _normalizar_sexo(paciente.sexo)
                    break
        
        # Actualizar sala (guardamos como string)
        sala.sexo_asignado = sexo_encontrado
        self.session.add(sala)
        
        logger.debug(f"Sala {sala.id} sexo actualizado a: {sexo_encontrado}")
        
        return sexo_encontrado
    
    # ============================================
    # VERIFICACIÓN DE AISLAMIENTO
    # ============================================
    
    def paciente_requiere_aislamiento_individual(self, paciente: Paciente) -> bool:
        """
        Verifica si un paciente requiere una sala individual por aislamiento.
        """
        return paciente.tipo_aislamiento in AISLAMIENTOS_SALA_INDIVIDUAL
    
    def cama_es_aislamiento_individual(self, cama: Cama) -> bool:
        """
        Verifica si una cama está en una sala de aislamiento individual.
        """
        sala = cama.sala
        if not sala:
            return False
        
        return self.es_sala_individual(sala)
    
    def verificar_compatibilidad_aislamiento(
        self,
        paciente: Paciente,
        cama: Cama
    ) -> Tuple[bool, str]:
        """
        Verifica compatibilidad de aislamiento entre paciente y cama.
        
        Reglas:
        - Paciente con aislamiento individual DEBE estar en sala individual
        - Paciente SIN aislamiento puede estar en cualquiera
        
        Returns:
            Tuple (es_compatible, mensaje)
        """
        requiere_individual = self.paciente_requiere_aislamiento_individual(paciente)
        cama_es_individual = self.cama_es_aislamiento_individual(cama)
        
        if requiere_individual:
            if cama_es_individual:
                return True, "Paciente requiere aislamiento y cama es individual"
            else:
                return False, "Paciente requiere aislamiento individual pero cama no es individual"
        else:
            # Paciente sin requerimiento de aislamiento individual puede estar en cualquiera
            return True, "Paciente no requiere aislamiento individual"
    
    # ============================================
    # VERIFICACIÓN DE COMPLEJIDAD (NUEVO)
    # ============================================
    
    def obtener_complejidad_maxima_cama(self, cama: Cama) -> ComplejidadEnum:
        """
        Obtiene la complejidad máxima que puede manejar una cama basándose
        en el tipo de servicio donde se encuentra.
        
        Args:
            cama: La cama a evaluar
        
        Returns:
            ComplejidadEnum con el nivel máximo soportado
        """
        # Si la cama tiene nivel_complejidad definido, usarlo
        if hasattr(cama, 'nivel_complejidad') and cama.nivel_complejidad:
            return cama.nivel_complejidad
        
        # Si no, derivar del tipo de servicio
        if cama.sala and cama.sala.servicio:
            tipo_servicio = cama.sala.servicio.tipo
            return COMPLEJIDAD_MAXIMA_SERVICIO.get(tipo_servicio, ComplejidadEnum.BAJA)
        
        # Por defecto, asumir baja complejidad
        return ComplejidadEnum.BAJA
    
    def verificar_compatibilidad_complejidad(
        self,
        paciente: Paciente,
        cama: Cama
    ) -> Tuple[bool, str]:
        """
        Verifica si la complejidad de la cama es suficiente para el paciente.
        
        Reglas:
        - El nivel de complejidad de la cama debe ser >= al del paciente
        - ALTA (UCI) > MEDIA (UTI) > BAJA > NINGUNA
        
        Args:
            paciente: Paciente a verificar
            cama: Cama destino
        
        Returns:
            Tuple (es_compatible, mensaje)
        """
        # Obtener complejidad del paciente
        complejidad_paciente = paciente.complejidad_requerida
        if not complejidad_paciente:
            # Si no tiene complejidad definida, calcularla
            complejidad_paciente = self.calcular_complejidad_paciente(paciente)
        
        # Obtener complejidad máxima de la cama
        complejidad_cama = self.obtener_complejidad_maxima_cama(cama)
        
        # Convertir a niveles numéricos para comparar
        nivel_paciente = _obtener_nivel_complejidad(complejidad_paciente)
        nivel_cama = _obtener_nivel_complejidad(complejidad_cama)
        
        # Log para debugging
        logger.debug(
            f"Verificando complejidad: paciente {paciente.nombre} "
            f"requiere nivel {nivel_paciente} ({_obtener_complejidad_display(complejidad_paciente)}), "
            f"cama {cama.identificador} soporta nivel {nivel_cama} ({_obtener_complejidad_display(complejidad_cama)})"
        )
        
        # La cama debe soportar al menos el nivel del paciente
        if nivel_cama >= nivel_paciente:
            return True, f"Complejidad compatible (paciente: {_obtener_complejidad_display(complejidad_paciente)}, cama: {_obtener_complejidad_display(complejidad_cama)})"
        else:
            # Convertir complejidad a nombre legible
            nombres_complejidad = {
                ComplejidadEnum.NINGUNA: "NINGUNA",
                ComplejidadEnum.BAJA: "BAJA",
                ComplejidadEnum.MEDIA: "MEDIA (UTI)",
                ComplejidadEnum.ALTA: "ALTA (UCI)",
            }
            nombre_paciente = nombres_complejidad.get(complejidad_paciente, str(complejidad_paciente))
            nombre_cama = nombres_complejidad.get(complejidad_cama, str(complejidad_cama))
            
            return False, f"Complejidad insuficiente: paciente requiere {nombre_paciente}, cama soporta {nombre_cama}"
    
    # ============================================
    # CÁLCULO DE COMPLEJIDAD
    # ============================================
    
    def calcular_complejidad_paciente(self, paciente: Paciente) -> ComplejidadEnum:
        """
        Calcula la complejidad requerida del paciente.
        
        Usa la complejidad_requerida si está definida, sino calcula.
        """
        if paciente.complejidad_requerida:
            return paciente.complejidad_requerida
        
        # Import local para evitar circular
        from app.services.asignacion_service import AsignacionService
        
        asignacion_service = AsignacionService(self.session)
        return asignacion_service.calcular_complejidad(paciente)
    
    # ============================================
    # VERIFICACIÓN DE CAMA DE COMPLEJIDAD CORRECTA (NUEVO)
    # ============================================
    
    def hay_camas_nivel_correcto_disponibles(
        self,
        paciente: Paciente,
        hospital_id: str
    ) -> bool:
        """
        Verifica si hay camas disponibles del nivel de complejidad EXACTO para el paciente.
        
        Args:
            paciente: Paciente para verificar
            hospital_id: ID del hospital donde buscar
        
        Returns:
            True si hay camas del nivel correcto disponibles
        """
        complejidad = self.calcular_complejidad_paciente(paciente)
        servicios_compatibles = MAPEO_COMPLEJIDAD_SERVICIO.get(complejidad, [])
        
        if not servicios_compatibles:
            return False
        
        # Buscar camas libres en servicios del nivel correcto
        query = (
            select(Cama)
            .join(Sala)
            .join(Servicio)
            .where(
                Servicio.hospital_id == hospital_id,
                Servicio.tipo.in_(servicios_compatibles),
                Cama.estado == EstadoCamaEnum.LIBRE
            )
        )
        camas_libres = self.session.exec(query).all()
        
        logger.debug(
            f"Buscando camas nivel correcto para {paciente.nombre} "
            f"(complejidad: {_obtener_complejidad_display(complejidad)}): "
            f"encontradas {len(camas_libres)} camas libres en servicios {servicios_compatibles}"
        )
        
        # Verificar compatibilidad de sexo y aislamiento en las camas encontradas
        for cama_candidata in camas_libres:
            compatible_sexo, _ = self.verificar_compatibilidad_sexo(paciente, cama_candidata)
            compatible_aislamiento, _ = self.verificar_compatibilidad_aislamiento(paciente, cama_candidata)
            if compatible_sexo and compatible_aislamiento:
                logger.info(
                    f"Cama de nivel correcto disponible para {paciente.nombre}: "
                    f"{cama_candidata.identificador}"
                )
                return True
        
        return False
    
    def paciente_en_cama_complejidad_superior(
        self,
        paciente: Paciente,
        cama_actual: Cama
    ) -> bool:
        """
        Verifica si un paciente está en una cama de complejidad SUPERIOR a la necesaria
        y hay camas de su nivel correcto disponibles.

        Ejemplo: Paciente UTI en cama UCI, cuando hay camas UTI disponibles.

        Esto es importante para:
        - Liberar camas UCI/UTI para pacientes que realmente las necesitan
        - Optimizar el uso de recursos hospitalarios

        CORREGIDO: Pacientes con aislamiento individual que ya están en sala individual
        del nivel correcto NO deben buscar otra cama.

        Returns:
            True si el paciente debería buscar cama de su nivel correcto
        """
        # Obtener complejidad del paciente
        complejidad_paciente = paciente.complejidad_requerida
        if not complejidad_paciente:
            complejidad_paciente = self.calcular_complejidad_paciente(paciente)

        # Obtener complejidad de la cama
        complejidad_cama = self.obtener_complejidad_maxima_cama(cama_actual)

        nivel_paciente = _obtener_nivel_complejidad(complejidad_paciente)
        nivel_cama = _obtener_nivel_complejidad(complejidad_cama)

        logger.debug(
            f"Verificando si paciente {paciente.nombre} está en cama de complejidad superior: "
            f"nivel_paciente={nivel_paciente} ({_obtener_complejidad_display(complejidad_paciente)}), "
            f"nivel_cama={nivel_cama} ({_obtener_complejidad_display(complejidad_cama)})"
        )

        # CORRECCIÓN PROBLEMA 1: Si el paciente requiere aislamiento individual
        # y ya está en sala individual del nivel CORRECTO, no buscar otra cama.
        # Esto evita traslados innecesarios entre salas de aislamiento.
        if nivel_cama == nivel_paciente:
            requiere_individual = self.paciente_requiere_aislamiento_individual(paciente)
            cama_es_individual = self.cama_es_aislamiento_individual(cama_actual)

            if requiere_individual and cama_es_individual:
                logger.info(
                    f"Paciente {paciente.nombre} requiere aislamiento individual, "
                    f"ya está en sala individual del nivel correcto - NO BUSCAR OTRA CAMA"
                )
                return False

        # Si la cama es del nivel correcto o inferior, no hay problema
        if nivel_cama <= nivel_paciente:
            logger.debug(f"Paciente {paciente.nombre}: cama es de nivel correcto o inferior")
            return False
        
        # La cama es de nivel SUPERIOR - verificar si hay camas del nivel correcto
        hospital_id = paciente.hospital_id
        
        if self.hay_camas_nivel_correcto_disponibles(paciente, hospital_id):
            logger.info(
                f"Paciente {paciente.nombre} (complejidad {_obtener_complejidad_display(complejidad_paciente)}) "
                f"está en cama {cama_actual.identificador} (complejidad {_obtener_complejidad_display(complejidad_cama)}) "
                f"y HAY camas de su nivel disponibles - DEBE BUSCAR NUEVA CAMA"
            )
            return True
        
        logger.debug(
            f"Paciente {paciente.nombre} está en cama de complejidad superior "
            f"pero NO hay camas de su nivel disponibles - permanece en cama actual"
        )
        return False
    
    # ============================================
    # BÚSQUEDA DE CAMAS COMPARTIDAS EN SERVICIOS COMPATIBLES
    # ============================================
    
    def hay_camas_compartidas_disponibles_en_servicios_compatibles(
        self,
        paciente: Paciente,
        hospital_id: str
    ) -> bool:
        """
        Verifica si hay camas disponibles en salas compartidas de servicios compatibles.
        
        CORREGIDO: Busca en TODOS los servicios compatibles según la complejidad
        del paciente, no solo en el servicio actual.
        
        Args:
            paciente: Paciente para verificar compatibilidad
            hospital_id: ID del hospital donde buscar
        
        Returns:
            True si hay camas compartidas disponibles y compatibles
        """
        # Calcular complejidad del paciente
        complejidad = self.calcular_complejidad_paciente(paciente)
        
        # Obtener servicios compatibles según la complejidad
        servicios_compatibles = MAPEO_COMPLEJIDAD_SERVICIO.get(complejidad, [])
        
        # Si no hay servicios compatibles definidos, permitir cualquiera
        if not servicios_compatibles:
            servicios_compatibles = [
                TipoServicioEnum.MEDICINA,
                TipoServicioEnum.CIRUGIA,
                TipoServicioEnum.MEDICO_QUIRURGICO,
            ]
        
        # Buscar camas libres en salas compartidas de servicios compatibles
        query = (
            select(Cama)
            .join(Sala)
            .join(Servicio)
            .where(
                Servicio.hospital_id == hospital_id,
                Servicio.tipo.in_(servicios_compatibles),
                Sala.es_individual == False,
                Cama.estado == EstadoCamaEnum.LIBRE
            )
        )
        camas_compartidas_libres = self.session.exec(query).all()
        
        logger.debug(
            f"Buscando camas compartidas para {paciente.nombre} "
            f"(complejidad: {_obtener_complejidad_display(complejidad)}): "
            f"encontradas {len(camas_compartidas_libres)} camas en servicios {servicios_compatibles}"
        )
        
        # Verificar compatibilidad de sexo en las camas encontradas
        for cama_candidata in camas_compartidas_libres:
            compatible_sexo, _ = self.verificar_compatibilidad_sexo(paciente, cama_candidata)
            if compatible_sexo:
                logger.info(
                    f"Cama compartida disponible para {paciente.nombre}: "
                    f"{cama_candidata.identificador}"
                )
                return True
        
        return False
    
    def paciente_deberia_buscar_cama_compartida(
        self,
        paciente: Paciente,
        cama_actual: Cama
    ) -> bool:
        """
        Verifica si un paciente debería buscar una cama en sala compartida.
        
        CORREGIDO: Ahora busca camas en TODOS los servicios compatibles,
        no solo en el servicio actual de la cama.
        
        Esto ocurre cuando:
        - El paciente NO requiere aislamiento individual
        - La cama actual ES de aislamiento individual (UCI/UTI/Aislamiento/es_individual)
        - Hay camas disponibles en salas compartidas de servicios compatibles
        
        Returns:
            True si debería buscar cama compartida
        """
        # Si requiere aislamiento individual, no debe buscar compartida
        if self.paciente_requiere_aislamiento_individual(paciente):
            logger.debug(f"Paciente {paciente.nombre} requiere aislamiento individual - no busca compartida")
            return False
        
        # Si la cama actual NO es individual, no hay problema
        if not self.cama_es_aislamiento_individual(cama_actual):
            logger.debug(f"Paciente {paciente.nombre} ya está en sala compartida")
            return False
        
        # Está en cama individual sin necesitarla - verificar si hay compartidas
        # CORREGIDO: usar hospital_id del paciente
        hospital_id = paciente.hospital_id
        
        # Verificar si hay camas compartidas disponibles en servicios compatibles
        if self.hay_camas_compartidas_disponibles_en_servicios_compatibles(paciente, hospital_id):
            logger.info(
                f"Paciente {paciente.nombre} está en sala individual sin necesitarla "
                f"y hay camas compartidas disponibles en servicios compatibles"
            )
            return True
        
        logger.debug(
            f"Paciente {paciente.nombre} está en sala individual sin necesitarla "
            f"pero NO hay camas compartidas disponibles"
        )
        return False
    
    # ============================================
    # VERIFICACIÓN COMPLETA DE COMPATIBILIDAD
    # ============================================
    
    def verificar_compatibilidad_completa(
        self,
        paciente: Paciente,
        cama: Cama
    ) -> Tuple[bool, List[str]]:
        """
        Realiza una verificación completa de compatibilidad.
        
        Verifica:
        1. Compatibilidad de sexo (en salas compartidas)
        2. Compatibilidad de aislamiento requerido
        3. Compatibilidad de complejidad (cama no puede ser INFERIOR al paciente)
        4. Si paciente en sala individual debería estar en compartida
        5. Si paciente está en cama de complejidad SUPERIOR con alternativas disponibles (NUEVO)
        
        Returns:
            Tuple (es_compatible, lista_de_problemas)
        """
        problemas = []
        es_compatible = True
        
        # 1. Verificar sexo
        compatible_sexo, msg_sexo = self.verificar_compatibilidad_sexo(paciente, cama)
        if not compatible_sexo:
            es_compatible = False
            problemas.append(msg_sexo)
        
        # 2. Verificar aislamiento requerido
        compatible_aislamiento, msg_aislamiento = self.verificar_compatibilidad_aislamiento(paciente, cama)
        if not compatible_aislamiento:
            es_compatible = False
            problemas.append(msg_aislamiento)
        
        # 3. Verificar complejidad de la cama (cama no puede ser INFERIOR)
        compatible_complejidad, msg_complejidad = self.verificar_compatibilidad_complejidad(paciente, cama)
        if not compatible_complejidad:
            es_compatible = False
            problemas.append(msg_complejidad)
        
        # 4. Verificar si debería estar en sala compartida
        if self.paciente_deberia_buscar_cama_compartida(paciente, cama):
            es_compatible = False
            problemas.append("Paciente no requiere aislamiento pero está en sala individual con camas compartidas disponibles")
        
        # 5. Verificar si está en cama de complejidad SUPERIOR con alternativas disponibles (NUEVO)
        if self.paciente_en_cama_complejidad_superior(paciente, cama):
            es_compatible = False
            # Generar mensaje descriptivo
            complejidad_paciente = paciente.complejidad_requerida or self.calcular_complejidad_paciente(paciente)
            complejidad_cama = self.obtener_complejidad_maxima_cama(cama)
            nombres = {
                ComplejidadEnum.NINGUNA: "NINGUNA",
                ComplejidadEnum.BAJA: "BAJA", 
                ComplejidadEnum.MEDIA: "UTI",
                ComplejidadEnum.ALTA: "UCI",
            }
            nombre_paciente = nombres.get(complejidad_paciente, str(complejidad_paciente))
            nombre_cama = nombres.get(complejidad_cama, str(complejidad_cama))
            problemas.append(
                f"Paciente requiere {nombre_paciente} pero está en cama {nombre_cama} - "
                f"hay camas {nombre_paciente} disponibles"
            )
        
        return es_compatible, problemas
    
    def verificar_compatibilidad_al_llegar(
        self,
        paciente: Paciente,
        cama: Cama
    ) -> Tuple[bool, str]:
        """
        Verificación de compatibilidad cuando el paciente llega a la cama.
        
        Se usa al completar un traslado para decidir si:
        - El paciente puede quedarse (OCUPADA)
        - El paciente necesita nueva cama (CAMA_EN_ESPERA)
        
        Returns:
            Tuple (es_compatible, mensaje)
        """
        es_compatible, problemas = self.verificar_compatibilidad_completa(paciente, cama)
        
        if es_compatible:
            return True, "Paciente compatible con cama"
        else:
            return False, "; ".join(problemas)

    def verificar_compatibilidad_arribo(
        self,
        paciente: Paciente,
        cama: Cama
    ) -> Tuple[bool, List[str]]:
        """
        Verificación de compatibilidad SIMPLIFICADA para cuando el paciente 
        llega a una cama que YA FUE ASIGNADA previamente.
        
        IMPORTANTE: Esta verificación NO busca alternativas porque la cama 
        ya fue asignada intencionalmente. Solo verifica incompatibilidades 
        FUNDAMENTALES que harían imposible que el paciente permanezca.
        
        Verifica SOLO:
        1. Compatibilidad de sexo (en salas compartidas)
        2. Compatibilidad de aislamiento requerido
        3. Complejidad MÍNIMA (cama debe soportar nivel del paciente)
        
        NO verifica (porque la cama ya fue asignada):
        - Si hay camas compartidas disponibles
        - Si hay camas de mejor nivel disponibles
        
        Returns:
            Tuple (es_compatible, lista_de_problemas)
        """
        problemas = []
        es_compatible = True
        
        # 1. Verificar sexo
        compatible_sexo, msg_sexo = self.verificar_compatibilidad_sexo(paciente, cama)
        if not compatible_sexo:
            es_compatible = False
            problemas.append(msg_sexo)
        
        # 2. Verificar aislamiento requerido
        compatible_aislamiento, msg_aislamiento = self.verificar_compatibilidad_aislamiento(paciente, cama)
        if not compatible_aislamiento:
            es_compatible = False
            problemas.append(msg_aislamiento)
        
        # 3. Verificar complejidad MÍNIMA de la cama (cama no puede ser INFERIOR)
        compatible_complejidad, msg_complejidad = self.verificar_compatibilidad_complejidad(paciente, cama)
        if not compatible_complejidad:
            es_compatible = False
            problemas.append(msg_complejidad)
        
        # NO verificamos:
        # - paciente_deberia_buscar_cama_compartida (busca alternativas)
        # - paciente_en_cama_complejidad_superior (busca alternativas)
        
        logger.debug(
            f"Verificación arribo para {paciente.nombre} en cama {cama.identificador}: "
            f"compatible={es_compatible}, problemas={problemas}"
        )
        
        return es_compatible, problemas

# ============================================
# FUNCIONES HELPER PARA INTEGRACIÓN
# ============================================

def verificar_y_actualizar_sexo_sala_al_egreso(session: Session, cama: Cama) -> None:
    """
    Actualiza el sexo de la sala cuando un paciente egresa de una cama.
    
    Debe llamarse después de que un paciente libera una cama.
    """
    if cama.sala:
        service = CompatibilidadService(session)
        nuevo_sexo = service.actualizar_sexo_sala(cama.sala)
        logger.debug(f"Sexo de sala actualizado a {nuevo_sexo} tras egreso de cama {cama.identificador}")


def verificar_y_actualizar_sexo_sala_al_ingreso(session: Session, cama: Cama, paciente: Paciente) -> None:
    """
    Actualiza el sexo de la sala cuando un paciente ingresa a una cama.
    
    Debe llamarse después de asignar un paciente a una cama.
    """
    if cama.sala:
        service = CompatibilidadService(session)
        if not service.es_sala_individual(cama.sala):
            sala = cama.sala
            if not sala.sexo_asignado:
                # Guardar como string normalizado
                sala.sexo_asignado = _normalizar_sexo(paciente.sexo)
                session.add(sala)
                logger.debug(f"Sexo de sala {sala.id} asignado a {sala.sexo_asignado} por ingreso de paciente")

def recalcular_sexo_sala_al_cancelar_asignacion(session: Session, cama: Cama) -> None:
    """
    Recalcula el sexo de la sala cuando se cancela una asignación.
    
    Debe llamarse después de que se cancela un traslado y se libera una cama destino.
    Esto asegura que si no quedan más pacientes/asignaciones del mismo sexo,
    la sala quede disponible para otro sexo.
    """
    if cama.sala:
        service = CompatibilidadService(session)
        if not service.es_sala_individual(cama.sala):
            nuevo_sexo = service.actualizar_sexo_sala(cama.sala)
            logger.debug(
                f"Sexo de sala {cama.sala.id} recalculado a {nuevo_sexo} "
                f"tras cancelar asignación de cama {cama.identificador}"
            )