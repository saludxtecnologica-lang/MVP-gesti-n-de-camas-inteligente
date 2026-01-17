#!/bin/bash

# ============================================
# Script de Deployment a Supabase
# ============================================
# Este script ayuda a configurar y desplegar
# la base de datos en Supabase

set -e  # Salir si hay algún error

echo "🚀 Iniciando deployment a Supabase..."
echo ""

# ============================================
# 1. Verificar prerequisitos
# ============================================
echo "📋 Verificando prerequisitos..."

# Verificar si existe .env.production
if [ ! -f .env.production ]; then
    echo "❌ Error: .env.production no encontrado"
    echo "   Por favor, crea .env.production a partir de .env.production.example"
    exit 1
fi

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 no está instalado"
    exit 1
fi

# Verificar si pip está instalado
if ! command -v pip &> /dev/null; then
    echo "❌ Error: pip no está instalado"
    exit 1
fi

echo "✅ Prerequisitos verificados"
echo ""

# ============================================
# 2. Cargar variables de entorno
# ============================================
echo "🔐 Cargando variables de entorno..."
export $(cat .env.production | grep -v '^#' | xargs)

if [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: DATABASE_URL no está configurado en .env.production"
    exit 1
fi

echo "✅ Variables de entorno cargadas"
echo ""

# ============================================
# 3. Instalar dependencias
# ============================================
echo "📦 Instalando dependencias..."
cd backend

if [ ! -d "venv" ]; then
    echo "   Creando entorno virtual..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Dependencias instaladas"
echo ""

# ============================================
# 4. Ejecutar migraciones
# ============================================
echo "🗄️  Ejecutando migraciones de base de datos..."

# Usar DIRECT_URL para migraciones (puerto 5432)
if [ -n "$DIRECT_URL" ]; then
    export DATABASE_URL=$DIRECT_URL
fi

alembic upgrade head

echo "✅ Migraciones ejecutadas"
echo ""

# ============================================
# 5. Inicializar datos
# ============================================
read -p "¿Deseas cargar datos iniciales? (s/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo "📊 Cargando datos iniciales..."
    python -m app.utils.init_data

    read -p "¿Deseas crear usuarios de prueba? (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        python -m app.utils.seed_users
    fi

    echo "✅ Datos iniciales cargados"
    echo ""
fi

# ============================================
# 6. Verificar conexión
# ============================================
echo "🔍 Verificando conexión a la base de datos..."

python -c "
from app.core.database import engine
from sqlalchemy import inspect, text

try:
    with engine.connect() as conn:
        # Verificar conexión
        result = conn.execute(text('SELECT 1'))

        # Obtener tablas
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        print(f'✅ Conexión exitosa a Supabase')
        print(f'   Tablas encontradas: {len(tables)}')
        print(f'   Tablas: {', '.join(tables[:5])}...')
except Exception as e:
    print(f'❌ Error de conexión: {e}')
    exit(1)
"

echo ""

# ============================================
# 7. Resumen
# ============================================
echo "=========================================="
echo "✅ Deployment completado exitosamente!"
echo "=========================================="
echo ""
echo "📝 Próximos pasos:"
echo ""
echo "1. Desplegar backend en Render/Railway:"
echo "   - Render: https://render.com"
echo "   - Railway: https://railway.app"
echo ""
echo "2. Desplegar frontend en Vercel/Netlify:"
echo "   - Vercel: https://vercel.com"
echo "   - Netlify: https://netlify.com"
echo ""
echo "3. Configurar variables de entorno en cada servicio"
echo ""
echo "4. Consulta la guía completa en:"
echo "   DOCUMENTACIÓN/DEPLOYMENT_SUPABASE.md"
echo ""

# Desactivar entorno virtual
deactivate

echo "🎉 ¡Listo!"
