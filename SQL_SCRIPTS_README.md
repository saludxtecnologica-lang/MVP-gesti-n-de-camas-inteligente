# Scripts SQL - Sistema de Gestión de Camas Hospitalarias

Documentación completa de todos los scripts SQL generados para la base de datos PostgreSQL.

## Archivos Generados

### 1. `database_schema.sql` - SCRIPT PRINCIPAL
**Descripción:** Script completo para crear todas las tablas del sistema
**Tamaño:** ~5.5 KB
**Líneas:** ~420 líneas
**Tiempo de ejecución:** 2-5 segundos

**Incluye:**
- 10 tablas completas
- 16 Foreign Keys
- 28 índices optimizados
- Comentarios de documentación
- Explicación de tipos de datos

**Contenido:**

```
1. TABLA: HOSPITAL (sin dependencias)
2. TABLA: USUARIOS (sin dependencias)
3. TABLA: REFRESH_TOKENS (depende de usuarios)
4. TABLA: SERVICIO (depende de hospital)
5. TABLA: SALA (depende de servicio)
6. TABLA: CAMA (depende de sala)
7. TABLA: PACIENTE (depende de hospital y cama)
8. TABLA: EVENTO_PACIENTE (depende de paciente, hospital, servicio, cama)
9. TABLA: CONFIGURACIONSISTEMA (sin dependencias)
10. TABLA: LOGACTIVIDAD (referencias opcionales)
```

**Uso:**
```bash
# En SQL Editor de Supabase:
# 1. Copia TODO el contenido del archivo
# 2. Pega en el editor SQL
# 3. Haz clic en RUN

# O en línea de comandos:
psql -U usuario -d base_datos -f database_schema.sql
```

---

### 2. `database_sample_data.sql` - DATOS DE EJEMPLO
**Descripción:** Script con datos de ejemplo para pruebas y desarrollo
**Tamaño:** ~8.2 KB
**Líneas:** ~320 líneas
**Tiempo de ejecución:** 1-2 segundos

**Incluye:**
- 4 hospitales de ejemplo
- 6 usuarios con diferentes roles
- 6 servicios
- 12 salas
- 24 camas (mix de individuales y compartidas)
- 6 pacientes con diferentes estados
- 8 eventos de pacientes
- 5 registros de actividad

**Datos de Prueba Incluidos:**

**Hospitales:**
- Hospital Puerto Montt (PM) - Principal
- Hospital Llanquihue (LL)
- Hospital Calbuco (CA)
- Hospital Puerto Varas (PR)

**Usuarios:**
- Programador (admin)
- Director de Red
- Gestor de Camas
- Médico
- Enfermera
- TENS

**Servicios:**
- UCI, UTI, Medicina, Cirugía (Puerto Montt)
- Medicina (Llanquihue, Calbuco)

**Pacientes Ejemplo:**
- Juan Pérez: 75 años, en UCI con neumonía
- María Rodríguez: 42 años, en medicina post-operatoria
- Carlos Silva: 58 años, con diabetes tipo 2
- Rosa García: En lista de espera UTI
- Fernando Valenzuela: En lista de espera UCI
- Andrea Muñoz: Paciente derivado

**Uso:**
```bash
# En SQL Editor de Supabase (después de ejecutar schema.sql):
# 1. Crear nueva query (botón +)
# 2. Copiar contenido del archivo
# 3. Pegar en el editor
# 4. Haz clic en RUN

# O en línea de comandos:
psql -U usuario -d base_datos -f database_sample_data.sql
```

**Notas:**
- Los UUIDs son hardcoded para fines de ejemplo
- En producción, estos se generarían automáticamente
- Las contraseñas deben ser hasheadas en la aplicación real
- Incluye comentarios SQL útiles para pruebas

---

### 3. `DATABASE_REFERENCE.md` - REFERENCIA COMPLETA
**Descripción:** Documentación detallada de todas las tablas, columnas, tipos y relaciones
**Tamaño:** ~35 KB
**Secciones:** 11 principales

**Contenido:**

#### Secciones Principales:

1. **Diagrama de Dependencias** - Visualización ASCII del árbol de dependencias
2. **Descripción de Tablas** - Una tabla por tabla con:
   - Todas las columnas
   - Tipos de datos
   - Nullable/Unique/Default
   - Descripción de cada campo
   - Primary keys, Foreign keys
   - Índices asociados

