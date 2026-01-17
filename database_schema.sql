-- ============================================
-- SCRIPT SQL COMPLETO - SISTEMA DE GESTIÓN DE CAMAS HOSPITALARIAS
-- Compatible con PostgreSQL (Supabase)
-- ============================================
--
-- Este script crea todas las tablas del sistema de gestión de camas hospitalarias
-- con sus columnas, tipos, constraints, índices y relaciones.
--
-- IMPORTANTE: Ejecutar en orden para respeta dependencias de Foreign Keys
-- ============================================

-- ============================================
-- 1. TABLA: HOSPITAL (sin dependencias)
-- ============================================
CREATE TABLE hospital (
    id VARCHAR NOT NULL PRIMARY KEY,
    nombre VARCHAR NOT NULL,
    codigo VARCHAR NOT NULL UNIQUE,
    es_central BOOLEAN NOT NULL DEFAULT FALSE,
    telefono_urgencias VARCHAR(50),
    telefono_ambulatorio VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT hospital_pkey PRIMARY KEY (id)
);

CREATE INDEX ix_hospital_nombre ON hospital (nombre);

-- ============================================
-- 2. TABLA: USUARIOS (sin dependencias)
-- ============================================
CREATE TABLE usuarios (
    id VARCHAR NOT NULL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    nombre_completo VARCHAR(255) NOT NULL,
    rol VARCHAR NOT NULL DEFAULT 'visualizador',
    hospital_id VARCHAR,
    servicio_id VARCHAR,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    CONSTRAINT usuarios_pkey PRIMARY KEY (id)
);

CREATE INDEX ix_usuarios_username ON usuarios (username);
CREATE INDEX ix_usuarios_email ON usuarios (email);
CREATE INDEX ix_usuarios_hospital_id ON usuarios (hospital_id);
CREATE INDEX ix_usuarios_servicio_id ON usuarios (servicio_id);

-- ============================================
-- 3. TABLA: REFRESH_TOKENS (depende de usuarios)
-- ============================================
CREATE TABLE refresh_tokens (
    id VARCHAR NOT NULL PRIMARY KEY,
    token VARCHAR NOT NULL UNIQUE,
    user_id VARCHAR NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_at TIMESTAMP,
    user_agent VARCHAR(500),
    ip_address VARCHAR(45),
    CONSTRAINT refresh_tokens_pkey PRIMARY KEY (id),
    CONSTRAINT fk_refresh_tokens_user FOREIGN KEY (user_id) REFERENCES usuarios (id)
);

CREATE INDEX ix_refresh_tokens_token ON refresh_tokens (token);
CREATE INDEX ix_refresh_tokens_user_id ON refresh_tokens (user_id);

-- ============================================
-- 4. TABLA: SERVICIO (depende de hospital)
-- ============================================
CREATE TABLE servicio (
    id VARCHAR NOT NULL PRIMARY KEY,
    nombre VARCHAR NOT NULL,
    codigo VARCHAR NOT NULL,
    tipo VARCHAR NOT NULL,
    hospital_id VARCHAR NOT NULL,
    telefono VARCHAR(50),
    CONSTRAINT servicio_pkey PRIMARY KEY (id),
    CONSTRAINT fk_servicio_hospital FOREIGN KEY (hospital_id) REFERENCES hospital (id)
);

CREATE INDEX ix_servicio_nombre ON servicio (nombre);
CREATE INDEX ix_servicio_hospital_id ON servicio (hospital_id);

-- ============================================
-- 5. TABLA: SALA (depende de servicio)
-- ============================================
CREATE TABLE sala (
    id VARCHAR NOT NULL PRIMARY KEY,
    numero INTEGER NOT NULL,
    servicio_id VARCHAR NOT NULL,
    es_individual BOOLEAN NOT NULL DEFAULT FALSE,
    sexo_asignado VARCHAR,
    CONSTRAINT sala_pkey PRIMARY KEY (id),
    CONSTRAINT fk_sala_servicio FOREIGN KEY (servicio_id) REFERENCES servicio (id)
);

CREATE INDEX ix_sala_servicio_id ON sala (servicio_id);

-- ============================================
-- 6. TABLA: CAMA (depende de sala)
-- ============================================
CREATE TABLE cama (
    id VARCHAR NOT NULL PRIMARY KEY,
    numero INTEGER NOT NULL,
    letra VARCHAR,
    identificador VARCHAR NOT NULL,
    sala_id VARCHAR NOT NULL,
    estado VARCHAR NOT NULL DEFAULT 'libre',
    estado_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    limpieza_inicio TIMESTAMP,
    mensaje_estado VARCHAR,
    cama_asignada_destino VARCHAR,
    paciente_derivado_id VARCHAR,
    CONSTRAINT cama_pkey PRIMARY KEY (id),
    CONSTRAINT fk_cama_sala FOREIGN KEY (sala_id) REFERENCES sala (id)
);

CREATE INDEX ix_cama_identificador ON cama (identificador);
CREATE INDEX ix_cama_sala_id ON cama (sala_id);
CREATE INDEX ix_cama_estado ON cama (estado);

