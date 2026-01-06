"""
Endpoints de WebSocket.
"""
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState
import logging

from app.core.websocket_manager import manager

router = APIRouter()
logger = logging.getLogger("gestion_camas.websocket")


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    hospital_id: Optional[str] = Query(None)
):
    """
    Endpoint WebSocket para actualizaciones en tiempo real.
    
    Parámetros de query:
    - token: JWT token de autenticación (opcional por ahora)
    - hospital_id: ID del hospital para suscripción automática
    
    El cliente puede enviar mensajes JSON con:
    - {"action": "subscribe", "hospital_id": "..."} para suscribirse a un hospital
    - {"action": "ping"} para mantener la conexión viva
    """
    # TODO: Validar token aquí si se requiere autenticación
    # if token:
    #     from app.services.auth_service import auth_service
    #     payload = auth_service.decode_token(token)
    #     if not payload:
    #         await websocket.close(code=4001)
    #         return
    
    # Conectar con hospital_id si se proporcionó
    await manager.connect(websocket, hospital_id)
    
    try:
        while True:
            # Verificar si la conexión sigue activa antes de intentar recibir
            if websocket.client_state != WebSocketState.CONNECTED:
                break
                
            try:
                data = await websocket.receive_json()
                
                # Manejar diferentes acciones
                action = data.get("action")
                
                if action == "subscribe":
                    sub_hospital_id = data.get("hospital_id")
                    if sub_hospital_id:
                        # Suscribir a hospital específico
                        if sub_hospital_id not in manager.hospital_subscriptions:
                            manager.hospital_subscriptions[sub_hospital_id] = set()
                        manager.hospital_subscriptions[sub_hospital_id].add(websocket)
                        
                        await websocket.send_json({
                            "tipo": "subscribed",
                            "hospital_id": sub_hospital_id
                        })
                
                elif action == "ping":
                    await websocket.send_json({"tipo": "pong"})
                
                elif action == "unsubscribe":
                    unsub_hospital_id = data.get("hospital_id")
                    if unsub_hospital_id and unsub_hospital_id in manager.hospital_subscriptions:
                        manager.hospital_subscriptions[unsub_hospital_id].discard(websocket)
                        await websocket.send_json({
                            "tipo": "unsubscribed",
                            "hospital_id": unsub_hospital_id
                        })
                
            except WebSocketDisconnect:
                break
            except RuntimeError as e:
                if "disconnect" in str(e).lower():
                    break
                logger.warning(f"Error de runtime en WebSocket: {e}")
                break
            except Exception as e:
                error_msg = str(e).lower()
                if "disconnect" in error_msg or "closed" in error_msg:
                    break
                logger.warning(f"Error procesando mensaje WebSocket: {e}")
                if websocket.client_state != WebSocketState.CONNECTED:
                    break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
    finally:
        manager.disconnect(websocket)
        logger.info("Cliente WebSocket desconectado")


@router.websocket("/ws/{hospital_id}")
async def websocket_hospital_endpoint(websocket: WebSocket, hospital_id: str):
    """
    Endpoint WebSocket con suscripción automática a un hospital.
    """
    await manager.connect(websocket, hospital_id)
    
    try:
        while True:
            if websocket.client_state != WebSocketState.CONNECTED:
                break
                
            try:
                data = await websocket.receive_json()
                action = data.get("action")
                
                if action == "ping":
                    await websocket.send_json({"tipo": "pong"})
                
            except WebSocketDisconnect:
                break
            except RuntimeError as e:
                if "disconnect" in str(e).lower():
                    break
                logger.warning(f"Error de runtime en WebSocket hospital: {e}")
                break
            except Exception as e:
                error_msg = str(e).lower()
                if "disconnect" in error_msg or "closed" in error_msg:
                    break
                logger.warning(f"Error procesando mensaje: {e}")
                if websocket.client_state != WebSocketState.CONNECTED:
                    break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Error en WebSocket hospital: {e}")
    finally:
        manager.disconnect(websocket)
