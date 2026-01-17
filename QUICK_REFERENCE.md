# Referencia Rápida - SQL Scripts

Guía de referencia rápida con comandos y consultas SQL más frecuentes.

## Instalación Rápida

### En Supabase SQL Editor
```
1. Copiar: database_schema.sql
2. Pegar en SQL Editor
3. Presionar: Ctrl+Enter o botón RUN
4. Esperar: 2-5 segundos
5. Listo: 10 tablas creadas
```

### En Línea de Comandos (PostgreSQL)
```bash
psql -U usuario -d base_datos -f database_schema.sql
```

---

## Verificación Rápida

### Contar Tablas
```sql
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';
-- Debe retornar: 10
```

### Listar Tablas
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' ORDER BY table_name;
```

### Contar Índices
```sql
SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public';
-- Debe retornar: 28
```

---

## Insertar Datos de Ejemplo

### Solo Hospitales
```sql
INSERT INTO hospital (id, nombre, codigo, es_central, created_at) VALUES
(gen_random_uuid(), 'Mi Hospital', 'MH', FALSE, NOW());
```

### Solo Usuario Médico
```sql
INSERT INTO usuarios (id, username, email, hashed_password, nombre_completo, rol, is_active)
VALUES (gen_random_uuid(), 'dr_perez', 'perez@hospital.cl', 'hashed_pwd', 'Dr. Pérez', 'medico', TRUE);
```

---

## Consultas Útiles

### 1. Ver Camas Disponibles
```sql
SELECT identificador, estado, estado_updated_at
FROM cama WHERE estado = 'libre'
ORDER BY identificador;
```

### 2. Ver Pacientes en Lista de Espera
```sql
SELECT nombre, run, prioridad_calculada, timestamp_lista_espera
FROM paciente WHERE en_lista_espera = TRUE
ORDER BY prioridad_calculada DESC;
```

### 3. Ver Camas por Servicio
```sql
SELECT srv.nombre as servicio, COUNT(c.id) as total_camas,
  SUM(CASE WHEN c.estado = 'libre' THEN 1 ELSE 0 END) as libres,
  SUM(CASE WHEN c.estado = 'ocupada' THEN 1 ELSE 0 END) as ocupadas
FROM cama c
JOIN sala s ON c.sala_id = s.id
JOIN servicio srv ON s.servicio_id = srv.id
GROUP BY srv.id, srv.nombre;
```

### 4. Ver Pacientes Actuales en Hospital
```sql
SELECT p.nombre, p.run, c.identificador as cama, srv.nombre as servicio
FROM paciente p
LEFT JOIN cama c ON p.cama_id = c.id
LEFT JOIN sala s ON c.sala_id = s.id
LEFT JOIN servicio srv ON s.servicio_id = srv.id
WHERE p.hospital_id = 'hospital-id'
  AND p.fallecido = FALSE;
```

### 5. Eventos de un Paciente (Últimos 7 días)
```sql
SELECT tipo_evento, timestamp, servicio_origen_id, servicio_destino_id
FROM evento_paciente
WHERE paciente_id = 'paciente-id'
  AND timestamp > NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;
```

### 6. Pacientes Derivados
```sql
SELECT nombre, run, derivacion_hospital_destino_id, derivacion_estado
FROM paciente WHERE tipo_paciente = 'derivado'
ORDER BY created_at DESC;
```

### 7. Camas en Limpieza
```sql
SELECT c.identificador, c.limpieza_inicio,
  NOW() - c.limpieza_inicio as tiempo_limpiando
FROM cama c
WHERE c.estado = 'en_limpieza'
ORDER BY c.limpieza_inicio;
```

---

## Operaciones Comunes

### Crear Hospital
```sql
INSERT INTO hospital (id, nombre, codigo, es_central, telefono_urgencias, telefono_ambulatorio)
VALUES (gen_random_uuid(), 'Hospital Nuevo', 'HN', FALSE, '65-1234567', '65-7654321');
```

### Crear Servicio
```sql
INSERT INTO servicio (id, nombre, codigo, tipo, hospital_id)
VALUES (gen_random_uuid(), 'UCI Nueva', 'UCI-N', 'uci', 'hospital-id');
```

### Crear Sala
```sql
INSERT INTO sala (id, numero, servicio_id, es_individual, sexo_asignado)
VALUES (gen_random_uuid(), 1, 'servicio-id', TRUE, NULL);
```

### Crear Cama
```sql
INSERT INTO cama (id, numero, letra, identificador, sala_id, estado, estado_updated_at)
VALUES (gen_random_uuid(), 1, 'A', 'UCI-01-A', 'sala-id', 'libre', NOW());
```

### Crear Paciente
```sql
INSERT INTO paciente (
  id, nombre, run, sexo, edad, edad_categoria, es_embarazada,
  diagnostico, tipo_enfermedad, tipo_aislamiento, tipo_paciente,
  hospital_id, complejidad_requerida, created_at, updated_at
)
VALUES (
  gen_random_uuid(), 'Juan Pérez', '12345678-K', 'hombre', 45, 'adulto', FALSE,
  'Neumonía', 'medica', 'ninguno', 'urgencia',
  'hospital-id', 'baja', NOW(), NOW()
);
```

### Asignar Cama a Paciente
```sql
UPDATE paciente
SET cama_id = 'cama-id', updated_at = NOW()
WHERE id = 'paciente-id';

