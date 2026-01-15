# ============================================
# Dockerfile para Backend - FastAPI
# Sistema de Gestión de Camas Hospitalarias
# ============================================

# Stage 1: Base
FROM python:3.11-slim as base

# Metadatos
LABEL maintainer="Hospital Dev Team"
LABEL description="Sistema de Gestión de Camas Hospitalarias - Backend"
LABEL version="1.0.0"

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/uploads && \
    chown -R appuser:appuser /app

WORKDIR /app

# ============================================
# Stage 2: Dependencies
# ============================================
FROM base as dependencies

# Copiar solo requirements para aprovechar caché de Docker
COPY --chown=appuser:appuser requeriments.txt .

# Instalar dependencias Python
RUN pip install --upgrade pip && \
    pip install -r requeriments.txt

# ============================================
# Stage 3: Development
# ============================================
FROM dependencies as development

# Copiar código de la aplicación
COPY --chown=appuser:appuser . .

# Cambiar a usuario no-root
USER appuser

# Exponer puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando por defecto (desarrollo con hot-reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================================
# Stage 4: Production
# ============================================
FROM dependencies as production

# Copiar código de la aplicación
COPY --chown=appuser:appuser . .

# Compilar archivos .pyc para mejor performance
RUN python -m compileall -b .

# Cambiar a usuario no-root
USER appuser

# Exponer puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando por defecto (producción con múltiples workers)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--log-level", "info"]
