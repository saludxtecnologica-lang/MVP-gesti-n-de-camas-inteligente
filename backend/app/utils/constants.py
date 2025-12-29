"""
Constantes del sistema.
Valores fijos utilizados en toda la aplicación.
"""

# ============================================
# CONSTANTES DE TIEMPO (en segundos)
# ============================================

# Tiempo por defecto para limpieza de camas
TIEMPO_LIMPIEZA_DEFAULT = 60

# Tiempo de espera post-desactivación de oxígeno
TIEMPO_ESPERA_OXIGENO_DEFAULT = 120

# Intervalo del proceso automático
PROCESO_AUTOMATICO_INTERVALO = 5

# Tiempo máximo de espera antes de escalar prioridad
TIEMPO_ESCALAMIENTO_PRIORIDAD = 3600  # 1 hora


# ============================================
# CONSTANTES DE PRIORIDAD
# ============================================

# Pesos base por tipo de paciente
PRIORIDAD_PESO_TIPO = {
    "urgencia": 100,
    "derivado": 80,
    "hospitalizado": 60,
    "ambulatorio": 40,
}

# Pesos por complejidad
PRIORIDAD_PESO_COMPLEJIDAD = {
    "alta": 50,
    "media": 30,
    "baja": 15,
    "ninguna": 0,
}

# Bonus por categoría de edad
PRIORIDAD_BONUS_EDAD = {
    "adulto_mayor": 20,
    "pediatrico": 15,
    "adulto": 0,
}

# Bonus por tipo de aislamiento
PRIORIDAD_BONUS_AISLAMIENTO = {
    "aereo": 25,
    "ambiente_protegido": 20,
    "especial": 15,
    "gotitas": 10,
    "contacto": 5,
    "ninguno": 0,
}

# Factor de tiempo (puntos por hora de espera)
PRIORIDAD_FACTOR_TIEMPO_HORA = 2.0

# Bonus adicionales
PRIORIDAD_BONUS_EMBARAZO = 15
PRIORIDAD_BONUS_CASOS_ESPECIALES = 10


# ============================================
# CONSTANTES DE ARCHIVOS
# ============================================

# Tamaño máximo de archivo (bytes)
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB

# Extensiones permitidas
EXTENSIONES_PERMITIDAS = [".pdf"]

# Directorio de uploads
UPLOAD_DIRECTORY = "uploads"


# ============================================
# CONSTANTES DE VALIDACIÓN
# ============================================

# Edad mínima y máxima
EDAD_MINIMA = 0
EDAD_MAXIMA = 120

# Rangos de categorías de edad
EDAD_PEDIATRICO_MAX = 14
EDAD_ADULTO_MAX = 59

# Longitud máxima de campos
MAX_LONGITUD_NOMBRE = 200
MAX_LONGITUD_DIAGNOSTICO = 500
MAX_LONGITUD_NOTAS = 2000


# ============================================
# CONSTANTES DE ESTADOS
# ============================================

# Estados de cama que cuentan como "ocupada"
ESTADOS_CAMA_OCUPADA = [
    "ocupada",
    "cama_en_espera",
    "traslado_saliente",
    "traslado_confirmado",
    "alta_sugerida",
    "cama_alta",
    "espera_derivacion",
    "derivacion_confirmada",
]

# Estados de cama que permiten asignación
ESTADOS_CAMA_DISPONIBLE = ["libre"]

# Estados de cama que bloquean operaciones
ESTADOS_CAMA_BLOQUEADOS = ["bloqueada", "en_limpieza"]

# Estados de derivación
ESTADOS_DERIVACION = {
    "PENDIENTE": "pendiente",
    "ACEPTADA": "aceptada",
    "RECHAZADA": "rechazada",
    "COMPLETADA": "completada",
}


# ============================================
# CONSTANTES DE SERVICIOS
# ============================================

# Mapeo de complejidad a tipos de servicio compatibles
MAPEO_COMPLEJIDAD_SERVICIO = {
    "alta": ["uci"],
    "media": ["uti", "uci"],
    "baja": ["medicina", "cirugia", "uti", "medico_quirurgico"],
    "ninguna": ["medicina", "cirugia", "medico_quirurgico"],
}

# Servicios que requieren sala individual
SERVICIOS_SALA_INDIVIDUAL = ["uci", "uti"]

# Servicios que permiten pacientes pediátricos
SERVICIOS_PEDIATRIA = ["medicina", "pediatria"]


