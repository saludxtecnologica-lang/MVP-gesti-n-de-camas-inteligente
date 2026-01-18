# Referencia de Base de Datos - Sistema de Gestión de Camas Hospitalarias

Documento de referencia completo para el esquema de base de datos PostgreSQL del sistema de gestión de camas hospitalarias.

## Tabla de Contenidos
1. [Diagrama de Dependencias](#diagrama-de-dependencias)
2. [Descripción de Tablas](#descripción-de-tablas)
3. [Relaciones y Foreign Keys](#relaciones-y-foreign-keys)
4. [Índices](#índices)
5. [Enumeraciones (ENUM)](#enumeraciones-enum)
6. [Notas Especiales](#notas-especiales)

---

## Diagrama de Dependencias

```
hospital ──────────┬──────────── servicio ──────────── sala ──────────── cama
                   │                                                        ↑
                   ├────────────────────────────────────────────────────────┤
                   │                                                        │
                   └─ paciente ──────────── evento_paciente ────────────────┘
                      ↑      ↓
                      │      └──── (cama_destino)
                      └──── (cama_id)

usuarios ────────── refresh_tokens

configuracionsistema (independiente)

logactividad (referencias opcionales)
```

---

## Descripción de Tablas

### 1. HOSPITAL
Tabla que representa los centros hospitalarios del sistema.

| Columna | Tipo | Nullable | Unique | Default | Descripción |
|---------|------|----------|--------|---------|-------------|
| id | VARCHAR | NO | SI | - | Identificador único (UUID) |
| nombre | VARCHAR | NO | NO | - | Nombre del hospital |
| codigo | VARCHAR | NO | SI | - | Código único del hospital (PM, LL, CA) |
| es_central | BOOLEAN | NO | NO | FALSE | Indica si es hospital central |
| telefono_urgencias | VARCHAR(50) | SI | NO | NULL | Teléfono de urgencias |
| telefono_ambulatorio | VARCHAR(50) | SI | NO | NULL | Teléfono de ambulatorio |
| created_at | TIMESTAMP | NO | NO | CURRENT_TIMESTAMP | Fecha de creación |

**Primary Key:** `id`
**Unique Constraints:** `codigo`
**Índices:** `ix_hospital_nombre`

---

### 2. USUARIOS
Tabla de usuarios del sistema con control de acceso RBAC.

| Columna | Tipo | Nullable | Unique | Default | Descripción |
|---------|------|----------|--------|---------|-------------|
| id | VARCHAR | NO | SI | - | Identificador único (UUID) |
| username | VARCHAR(50) | NO | SI | - | Nombre de usuario único |
| email | VARCHAR(255) | NO | SI | - | Email único del usuario |
| hashed_password | VARCHAR(255) | NO | NO | - | Contraseña hasheada |
| nombre_completo | VARCHAR(255) | NO | NO | - | Nombre completo del usuario |
| rol | VARCHAR | NO | NO | 'visualizador' | Rol del usuario en el sistema |
| hospital_id | VARCHAR | SI | NO | NULL | Hospital asignado (FK a hospital) |
| servicio_id | VARCHAR | SI | NO | NULL | Servicio asignado (FK a servicio) |
| is_active | BOOLEAN | NO | NO | TRUE | Usuario activo |
| is_verified | BOOLEAN | NO | NO | FALSE | Usuario verificado |
| created_at | TIMESTAMP | NO | NO | CURRENT_TIMESTAMP | Fecha de creación |
| updated_at | TIMESTAMP | NO | NO | CURRENT_TIMESTAMP | Fecha de actualización |
| last_login | TIMESTAMP | SI | NO | NULL | Último acceso |

**Primary Key:** `id`
**Unique Constraints:** `username`, `email`
**Índices:** `ix_usuarios_username`, `ix_usuarios_email`, `ix_usuarios_hospital_id`, `ix_usuarios_servicio_id`

**Roles disponibles:**
- programador, directivo_red, directivo_hospital, gestor_camas, medico, enfermera, tens, jefe_servicio, supervisora_enfermeria, urgencias, jefe_urgencias, ambulatorio, derivaciones, estadisticas, visualizador, limpieza

---

### 3. REFRESH_TOKENS
Tabla para almacenar tokens de autenticación y sesiones.

| Columna | Tipo | Nullable | Unique | Default | Descripción |
|---------|------|----------|--------|---------|-------------|
| id | VARCHAR | NO | SI | - | Identificador único (UUID) |
| token | VARCHAR | NO | SI | - | Token de autenticación único |
| user_id | VARCHAR | NO | NO | - | FK a usuarios.id |
| expires_at | TIMESTAMP | NO | NO | - | Fecha de expiración del token |
| created_at | TIMESTAMP | NO | NO | CURRENT_TIMESTAMP | Fecha de creación |
| revoked | BOOLEAN | NO | NO | FALSE | Token revocado |
| revoked_at | TIMESTAMP | SI | NO | NULL | Fecha de revocación |
| user_agent | VARCHAR(500) | SI | NO | NULL | User agent del dispositivo |
| ip_address | VARCHAR(45) | SI | NO | NULL | Dirección IP del usuario |

**Primary Key:** `id`
**Foreign Keys:** `user_id` → `usuarios.id`
**Índices:** `ix_refresh_tokens_token`, `ix_refresh_tokens_user_id`

---

### 4. SERVICIO
Tabla que representa los servicios hospitalarios (UCI, UTI, Medicina, etc.).

| Columna | Tipo | Nullable | Unique | Default | Descripción |
|---------|------|----------|--------|---------|-------------|
| id | VARCHAR | NO | SI | - | Identificador único (UUID) |
| nombre | VARCHAR | NO | NO | - | Nombre del servicio |
| codigo | VARCHAR | NO | NO | - | Código del servicio |
| tipo | VARCHAR | NO | NO | - | Tipo de servicio (uci, uti, medicina, etc.) |
| hospital_id | VARCHAR | NO | NO | - | FK a hospital.id |
| telefono | VARCHAR(50) | SI | NO | NULL | Teléfono de contacto del servicio |

**Primary Key:** `id`
**Foreign Keys:** `hospital_id` → `hospital.id`
**Índices:** `ix_servicio_nombre`, `ix_servicio_hospital_id`

**Tipos de servicio:**
- uci, uti, medicina, aislamiento, cirugia, obstetricia, pediatria, medico_quirurgico

---

### 5. SALA
Tabla que representa las salas físicas dentro de un servicio.

| Columna | Tipo | Nullable | Unique | Default | Descripción |
|---------|------|----------|--------|---------|-------------|
| id | VARCHAR | NO | SI | - | Identificador único (UUID) |
| numero | INTEGER | NO | NO | - | Número de la sala |
| servicio_id | VARCHAR | NO | NO | - | FK a servicio.id |
| es_individual | BOOLEAN | NO | NO | FALSE | Sala individual (UCI/UTI) o compartida |
| sexo_asignado | VARCHAR | SI | NO | NULL | 'hombre', 'mujer' o NULL |

**Primary Key:** `id`
**Foreign Keys:** `servicio_id` → `servicio.id`
**Índices:** `ix_sala_servicio_id`

---

### 6. CAMA
Tabla que representa las camas hospitalarias.

| Columna | Tipo | Nullable | Unique | Default | Descripción |
|---------|------|----------|--------|---------|-------------|
| id | VARCHAR | NO | SI | - | Identificador único (UUID) |
| numero | INTEGER | NO | NO | - | Número de la cama en la sala |
| letra | VARCHAR | SI | NO | NULL | Letra adicional (A, B, C para salas compartidas) |
| identificador | VARCHAR | NO | NO | - | Identificador completo (MED-501-A) |
| sala_id | VARCHAR | NO | NO | - | FK a sala.id |
| estado | VARCHAR | NO | NO | 'libre' | Estado actual de la cama |
| estado_updated_at | TIMESTAMP | NO | NO | CURRENT_TIMESTAMP | Última actualización de estado |
| limpieza_inicio | TIMESTAMP | SI | NO | NULL | Inicio del proceso de limpieza |
| mensaje_estado | VARCHAR | SI | NO | NULL | Mensaje personalizado del estado |
| cama_asignada_destino | VARCHAR | SI | NO | NULL | Cama destino en un traslado |
| paciente_derivado_id | VARCHAR | SI | NO | NULL | Paciente derivado asociado |

**Primary Key:** `id`
**Foreign Keys:** `sala_id` → `sala.id`
**Índices:** `ix_cama_identificador`, `ix_cama_sala_id`, `ix_cama_estado`

**Estados de cama:**
- libre, ocupada, traslado_entrante, cama_en_espera, traslado_saliente, traslado_confirmado, alta_sugerida, cama_alta, en_limpieza, bloqueada, espera_derivacion, derivacion_confirmada, fallecido, reservada

---

### 7. PACIENTE
Tabla principal de pacientes del sistema con toda su información clínica.

| Columna | Tipo | Nullable | Unique | Default | Descripción |
|---------|------|----------|--------|---------|-------------|
| **DATOS PERSONALES** |
| id | VARCHAR | NO | SI | - | Identificador único (UUID) |
| nombre | VARCHAR | NO | NO | - | Nombre del paciente |
| run | VARCHAR | NO | NO | - | RUN (identificador legal chileno) |
| sexo | VARCHAR | NO | NO | - | hombre, mujer |
| edad | INTEGER | NO | NO | - | Edad en años |
| edad_categoria | VARCHAR | NO | NO | - | pediatrico, adulto, adulto_mayor |
| es_embarazada | BOOLEAN | NO | NO | FALSE | Indica si es embarazada |
| **DATOS CLÍNICOS** |
| diagnostico | VARCHAR | NO | NO | - | Diagnóstico principal |
| tipo_enfermedad | VARCHAR | NO | NO | - | Tipo de enfermedad |
| tipo_aislamiento | VARCHAR | NO | NO | 'ninguno' | Tipo de aislamiento requerido |
| notas_adicionales | TEXT | SI | NO | NULL | Notas clínicas adicionales |
| documento_adjunto | VARCHAR | SI | NO | NULL | Ruta a documento adjunto |
| **REQUERIMIENTOS (JSON)** |
| requerimientos_no_definen | TEXT | SI | NO | NULL | JSON con requerimientos |
| requerimientos_baja | TEXT | SI | NO | NULL | JSON con requerimientos baja complejidad |
| requerimientos_uti | TEXT | SI | NO | NULL | JSON con requerimientos UTI |
| requerimientos_uci | TEXT | SI | NO | NULL | JSON con requerimientos UCI |
| casos_especiales | TEXT | SI | NO | NULL | JSON con casos especiales |
| **OBSERVACIÓN Y MONITORIZACIÓN** |
| motivo_observacion | VARCHAR | SI | NO | NULL | Motivo de observación |
| justificacion_observacion | TEXT | SI | NO | NULL | Justificación de observación |
| motivo_monitorizacion | VARCHAR | SI | NO | NULL | Motivo de monitorización |
| justificacion_monitorizacion | TEXT | SI | NO | NULL | Justificación de monitorización |
| procedimiento_invasivo | VARCHAR(500) | SI | NO | NULL | Procedimiento invasivo |
| preparacion_quirurgica_detalle | VARCHAR(500) | SI | NO | NULL | Detalles de preparación quirúrgica |
| observacion_tiempo_horas | INTEGER | SI | NO | NULL | Duración de observación en horas |
| observacion_inicio | TIMESTAMP | SI | NO | NULL | Inicio de observación |
| monitorizacion_tiempo_horas | INTEGER | SI | NO | NULL | Duración de monitorización en horas |
| monitorizacion_inicio | TIMESTAMP | SI | NO | NULL | Inicio de monitorización |
| motivo_ingreso_ambulatorio | VARCHAR | SI | NO | NULL | Motivo de ingreso ambulatorio |
| **COMPLEJIDAD Y TIPO** |
| complejidad_requerida | VARCHAR | NO | NO | 'baja' | ninguna, baja, media (UTI), alta (UCI) |
| tipo_paciente | VARCHAR | NO | NO | - | urgencia, ambulatorio, hospitalizado, derivado |
| hospital_id | VARCHAR | NO | NO | - | FK a hospital.id |
| **ASIGNACIÓN DE CAMAS** |
| cama_id | VARCHAR | SI | NO | NULL | FK a cama.id (cama actual) |
| cama_destino_id | VARCHAR | SI | NO | NULL | FK a cama.id (cama destino en traslado) |
| cama_origen_derivacion_id | VARCHAR | SI | NO | NULL | Cama de origen de derivación |
| cama_reservada_derivacion_id | VARCHAR | SI | NO | NULL | FK a cama.id (cama reservada para derivación) |
| **ORIGEN Y DESTINO** |
| origen_servicio_nombre | VARCHAR | SI | NO | NULL | Nombre del servicio de origen |
| servicio_destino | VARCHAR | SI | NO | NULL | Nombre del servicio destino |
| **LISTA DE ESPERA** |
| en_lista_espera | BOOLEAN | NO | NO | FALSE | En lista de espera |
| estado_lista_espera | VARCHAR | NO | NO | 'esperando' | esperando, buscando, asignado |
| prioridad_calculada | FLOAT | NO | NO | 0.0 | Score de prioridad |
| timestamp_lista_espera | TIMESTAMP | SI | NO | NULL | Entrada a lista de espera |
| **ESTADOS ESPECIALES** |
| requiere_nueva_cama | BOOLEAN | NO | NO | FALSE | Requiere reevaluación de cama |
| en_espera | BOOLEAN | NO | NO | FALSE | En espera |
| oxigeno_desactivado_at | TIMESTAMP | SI | NO | NULL | Fecha desactivación oxígeno |
| requerimientos_oxigeno_previos | TEXT | SI | NO | NULL | Requerimientos de oxígeno anteriores |
| esperando_evaluacion_oxigeno | BOOLEAN | NO | NO | FALSE | Evaluación de oxígeno pendiente |
| **DERIVACIÓN** |
| derivacion_hospital_destino_id | VARCHAR | SI | NO | NULL | Hospital destino de derivación |
| derivacion_motivo | VARCHAR | SI | NO | NULL | Motivo de derivación |
| derivacion_estado | VARCHAR | SI | NO | NULL | Estado de la derivación |
| derivacion_motivo_rechazo | VARCHAR | SI | NO | NULL | Motivo de rechazo de derivación |
| **ALTA** |
| alta_solicitada | BOOLEAN | NO | NO | FALSE | Alta solicitada |
| alta_motivo | VARCHAR | SI | NO | NULL | Motivo del alta |
| **FALLECIMIENTO** |
| fallecido | BOOLEAN | NO | NO | FALSE | Paciente fallecido |
| causa_fallecimiento | VARCHAR | SI | NO | NULL | Causa del fallecimiento |
| fallecido_at | TIMESTAMP | SI | NO | NULL | Fecha del fallecimiento |
| estado_cama_anterior_fallecimiento | VARCHAR | SI | NO | NULL | Estado anterior de la cama |
| **TIMESTAMPS** |
| created_at | TIMESTAMP | NO | NO | CURRENT_TIMESTAMP | Fecha de creación |
| updated_at | TIMESTAMP | NO | NO | CURRENT_TIMESTAMP | Fecha de actualización |

**Primary Key:** `id`
**Foreign Keys:**
- `hospital_id` → `hospital.id`
- `cama_id` → `cama.id`
- `cama_destino_id` → `cama.id`
- `cama_reservada_derivacion_id` → `cama.id`

**Índices:** `ix_paciente_run`, `ix_paciente_hospital_id`, `ix_paciente_cama_id`, `ix_paciente_en_lista_espera`, `ix_paciente_derivacion_estado`, `ix_paciente_fallecido`

---

### 8. EVENTO_PACIENTE
Tabla para registrar todos los eventos importantes del paciente (auditoría y estadísticas).

| Columna | Tipo | Nullable | Unique | Default | Descripción |
|---------|------|----------|--------|---------|-------------|
| id | VARCHAR | NO | SI | - | Identificador único (UUID) |
| tipo_evento | VARCHAR | NO | NO | - | Tipo de evento (ingreso, traslado, etc.) |
| timestamp | TIMESTAMP | NO | NO | CURRENT_TIMESTAMP | Fecha y hora del evento |
| paciente_id | VARCHAR | NO | NO | - | FK a paciente.id |
| hospital_id | VARCHAR | NO | NO | - | FK a hospital.id |
| servicio_origen_id | VARCHAR | SI | NO | NULL | FK a servicio.id (origen) |
| servicio_destino_id | VARCHAR | SI | NO | NULL | FK a servicio.id (destino) |
| cama_origen_id | VARCHAR | SI | NO | NULL | FK a cama.id (origen) |
| cama_destino_id | VARCHAR | SI | NO | NULL | FK a cama.id (destino) |
| hospital_destino_id | VARCHAR | SI | NO | NULL | FK a hospital.id (destino en derivación) |
| datos_adicionales | TEXT | SI | NO | NULL | JSON con metadata adicional |
| dia_clinico | TIMESTAMP | SI | NO | NULL | Día clínico (8 AM) para agrupación |
| duracion_segundos | INTEGER | SI | NO | NULL | Duración del evento en segundos |

**Primary Key:** `id`
**Foreign Keys:**
- `paciente_id` → `paciente.id`
- `hospital_id` → `hospital.id`
- `servicio_origen_id` → `servicio.id`
- `servicio_destino_id` → `servicio.id`
- `cama_origen_id` → `cama.id`
- `cama_destino_id` → `cama.id`
- `hospital_destino_id` → `hospital.id`

**Índices:** `ix_evento_paciente_tipo_evento`, `ix_evento_paciente_timestamp`, `ix_evento_paciente_paciente_id`, `ix_evento_paciente_hospital_id`, `ix_evento_paciente_dia_clinico`

**Tipos de evento:**
- ingreso_urgencia, ingreso_ambulatorio, cama_asignada, busqueda_cama_iniciada, traslado_iniciado, traslado_confirmado, traslado_completado, traslado_cancelado, cama_en_espera_inicio, cama_en_espera_fin, derivacion_solicitada, derivacion_aceptada, derivacion_rechazada, derivacion_cama_asignada, derivacion_egreso_confirmado, derivacion_completada, alta_sugerida, alta_iniciada, alta_completada, alta_cancelada, fallecido_marcado, fallecido_egresado, egreso_alta, egreso_fallecido, egreso_derivacion

---

### 9. CONFIGURACIONSISTEMA
Tabla de configuración global del sistema.

| Columna | Tipo | Nullable | Unique | Default | Descripción |
|---------|------|----------|--------|---------|-------------|
| id | VARCHAR | NO | SI | - | Identificador único (UUID) |
| modo_manual | BOOLEAN | NO | NO | FALSE | Sistema en modo manual |
| tiempo_limpieza_segundos | INTEGER | NO | NO | 60 | Tiempo de limpieza automática |
| tiempo_espera_oxigeno_segundos | INTEGER | NO | NO | 120 | Tiempo de espera de oxígeno |
| updated_at | TIMESTAMP | NO | NO | CURRENT_TIMESTAMP | Última actualización |

**Primary Key:** `id`

---

### 10. LOGACTIVIDAD
Tabla de auditoría para registrar todas las actividades del sistema.

| Columna | Tipo | Nullable | Unique | Default | Descripción |
|---------|------|----------|--------|---------|-------------|
| id | VARCHAR | NO | SI | - | Identificador único (UUID) |
| tipo | VARCHAR | NO | NO | - | Tipo de actividad (asignacion, traslado, etc.) |
| descripcion | TEXT | NO | NO | - | Descripción de la actividad |
| hospital_id | VARCHAR | SI | NO | NULL | Hospital asociado (sin FK) |
| paciente_id | VARCHAR | SI | NO | NULL | Paciente asociado (sin FK) |
| cama_id | VARCHAR | SI | NO | NULL | Cama asociada |
| datos_extra | TEXT | SI | NO | NULL | JSON con datos adicionales |
| created_at | TIMESTAMP | NO | NO | CURRENT_TIMESTAMP | Fecha de creación |

**Primary Key:** `id`
**Índices:** `ix_logactividad_hospital_id`, `ix_logactividad_paciente_id`, `ix_logactividad_created_at`

**Nota:** Las referencias a hospital_id y paciente_id no tienen Foreign Keys para mayor flexibilidad en auditoría.

---

## Relaciones y Foreign Keys

### Diagrama de Relaciones

```
hospital (1) ──────────── (N) servicio
    ↓
    └─────────── (N) paciente
    └─────────── (N) evento_paciente

servicio (1) ─────────── (N) sala
    ↓
    └─────────── (N) evento_paciente

sala (1) ─────────── (N) cama

cama (1) ─────────── (N) paciente
    ├─ cama_id (paciente_actual)
    ├─ cama_destino_id (pacientes en traslado)
    └─ cama_reservada_derivacion_id

paciente (1) ─────────── (N) evento_paciente

usuarios (1) ─────────── (N) refresh_tokens
```

### Lista de Foreign Keys

| Tabla | Columna | Referencia | Nombre Constraint |
|-------|---------|-----------|-------------------|
| servicio | hospital_id | hospital.id | fk_servicio_hospital |
| sala | servicio_id | servicio.id | fk_sala_servicio |
| cama | sala_id | sala.id | fk_cama_sala |
| paciente | hospital_id | hospital.id | fk_paciente_hospital |
| paciente | cama_id | cama.id | fk_paciente_cama |
| paciente | cama_destino_id | cama.id | fk_paciente_cama_destino |
| paciente | cama_reservada_derivacion_id | cama.id | fk_paciente_cama_reservada_derivacion |
| refresh_tokens | user_id | usuarios.id | fk_refresh_tokens_user |
| evento_paciente | paciente_id | paciente.id | fk_evento_paciente_paciente |
| evento_paciente | hospital_id | hospital.id | fk_evento_paciente_hospital |
| evento_paciente | servicio_origen_id | servicio.id | fk_evento_paciente_servicio_origen |
| evento_paciente | servicio_destino_id | servicio.id | fk_evento_paciente_servicio_destino |
| evento_paciente | cama_origen_id | cama.id | fk_evento_paciente_cama_origen |
| evento_paciente | cama_destino_id | cama.id | fk_evento_paciente_cama_destino |
| evento_paciente | hospital_destino_id | hospital.id | fk_evento_paciente_hospital_destino |

---

## Índices

### Resumen de Índices (28 total)

| Tabla | Índice | Columnas | Propósito |
|-------|--------|----------|-----------|
| hospital | ix_hospital_nombre | nombre | Búsquedas por nombre |
| usuarios | ix_usuarios_username | username | Login |
| usuarios | ix_usuarios_email | email | Búsqueda de usuario |
| usuarios | ix_usuarios_hospital_id | hospital_id | Filtros por hospital |
| usuarios | ix_usuarios_servicio_id | servicio_id | Filtros por servicio |
| refresh_tokens | ix_refresh_tokens_token | token | Validación de token |
| refresh_tokens | ix_refresh_tokens_user_id | user_id | Sesiones de usuario |
| servicio | ix_servicio_nombre | nombre | Búsquedas por nombre |
| servicio | ix_servicio_hospital_id | hospital_id | Filtros por hospital |
| sala | ix_sala_servicio_id | servicio_id | Camas de un servicio |
| cama | ix_cama_identificador | identificador | Búsqueda rápida de cama |
| cama | ix_cama_sala_id | sala_id | Camas de una sala |
| cama | ix_cama_estado | estado | Camas por estado |
| paciente | ix_paciente_run | run | Búsqueda por RUN |
| paciente | ix_paciente_hospital_id | hospital_id | Pacientes del hospital |
| paciente | ix_paciente_cama_id | cama_id | Asignación actual |
| paciente | ix_paciente_en_lista_espera | en_lista_espera | Lista de espera |
| paciente | ix_paciente_derivacion_estado | derivacion_estado | Derivaciones |
| paciente | ix_paciente_fallecido | fallecido | Histórico de fallecidos |
| evento_paciente | ix_evento_paciente_tipo_evento | tipo_evento | Análisis de eventos |
| evento_paciente | ix_evento_paciente_timestamp | timestamp | Eventos por fecha |
| evento_paciente | ix_evento_paciente_paciente_id | paciente_id | Historial del paciente |
| evento_paciente | ix_evento_paciente_hospital_id | hospital_id | Eventos del hospital |
| evento_paciente | ix_evento_paciente_dia_clinico | dia_clinico | Agrupación diaria |
| logactividad | ix_logactividad_hospital_id | hospital_id | Auditoria por hospital |
| logactividad | ix_logactividad_paciente_id | paciente_id | Auditoria del paciente |
| logactividad | ix_logactividad_created_at | created_at | Historial por fecha |

---

## Enumeraciones (ENUM)

### Roles de Usuario (Tabla usuarios, columna rol)
```
programador, directivo_red, directivo_hospital, gestor_camas,
medico, enfermera, tens, jefe_servicio, supervisora_enfermeria,
urgencias, jefe_urgencias, ambulatorio, derivaciones, estadisticas,
visualizador, limpieza
```

### Tipos de Servicio (Tabla servicio, columna tipo)
```
uci, uti, medicina, aislamiento, cirugia, obstetricia, pediatria, medico_quirurgico
```

### Tipo de Paciente (Tabla paciente, columna tipo_paciente)
```
urgencia, ambulatorio, hospitalizado, derivado
```

### Sexo (Tabla paciente, columna sexo)
```
hombre, mujer
```

### Categoría de Edad (Tabla paciente, columna edad_categoria)
```
pediatrico (0-14 años)
adulto (15-59 años)
adulto_mayor (60+ años)
```

### Tipo de Enfermedad (Tabla paciente, columna tipo_enfermedad)
```
medica, quirurgica, traumatologica, neurologica, urologica, geriatrica, ginecologica, obstetrica
```

### Tipo de Aislamiento (Tabla paciente, columna tipo_aislamiento)
```
ninguno, contacto, gotitas, aereo, ambiente_protegido, especial
```

### Complejidad Requerida (Tabla paciente, columna complejidad_requerida)
```
ninguna, baja, media (UTI), alta (UCI)
```

### Estado de Lista de Espera (Tabla paciente, columna estado_lista_espera)
```
esperando, buscando, asignado
```

### Estados de Cama (Tabla cama, columna estado)
```
libre, ocupada, traslado_entrante, cama_en_espera, traslado_saliente,
traslado_confirmado, alta_sugerida, cama_alta, en_limpieza, bloqueada,
espera_derivacion, derivacion_confirmada, fallecido, reservada
```

### Tipos de Evento (Tabla evento_paciente, columna tipo_evento)
```
ingreso_urgencia, ingreso_ambulatorio, cama_asignada, busqueda_cama_iniciada,
traslado_iniciado, traslado_confirmado, traslado_completado, traslado_cancelado,
cama_en_espera_inicio, cama_en_espera_fin, derivacion_solicitada, derivacion_aceptada,
derivacion_rechazada, derivacion_cama_asignada, derivacion_egreso_confirmado,
derivacion_completada, alta_sugerida, alta_iniciada, alta_completada, alta_cancelada,
fallecido_marcado, fallecido_egresado, egreso_alta, egreso_fallecido, egreso_derivacion
```

---

## Notas Especiales

### 1. Campos JSON
Varias columnas de la tabla `paciente` almacenan JSON como strings:
- `requerimientos_no_definen`
- `requerimientos_baja`
- `requerimientos_uti`
- `requerimientos_uci`
- `casos_especiales`
- `datos_adicionales` (en evento_paciente)
- `datos_extra` (en logactividad)

Estos se almacenan como TEXT pero deben ser parseados como JSON en la aplicación.

### 2. Campos de Timestamps
Todas las tablas incluyen timestamps para auditoría:
- `created_at` - Fecha de creación
- `updated_at` - Fecha de última actualización (donde aplica)

### 3. Integridad Referencial
- **Cascada:** No se utilizan ON DELETE CASCADE para preservar historial de auditoría
- **Restricción:** Los deletes se restringen si existen referencias

### 4. Performance
Los índices están diseñados para optimizar:
- Búsquedas de pacientes (run, hospital_id, cama_id)
- Filtrados de camas (estado, sala_id, identificador)
- Análisis de eventos (tipo, timestamp, dia_clinico)
- Auditoría (created_at, hospital_id, paciente_id)

### 5. Día Clínico
El campo `dia_clinico` en evento_paciente se calcula como:
- Si hora < 8 AM: Pertenece al día clínico anterior a las 8 AM
- Si hora >= 8 AM: Pertenece al mismo día a las 8 AM

Ejemplo: 2024-01-15 07:30 → 2024-01-14 08:00

### 6. Orden de Inserción
Para respetar las dependencias de Foreign Keys, el orden correcto es:
1. hospital
2. usuarios
3. refresh_tokens
4. servicio (depende de hospital)
5. sala (depende de servicio)
6. cama (depende de sala)
7. paciente (depende de hospital y cama)
8. evento_paciente (depende de paciente, hospital, servicio, cama)
9. configuracionsistema
10. logactividad

### 7. Sexo Asignado en Salas
La tabla `sala` tiene un campo `sexo_asignado` para compatibilidad con sistemas de salas segregadas por sexo. Valores: 'hombre', 'mujer', NULL

---

## Consultas Útiles

### Obtener todas las camas de un hospital con su estado
```sql
SELECT c.identificador, c.estado, s.numero as sala_numero, srv.nombre as servicio_nombre
FROM cama c
JOIN sala s ON c.sala_id = s.id
JOIN servicio srv ON s.servicio_id = srv.id
WHERE srv.hospital_id = 'hospital_id'
ORDER BY srv.nombre, s.numero, c.numero;
```

### Pacientes en lista de espera por prioridad
```sql
SELECT p.nombre, p.run, p.prioridad_calculada, p.timestamp_lista_espera
FROM paciente p
WHERE p.en_lista_espera = TRUE
ORDER BY p.prioridad_calculada DESC, p.timestamp_lista_espera ASC;
```

### Eventos de un paciente en los últimos 7 días
```sql
SELECT tipo_evento, timestamp, servicio_origen_id, servicio_destino_id
FROM evento_paciente
WHERE paciente_id = 'paciente_id'
  AND timestamp > NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;
```

### Camas ocupadas por servicio
```sql
SELECT srv.nombre, COUNT(c.id) as camas_ocupadas
FROM cama c
JOIN sala s ON c.sala_id = s.id
JOIN servicio srv ON s.servicio_id = srv.id
WHERE c.estado IN ('ocupada', 'traslado_entrante', 'traslado_saliente')
GROUP BY srv.id, srv.nombre;
```

---

**Última actualización:** 17 de Enero, 2026
**Versión:** 1.0
**Compatibilidad:** PostgreSQL 12+, Supabase