UPDATE cama
SET estado = 'ocupada', estado_updated_at = NOW()
WHERE id = 'cama-id';
```

### Registrar Alta
```sql
UPDATE paciente
SET alta_solicitada = TRUE, alta_motivo = 'Mejoría clínica', updated_at = NOW()
WHERE id = 'paciente-id';

UPDATE cama
SET estado = 'cama_alta', estado_updated_at = NOW()
WHERE id = 'cama-id';
```

### Registrar Fallecimiento
```sql
UPDATE paciente
SET fallecido = TRUE, fallecido_at = NOW(), causa_fallecimiento = 'Causa', updated_at = NOW()
WHERE id = 'paciente-id';

UPDATE cama
SET estado = 'fallecido', estado_updated_at = NOW()
WHERE id = 'cama-id';
```

### Registrar Evento
```sql
INSERT INTO evento_paciente (
  id, tipo_evento, timestamp, paciente_id, hospital_id,
  servicio_origen_id, servicio_destino_id, cama_origen_id, cama_destino_id,
  dia_clinico
)
VALUES (
  gen_random_uuid(), 'cama_asignada', NOW(), 'paciente-id', 'hospital-id',
  NULL, 'servicio-id', NULL, 'cama-id',
  (NOW()::date + INTERVAL '8 hours')::timestamp
);
```

---

## Estados de Cama

```
libre                    ← Disponible para asignar
ocupada                  ← Paciente internado
traslado_entrante        ← Paciente llegando
traslado_saliente        ← Paciente saliendo
traslado_confirmado      ← Traslado confirmado
cama_en_espera           ← En proceso
alta_sugerida            ← Alta pendiente
cama_alta                ← Alta ejecutada
en_limpieza              ← Siendo limpiada
bloqueada                ← Bloqueada del sistema
espera_derivacion        ← Esperando derivación
derivacion_confirmada    ← Derivación confirmada
fallecido                ← Paciente fallecido
reservada                ← Reservada
```

## Tipos de Evento

```
ingreso_urgencia, ingreso_ambulatorio, cama_asignada,
busqueda_cama_iniciada, traslado_iniciado, traslado_confirmado,
traslado_completado, traslado_cancelado, derivacion_solicitada,
derivacion_aceptada, derivacion_rechazada, alta_sugerida,
alta_iniciada, alta_completada, fallecido_marcado, egreso_alta
```

---

## Roles RBAC

```
programador              ← Admin total
directivo_red            ← Director de red (lectura)
directivo_hospital       ← Director hospital (lectura)
gestor_camas             ← Gestor de camas (operativo)
medico                   ← Médico (clínico)
enfermera                ← Enfermera/Matrona
tens                     ← Técnico de enfermería
jefe_servicio            ← Jefe del servicio
supervisora_enfermeria   ← Supervisora
urgencias                ← Urgencias
jefe_urgencias           ← Jefe urgencias
ambulatorio              ← Ambulatorio
derivaciones             ← Especialista derivaciones
estadisticas             ← Analista
visualizador             ← Solo lectura
limpieza                 ← Marcaje de limpieza
```

---

## Limpiar Base de Datos (DEV ONLY)

### Opción 1: Truncate (Rápido)
```sql
TRUNCATE TABLE evento_paciente CASCADE;
TRUNCATE TABLE paciente CASCADE;
TRUNCATE TABLE cama CASCADE;
TRUNCATE TABLE sala CASCADE;
TRUNCATE TABLE servicio CASCADE;
TRUNCATE TABLE hospital CASCADE;
TRUNCATE TABLE refresh_tokens CASCADE;
TRUNCATE TABLE usuarios CASCADE;
TRUNCATE TABLE logactividad CASCADE;
TRUNCATE TABLE configuracionsistema CASCADE;
```

### Opción 2: Delete (Más lento pero reversible)
```sql
DELETE FROM evento_paciente;
DELETE FROM logactividad;
DELETE FROM paciente;
DELETE FROM cama;
DELETE FROM sala;
DELETE FROM servicio;
DELETE FROM refresh_tokens;
DELETE FROM usuarios;
DELETE FROM hospital;
DELETE FROM configuracionsistema;
```

---

## Actualizar Información

### Actualizar Estado Cama
```sql
UPDATE cama
SET estado = 'en_limpieza', estado_updated_at = NOW()
WHERE id = 'cama-id';
```

### Actualizar Diagnóstico Paciente
```sql
UPDATE paciente
SET diagnostico = 'Nuevo diagnóstico', updated_at = NOW()
WHERE id = 'paciente-id';
```

### Agregar Paciente a Lista de Espera
```sql
UPDATE paciente
SET en_lista_espera = TRUE,
    estado_lista_espera = 'esperando',
    timestamp_lista_espera = NOW(),
    prioridad_calculada = 50.0,
    updated_at = NOW()
