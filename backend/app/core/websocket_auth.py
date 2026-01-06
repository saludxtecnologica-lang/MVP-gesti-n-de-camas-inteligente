"""
WebSocket con Autenticación.
Middleware y dependencias para WebSocket autenticado.
"""
from typing import Optional, List, Dict, Set
from fastapi import WebSocket, WebSocketDisconnect, Query, status
from sqlmodel import Session
import json
import asyncio

from app.core.database import get_session_direct
from app.services.auth_service import auth_service
from app.models.usuario import Usuario


class ConnectionManager:
    """
    Gestor de conexiones WebSocket con autenticación.
    """
    
    def __init__(self):
        # Conexiones activas: {user_id: {websocket, ...}}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Conexiones por hospital: {hospital_id: {websocket, ...}}
        self.hospital_connections: Dict[str, Set[WebSocket]] = {}
        # Todas las conexiones
        self.all_connections: Set[WebSocket] = set()
        # Mapeo websocket -> user_id
        self.websocket_user: Dict[WebSocket, str] = {}
        # Mapeo websocket -> hospital_id
        self.websocket_hospital: Dict[WebSocket, Optional[str]] = {}
    
    async def authenticate(
        self, 
        websocket: WebSocket, 
        token: Optional[str] = None
    ) -> Optional[Usuario]:
        """
        Autentica una conexión WebSocket.
        Retorna el usuario si es válido, None si no.
        """
        if not token:
            return None
        
        # Decodificar token
        payload = auth_service.decode_token(token)
        if not payload or payload.type != "access":
            return None
        
        # Obtener usuario
        session = get_session_direct()
        try:
            user = auth_service.get_user_by_id(payload.sub, session)
            if not user or not user.is_active:
                return None
            return user
        finally:
            session.close()
    
    async def connect(
        self, 
        websocket: WebSocket,
        user: Usuario,
        hospital_id: Optional[str] = None
    ):
        """
        Acepta y registra una conexión WebSocket autenticada.
        """
        await websocket.accept()
        
        user_id = user.id
        
        # Registrar en conexiones de usuario
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        
        # Registrar en conexiones de hospital
        effective_hospital = hospital_id or user.hospital_id
        if effective_hospital:
            if effective_hospital not in self.hospital_connections:
                self.hospital_connections[effective_hospital] = set()
            self.hospital_connections[effective_hospital].add(websocket)
        
        # Registrar en todas las conexiones
        self.all_connections.add(websocket)
        
        # Mapeos inversos
        self.websocket_user[websocket] = user_id
        self.websocket_hospital[websocket] = effective_hospital
        
        # Enviar mensaje de bienvenida
        await self.send_personal(websocket, {
            "tipo": "conectado",
            "mensaje": f"Bienvenido, {user.nombre_completo}",
            "user_id": user_id,
            "hospital_id": effective_hospital
        })
    
    def disconnect(self, websocket: WebSocket):
        """
        Desregistra una conexión WebSocket.
        """
        # Obtener user_id y hospital_id
        user_id = self.websocket_user.get(websocket)
        hospital_id = self.websocket_hospital.get(websocket)
        
        # Remover de conexiones de usuario
        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Remover de conexiones de hospital
        if hospital_id and hospital_id in self.hospital_connections:
            self.hospital_connections[hospital_id].discard(websocket)
            if not self.hospital_connections[hospital_id]:
                del self.hospital_connections[hospital_id]
        
        # Remover de todas las conexiones
        self.all_connections.discard(websocket)
        
        # Limpiar mapeos
        self.websocket_user.pop(websocket, None)
        self.websocket_hospital.pop(websocket, None)
    
    async def send_personal(self, websocket: WebSocket, message: dict):
        """Envía un mensaje a una conexión específica."""
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)
    
    async def send_to_user(self, user_id: str, message: dict):
        """Envía un mensaje a todas las conexiones de un usuario."""
        connections = self.active_connections.get(user_id, set()).copy()
        for websocket in connections:
            await self.send_personal(websocket, message)
    
    async def send_to_hospital(self, hospital_id: str, message: dict):
        """Envía un mensaje a todas las conexiones de un hospital."""
        connections = self.hospital_connections.get(hospital_id, set()).copy()
        for websocket in connections:
            await self.send_personal(websocket, message)
    
    async def broadcast(self, message: dict):
        """Envía un mensaje a todas las conexiones."""
        connections = self.all_connections.copy()
        for websocket in connections:
            await self.send_personal(websocket, message)
    
    async def broadcast_except(self, message: dict, exclude_user_id: str):
        """Envía un mensaje a todos excepto a un usuario específico."""
        for websocket in self.all_connections.copy():
            if self.websocket_user.get(websocket) != exclude_user_id:
                await self.send_personal(websocket, message)
    
    def get_online_users(self) -> List[str]:
        """Retorna lista de user_ids conectados."""
        return list(self.active_connections.keys())
    
    def get_connection_count(self) -> int:
        """Retorna número total de conexiones."""
        return len(self.all_connections)
    
    def is_user_online(self, user_id: str) -> bool:
        """Verifica si un usuario está conectado."""
        return user_id in self.active_connections