3. **Relaciones y Foreign Keys** - Diagrama ER y tabla de todas las FK

4. **Índices** - Lista de los 28 índices con propósito de cada uno

5. **Enumeraciones (ENUM)** - Todos los valores válidos para campos tipo enum:
   - Roles de usuario (16 opciones)
   - Tipos de servicio (8 opciones)
   - Tipo de paciente (4 opciones)
   - Sexo (2 opciones)
   - Categoría edad (3 opciones)
   - Tipo enfermedad (8 opciones)
   - Tipo aislamiento (6 opciones)
   - Complejidad (4 opciones)
   - Estados de cama (14 opciones)
   - Tipos de evento (25 opciones)

6. **Notas Especiales** - Información importante:
   - Campos JSON
   - Timestamps
   - Integridad referencial
   - Performance
   - Día clínico (cálculo)
   - Orden de inserción

7. **Consultas Útiles** - 4 ejemplos SQL comunes:
   - Camas por hospital y estado
   - Pacientes en lista de espera
   - Eventos de un paciente
   - Camas ocupadas por servicio

**Uso:**
- Referencia durante desarrollo
- Documentación para nuevos desarrolladores
- Especificación de requisitos
- Validation de tipos de datos

---

### 4. `SUPABASE_SETUP_GUIDE.md` - GUÍA DE INSTALACIÓN
**Descripción:** Paso a paso para instalar el esquema en Supabase
**Tamaño:** ~15 KB
**Secciones:** 7 principales

**Contenido:**

1. **Prerrequisitos** - Qué necesitas
2. **Acceso a Supabase SQL Editor** - Cómo acceder
3. **Ejecución del Script Principal** - 2 opciones:
   - Copiar y pegar (recomendado)
   - Ejecutar por secciones
4. **Inserción de Datos de Ejemplo** - Paso a paso
5. **Verificación de Instalación** - 5 verificaciones:
   - Contar tablas
   - Listar todas las tablas
   - Contar índices
   - Validar FKs
   - Consultar datos

6. **Troubleshooting** - 7 problemas comunes con soluciones:
   - relation already exists
   - foreign key constraint failed
   - duplicate key value
   - column doesn't exist
   - script doesn't run
   - slow queries
   - database cleanup

7. **Próximos Pasos** - Integración con la aplicación

**Uso:**
- Para nuevos desarrolladores
- Configuración de ambientes
- Resolución de problemas
- Mantenimiento de BD

---

## Tabla de Relaciones Entre Archivos

| Documento | Propósito | Audiencia | Cuando Usar |
|-----------|-----------|-----------|-----------|
| database_schema.sql | Crear esquema | DevOps, DBA | Primera vez |
| database_sample_data.sql | Datos de prueba | Desarrolladores | Desarrollo/Testing |
| DATABASE_REFERENCE.md | Documentación | Todos | Desarrollo, diseño |
| SUPABASE_SETUP_GUIDE.md | Setup/troubleshooting | Desarrolladores | Setup inicial, problemas |

---

## Orden de Ejecución Recomendado

### Primera Instalación:
```
1. database_schema.sql        ← Crear estructura
2. Verificar con consultas SQL
3. database_sample_data.sql   ← Datos de ejemplo (opcional)
```

### Resetear Datos (Desarrollo):
```
1. Truncate o DELETE desde SQL
2. database_sample_data.sql   ← Reinicializar
```

### Integración con Aplicación:
```
1. Leer DATABASE_REFERENCE.md ← Entender estructura
2. Configurar conexión
3. Ejecutar migraciones Alembic
4. Tests de conectividad
```

---

## Especificaciones de la Base de Datos

### Totales:
- **Tablas:** 10
- **Columnas:** ~180
- **Foreign Keys:** 16
- **Índices:** 28
- **Unique Constraints:** 5

### Tipos de Datos Utilizados:
- VARCHAR (strings variables)
- VARCHAR(n) (strings con límite)
- INTEGER (números enteros)
- FLOAT (decimales)
- BOOLEAN (true/false)
- TEXT (texto largo)
- TIMESTAMP (fecha y hora)

### Patrones de Diseño:

#### Identificadores:
- Todas las PK son VARCHAR con UUID v4
- Se generan en aplicación con `uuid.uuid4()`

#### Timestamps:
- `created_at` - Fecha de creación (NOT NULL)
- `updated_at` - Última actualización (cuando aplica)
- Valores por defecto: `CURRENT_TIMESTAMP` o `datetime.utcnow()`