WHERE id = 'paciente-id';
```

---

## Transacciones (Importante para Integridad)

```sql
BEGIN;
  -- Paso 1: Cambiar estado de cama
  UPDATE cama SET estado = 'ocupada' WHERE id = 'cama-id';

  -- Paso 2: Asignar cama a paciente
  UPDATE paciente SET cama_id = 'cama-id' WHERE id = 'paciente-id';

  -- Paso 3: Registrar evento
  INSERT INTO evento_paciente (id, tipo_evento, timestamp, paciente_id, hospital_id)
  VALUES (gen_random_uuid(), 'cama_asignada', NOW(), 'paciente-id', 'hospital-id');

COMMIT;  -- Si todo OK, guarda cambios
-- ROLLBACK;  -- Si hay error, cancela todo
```

---

## Búsquedas Avanzadas

### Pacientes por Complejidad
```sql
SELECT nombre, complejidad_requerida, en_lista_espera
FROM paciente WHERE complejidad_requerida = 'alta'
ORDER BY prioridad_calculada DESC;
```

### Camas Ocupadas Más de 48h
```sql
SELECT c.identificador, p.nombre,
  NOW() - c.estado_updated_at as tiempo_ocupada
FROM cama c
JOIN paciente p ON c.id = p.cama_id
WHERE c.estado = 'ocupada'
  AND NOW() - c.estado_updated_at > INTERVAL '48 hours'
ORDER BY c.estado_updated_at;
```

### Servicios con Pocas Camas Libres
```sql
SELECT srv.nombre,
  COUNT(c.id) as total,
  SUM(CASE WHEN c.estado = 'libre' THEN 1 ELSE 0 END) as libres
FROM cama c
JOIN sala s ON c.sala_id = s.id
JOIN servicio srv ON s.servicio_id = srv.id
GROUP BY srv.id, srv.nombre
HAVING SUM(CASE WHEN c.estado = 'libre' THEN 1 ELSE 0 END) < 3;
```

---

## Estadísticas Rápidas

### Ocupación General
```sql
SELECT
  COUNT(*) as total_camas,
  SUM(CASE WHEN estado = 'libre' THEN 1 ELSE 0 END) as libres,
  SUM(CASE WHEN estado IN ('ocupada', 'en_limpieza', 'bloqueada') THEN 1 ELSE 0 END) as no_disponibles,
  ROUND(100.0 * SUM(CASE WHEN estado = 'libre' THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_disponible
FROM cama;
```

### Pacientes en Hospital
```sql
SELECT
  COUNT(*) as total,
  SUM(CASE WHEN fallecido = FALSE AND cama_id IS NOT NULL THEN 1 ELSE 0 END) as internados,
  SUM(CASE WHEN en_lista_espera = TRUE THEN 1 ELSE 0 END) as en_espera,
  SUM(CASE WHEN fallecido = TRUE THEN 1 ELSE 0 END) as fallecidos
FROM paciente WHERE hospital_id = 'hospital-id';
```

---

## Exportar/Backup

```bash
# Backup completo
pg_dump -U usuario -d base_datos > backup.sql

# Solo esquema
pg_dump -U usuario -d base_datos --schema-only > schema_backup.sql

# Solo datos
pg_dump -U usuario -d base_datos --data-only > data_backup.sql

# Restaurar
psql -U usuario -d base_datos < backup.sql
```

---

## Troubleshooting Rápido

### Error: "relation doesn't exist"
→ La tabla no existe. Ejecutar database_schema.sql primero.

### Error: "duplicate key"
→ UUID o valor único repetido. Usar `gen_random_uuid()` para IDs.

### Error: "foreign key violation"
→ Respetar orden: hospital → servicio → sala → cama → paciente

### Query Lenta
→ Verificar índices: `SELECT * FROM pg_stat_user_indexes;`

### Conexión Rechazada
→ Verificar credenciales y firewall (en Supabase: network settings)

---

## Archivos Principales

| Archivo | Uso |
|---------|-----|
| `database_schema.sql` | Crear esquema (EJECUTAR PRIMERO) |
| `database_sample_data.sql` | Datos de prueba (opcional) |
| `DATABASE_REFERENCE.md` | Documentación detallada |
| `SUPABASE_SETUP_GUIDE.md` | Setup y troubleshooting |
| `SQL_SCRIPTS_README.md` | Información general |

---

**Última actualización:** 17 de Enero, 2026
**Versión:** 1.0

