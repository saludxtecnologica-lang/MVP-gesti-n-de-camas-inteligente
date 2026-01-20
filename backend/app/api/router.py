"""
Router principal que agrupa todos los sub-routers.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from urllib.parse import unquote
from app.api.auth_router import router as auth_router

import os

from app.api import health
from app.api import hospitales
from app.api import camas
from app.api import pacientes
from app.api import traslados
from app.api import derivaciones
from app.api import altas
from app.api import manual
from app.api import estadisticas
from app.api import configuracion
from app.api import websocket
from app.api import dev_init  # Endpoint temporal para inicialización
from app.api import dev_debug  # Endpoint temporal para debug
from app.api import dev_fix_roles  # Endpoint temporal para arreglar roles
from app.api import dev_fix_passwords  # Endpoint temporal para arreglar contraseñas
from app.api import dev_fix_enums  # Endpoint temporal para arreglar enums
from app.config import settings

api_router = APIRouter()
api_router.include_router(auth_router)

# ============================================
# ENDPOINT PARA DOCUMENTOS
# ============================================
# Usar settings.UPLOAD_DIR para consistencia con donde se guardan los archivos
UPLOAD_DIR = getattr(settings, 'UPLOAD_DIR', 'uploads/documentos')

@api_router.get("/documentos/{filename:path}")
async def obtener_documento(filename: str):
    """
    Obtiene un documento PDF por su nombre de archivo.
    
    El parámetro :path permite capturar el nombre completo incluyendo caracteres especiales.
    Se decodifica la URL para manejar espacios (%20) y otros caracteres.
    """
    # Decodificar el nombre del archivo (convierte %20 a espacio, etc.)
    decoded_filename = unquote(filename)
    
    # Construir la ruta del archivo
    filepath = os.path.join(UPLOAD_DIR, decoded_filename)
    
    # Verificar que el archivo existe
    if not os.path.exists(filepath):
        # Log para debugging
        print(f"[DEBUG] Documento no encontrado: {filepath}")
        print(f"[DEBUG] Filename original: {filename}")
        print(f"[DEBUG] Filename decodificado: {decoded_filename}")
        print(f"[DEBUG] UPLOAD_DIR: {UPLOAD_DIR}")
        
        # Intentar buscar en directorio alternativo si no se encuentra
        alt_filepath = os.path.join("uploads", decoded_filename)
        if os.path.exists(alt_filepath):
            filepath = alt_filepath
        else:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    return FileResponse(
        path=filepath, 
        media_type='application/pdf',
        headers={
            "Content-Disposition": f'inline; filename="{decoded_filename}"'
        }
    )

# ============================================
# INCLUIR TODOS LOS ROUTERS
# ============================================

# Health Check (sin autenticación para load balancers)
api_router.include_router(health.router)

api_router.include_router(
    hospitales.router,
    prefix="/hospitales",
    tags=["Hospitales"]
)

api_router.include_router(
    camas.router,
    prefix="/camas",
    tags=["Camas"]
)

api_router.include_router(
    pacientes.router,
    prefix="/pacientes",
    tags=["Pacientes"]
)

api_router.include_router(
    traslados.router,
    prefix="/traslados",
    tags=["Traslados"]
)

api_router.include_router(
    derivaciones.router,
    prefix="/derivaciones",
    tags=["Derivaciones"]
)

api_router.include_router(
    altas.router,
    prefix="/altas",
    tags=["Altas"]
)

api_router.include_router(
    manual.router,
    prefix="/manual",
    tags=["Modo Manual"]
)

api_router.include_router(
    estadisticas.router,
    prefix="/estadisticas",
    tags=["Estadísticas"]
)

api_router.include_router(
    configuracion.router,
    prefix="/configuracion",
    tags=["Configuración"]
)

api_router.include_router(
    websocket.router,
    tags=["WebSocket"]
)

# Endpoints de desarrollo (ELIMINAR EN PRODUCCIÓN)
api_router.include_router(dev_init.router)
api_router.include_router(dev_debug.router)
api_router.include_router(dev_fix_roles.router)
api_router.include_router(dev_fix_passwords.router)
api_router.include_router(dev_fix_enums.router)