#### Almacenamiento JSON:
- Guardado como TEXT
- Se parsea en la aplicación con `json.loads()`
- Campos: requerimientos, casos_especiales, datos_adicionales, datos_extra

#### Índices:
- Sobre campos de búsqueda frecuente
- Sobre Foreign Keys
- Sobre filtros comunes
- Sobre ordenamiento

---

## Compatibilidad

### PostgreSQL:
- Versión mínima: 12
- Características usadas:
  - TIMESTAMP con UTC
  - UUID (string)
  - BOOLEAN
  - TEXT ilimitado
  - CURRENT_TIMESTAMP

### Supabase:
- Compatible 100%
- Versión PostgreSQL 14+ (default)
- Funciones PostgRES disponibles

### ORM Compatibles:
- SQLAlchemy ✓
- SQLModel (recomendado)
- Sequelize (adaptar)
- Prisma (adaptar)

---

## Seguridad y Mejores Prácticas

### Implementado:
- Foreign Keys para integridad referencial
- Índices para performance
- Unique constraints donde corresponde
- Campos NOT NULL para datos críticos
- Timestamps de auditoría

### No Implementado (agregar en aplicación):
- Row-Level Security (RLS) de Supabase
- Encrypting sensibles
- Sanitización de inputs
- Rate limiting

### Recomendaciones:
```sql
-- Agregar RLS en Supabase:
ALTER TABLE paciente ENABLE ROW LEVEL SECURITY;
CREATE POLICY "usuarios ven su hospital" ON paciente
  USING (hospital_id = (SELECT hospital_id FROM usuarios WHERE id = auth.uid()));

-- Auditoría de cambios:
CREATE TRIGGER audit_paciente
BEFORE UPDATE ON paciente
FOR EACH ROW
EXECUTE FUNCTION audit_trigger_function();
```

---

## Queries de Mantenimiento

### Estadísticas:
```sql
-- Ver tamaño de BD
SELECT pg_size_pretty(pg_database_size(current_database())) as db_size;

-- Índices no usados
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0;

-- Tablas sin índices
SELECT t.tablename
FROM pg_tables t
WHERE NOT EXISTS (
  SELECT 1 FROM pg_indexes i WHERE t.tablename = i.tablename
)
AND schemaname = 'public';
```

### Optimización:
```sql
-- Reconstruir índices
REINDEX DATABASE tu_bd;

-- Vacuum y análisis
VACUUM ANALYZE;

-- Estadísticas de la tabla
ANALYZE paciente;
```

---

## Versionado de Esquema

### Scripts de Migración Alembic (backend/alembic/versions/):
- `001_initial_migration.py` - Crear todas las tablas
- `002_add_cama_reservada_derivacion_id.py` - Agregar campo a paciente
- `003_add_evento_paciente_table.py` - Crear tabla evento_paciente

### Ejecutar migraciones:
```bash
cd backend
alembic upgrade head  # Aplicar todas las migraciones
alembic downgrade -1  # Revertir última migración
```

---

## Checklist de Implementación

- [ ] Ejecutar `database_schema.sql` en Supabase
- [ ] Verificar que las 10 tablas fueron creadas
- [ ] Verificar que los índices fueron creados (28)
- [ ] (Opcional) Ejecutar `database_sample_data.sql` para datos de prueba
- [ ] Probar conectividad desde aplicación
- [ ] Ejecutar migraciones Alembic si corresponde
- [ ] Configurar Row-Level Security en Supabase (recomendado)
- [ ] Hacer backup de la BD
- [ ] Documentar credenciales en `.env`
- [ ] Ejecutar tests de conectividad

---

## Soporte y Documentación

### Este Proyecto:
- Archivos de migraciones: `backend/alembic/versions/`
- Modelos SQLModel: `backend/app/models/`
- Enumeraciones: `backend/app/models/enums.py`

### Externa:
- PostgreSQL: https://www.postgresql.org/docs/
- Supabase: https://supabase.com/docs
- SQLAlchemy: https://docs.sqlalchemy.org/
- SQLModel: https://sqlmodel.tiangolo.com/

---

**Autor:** Sistema de Gestión de Camas Hospitalarias
**Fecha:** 17 de Enero, 2026
**Versión:** 1.0
**Licencia:** Proyecto Hospital Salud X Tecnología

