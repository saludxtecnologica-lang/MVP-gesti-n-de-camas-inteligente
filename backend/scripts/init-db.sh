#!/bin/bash
set -e

# ============================================
# Script de Inicialización de PostgreSQL
# Sistema de Gestión de Camas Hospitalarias
# ============================================

echo "🏥 Inicializando base de datos para Sistema de Gestión de Camas..."

# Conectar a la base de datos y ejecutar configuraciones
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- ============================================
    -- EXTENSIONES
    -- ============================================

    -- UUID para IDs únicos
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    -- pg_trgm para búsqueda de texto similitud (útil para buscar pacientes)
    CREATE EXTENSION IF NOT EXISTS pg_trgm;

    -- pgcrypto para funciones criptográficas adicionales
    CREATE EXTENSION IF NOT EXISTS pgcrypto;

    -- pg_stat_statements para análisis de performance de queries
    CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

    -- ============================================
    -- CONFIGURACIÓN DE BÚSQUEDA DE TEXTO
    -- ============================================

    -- Configurar búsqueda en español
    CREATE TEXT SEARCH CONFIGURATION es_hospital (COPY = spanish);

    -- ============================================
    -- ROLES Y PERMISOS
    -- ============================================

    -- Rol de solo lectura (para réplica y reportes)
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'readonly_user') THEN
            CREATE ROLE readonly_user WITH LOGIN PASSWORD 'readonly_pass_changeme';
        END IF;
    END
    \$\$;

    GRANT CONNECT ON DATABASE $POSTGRES_DB TO readonly_user;
    GRANT USAGE ON SCHEMA public TO readonly_user;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_user;

    -- Rol de aplicación (lectura/escritura)
    -- Ya existe el rol principal $POSTGRES_USER

    -- ============================================
    -- FUNCIONES ÚTILES
    -- ============================================

    -- Función para actualizar timestamp automáticamente
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS \$\$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    \$\$ language 'plpgsql';

    -- Función para validar RUN chileno
    CREATE OR REPLACE FUNCTION validar_run_chileno(run TEXT)
    RETURNS BOOLEAN AS \$\$
    DECLARE
        rut TEXT;
        dv TEXT;
        suma INTEGER := 0;
        multiplicador INTEGER := 2;
        resto INTEGER;
        dv_calculado TEXT;
    BEGIN
        -- Limpiar run (quitar puntos y guión)
        run := REGEXP_REPLACE(run, '[^0-9kK]', '', 'g');

        -- Verificar largo mínimo
        IF LENGTH(run) < 2 THEN
            RETURN FALSE;
        END IF;

        -- Separar rut y dígito verificador
        rut := SUBSTRING(run FROM 1 FOR LENGTH(run)-1);
        dv := UPPER(SUBSTRING(run FROM LENGTH(run) FOR 1));

        -- Calcular dígito verificador
        FOR i IN REVERSE LENGTH(rut)..1 LOOP
            suma := suma + (SUBSTRING(rut FROM i FOR 1)::INTEGER * multiplicador);
            multiplicador := CASE WHEN multiplicador = 7 THEN 2 ELSE multiplicador + 1 END;
        END LOOP;

        resto := suma % 11;
        dv_calculado := CASE
            WHEN 11 - resto = 11 THEN '0'
            WHEN 11 - resto = 10 THEN 'K'
            ELSE (11 - resto)::TEXT
        END;

        RETURN dv = dv_calculado;
    END;
    \$\$ LANGUAGE plpgsql IMMUTABLE;

    -- ============================================
    -- VISTAS ÚTILES PARA REPORTES
    -- ============================================

    -- Vista de ocupación por servicio (se creará después de las tablas)
    -- CREATE OR REPLACE VIEW vista_ocupacion_servicios AS ...

    -- ============================================
    -- CONFIGURACIONES ADICIONALES
    -- ============================================

    -- Aumentar límites de memoria para queries complejas
    SET work_mem = '16MB';
    SET maintenance_work_mem = '256MB';

    COMMENT ON DATABASE $POSTGRES_DB IS 'Base de datos del Sistema de Gestión de Camas Hospitalarias';

EOSQL

echo "✅ Base de datos inicializada correctamente"
echo "📊 Extensiones instaladas:"
echo "   - uuid-ossp (generación de UUIDs)"
echo "   - pg_trgm (búsqueda de texto)"
echo "   - pgcrypto (funciones criptográficas)"
echo "   - pg_stat_statements (análisis de performance)"
echo ""
echo "👥 Roles creados:"
echo "   - readonly_user (solo lectura)"
echo "   - $POSTGRES_USER (lectura/escritura)"