-- ============================================
-- 7. TABLA: PACIENTE (depende de hospital y cama)
-- ============================================
CREATE TABLE paciente (
    id VARCHAR NOT NULL PRIMARY KEY,
    -- Datos personales
    nombre VARCHAR NOT NULL,
    run VARCHAR NOT NULL,
    sexo VARCHAR NOT NULL,
    edad INTEGER NOT NULL,
    edad_categoria VARCHAR NOT NULL,
    es_embarazada BOOLEAN NOT NULL DEFAULT FALSE,
    -- Datos clínicos
    diagnostico VARCHAR NOT NULL,
    tipo_enfermedad VARCHAR NOT NULL,
    tipo_aislamiento VARCHAR NOT NULL DEFAULT 'ninguno',
    notas_adicionales TEXT,
    documento_adjunto VARCHAR,
    -- Requerimientos (JSON como string)
    requerimientos_no_definen TEXT,
    requerimientos_baja TEXT,
    requerimientos_uti TEXT,
    requerimientos_uci TEXT,
    casos_especiales TEXT,
    -- Observación y monitorización
    motivo_observacion VARCHAR,
    justificacion_observacion TEXT,
    motivo_monitorizacion VARCHAR,
    justificacion_monitorizacion TEXT,
    procedimiento_invasivo VARCHAR(500),
    preparacion_quirurgica_detalle VARCHAR(500),
    observacion_tiempo_horas INTEGER,
    observacion_inicio TIMESTAMP,
    monitorizacion_tiempo_horas INTEGER,
    monitorizacion_inicio TIMESTAMP,
    motivo_ingreso_ambulatorio VARCHAR,
    -- Complejidad y tipo
    complejidad_requerida VARCHAR NOT NULL DEFAULT 'baja',
    tipo_paciente VARCHAR NOT NULL,
    hospital_id VARCHAR NOT NULL,
    -- Asignación de camas
    cama_id VARCHAR,
    cama_destino_id VARCHAR,
    cama_origen_derivacion_id VARCHAR,
    cama_reservada_derivacion_id VARCHAR,
    -- Origen y destino (para priorización)
    origen_servicio_nombre VARCHAR,
    servicio_destino VARCHAR,
    -- Lista de espera
    en_lista_espera BOOLEAN NOT NULL DEFAULT FALSE,
    estado_lista_espera VARCHAR NOT NULL DEFAULT 'esperando',
    prioridad_calculada FLOAT NOT NULL DEFAULT 0.0,
    timestamp_lista_espera TIMESTAMP,
    -- Estados especiales
    requiere_nueva_cama BOOLEAN NOT NULL DEFAULT FALSE,
    en_espera BOOLEAN NOT NULL DEFAULT FALSE,
    oxigeno_desactivado_at TIMESTAMP,
    requerimientos_oxigeno_previos TEXT,
    esperando_evaluacion_oxigeno BOOLEAN NOT NULL DEFAULT FALSE,
    -- Derivación
    derivacion_hospital_destino_id VARCHAR,
    derivacion_motivo VARCHAR,
    derivacion_estado VARCHAR,
    derivacion_motivo_rechazo VARCHAR,
    -- Alta
    alta_solicitada BOOLEAN NOT NULL DEFAULT FALSE,
    alta_motivo VARCHAR,
    -- Fallecimiento
    fallecido BOOLEAN NOT NULL DEFAULT FALSE,
    causa_fallecimiento VARCHAR,
    fallecido_at TIMESTAMP,
    estado_cama_anterior_fallecimiento VARCHAR,
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Constraints
    CONSTRAINT paciente_pkey PRIMARY KEY (id),
    CONSTRAINT fk_paciente_hospital FOREIGN KEY (hospital_id) REFERENCES hospital (id),
    CONSTRAINT fk_paciente_cama FOREIGN KEY (cama_id) REFERENCES cama (id),
    CONSTRAINT fk_paciente_cama_destino FOREIGN KEY (cama_destino_id) REFERENCES cama (id),
    CONSTRAINT fk_paciente_cama_reservada_derivacion FOREIGN KEY (cama_reservada_derivacion_id) REFERENCES cama (id)
);

CREATE INDEX ix_paciente_run ON paciente (run);
CREATE INDEX ix_paciente_hospital_id ON paciente (hospital_id);
CREATE INDEX ix_paciente_cama_id ON paciente (cama_id);
CREATE INDEX ix_paciente_en_lista_espera ON paciente (en_lista_espera);
CREATE INDEX ix_paciente_derivacion_estado ON paciente (derivacion_estado);
CREATE INDEX ix_paciente_fallecido ON paciente (fallecido);