# ============================================
# CONSTANTES DE REQUERIMIENTOS
# ============================================

# Requerimientos que no definen complejidad
REQUERIMIENTOS_NO_DEFINEN = [
    "estudio",
    "procedimiento_diagnostico",
    "espera_resultado",
    "evaluacion_especialista",
]

# Requerimientos de baja complejidad
REQUERIMIENTOS_BAJA = [
    "tratamiento_ev_frecuente",
    "curacion_compleja",
    "oxigeno_bajo_flujo",
    "kinesioterapia",
    "nutricion_enteral",
    "control_signos_vitales",
]

# Requerimientos de UTI (media complejidad)
REQUERIMIENTOS_UTI = [
    "droga_vasoactiva",
    "ventilacion_no_invasiva",
    "oxigeno_alto_flujo",
    "monitorizacion_continua",
    "transfusion_frecuente",
    "dialisis",
]

# Requerimientos de UCI (alta complejidad)
REQUERIMIENTOS_UCI = [
    "vmi",
    "soporte_vital_avanzado",
    "monitorizacion_invasiva",
    "drogas_vasoactivas_multiples",
    "hipotermia_terapeutica",
]

# Casos especiales
CASOS_ESPECIALES = [
    "paciente_psiquiatrico",
    "riesgo_fuga",
    "aislamiento_estricto",
    "cuidados_paliativos",
    "donante_organos",
]


# ============================================
# CONSTANTES DE WEBSOCKET
# ============================================

# Tipos de notificación
NOTIFICACION_TIPOS = {
    "INFO": "info",
    "SUCCESS": "success",
    "WARNING": "warning",
    "ERROR": "error",
    "ASIGNACION": "asignacion",
}

# Tipos de eventos WebSocket
EVENTO_TIPOS = {
    "CAMA_ACTUALIZADA": "cama_actualizada",
    "PACIENTE_CREADO": "paciente_creado",
    "PACIENTE_ACTUALIZADO": "paciente_actualizado",
    "TRASLADO_COMPLETADO": "traslado_completado",
    "TRASLADO_CANCELADO": "traslado_cancelado",
    "DERIVACION_SOLICITADA": "derivacion_solicitada",
    "DERIVACION_ACEPTADA": "derivacion_aceptada",
    "DERIVACION_RECHAZADA": "derivacion_rechazada",
    "ALTA_INICIADA": "alta_iniciada",
    "ALTA_COMPLETADA": "alta_completada",
    "CONFIGURACION_ACTUALIZADA": "configuracion_actualizada",
    "ASIGNACION_AUTOMATICA": "asignacion_automatica",
}


# ============================================
# MENSAJES DEL SISTEMA
# ============================================

MENSAJES = {
    # Éxito
    "PACIENTE_CREADO": "Paciente registrado exitosamente",
    "PACIENTE_ACTUALIZADO": "Paciente actualizado exitosamente",
    "TRASLADO_COMPLETADO": "Traslado completado exitosamente",
    "TRASLADO_CANCELADO": "Traslado cancelado",
    "DERIVACION_SOLICITADA": "Derivación solicitada exitosamente",
    "DERIVACION_ACEPTADA": "Derivación aceptada",
    "DERIVACION_RECHAZADA": "Derivación rechazada",
    "ALTA_INICIADA": "Proceso de alta iniciado",
    "ALTA_COMPLETADA": "Alta completada, cama en limpieza",
    "CAMA_BLOQUEADA": "Cama bloqueada correctamente",
    "CAMA_DESBLOQUEADA": "Cama desbloqueada correctamente",
    
    # Errores
    "ERROR_PACIENTE_NO_ENCONTRADO": "Paciente no encontrado",
    "ERROR_CAMA_NO_ENCONTRADA": "Cama no encontrada",
    "ERROR_HOSPITAL_NO_ENCONTRADO": "Hospital no encontrado",
    "ERROR_CAMA_NO_DISPONIBLE": "La cama no está disponible",
    "ERROR_PACIENTE_SIN_CAMA": "El paciente no tiene cama asignada",
    "ERROR_TRASLADO_NO_PENDIENTE": "No hay traslado pendiente",
    "ERROR_DERIVACION_NO_PENDIENTE": "No hay derivación pendiente",
    "ERROR_TIPO_PACIENTE_INVALIDO": "Tipo de paciente no válido para esta operación",
}