# Instancia global del manager
manager = ConnectionManager()


# ============================================
# ENDPOINT DE WEBSOCKET
# ============================================

async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    hospital_id: Optional[str] = Query(None)
):
    """
    Endpoint principal de WebSocket con autenticación.
    
    Uso:
        ws://localhost:8000/api/ws?token=<jwt_token>&hospital_id=<hospital_id>
    
    Añadir a tu router:
        from app.core.websocket_auth import websocket_endpoint
        
        @router.websocket("/ws")
        async def ws_endpoint(
            websocket: WebSocket,
            token: Optional[str] = Query(None),
            hospital_id: Optional[str] = Query(None)
        ):
            await websocket_endpoint(websocket, token, hospital_id)
    """
    # Autenticar
    user = await manager.authenticate(websocket, token)
    
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Conectar
    await manager.connect(websocket, user, hospital_id)
    
    try:
        while True:
            # Recibir mensajes del cliente
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Procesar mensaje según tipo
                msg_type = message.get("tipo")
                
                if msg_type == "ping":
                    await manager.send_personal(websocket, {"tipo": "pong"})
                
                # Añadir más handlers según necesidad...
                
            except json.JSONDecodeError:
                await manager.send_personal(websocket, {
                    "tipo": "error",
                    "mensaje": "Mensaje inválido"
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)
        raise e


# ============================================
# FUNCIONES DE BROADCAST PARA EVENTOS
# ============================================

async def notificar_cambio_cama(hospital_id: str, cama_id: str, evento: str, datos: dict = None):
    """Notifica un cambio en una cama a todos los conectados del hospital."""
    message = {
        "tipo": evento,
        "hospital_id": hospital_id,
        "cama_id": cama_id,
        "datos": datos or {},
        "reload": True
    }
    await manager.send_to_hospital(hospital_id, message)


async def notificar_paciente_creado(hospital_id: str, paciente_id: str, datos: dict = None):
    """Notifica la creación de un paciente."""
    message = {
        "tipo": "paciente_creado",
        "hospital_id": hospital_id,
        "paciente_id": paciente_id,
        "datos": datos or {},
        "reload": True,
        "play_sound": True
    }
    await manager.send_to_hospital(hospital_id, message)


async def notificar_asignacion(hospital_id: str, paciente_id: str, cama_id: str, datos: dict = None):
    """Notifica una asignación de cama."""
    message = {
        "tipo": "asignacion_completada",
        "hospital_id": hospital_id,
        "paciente_id": paciente_id,
        "cama_id": cama_id,
        "datos": datos or {},
        "reload": True,
        "play_sound": True
    }
    await manager.send_to_hospital(hospital_id, message)


async def notificar_derivacion(
    hospital_origen_id: str, 
    hospital_destino_id: str, 
    paciente_id: str, 
    evento: str,
    datos: dict = None
):
    """Notifica un evento de derivación a ambos hospitales."""
    message = {
        "tipo": evento,
        "hospital_origen_id": hospital_origen_id,
        "hospital_destino_id": hospital_destino_id,
        "paciente_id": paciente_id,
        "datos": datos or {},
        "reload": True,
        "play_sound": True
    }
    await manager.send_to_hospital(hospital_origen_id, message)
    await manager.send_to_hospital(hospital_destino_id, message)


async def notificar_broadcast(mensaje: str, tipo: str = "info"):
    """Envía una notificación a todos los usuarios conectados."""
    message = {
        "tipo": "notificacion",
        "notification_type": tipo,
        "message": mensaje,
        "play_sound": tipo in ["warning", "error"]
    }
    await manager.broadcast(message)


# ============================================
# EJEMPLO DE USO EN ROUTER
# ============================================

"""
# En tu archivo de router (ej: app/api/websocket.py)

from fastapi import APIRouter, WebSocket, Query
from typing import Optional
from app.core.websocket_auth import websocket_endpoint

router = APIRouter()

@router.websocket("/ws")
async def ws(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    hospital_id: Optional[str] = Query(None)
):
    await websocket_endpoint(websocket, token, hospital_id)


# En tus endpoints de API, puedes notificar cambios:

from app.core.websocket_auth import (
    notificar_paciente_creado,
    notificar_asignacion,
    notificar_cambio_cama
)

@router.post("/pacientes")
async def crear_paciente(data: PacienteCreate, ...):
    # ... crear paciente ...
    
    # Notificar a todos los conectados del hospital
    await notificar_paciente_creado(
        hospital_id=paciente.hospital_id,
        paciente_id=paciente.id,
        datos={"nombre": paciente.nombre}
    )
    
    return paciente
"""
