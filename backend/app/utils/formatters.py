"""
Funciones de formateo.
Conversión y presentación de datos.
"""
from typing import Optional, List, Any, Dict
from datetime import datetime, timedelta
import json


# ============================================
# FORMATEO DE TIEMPO
# ============================================

def formatear_tiempo_espera(minutos: int) -> str:
    """
    Formatea minutos de espera en formato legible.
    
    Args:
        minutos: Tiempo en minutos
    
    Returns:
        String formateado (ej: "45 min", "2h 30m", "1d 5h")
    
    Examples:
        >>> formatear_tiempo_espera(45)
        '45 min'
        >>> formatear_tiempo_espera(150)
        '2h 30m'
        >>> formatear_tiempo_espera(1500)
        '1d 1h'
    """
    if minutos < 0:
        return "0 min"
    
    if minutos < 60:
        return f"{minutos} min"
    
    horas = minutos // 60
    mins = minutos % 60
    
    if horas < 24:
        if mins > 0:
            return f"{horas}h {mins}m"
        return f"{horas}h"
    
    dias = horas // 24
    hrs = horas % 24
    
    if hrs > 0:
        return f"{dias}d {hrs}h"
    return f"{dias}d"


def formatear_segundos(segundos: int) -> str:
    """
    Formatea segundos en formato legible.
    
    Args:
        segundos: Tiempo en segundos
    
    Returns:
        String formateado
    """
    if segundos < 60:
        return f"{segundos}s"
    
    minutos = segundos // 60
    segs = segundos % 60
    
    if minutos < 60:
        if segs > 0:
            return f"{minutos}m {segs}s"
        return f"{minutos}m"
    
    return formatear_tiempo_espera(minutos)


def formatear_duracion(inicio: datetime, fin: Optional[datetime] = None) -> str:
    """
    Formatea la duración entre dos fechas.
    
    Args:
        inicio: Fecha de inicio
        fin: Fecha de fin (usa ahora si no se especifica)
    
    Returns:
        Duración formateada
    """
    if fin is None:
        fin = datetime.utcnow()
    
    delta = fin - inicio
    minutos = int(delta.total_seconds() / 60)
    
    return formatear_tiempo_espera(minutos)


# ============================================
# FORMATEO DE FECHAS
# ============================================

def formatear_fecha(
    fecha: Optional[datetime], 
    formato: str = '%d/%m/%Y %H:%M'
) -> str:
    """
    Formatea una fecha de manera segura.
    
    Args:
        fecha: Datetime a formatear (puede ser None)
        formato: Formato de salida
    
    Returns:
        String con fecha formateada o 'No disponible'
    """
    if not fecha:
        return 'No disponible'
    try:
        return fecha.strftime(formato)
    except (ValueError, AttributeError):
        return str(fecha)


def formatear_fecha_corta(fecha: Optional[datetime]) -> str:
    """
    Formatea fecha en formato corto (DD/MM/YYYY).
    
    Args:
        fecha: Datetime a formatear
    
    Returns:
        Fecha formateada
    """
    return formatear_fecha(fecha, '%d/%m/%Y')


def formatear_hora(fecha: Optional[datetime]) -> str:
    """
    Formatea solo la hora (HH:MM).
    
    Args:
        fecha: Datetime a formatear
    
    Returns:
        Hora formateada
    """
    return formatear_fecha(fecha, '%H:%M')


def formatear_fecha_relativa(fecha: datetime) -> str:
    """
    Formatea fecha como tiempo relativo (hace X minutos/horas/días).
    
    Args:
        fecha: Datetime a formatear
    
    Returns:
        Tiempo relativo
    """
    ahora = datetime.utcnow()
    delta = ahora - fecha
    
    segundos = int(delta.total_seconds())
    
    if segundos < 60:
        return "hace un momento"
    
    minutos = segundos // 60
    if minutos < 60:
        return f"hace {minutos} min"
    
    horas = minutos // 60
    if horas < 24:
        return f"hace {horas}h"
    
    dias = horas // 24
    if dias < 7:
        return f"hace {dias}d"
    
    semanas = dias // 7
    if semanas < 4:
        return f"hace {semanas} sem"
    
    return formatear_fecha_corta(fecha)


# ============================================
# FORMATEO DE RUN
# ============================================

def formatear_run(run: str) -> str:
    """
    Formatea RUN chileno con puntos y guión.
    
    Args:
        run: RUN sin formato o parcialmente formateado
    
    Returns:
        RUN formateado (ej: "12.345.678-9")
    
    Examples:
        >>> formatear_run("123456785")
        '12.345.678-5'
        >>> formatear_run("12345678-5")
        '12.345.678-5'
    """
    # Limpiar
    cleaned = run.replace(".", "").replace("-", "").replace(" ", "").upper()
    
    if len(cleaned) < 2:
        return cleaned
    
    dv = cleaned[-1]
    numbers = cleaned[:-1]
    
    # Agregar puntos cada 3 dígitos desde la derecha
    formatted = ""
    for i, digit in enumerate(reversed(numbers)):
        if i > 0 and i % 3 == 0:
            formatted = "." + formatted
        formatted = digit + formatted
    
    return f"{formatted}-{dv}"


def limpiar_run(run: str) -> str:
    """
    Limpia RUN removiendo puntos y espacios.
    
    Args:
        run: RUN con formato
    
    Returns:
        RUN limpio (ej: "12345678-5")
    """
    cleaned = run.replace(".", "").replace(" ", "").upper()
    
    # Asegurar que tenga guión
    if "-" not in cleaned and len(cleaned) >= 2:
        cleaned = cleaned[:-1] + "-" + cleaned[-1]
    
    return cleaned


