# Migraciones de Base de Datos - Alembic

Este directorio contiene las migraciones de base de datos para el Sistema de Gestión de Camas Hospitalarias.

## Comandos Básicos

### Generar nueva migración automática
```bash
alembic revision --autogenerate -m "descripcion_del_cambio"
```

### Aplicar todas las migraciones pendientes
```bash
alembic upgrade head
```

### Ver migración actual
```bash
alembic current
```

### Ver historial de migraciones
```bash
alembic history
```

### Revertir última migración
```bash
alembic downgrade -1
```

### Revertir todas las migraciones
```bash
alembic downgrade base
```

### Generar script SQL (sin aplicar)
```bash
alembic upgrade head --sql > migration.sql
```

## Estructura de Archivos

- `env.py` - Configuración del entorno de Alembic
- `script.py.mako` - Template para nuevas migraciones
- `versions/` - Directorio con archivos de migración

## Notas Importantes

1. Siempre revisar las migraciones autogeneradas antes de aplicarlas
2. En producción, usar `--sql` para revisar cambios antes de aplicar
3. SQLite tiene limitaciones con ALTER TABLE, se usa batch mode
4. Hacer backup antes de migraciones en producción
