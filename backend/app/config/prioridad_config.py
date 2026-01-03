"""
Configuración del Sistema de Priorización v3.1

Este archivo permite ajustar los pesos y umbrales del sistema de priorización
sin modificar el código principal. Puede ser sobrescrito por configuración
en base de datos o variables de entorno.

"""
from typing import Dict, Set
from dataclasses import dataclass, field


@dataclass
class ConfiguracionPrioridad:
    """
    Configuración completa del sistema de priorización v3.1.
    
    Permite ajustar todos los pesos y umbrales desde un solo lugar.
    """
    
    # ========================================
    # PESOS BASE POR TIPO DE PACIENTE
    # ========================================
    peso_tipo: Dict[str, int] = field(default_factory=lambda: {
        'hospitalizado': 200,
        'urgencia': 100,
        'derivado': 80,
        'ambulatorio': 60,
    })
    
    # ========================================
    # BONUS POR SERVICIO DE ORIGEN
    # ========================================
    bonus_servicio_origen: Dict[str, int] = field(default_factory=lambda: {
        'uci': 60,
        'uti': 50,
        'aislamiento': 40,
        'otros': 0,
    })
    
    # ========================================
    # IVC - ÍNDICE DE VULNERABILIDAD CLÍNICA
    # ========================================
    
    # Edad granular
    bonus_edad_granular: Dict[str, int] = field(default_factory=lambda: {
        'muy_mayor': 25,      # ≥80 años
        'mayor': 20,          # 70-79 años
        'adulto_mayor': 15,   # 60-69 años
        'infante': 20,        # <5 años
        'nino': 15,           # 5-14 años
        'adulto': 0,          # 15-59 años
    })
    
    # Umbrales de edad
    umbral_muy_mayor: int = 80
    umbral_mayor: int = 70
    umbral_adulto_mayor: int = 60
    umbral_nino: int = 15
    umbral_infante: int = 5
    
    # Timers activos
    bonus_monitorizacion_activa: int = 20
    bonus_observacion_activa: int = 15
    
    # Complejidad (para IVC)
    bonus_complejidad_ivc: Dict[str, int] = field(default_factory=lambda: {
        'alta': 30,
        'media': 20,
        'baja': 5,
        'ninguna': 0,
    })
    
    # Aislamiento crítico
    bonus_aislamiento_ivc: Dict[str, int] = field(default_factory=lambda: {
        'aereo': 20,
        'aéreo': 20,
        'ambiente_protegido': 15,
        'ambiente protegido': 15,
        'especial': 10,
        'gotitas': 5,
        'contacto': 3,
        'ninguno': 0,
    })
    
    # Condiciones especiales
    bonus_embarazada: int = 20
    bonus_casos_especiales: int = 15
    
    # ========================================
    # FRC - FACTOR DE REQUERIMIENTOS CRÍTICOS
    # ========================================
    bonus_requerimientos_criticos: Dict[str, int] = field(default_factory=lambda: {
        'drogas_vasoactivas': 15,
        'sedacion': 12,
        'oxigeno': 10,
        'procedimiento_invasivo': 10,
        'aspiracion_secreciones': 10,
    })
    
    # ========================================
    # KEYWORDS PARA DETECCIÓN DE REQUERIMIENTOS
    # ========================================
    # Estas pueden ser ajustadas según la nomenclatura del hospital
    
    keywords_drogas_vasoactivas: Set[str] = field(default_factory=lambda: {
        'drogas_vasoactivas', 'vasoactivos', 'noradrenalina', 'norepinefrina',
        'dopamina', 'dobutamina', 'vasopresina', 'adrenalina', 'epinefrina',
        'dva', 'drogas vasoactivas', 'aminas', 'inotropicos', 'vasopresores'
    })
    
    keywords_sedacion: Set[str] = field(default_factory=lambda: {
        'sedacion', 'sedación', 'midazolam', 'propofol', 'fentanilo', 'fentanil',
        'dexmedetomidina', 'ketamina', 'bic_sedacion', 'infusion_sedacion',
        'sedoanalgesia', 'analgosedacion'
    })
    
    keywords_oxigeno: Set[str] = field(default_factory=lambda: {
        'oxigeno', 'oxígeno', 'o2', 'naricera', 'canula_nasal', 'cánula nasal',
        'mascarilla', 'venturi', 'multiventuri', 'reservorio', 'mascara_reservorio',
        'cnaf', 'alto_flujo', 'alto flujo', 'vmni', 'ventilacion_no_invasiva',
        'vmi', 'ventilacion_mecanica', 'ventilacion_invasiva', 'tubo_endotraqueal',
        'intubacion', 'soporte_ventilatorio', 'oxigenoterapia'
    })
    
    keywords_aspiracion: Set[str] = field(default_factory=lambda: {
        'aspiracion_secreciones', 'aspiración', 'aspiracion', 'aspiracion_invasiva',
        'traqueostomia', 'traqueostomía', 'tqt', 'tubo_endotraqueal', 'tet',
        'secreciones_invasivo', 'manejo_via_aerea', 'toilet_bronquial'
    })
    
    keywords_procedimiento: Set[str] = field(default_factory=lambda: {
        'procedimiento_invasivo', 'cirugia', 'cirugía', 'quirurgico', 'quirúrgico',
        'intervencion', 'intervención', 'operacion', 'operación', 'biopsia',
        'drenaje', 'puncion', 'punción', 'cateterismo', 'endoscopia'
    })
    
    # ========================================
    # CONFIGURACIÓN DE TIEMPO NO LINEAL
    # ========================================
    
    # Urgencias
    tiempo_urgencia_fase1_horas: int = 4
    tiempo_urgencia_fase1_pts: float = 3.0
    tiempo_urgencia_fase2_horas: int = 8
    tiempo_urgencia_fase2_pts: float = 5.0
    tiempo_urgencia_fase3_pts: float = 8.0
    tiempo_urgencia_boost: int = 40
    
    # Derivados
    tiempo_derivado_fase1_horas: int = 12
    tiempo_derivado_fase1_pts: float = 2.0
    tiempo_derivado_fase2_horas: int = 24
    tiempo_derivado_fase2_pts: float = 4.0
    tiempo_derivado_fase3_pts: float = 6.0
    tiempo_derivado_boost: int = 45
    
    # Ambulatorios
    tiempo_ambulatorio_fase1_horas: int = 48
    tiempo_ambulatorio_fase1_pts: float = 1.0
    tiempo_ambulatorio_fase2_horas: int = 96
    tiempo_ambulatorio_fase2_pts: float = 2.0
    tiempo_ambulatorio_fase3_pts: float = 4.0
    tiempo_ambulatorio_boost: int = 50
    
    # ========================================
    # MECANISMO DE RESCATE
    # ========================================
    umbral_rescate_horas: Dict[str, int] = field(default_factory=lambda: {
        'urgencia': 24,
        'derivado': 48,
        'ambulatorio': 168,  # 7 días
    })
    prioridad_rescate: int = 500
    
    # ========================================
    # SERVICIOS CONOCIDOS (para clasificación)
    # ========================================
    servicios_uci: Set[str] = field(default_factory=lambda: {
        'uci', 'unidad de cuidados intensivos', 'cuidados intensivos', 'upc'
    })
    
    servicios_uti: Set[str] = field(default_factory=lambda: {
        'uti', 'unidad de tratamiento intensivo', 'intermedio', 'uci intermedia'
    })
    
    servicios_aislamiento: Set[str] = field(default_factory=lambda: {
        'aislamiento', 'aislado', 'aislamiento respiratorio',
        'aislamiento contacto', 'aislamiento gotitas', 'aislamiento aereo'
    })