# ============================================
# FORMATEO DE NÚMEROS
# ============================================

def formatear_porcentaje(valor: float, decimales: int = 1) -> str:
    """
    Formatea un valor como porcentaje.
    
    Args:
        valor: Valor entre 0 y 100
        decimales: Número de decimales
    
    Returns:
        Porcentaje formateado
    """
    return f"{valor:.{decimales}f}%"


def formatear_numero(numero: int) -> str:
    """
    Formatea número con separador de miles.
    
    Args:
        numero: Número a formatear
    
    Returns:
        Número formateado
    """
    return f"{numero:,}".replace(",", ".")


# ============================================
# FORMATEO DE TEXTO
# ============================================

def truncar_texto(texto: str, max_length: int = 50, sufijo: str = "...") -> str:
    """
    Trunca texto a una longitud máxima.
    
    Args:
        texto: Texto a truncar
        max_length: Longitud máxima
        sufijo: Sufijo a agregar si se trunca
    
    Returns:
        Texto truncado
    """
    if not texto:
        return ""
    
    if len(texto) <= max_length:
        return texto
    
    return texto[:max_length - len(sufijo)] + sufijo


def capitalizar_nombre(nombre: str) -> str:
    """
    Capitaliza un nombre (primera letra de cada palabra en mayúscula).
    
    Args:
        nombre: Nombre a capitalizar
    
    Returns:
        Nombre capitalizado
    """
    if not nombre:
        return ""
    
    # Palabras que no se capitalizan (conectores)
    excepciones = {"de", "del", "la", "las", "los", "el", "y", "e", "o", "u"}
    
    palabras = nombre.lower().split()
    resultado = []
    
    for i, palabra in enumerate(palabras):
        if i == 0 or palabra not in excepciones:
            resultado.append(palabra.capitalize())
        else:
            resultado.append(palabra)
    
    return " ".join(resultado)


def formatear_lista_texto(items: List[str], separador: str = ", ", ultimo: str = " y ") -> str:
    """
    Formatea una lista como texto legible.
    
    Args:
        items: Lista de strings
        separador: Separador entre items
        ultimo: Separador antes del último item
    
    Returns:
        Texto formateado
    
    Examples:
        >>> formatear_lista_texto(["a", "b", "c"])
        'a, b y c'
    """
    if not items:
        return ""
    
    if len(items) == 1:
        return items[0]
    
    if len(items) == 2:
        return f"{items[0]}{ultimo}{items[1]}"
    
    return separador.join(items[:-1]) + ultimo + items[-1]


# ============================================
# FORMATEO DE ESTADOS
# ============================================

ESTADOS_DISPLAY = {
    "libre": "Libre",
    "ocupada": "Ocupada",
    "traslado_entrante": "Traslado Entrante",
    "cama_en_espera": "En Espera",
    "traslado_saliente": "Traslado Saliente",
    "traslado_confirmado": "Traslado Confirmado",
    "alta_sugerida": "Alta Sugerida",
    "cama_alta": "En Alta",
    "en_limpieza": "En Limpieza",
    "bloqueada": "Bloqueada",
    "espera_derivacion": "Espera Derivación",
    "derivacion_confirmada": "Derivación Confirmada",
}

COMPLEJIDAD_DISPLAY = {
    "ninguna": "Sin requerimientos",
    "baja": "Baja Complejidad",
    "media": "UTI",
    "alta": "UCI",
}

TIPO_PACIENTE_DISPLAY = {
    "urgencia": "Urgencia",
    "ambulatorio": "Ambulatorio",
    "hospitalizado": "Hospitalizado",
    "derivado": "Derivado",
}


def formatear_estado_cama(estado: str) -> str:
    """
    Formatea estado de cama para mostrar.
    
    Args:
        estado: Estado en formato enum
    
    Returns:
        Estado legible
    """
    return ESTADOS_DISPLAY.get(estado, estado.replace("_", " ").title())


def formatear_complejidad(complejidad: str) -> str:
    """
    Formatea complejidad para mostrar.
    
    Args:
        complejidad: Complejidad en formato enum
    
    Returns:
        Complejidad legible
    """
    return COMPLEJIDAD_DISPLAY.get(complejidad, complejidad.title())


def formatear_tipo_paciente(tipo: str) -> str:
    """
    Formatea tipo de paciente para mostrar.
    
    Args:
        tipo: Tipo en formato enum
    
    Returns:
        Tipo legible
    """
    return TIPO_PACIENTE_DISPLAY.get(tipo, tipo.title())


# ============================================
# FORMATEO DE JSON
# ============================================

def formatear_json(data: Any, indent: int = 2) -> str:
    """
    Formatea datos como JSON legible.
    
    Args:
        data: Datos a formatear
        indent: Indentación
    
    Returns:
        JSON formateado
    """
    try:
        return json.dumps(data, indent=indent, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(data)


def formatear_dict_para_log(data: Dict[str, Any], max_value_length: int = 100) -> str:
    """
    Formatea un diccionario para logging.
    
    Args:
        data: Diccionario a formatear
        max_value_length: Longitud máxima de valores
    
    Returns:
        String formateado
    """
    items = []
    for key, value in data.items():
        value_str = str(value)
        if len(value_str) > max_value_length:
            value_str = value_str[:max_value_length] + "..."
        items.append(f"{key}={value_str}")
    
    return ", ".join(items)