-- ============================================
-- 8. TABLA: EVENTO_PACIENTE (depende de paciente, hospital, servicio, cama)
-- ============================================
CREATE TABLE evento_paciente (
    id VARCHAR NOT NULL PRIMARY KEY,
    -- Tipo de evento y timestamp
    tipo_evento VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Referencias a entidades
    paciente_id VARCHAR NOT NULL,
    hospital_id VARCHAR NOT NULL,
    servicio_origen_id VARCHAR,
    servicio_destino_id VARCHAR,
    cama_origen_id VARCHAR,
    cama_destino_id VARCHAR,
    hospital_destino_id VARCHAR,
    -- Metadata adicional
    datos_adicionales TEXT,
    -- Datos calculados (para optimización)
    dia_clinico TIMESTAMP,
    duracion_segundos INTEGER,
    -- Constraints
    CONSTRAINT evento_paciente_pkey PRIMARY KEY (id),
    CONSTRAINT fk_evento_paciente_paciente FOREIGN KEY (paciente_id) REFERENCES paciente (id),
    CONSTRAINT fk_evento_paciente_hospital FOREIGN KEY (hospital_id) REFERENCES hospital (id),
    CONSTRAINT fk_evento_paciente_servicio_origen FOREIGN KEY (servicio_origen_id) REFERENCES servicio (id),
    CONSTRAINT fk_evento_paciente_servicio_destino FOREIGN KEY (servicio_destino_id) REFERENCES servicio (id),
    CONSTRAINT fk_evento_paciente_cama_origen FOREIGN KEY (cama_origen_id) REFERENCES cama (id),
    CONSTRAINT fk_evento_paciente_cama_destino FOREIGN KEY (cama_destino_id) REFERENCES cama (id),
    CONSTRAINT fk_evento_paciente_hospital_destino FOREIGN KEY (hospital_destino_id) REFERENCES hospital (id)
);

CREATE INDEX ix_evento_paciente_tipo_evento ON evento_paciente (tipo_evento);
CREATE INDEX ix_evento_paciente_timestamp ON evento_paciente (timestamp);
CREATE INDEX ix_evento_paciente_paciente_id ON evento_paciente (paciente_id);
CREATE INDEX ix_evento_paciente_hospital_id ON evento_paciente (hospital_id);
CREATE INDEX ix_evento_paciente_dia_clinico ON evento_paciente (dia_clinico);

-- ============================================
-- 9. TABLA: CONFIGURACIONSISTEMA (sin dependencias)
-- ============================================
CREATE TABLE configuracionsistema (
    id VARCHAR NOT NULL PRIMARY KEY,
    -- Modo de operación
    modo_manual BOOLEAN NOT NULL DEFAULT FALSE,
    -- Tiempos de procesos automáticos (en segundos)
    tiempo_limpieza_segundos INTEGER NOT NULL DEFAULT 60,
    tiempo_espera_oxigeno_segundos INTEGER NOT NULL DEFAULT 120,
    -- Timestamp de última actualización
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT configuracionsistema_pkey PRIMARY KEY (id)
);

-- ============================================
-- 10. TABLA: LOGACTIVIDAD (sin dependencias de FK)
-- ============================================
CREATE TABLE logactividad (
    id VARCHAR NOT NULL PRIMARY KEY,
    -- Tipo de actividad
    tipo VARCHAR NOT NULL,
    descripcion TEXT NOT NULL,
    -- Referencias opcionales (sin FK constraints)
    hospital_id VARCHAR,
    paciente_id VARCHAR,
    cama_id VARCHAR,
    -- Datos adicionales en JSON
    datos_extra TEXT,
    -- Timestamp
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT logactividad_pkey PRIMARY KEY (id)
);

CREATE INDEX ix_logactividad_hospital_id ON logactividad (hospital_id);
CREATE INDEX ix_logactividad_paciente_id ON logactividad (paciente_id);
CREATE INDEX ix_logactividad_created_at ON logactividad (created_at);

-- ============================================
-- RESUMEN DE TABLAS CREADAS
-- ============================================
--
-- Total de tablas: 10
--
-- 1. hospital - Centro hospitalario (sin dependencias)
-- 2. usuarios - Usuarios del sistema (sin dependencias)
-- 3. refresh_tokens - Tokens de autenticación (depende de usuarios)
-- 4. servicio - Servicios dentro de hospitales (depende de hospital)
-- 5. sala - Salas dentro de servicios (depende de servicio)
-- 6. cama - Camas dentro de salas (depende de sala)
-- 7. paciente - Pacientes del sistema (depende de hospital y cama)
-- 8. evento_paciente - Eventos de pacientes (depende de paciente, hospital, servicio, cama)
-- 9. configuracionsistema - Configuración global (sin dependencias)
-- 10. logactividad - Log de actividades (sin dependencias de FK)
--
-- Total de Foreign Keys: 16
-- Total de Índices: 28
--
-- ============================================
-- TIPOS DE DATOS UTILIZADOS
-- ============================================
--
-- VARCHAR - Para strings de longitud variable
-- VARCHAR(n) - Para strings con límite de caracteres
-- INTEGER - Para números enteros
-- FLOAT - Para números decimales
-- BOOLEAN - Para valores booleanos (TRUE/FALSE)
-- TEXT - Para texto largo (notas, descripciones)
-- TIMESTAMP - Para fechas y horas
--
-- ============================================
