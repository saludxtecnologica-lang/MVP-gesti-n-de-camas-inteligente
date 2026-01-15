#!/bin/bash
set -e

# ============================================
# Script de Configuración de Réplica PostgreSQL
# Sistema de Gestión de Camas Hospitalarias
# ============================================

echo "🔄 Configurando réplica de PostgreSQL..."

# Esperar a que el servidor primario esté disponible
until pg_isready -h $POSTGRES_PRIMARY_HOST -p $POSTGRES_PRIMARY_PORT -U $POSTGRES_USER; do
    echo "⏳ Esperando a que el servidor primario esté listo..."
    sleep 2
done

echo "✅ Servidor primario está listo"

# Si ya existe una réplica, no hacer nada
if [ -s "$PGDATA/PG_VERSION" ]; then
    echo "✅ Réplica ya configurada"
    exit 0
fi

echo "📥 Creando base de datos réplica desde el servidor primario..."

# Crear réplica usando pg_basebackup
PGPASSWORD=$POSTGRES_PASSWORD pg_basebackup \
    -h $POSTGRES_PRIMARY_HOST \
    -p $POSTGRES_PRIMARY_PORT \
    -D ${PGDATA} \
    -U $POSTGRES_USER \
    -Fp -Xs -P -R

echo "✅ Réplica creada correctamente"

# Configurar parámetros específicos de réplica
cat >> ${PGDATA}/postgresql.auto.conf <<EOF
# Configuración de réplica
hot_standby = on
hot_standby_feedback = on
max_standby_streaming_delay = 30s
EOF

echo "🎉 Configuración de réplica completada"
echo "📊 La réplica comenzará a replicar automáticamente"
