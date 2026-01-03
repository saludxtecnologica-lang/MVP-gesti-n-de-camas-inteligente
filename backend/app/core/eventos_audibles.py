"""
Módulo de eventos audibles para Text-to-Speech.

Este módulo proporciona funciones para crear eventos WebSocket
enriquecidos con información necesaria para las notificaciones TTS.
"""
from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger("gestion_camas.eventos_audibles")


def crear_evento_asignacion(
    cama_destino_identificador: str,
    paciente_nombre: str,
    servicio_origen_id: Optional[str],
    servicio_origen_nombre: Optional[str],
    servicio_destino_id: str,
    servicio_destino_nombre: str,
    cama_origen_identificador: Optional[str],
    hospital_id: str,
    paciente_id: str,
    cama_id: str
) -> Dict[str, Any]:
    """
    Crea un evento de asignación completada con datos TTS.
    
    El mensaje se reproduce en el servicio de ORIGEN y DESTINO.
    
    Mensaje TTS:
    "Cama [identificador], ha sido asignada a paciente [nombre], 
    de origen servicio [servicio], de la cama [cama_origen]"
    
    Args:
        cama_destino_identificador: Identificador de la cama asignada
        paciente_nombre: Nombre del paciente
        servicio_origen_id: ID del servicio de origen (puede ser None)
        servicio_origen_nombre: Nombre del servicio de origen
        servicio_destino_id: ID del servicio de destino
        servicio_destino_nombre: Nombre del servicio de destino
        cama_origen_identificador: Identificador de la cama de origen (puede ser None)
        hospital_id: ID del hospital
        paciente_id: ID del paciente
        cama_id: ID de la cama asignada
    
    Returns:
        Diccionario con el evento WebSocket
    """
    return {
        "tipo": "asignacion_completada",
        "hospital_id": hospital_id,
        "paciente_id": paciente_id,
        "cama_id": cama_id,
        "reload": True,
        "play_sound": True,
        "timestamp": datetime.utcnow().isoformat(),
        # Campos TTS
        "tts_habilitado": True,
        "cama_identificador": cama_destino_identificador,
        "paciente_nombre": paciente_nombre,
        "servicio_origen_id": servicio_origen_id,
        "servicio_origen_nombre": servicio_origen_nombre,
        "servicio_destino_id": servicio_destino_id,
        "servicio_destino_nombre": servicio_destino_nombre,
        "cama_origen_identificador": cama_origen_identificador,
        "mensaje": f"Cama {cama_destino_identificador} asignada a {paciente_nombre}"
    }


def crear_evento_traslado_completado(
    cama_origen_identificador: str,
    paciente_nombre: str,
    servicio_origen_id: str,
    servicio_origen_nombre: str,
    servicio_destino_id: str,
    servicio_destino_nombre: str,
    hospital_id: str,
    paciente_id: str
) -> Dict[str, Any]:
    """
    Crea un evento de traslado completado con datos TTS.
    
    El mensaje se reproduce SOLO en el servicio de ORIGEN.
    
    Mensaje TTS:
    "Traslado a servicio [destino] de paciente [nombre] completado, 
    cama [cama] entra a fase de limpieza"
    
    Args:
        cama_origen_identificador: Identificador de la cama de origen
        paciente_nombre: Nombre del paciente
        servicio_origen_id: ID del servicio de origen
        servicio_origen_nombre: Nombre del servicio de origen
        servicio_destino_id: ID del servicio de destino
        servicio_destino_nombre: Nombre del servicio de destino
        hospital_id: ID del hospital
        paciente_id: ID del paciente
    
    Returns:
        Diccionario con el evento WebSocket
    """
    return {
        "tipo": "traslado_completado",
        "hospital_id": hospital_id,
        "paciente_id": paciente_id,
        "reload": True,
        "play_sound": True,
        "timestamp": datetime.utcnow().isoformat(),
        # Campos TTS
        "tts_habilitado": True,
        "cama_origen_identificador": cama_origen_identificador,
        "paciente_nombre": paciente_nombre,
        "servicio_origen_id": servicio_origen_id,
        "servicio_origen_nombre": servicio_origen_nombre,
        "servicio_destino_id": servicio_destino_id,
        "servicio_destino_nombre": servicio_destino_nombre,
        "mensaje": f"Traslado de {paciente_nombre} a {servicio_destino_nombre} completado"
    }


def crear_evento_derivacion_aceptada(
    paciente_nombre: str,
    servicio_origen_id: Optional[str],
    servicio_origen_nombre: Optional[str],
    cama_origen_identificador: Optional[str],
    hospital_origen_id: str,
    hospital_origen_nombre: str,
    hospital_destino_id: str,
    hospital_destino_nombre: str,
    paciente_id: str,
    derivacion_id: str
) -> Dict[str, Any]:
    """
    Crea un evento de derivación aceptada con datos TTS.
    
    El mensaje se reproduce SOLO en el servicio de ORIGEN del hospital de origen.
    
    Mensaje TTS:
    "Paciente [nombre] ha sido aceptado en [hospital destino] 
    en espera de asignación de cama"
    
    Args:
        paciente_nombre: Nombre del paciente
        servicio_origen_id: ID del servicio de origen (puede ser None)
        servicio_origen_nombre: Nombre del servicio de origen
        cama_origen_identificador: Identificador de la cama de origen (puede ser None)
        hospital_origen_id: ID del hospital de origen
        hospital_origen_nombre: Nombre del hospital de origen
        hospital_destino_id: ID del hospital de destino
        hospital_destino_nombre: Nombre del hospital de destino
        paciente_id: ID del paciente
        derivacion_id: ID de la derivación
    
    Returns:
        Diccionario con el evento WebSocket
    """
    return {
        "tipo": "derivacion_aceptada",
        "hospital_id": hospital_origen_id,  # Evento se muestra en hospital origen
        "hospital_origen_id": hospital_origen_id,
        "hospital_destino_id": hospital_destino_id,
        "paciente_id": paciente_id,
        "derivacion_id": derivacion_id,
        "reload": True,
        "play_sound": True,
        "timestamp": datetime.utcnow().isoformat(),
        # Campos TTS
        "tts_habilitado": True,
        "paciente_nombre": paciente_nombre,
        "servicio_origen_id": servicio_origen_id,
        "servicio_origen_nombre": servicio_origen_nombre,
        "cama_origen_identificador": cama_origen_identificador,
        "hospital_destino_nombre": hospital_destino_nombre,
        "hospital_origen_nombre": hospital_origen_nombre,
        "mensaje": f"Paciente {paciente_nombre} aceptado en {hospital_destino_nombre}"
    }