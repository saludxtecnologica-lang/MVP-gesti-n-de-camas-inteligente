# Guía de Configuración de Base de Datos en Supabase

Guía paso a paso para crear el esquema de base de datos del sistema de gestión de camas hospitalarias en Supabase.

## Tabla de Contenidos
1. [Prerrequisitos](#prerrequisitos)
2. [Acceso a Supabase SQL Editor](#acceso-a-supabase-sql-editor)
3. [Ejecución del Script Principal](#ejecución-del-script-principal)
4. [Inserción de Datos de Ejemplo](#inserción-de-datos-de-ejemplo)
5. [Verificación de la Instalación](#verificación-de-la-instalación)
6. [Troubleshooting](#troubleshooting)

---

## Prerrequisitos

- Cuenta activa en Supabase (https://supabase.com)
- Proyecto PostgreSQL creado en Supabase
- Acceso a la consola de administración
- Los archivos SQL de este proyecto

---

## Acceso a Supabase SQL Editor

### Paso 1: Ingresar a Supabase

1. Ve a https://supabase.com y accede con tu cuenta
2. Selecciona tu proyecto
3. En la barra lateral izquierda, haz clic en **"SQL Editor"**
4. Verás dos secciones:
   - **Quick Start** (arriba)
   - **SQL Snippets** (abajo)
   - **Editor SQL** (área principal)

### Paso 2: Preparar el Editor

El SQL Editor de Supabase te permite ejecutar scripts SQL directamente.

---

## Ejecución del Script Principal

### Opción A: Copiar y Pegar (Recomendado para Supabase)

1. Abre el archivo `database_schema.sql` en un editor de texto
2. Selecciona TODO el contenido (Ctrl+A)
3. Cópialo (Ctrl+C)
4. En Supabase SQL Editor:
   - Haz clic en el área de texto principal
   - Pega el código (Ctrl+V)
5. Haz clic en el botón **"RUN"** (esquina superior derecha)
   - O presiona Ctrl+Enter

**Tiempo estimado:** 2-5 segundos

### Opción B: Ejecutar por Secciones

Si prefieres mayor control o encuentras errores:

1. Divide el script en secciones por tabla
2. Ejecuta cada sección por separado
3. Si una tabla falla, lee el mensaje de error y corrígelo

**Estructura de secciones:**

```sql
-- Sección 1: Hospital (sin dependencias)
CREATE TABLE hospital (...);

-- Sección 2: Usuarios (sin dependencias)
CREATE TABLE usuarios (...);

-- Sección 3: Refresh Tokens
CREATE TABLE refresh_tokens (...);

-- Y así sucesivamente...
```

### Resultado Esperado

Cuando se ejecute correctamente, verás:

```
Command completed successfully
Query returned 0 rows
```

Y en la barra lateral verás las nuevas tablas:
- hospital
- usuarios
- refresh_tokens
- servicio
- sala
- cama
- paciente
- evento_paciente
- configuracionsistema
- logactividad

---

## Inserción de Datos de Ejemplo

**IMPORTANTE:** Solo sigue estos pasos si quieres datos de ejemplo para pruebas.

### Paso 1: Ejecutar Script de Datos

1. Abre `database_sample_data.sql`
2. Copia TODO el contenido
3. En Supabase SQL Editor, **crea una nueva query** (botón + en la pestaña)
4. Pega el contenido
5. Haz clic en **RUN**

**Nota:** Si quieres insertar solo cierta sección (ej., solo hospitales):

```sql
-- Ejecuta solo esto:
INSERT INTO hospital (id, nombre, codigo, es_central, telefono_urgencias, telefono_ambulatorio, created_at) VALUES
('hospital-pm-001', 'Hospital Puerto Montt', 'PM', FALSE, '65-2412000', '65-2412000', NOW());
```

### Paso 2: Verificar Datos Insertados

En una nueva query, ejecuta:

```sql
SELECT COUNT(*) as total_hospitales FROM hospital;
SELECT COUNT(*) as total_pacientes FROM paciente;
SELECT COUNT(*) as total_camas FROM cama;
```

Deberías ver resultados como:
```
total_hospitales
4

total_pacientes
6

total_camas
24
```

---

## Verificación de la Instalación

### Verificación 1: Contar Tablas Creadas

```sql
SELECT count(*) as total_tables
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_type = 'BASE TABLE';
```

**Resultado esperado:** `10` tablas

### Verificación 2: Listar Todas las Tablas

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

**Resultado esperado:**
```
cama
configuracionsistema
evento_paciente
hospital
logactividad
paciente
refresh_tokens
sala
servicio
usuarios
```

### Verificación 3: Contar Índices

```sql
SELECT COUNT(*) as total_indices
FROM pg_indexes
WHERE schemaname = 'public';
```

**Resultado esperado:** `28` índices

### Verificación 4: Validar Foreign Keys

```sql
SELECT
    constraint_name,
    table_name,
    column_name
FROM information_schema.key_column_usage
WHERE constraint_type = 'FOREIGN KEY'
AND table_schema = 'public'
ORDER BY table_name;
```

**Resultado esperado:** Ver todas las relaciones FK listadas

### Verificación 5: Consultar Datos de Ejemplo

```sql
-- Ver todos los hospitales
SELECT id, nombre, codigo FROM hospital;

-- Ver pacientes con camas
SELECT p.nombre, p.run, c.identificador
FROM paciente p
LEFT JOIN cama c ON p.cama_id = c.id;

-- Ver pacientes en lista de espera
SELECT nombre, run, prioridad_calculada
FROM paciente
WHERE en_lista_espera = TRUE
ORDER BY prioridad_calculada DESC;
```

---

## Troubleshooting

### Error: "relation already exists"

**Causa:** La tabla ya existe
**Solución:**
```sql
-- Opción 1: Usar DROP TABLE IF EXISTS (solo en desarrollo)
DROP TABLE IF EXISTS hospital CASCADE;

-- Opción 2: Usar nombres diferentes
CREATE TABLE hospital_v2 (...);
```

### Error: "foreign key constraint failed"

**Causa:** Intenta insertar datos sin respetar dependencias
**Solución:**
1. Primero inserta en tablas sin dependencias (hospital, usuarios)
2. Luego en tablas dependientes (servicio, paciente)
3. Finalmente en tablas que dependen de varias (evento_paciente)

**Orden correcto:**
```
1. hospital
2. usuarios
3. refresh_tokens
4. servicio
5. sala
6. cama
7. paciente
8. evento_paciente
9. configuracionsistema
10. logactividad
```

### Error: "duplicate key value violates unique constraint"

**Causa:** UUIDs o valores únicos repetidos
**Solución:** Usa UUIDs reales (auto-generados):

```sql
-- Mal (se repite):
INSERT INTO hospital (id, nombre, codigo) VALUES
('id-1', 'Hospital A', 'HA'),
('id-1', 'Hospital B', 'HB');  -- ERROR: id duplicado

-- Bien (con gen_random_uuid):
INSERT INTO hospital (id, nombre, codigo) VALUES
(gen_random_uuid(), 'Hospital A', 'HA'),
(gen_random_uuid(), 'Hospital B', 'HB');
```

### Error: "column doesn't exist"

**Causa:** Typo en nombre de columna
**Solución:** Verifica con:

```sql
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'paciente'
ORDER BY column_name;
```

### El Script No Se Ejecuta

**Verificar:**

1. **¿Hay espacio en la query?**
   - El SQL Editor a veces necesita espacio antes del código
   - Intenta presionar Ctrl+Home para ir al inicio

2. **¿Hay caracteres especiales?**
   - Los comentarios con ñ pueden causar problemas
   - Si es necesario, elimina comentarios en español

3. **¿La conexión está activa?**
   - Recarga la página (F5)
   - Vuelve a conectar a Supabase

4. **¿El proyecto está activo?**
   - Verifica en Dashboard que el proyecto esté "Active"

### Consultas Lentas

**Problema:** Las consultas tardan mucho
**Solución:** Supabase tiene límites de conexión gratuita. Si es en desarrollo:

```sql
-- Limitar resultados
SELECT * FROM paciente LIMIT 10;

-- Usar índices existentes
SELECT * FROM paciente WHERE run = '12345678-K';  -- usa ix_paciente_run
SELECT * FROM cama WHERE estado = 'libre';        -- usa ix_cama_estado
```

---

## Limpiar la Base de Datos (Solo Desarrollo)

**ADVERTENCIA:** Esto elimina TODOS los datos. Solo en desarrollo.

```sql
-- Opción 1: Eliminar todas las tablas
DROP TABLE IF EXISTS logactividad CASCADE;
DROP TABLE IF EXISTS evento_paciente CASCADE;
DROP TABLE IF EXISTS configuracionsistema CASCADE;
DROP TABLE IF EXISTS paciente CASCADE;
DROP TABLE IF EXISTS cama CASCADE;
DROP TABLE IF EXISTS sala CASCADE;
DROP TABLE IF EXISTS servicio CASCADE;
DROP TABLE IF EXISTS refresh_tokens CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;
DROP TABLE IF EXISTS hospital CASCADE;

-- Luego vuelve a ejecutar database_schema.sql
```

---

## Exportar la Estructura (Backup)

Para exportar tu esquema actual:

```sql
-- En SQL Editor, copia el resultado de:
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

O en la línea de comandos con `psql`:

```bash
pg_dump -U postgres -h localhost -d tu_base_datos --schema-only > backup_schema.sql
```

---

## Próximos Pasos

### 1. Conectar la Aplicación

Usa las credenciales de conexión de Supabase en tu `.env`:

```env
DATABASE_URL=postgresql://usuario:contraseña@host:5432/nombre_bd
SUPABASE_URL=https://tuproyecto.supabase.co
SUPABASE_KEY=tu-anon-key
```

### 2. Verificar Relaciones en la Aplicación

SQLAlchemy/SQLModel debería reconocer todas las tablas automáticamente:

```python
from app.models import Hospital, Paciente, Cama
from sqlalchemy import inspect
from app.db import engine

inspector = inspect(engine)
tables = inspector.get_table_names()
print(tables)  # Debería mostrar todas las 10 tablas
```

### 3. Ejecutar Migraciones de Alembic

Si usas Alembic para versionamiento:

```bash
# En el directorio backend:
alembic upgrade head
```

---

## Monitoreo y Mantenimiento

### Ver Tamaño de Base de Datos

```sql
SELECT
    table_name,
    round(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY (data_length + index_length) DESC;
```

### Ver Estadísticas de Tablas

```sql
SELECT
    schemaname,
    tablename,
    n_live_tup as filas_activas,
    n_dead_tup as filas_muertas,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC;
```

### Ejecutar VACUUM (Optimización)

```sql
VACUUM ANALYZE;
```

---

## Contacto y Soporte

- **Documentación Supabase:** https://supabase.com/docs
- **Comunidad:** https://github.com/supabase/supabase/discussions
- **Estado del Sistema:** https://status.supabase.com

---

**Última actualización:** 17 de Enero, 2026
**Versión:** 1.0
**Compatible con:** PostgreSQL 12+, Supabase

