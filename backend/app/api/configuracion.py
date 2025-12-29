"""
Endpoints de Configuración.
"""
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.websocket_manager import manager
from app.schemas.responses import ConfiguracionResponse, ConfiguracionUpdate, MessageResponse
from app.repositories.configuracion_repo import ConfiguracionRepository

router = APIRouter()


@router.get("", response_model=ConfiguracionResponse)
def obtener_configuracion(session: Session = Depends(get_session)):
    """Obtiene la configuración del sistema."""
    repo = ConfiguracionRepository(session)
    config = repo.obtener_o_crear()
    
    return ConfiguracionResponse(
        modo_manual=config.modo_manual,
        tiempo_limpieza_segundos=config.tiempo_limpieza_segundos,
        tiempo_espera_oxigeno_segundos=config.tiempo_espera_oxigeno_segundos
    )


@router.put("", response_model=ConfiguracionResponse)
async def actualizar_configuracion(
    config_update: ConfiguracionUpdate,
    session: Session = Depends(get_session)
):
    """Actualiza la configuración del sistema."""
    repo = ConfiguracionRepository(session)
    
    config = repo.actualizar_configuracion(
        modo_manual=config_update.modo_manual,
        tiempo_limpieza=config_update.tiempo_limpieza_segundos,
        tiempo_oxigeno=config_update.tiempo_espera_oxigeno_segundos
    )
    
    # Notificar cambio de configuración
    await manager.broadcast({
        "tipo": "configuracion_actualizada",
        "modo_manual": config.modo_manual
    })
    
    return ConfiguracionResponse(
        modo_manual=config.modo_manual,
        tiempo_limpieza_segundos=config.tiempo_limpieza_segundos,
        tiempo_espera_oxigeno_segundos=config.tiempo_espera_oxigeno_segundos
    )


@router.post("/toggle-modo", response_model=MessageResponse)
async def toggle_modo_manual(session: Session = Depends(get_session)):
    """Alterna entre modo manual y automático."""
    repo = ConfiguracionRepository(session)
    config = repo.obtener_o_crear()
    
    nuevo_modo = not config.modo_manual
    config = repo.actualizar_configuracion(modo_manual=nuevo_modo)
    
    await manager.broadcast({
        "tipo": "modo_cambiado",
        "modo_manual": nuevo_modo
    })
    
    modo_texto = "manual" if nuevo_modo else "automático"
    return MessageResponse(
        success=True,
        message=f"Sistema cambiado a modo {modo_texto}",
        data={"modo_manual": nuevo_modo}
    )