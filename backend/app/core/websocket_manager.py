"""
Gestor de conexiones WebSocket.
Maneja broadcast de mensajes a clientes conectados.
"""
from typing import List, Dict, Optional, Set
from fastapi import WebSocket
import logging

logger = logging.getLogger("gestion_camas.websocket")


class ConnectionManager:
    """
    Gestor de conexiones WebSocket.
    
    Características:
    - Mantiene lista de conexiones activas
    - Soporta suscripción por hospital
    - Limpieza automática de conexiones muertas
    - Notificaciones con tipo y sonido opcional
    """
    
    def __init__(self):
        # Todas las conexiones activas
        self.active_connections: List[WebSocket] = []
        # Conexiones por hospital (para broadcast selectivo)
        self.hospital_subscriptions: Dict[str, Set[WebSocket]] = {}
    
    async def connect(
        self, 
        websocket: WebSocket, 
        hospital_id: Optional[str] = None
    ) -> None:
        """
        Conecta un cliente WebSocket.
        
        Args:
            websocket: Conexión WebSocket
            hospital_id: ID del hospital al que suscribirse (opcional)
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if hospital_id:
            if hospital_id not in self.hospital_subscriptions:
                self.hospital_subscriptions[hospital_id] = set()
            self.hospital_subscriptions[hospital_id].add(websocket)
        
        logger.info(
            f"WebSocket conectado. Total conexiones: {len(self.active_connections)}"
        )
    
    def disconnect(self, websocket: WebSocket) -> None:
        """
        Desconecta un cliente WebSocket.
        
        Args:
            websocket: Conexión a desconectar
        """
        # Remover de lista general
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Remover de suscripciones de hospital
        for hospital_id in list(self.hospital_subscriptions.keys()):
            if websocket in self.hospital_subscriptions[hospital_id]:
                self.hospital_subscriptions[hospital_id].discard(websocket)
                # Limpiar set vacío
                if not self.hospital_subscriptions[hospital_id]:
                    del self.hospital_subscriptions[hospital_id]
        
        logger.info(
            f"WebSocket desconectado. Total conexiones: {len(self.active_connections)}"
        )
    
    async def broadcast(self, message: dict) -> None:
        """
        Envía un mensaje a todos los clientes conectados.
        
        Args:
            message: Diccionario con el mensaje a enviar
        """
        disconnected: List[WebSocket] = []
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error enviando mensaje: {e}")
                disconnected.append(connection)
        
        # Limpiar conexiones muertas
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_to_hospital(
        self, 
        hospital_id: str, 
        message: dict
    ) -> None:
        """
        Envía un mensaje solo a clientes suscritos a un hospital específico.
        
        Args:
            hospital_id: ID del hospital
            message: Diccionario con el mensaje a enviar
        """
        if hospital_id not in self.hospital_subscriptions:
            return
        
        disconnected: List[WebSocket] = []
        
        for connection in self.hospital_subscriptions[hospital_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error enviando mensaje a hospital {hospital_id}: {e}")
                disconnected.append(connection)
        
        # Limpiar conexiones muertas
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_notification(
        self,
        message: dict,
        notification_type: str = "info",
        play_sound: bool = False,
        hospital_id: Optional[str] = None
    ) -> None:
        """
        Envía una notificación con tipo específico y sonido opcional.
        
        Args:
            message: Diccionario con el mensaje
            notification_type: Tipo de notificación (info, success, warning, error, asignacion)
            play_sound: Si debe reproducir sonido en el cliente
            hospital_id: Si se especifica, envía solo a ese hospital
        """
        notification = {
            **message,
            "notification_type": notification_type,
            "play_sound": play_sound or notification_type == "asignacion"
        }
        
        if hospital_id:
            await self.broadcast_to_hospital(hospital_id, notification)
        else:
            await self.broadcast(notification)
    
    async def send_update(
        self,
        tipo: str,
        hospital_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Envía una actualización de estado.
        
        Args:
            tipo: Tipo de actualización (cama_actualizada, paciente_creado, etc.)
            hospital_id: Hospital afectado
            **kwargs: Datos adicionales
        """
        message = {
            "tipo": tipo,
            "hospital_id": hospital_id,
            **kwargs
        }
        
        if hospital_id:
            await self.broadcast_to_hospital(hospital_id, message)
        else:
            await self.broadcast(message)
    
    @property
    def connection_count(self) -> int:
        """Número total de conexiones activas."""
        return len(self.active_connections)
    
    def get_hospital_connection_count(self, hospital_id: str) -> int:
        """Número de conexiones para un hospital específico."""
        if hospital_id in self.hospital_subscriptions:
            return len(self.hospital_subscriptions[hospital_id])
        return 0


# Instancia global del manager
manager = ConnectionManager()