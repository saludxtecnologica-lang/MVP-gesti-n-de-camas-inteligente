"""
CONFIGURACIÓN - Sin campos de teléfono (están en Hospital)

"""
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.websocket_manager import manager
from app.schemas.responses import MessageResponse
from app.repositories.configuracion_repo import ConfiguracionRepository

router = APIRouter()


# ============================================
# SCHEMAS
# ============================================
from pydantic import BaseModel
from typing import Optional


class ConfiguracionResponseMinutos(BaseModel):
    """Respuesta de configuración en MINUTOS para el frontend."""
    modo_manual: bool
    tiempo_limpieza_minutos: int
    tiempo_espera_oxigeno_minutos: int


class ConfiguracionUpdateMinutos(BaseModel):
    """Request de actualización en MINUTOS desde el frontend."""
    modo_manual: Optional[bool] = None
    tiempo_limpieza_minutos: Optional[int] = None
    tiempo_espera_oxigeno_minutos: Optional[int] = None


# ============================================
# FUNCIONES DE CONVERSIÓN
# ============================================
def segundos_a_minutos(segundos: int) -> int:
    """Convierte segundos a minutos (redondeando hacia arriba)."""
    return (segundos + 59) // 60


def minutos_a_segundos(minutos: int) -> int:
    """Convierte minutos a segundos."""
    return minutos * 60


# ============================================
# ENDPOINTS
# ============================================
@router.get("", response_model=ConfiguracionResponseMinutos)
def obtener_configuracion(session: Session = Depends(get_session)):
    """
    Obtiene la configuración del sistema.
    
    NOTA: Los tiempos se devuelven en MINUTOS para el frontend.
    NOTA: Los teléfonos están en el modelo Hospital, no aquí.
    """
    repo = ConfiguracionRepository(session)
    config = repo.obtener_o_crear()
    
    return ConfiguracionResponseMinutos(
        modo_manual=config.modo_manual,
        tiempo_limpieza_minutos=segundos_a_minutos(config.tiempo_limpieza_segundos),
        tiempo_espera_oxigeno_minutos=segundos_a_minutos(config.tiempo_espera_oxigeno_segundos)
    )


@router.put("", response_model=ConfiguracionResponseMinutos)
async def actualizar_configuracion(
    config_update: ConfiguracionUpdateMinutos,
    session: Session = Depends(get_session)
):
    """
    Actualiza la configuración del sistema.
    
    NOTA: El frontend envía los tiempos en MINUTOS.
          Se convierten a segundos internamente.
    """
    repo = ConfiguracionRepository(session)
    
    # Convertir minutos a segundos para almacenamiento interno
    tiempo_limpieza_seg = None
    if config_update.tiempo_limpieza_minutos is not None:
        tiempo_limpieza_seg = minutos_a_segundos(config_update.tiempo_limpieza_minutos)
    
    tiempo_oxigeno_seg = None
    if config_update.tiempo_espera_oxigeno_minutos is not None:
        tiempo_oxigeno_seg = minutos_a_segundos(config_update.tiempo_espera_oxigeno_minutos)
    
    config = repo.actualizar_configuracion(
        modo_manual=config_update.modo_manual,
        tiempo_limpieza=tiempo_limpieza_seg,
        tiempo_oxigeno=tiempo_oxigeno_seg
    )
    
    # Notificar cambio de configuración
    await manager.broadcast({
        "tipo": "configuracion_actualizada",
        "modo_manual": config.modo_manual
    })
    
    return ConfiguracionResponseMinutos(
        modo_manual=config.modo_manual,
        tiempo_limpieza_minutos=segundos_a_minutos(config.tiempo_limpieza_segundos),
        tiempo_espera_oxigeno_minutos=segundos_a_minutos(config.tiempo_espera_oxigeno_segundos)
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