# Instancia por defecto (puede ser sobrescrita)
config_prioridad_default = ConfiguracionPrioridad()


def obtener_config_prioridad() -> ConfiguracionPrioridad:
    """
    Obtiene la configuración de prioridad actual.
    
    Puede ser extendido para cargar desde base de datos o variables de entorno.
    """
    # TODO: Implementar carga desde BD o env vars si es necesario
    return config_prioridad_default


def actualizar_keywords_hospital(
    config: ConfiguracionPrioridad,
    nuevas_keywords: Dict[str, Set[str]]
) -> ConfiguracionPrioridad:
    """
    Permite al hospital agregar sus propias keywords a la configuración.
    
    Args:
        config: Configuración actual
        nuevas_keywords: Dict con las categorías y nuevas keywords a agregar
        
    Returns:
        Configuración actualizada
    """
    if 'drogas_vasoactivas' in nuevas_keywords:
        config.keywords_drogas_vasoactivas.update(nuevas_keywords['drogas_vasoactivas'])
    
    if 'sedacion' in nuevas_keywords:
        config.keywords_sedacion.update(nuevas_keywords['sedacion'])
    
    if 'oxigeno' in nuevas_keywords:
        config.keywords_oxigeno.update(nuevas_keywords['oxigeno'])
    
    if 'aspiracion' in nuevas_keywords:
        config.keywords_aspiracion.update(nuevas_keywords['aspiracion'])
    
    if 'procedimiento' in nuevas_keywords:
        config.keywords_procedimiento.update(nuevas_keywords['procedimiento'])
    
    return config