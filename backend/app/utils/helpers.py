"""
Funciones auxiliares compartidas.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from app.models.enums import EstadoCamaEnum, ESTADOS_CAMA_OCUPADA


def calcular_estadisticas_camas(camas: List[Any]) -> Dict[str, int]:
    """
    Calcula estadísticas de una lista de camas.
    
    Args:
        camas: Lista de objetos Cama
    
    Returns:
        Diccionario con conteos por estado
    """
    stats = {
        "total": len(camas),
        "libres": 0,
        "ocupadas": 0,
        "traslado_entrante": 0,
        "en_limpieza": 0,
        "bloqueadas": 0,
    }
    
    for cama in camas:
        if cama.estado == EstadoCamaEnum.LIBRE:
            stats["libres"] += 1
        elif cama.estado == EstadoCamaEnum.BLOQUEADA:
            stats["bloqueadas"] += 1
        elif cama.estado == EstadoCamaEnum.EN_LIMPIEZA:
            stats["en_limpieza"] += 1
        elif cama.estado == EstadoCamaEnum.TRASLADO_ENTRANTE:
            stats["traslado_entrante"] += 1
        elif cama.estado in ESTADOS_CAMA_OCUPADA:
            stats["ocupadas"] += 1
    
    return stats


def crear_paciente_response(paciente: Any) -> Dict[str, Any]:
    """
    Crea un diccionario de respuesta para un paciente.
    
    Args:
        paciente: Objeto Paciente
    
    Returns:
        Diccionario con datos del paciente
    """
    from app.schemas.paciente import PacienteResponse
    
    return PacienteResponse(
        id=paciente.id,
        nombre=paciente.nombre,
        run=paciente.run,
        sexo=paciente.sexo,
        edad=paciente.edad,
        edad_categoria=paciente.edad_categoria,
        es_embarazada=paciente.es_embarazada,
        diagnostico=paciente.diagnostico,
        tipo_enfermedad=paciente.tipo_enfermedad,
        tipo_aislamiento=paciente.tipo_aislamiento,
        notas_adicionales=paciente.notas_adicionales,
        complejidad_requerida=paciente.complejidad_requerida,
        tipo_paciente=paciente.tipo_paciente,
        hospital_id=paciente.hospital_id,
        cama_id=paciente.cama_id,
        cama_destino_id=paciente.cama_destino_id,
        en_lista_espera=paciente.en_lista_espera,
        estado_lista_espera=paciente.estado_lista_espera,
        prioridad_calculada=paciente.prioridad_calculada,
        tiempo_espera_min=paciente.tiempo_espera_min,
        requiere_nueva_cama=paciente.requiere_nueva_cama,
        derivacion_hospital_destino_id=paciente.derivacion_hospital_destino_id,
        derivacion_motivo=paciente.derivacion_motivo,
        derivacion_estado=paciente.derivacion_estado,
        alta_solicitada=paciente.alta_solicitada,
        created_at=paciente.created_at,
        updated_at=paciente.updated_at,
        requerimientos_no_definen=safe_json_loads(paciente.requerimientos_no_definen),
        requerimientos_baja=safe_json_loads(paciente.requerimientos_baja),
        requerimientos_uti=safe_json_loads(paciente.requerimientos_uti),
        requerimientos_uci=safe_json_loads(paciente.requerimientos_uci),
        casos_especiales=safe_json_loads(paciente.casos_especiales),
        motivo_observacion=paciente.motivo_observacion,
        justificacion_observacion=paciente.justificacion_observacion,
        motivo_monitorizacion=paciente.motivo_monitorizacion,
        justificacion_monitorizacion=paciente.justificacion_monitorizacion,
        procedimiento_invasivo=paciente.procedimiento_invasivo,
        documento_adjunto=paciente.documento_adjunto,
        esperando_evaluacion_oxigeno=paciente.esperando_evaluacion_oxigeno,
    )


def safe_json_loads(value: Any, default: Any = None) -> Any:
    """
    Parsea JSON de manera segura.
    
    Args:
        value: Valor a parsear
        default: Valor por defecto si falla
    
    Returns:
        Valor parseado o default
    """
    if default is None:
        default = []
    
    if not value:
        return default
    
    if isinstance(value, list):
        return value
    
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else default
        except (json.JSONDecodeError, TypeError, ValueError):
            return default
    
    return default


def safe_json_dumps(value: Any) -> str:
    """
    Convierte a JSON string de manera segura.
    
    Args:
        value: Valor a convertir
    
    Returns:
        String JSON
    """
    if value is None:
        return "[]"
    
    if isinstance(value, str):
        try:
            json.loads(value)
            return value
        except:
            return "[]"
    
    try:
        return json.dumps(value)
    except (TypeError, ValueError):
        return "[]"


def formatear_tiempo_espera(minutos: int) -> str:
    """
    Formatea minutos de espera en formato legible.
    
    Args:
        minutos: Tiempo en minutos
    
    Returns:
        String formateado (ej: "45 min", "2h 30m", "1d 5h")
    """
    if minutos < 60:
        return f"{minutos} min"
    
    horas = minutos // 60
    mins = minutos % 60
    
    if horas < 24:
        return f"{horas}h {mins}m"
    
    dias = horas // 24
    hrs = horas % 24
    return f"{dias}d {hrs}h"


def formatear_fecha(fecha: Optional[datetime], formato: str = '%d/%m/%Y %H:%M') -> str:
    """
    Formatea una fecha de manera segura.
    
    Args:
        fecha: Datetime a formatear
        formato: Formato de salida
    
    Returns:
        String formateado o 'No disponible'
    """
    if not fecha:
        return 'No disponible'
    try:
        return fecha.strftime(formato)
    except (ValueError, AttributeError):
        return str(fecha)