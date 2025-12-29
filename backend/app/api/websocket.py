"""
Endpoints de WebSocket.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
import logging

from app.core.websocket_manager import manager

router = APIRouter()
logger = logging.getLogger("gestion_camas.websocket")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Endpoint WebSocket para actualizaciones en tiempo real.
    
    El cliente puede enviar mensajes JSON con:
    - {"action": "subscribe", "hospital_id": "..."} para suscribirse a un hospital
    - {"action": "ping"} para mantener la conexión viva
    """
    await manager.connect(websocket)
    
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
                    hospital_id = data.get("hospital_id")
                    if hospital_id:
                        # Suscribir a hospital específico
                        if hospital_id not in manager.hospital_subscriptions:
                            manager.hospital_subscriptions[hospital_id] = set()
                        manager.hospital_subscriptions[hospital_id].add(websocket)
                        
                        await websocket.send_json({
                            "tipo": "subscribed",
                            "hospital_id": hospital_id
                        })
                
                elif action == "ping":
                    await websocket.send_json({"tipo": "pong"})
                
                elif action == "unsubscribe":
                    hospital_id = data.get("hospital_id")
                    if hospital_id and hospital_id in manager.hospital_subscriptions:
                        manager.hospital_subscriptions[hospital_id].discard(websocket)
                        await websocket.send_json({
                            "tipo": "unsubscribed",
                            "hospital_id": hospital_id
                        })
                
            except WebSocketDisconnect:
                # Cliente desconectado, salir del loop
                break
            except RuntimeError as e:
                # Error de runtime (ej: "Cannot call receive once a disconnect...")
                if "disconnect" in str(e).lower():
                    break
                logger.warning(f"Error de runtime en WebSocket: {e}")
                break
            except Exception as e:
                # Otros errores - verificar si es por desconexión
                error_msg = str(e).lower()
                if "disconnect" in error_msg or "closed" in error_msg:
                    break
                logger.warning(f"Error procesando mensaje WebSocket: {e}")
                # Para otros errores, continuar el loop pero con precaución
                # Si el websocket ya no está conectado, salir
                if websocket.client_state != WebSocketState.CONNECTED:
                    break
                
    except WebSocketDisconnect:
        pass  # Desconexión normal
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
    finally:
        # Siempre limpiar la conexión al salir
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
            # Verificar si la conexión sigue activa
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