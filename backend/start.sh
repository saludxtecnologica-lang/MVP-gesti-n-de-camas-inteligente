#!/bin/bash
# Script de inicio para Railway
# Lee la variable de entorno PORT y ejecuta uvicorn

# Obtener el puerto (Railway lo asigna, o usar 8000 por defecto)
PORT=${PORT:-8000}

echo "🚀 Iniciando servidor en puerto $PORT"

# Ejecutar uvicorn
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"
