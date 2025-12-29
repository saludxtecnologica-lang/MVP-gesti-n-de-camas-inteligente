"""
Funciones de validación.
"""
import re


def validar_run_chileno(run: str) -> bool:
    """
    Valida formato y dígito verificador de RUN chileno.
    
    Args:
        run: RUN en formato "12345678-9" o "12345678-K"
    
    Returns:
        True si el RUN es válido
    """
    # Limpiar y normalizar
    run = run.upper().replace(".", "").replace(" ", "")
    
    # Verificar formato básico
    if not re.match(r'^\d{7,8}-[\dK]$', run):
        return False
    
    # Separar número y dígito verificador
    partes = run.split('-')
    numero = partes[0]
    dv_ingresado = partes[1]
    
    # Calcular dígito verificador
    suma = 0
    multiplicador = 2
    
    for digito in reversed(numero):
        suma += int(digito) * multiplicador
        multiplicador = multiplicador + 1 if multiplicador < 7 else 2
    
    resto = suma % 11
    dv_calculado = 11 - resto
    
    if dv_calculado == 11:
        dv_esperado = '0'
    elif dv_calculado == 10:
        dv_esperado = 'K'
    else:
        dv_esperado = str(dv_calculado)
    
    return dv_ingresado == dv_esperado


def validar_formato_run(run: str) -> bool:
    """
    Valida solo el formato del RUN (sin verificar dígito).
    
    Args:
        run: RUN a validar
    
    Returns:
        True si el formato es válido
    """
    if not run:
        return False
    pattern = r'^\d{7,8}-[\dkK]$'
    return bool(re.match(pattern, run.strip()))


def formatear_run(run: str) -> str:
    """
    Formatea RUN con puntos y guión.
    
    Args:
        run: RUN sin formato
    
    Returns:
        RUN formateado (ej: "12.345.678-9")
    """
    # Limpiar
    cleaned = run.replace(".", "").replace("-", "").replace(" ", "").upper()
    
    if len(cleaned) < 2:
        return cleaned
    
    dv = cleaned[-1]
    numbers = cleaned[:-1]
    
    # Agregar puntos
    formatted = ""
    for i, digit in enumerate(reversed(numbers)):
        if i > 0 and i % 3 == 0:
            formatted = "." + formatted
        formatted = digit + formatted
    
    return f"{formatted}-{dv}"


def validar_email(email: str) -> bool:
    """
    Valida formato de email.
    
    Args:
        email: Email a validar
    
    Returns:
        True si el formato es válido
    """
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def validar_edad(edad: int) -> bool:
    """
    Valida que la edad esté en rango válido.
    
    Args:
        edad: Edad a validar
    
    Returns:
        True si es válida
    """
    return 0 <= edad <= 120