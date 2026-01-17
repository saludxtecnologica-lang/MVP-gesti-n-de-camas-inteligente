-- ============================================
-- SCRIPT DE DATOS DE EJEMPLO
-- Sistema de Gestión de Camas Hospitalarias
-- ============================================
--
-- Este script contiene ejemplos de INSERT para:
-- 1. Inicializar hospitales
-- 2. Crear servicios y salas
-- 3. Crear camas
-- 4. Registrar pacientes
-- 5. Registrar usuarios
-- 6. Crear eventos de prueba
--
-- NOTA: Los UUIDs son de ejemplo. En producción se generarán automáticamente.
-- ============================================

-- ============================================
-- 1. INSERTAR HOSPITALES
-- ============================================
INSERT INTO hospital (id, nombre, codigo, es_central, telefono_urgencias, telefono_ambulatorio, created_at) VALUES
('hospital-pm-001', 'Hospital Puerto Montt', 'PM', FALSE, '65-2412000', '65-2412000', NOW()),
('hospital-ll-001', 'Hospital Llanquihue', 'LL', FALSE, '65-2413000', '65-2413000', NOW()),
('hospital-ca-001', 'Hospital Calbuco', 'CA', FALSE, '65-2414000', '65-2414000', NOW()),
('hospital-pr-001', 'Hospital Puerto Varas', 'PR', FALSE, '65-2415000', '65-2415000', NOW());

-- ============================================
-- 2. INSERTAR USUARIOS
-- ============================================
-- Nota: Las contraseñas deben estar hasheadas en aplicación real
INSERT INTO usuarios (id, username, email, hashed_password, nombre_completo, rol, hospital_id, is_active, created_at, updated_at) VALUES
('user-admin-001', 'programador', 'admin@hospital.cl', 'hashed_password_1', 'Administrador del Sistema', 'programador', NULL, TRUE, NOW(), NOW()),
('user-director-001', 'director_red', 'director@hospital.cl', 'hashed_password_2', 'Director de Red', 'directivo_red', NULL, TRUE, NOW(), NOW()),
('user-gestor-001', 'gestor_camas', 'gestor@hospital.cl', 'hashed_password_3', 'Gestor de Camas Puerto Montt', 'gestor_camas', 'hospital-pm-001', TRUE, NOW(), NOW()),
('user-medico-001', 'dr_flores', 'flores@hospital.cl', 'hashed_password_4', 'Dr. Francisco Flores', 'medico', 'hospital-pm-001', TRUE, NOW(), NOW()),
('user-enfermera-001', 'enfermera_torres', 'torres@hospital.cl', 'hashed_password_5', 'Enfermera María Torres', 'enfermera', 'hospital-pm-001', TRUE, NOW(), NOW()),
('user-tens-001', 'tens_lopez', 'lopez@hospital.cl', 'hashed_password_6', 'TENS Juan López', 'tens', 'hospital-pm-001', TRUE, NOW(), NOW());

-- ============================================
-- 3. INSERTAR SERVICIOS
-- ============================================
INSERT INTO servicio (id, nombre, codigo, tipo, hospital_id, telefono) VALUES
-- Puerto Montt
('servicio-pm-uci', 'UCI Puerto Montt', 'PM-UCI', 'uci', 'hospital-pm-001', '65-2412100'),
('servicio-pm-uti', 'UTI Puerto Montt', 'PM-UTI', 'uti', 'hospital-pm-001', '65-2412200'),
('servicio-pm-med', 'Medicina General', 'PM-MED', 'medicina', 'hospital-pm-001', '65-2412300'),
('servicio-pm-cir', 'Cirugía', 'PM-CIR', 'cirugia', 'hospital-pm-001', '65-2412400'),
-- Llanquihue
('servicio-ll-med', 'Medicina Llanquihue', 'LL-MED', 'medicina', 'hospital-ll-001', '65-2413300'),
-- Calbuco
('servicio-ca-med', 'Medicina Calbuco', 'CA-MED', 'medicina', 'hospital-ca-001', '65-2414300');

-- ============================================
-- 4. INSERTAR SALAS
-- ============================================
-- UCI Puerto Montt (salas individuales)
INSERT INTO sala (id, numero, servicio_id, es_individual, sexo_asignado) VALUES
('sala-pm-uci-01', 1, 'servicio-pm-uci', TRUE, NULL),
('sala-pm-uci-02', 2, 'servicio-pm-uci', TRUE, NULL),
('sala-pm-uci-03', 3, 'servicio-pm-uci', TRUE, NULL);

-- UTI Puerto Montt (salas individuales)
INSERT INTO sala (id, numero, servicio_id, es_individual, sexo_asignado) VALUES
('sala-pm-uti-01', 1, 'servicio-pm-uti', TRUE, NULL),
('sala-pm-uti-02', 2, 'servicio-pm-uti', TRUE, NULL);

-- Medicina Puerto Montt (salas compartidas)
INSERT INTO sala (id, numero, servicio_id, es_individual, sexo_asignado) VALUES
('sala-pm-med-01', 1, 'servicio-pm-med', FALSE, 'hombre'),
('sala-pm-med-02', 2, 'servicio-pm-med', FALSE, 'mujer'),
('sala-pm-med-03', 3, 'servicio-pm-med', FALSE, 'hombre');

-- Cirugía Puerto Montt (salas compartidas)
INSERT INTO sala (id, numero, servicio_id, es_individual, sexo_asignado) VALUES
('sala-pm-cir-01', 1, 'servicio-pm-cir', FALSE, NULL),
('sala-pm-cir-02', 2, 'servicio-pm-cir', FALSE, NULL);

-- ============================================
-- 5. INSERTAR CAMAS
-- ============================================
-- UCI (salas individuales, una cama por sala)
INSERT INTO cama (id, numero, letra, identificador, sala_id, estado, estado_updated_at) VALUES
('cama-pm-uci-001', 1, NULL, 'UCI-01-01', 'sala-pm-uci-01', 'libre', NOW()),
('cama-pm-uci-002', 1, NULL, 'UCI-01-02', 'sala-pm-uci-02', 'ocupada', NOW()),
('cama-pm-uci-003', 1, NULL, 'UCI-01-03', 'sala-pm-uci-03', 'en_limpieza', NOW());

-- UTI (salas individuales, una cama por sala)
INSERT INTO cama (id, numero, letra, identificador, sala_id, estado, estado_updated_at) VALUES
('cama-pm-uti-001', 1, NULL, 'UTI-01-01', 'sala-pm-uti-01', 'libre', NOW()),
('cama-pm-uti-002', 1, NULL, 'UTI-02-01', 'sala-pm-uti-02', 'ocupada', NOW());

-- Medicina (salas compartidas, 4 camas por sala)
INSERT INTO cama (id, numero, letra, identificador, sala_id, estado, estado_updated_at) VALUES
-- Sala 1 (Hombres)
('cama-pm-med-001', 1, 'A', 'MED-01-A', 'sala-pm-med-01', 'libre', NOW()),
('cama-pm-med-002', 1, 'B', 'MED-01-B', 'sala-pm-med-01', 'libre', NOW()),
('cama-pm-med-003', 2, 'A', 'MED-02-A', 'sala-pm-med-01', 'ocupada', NOW()),
('cama-pm-med-004', 2, 'B', 'MED-02-B', 'sala-pm-med-01', 'libre', NOW()),
-- Sala 2 (Mujeres)
('cama-pm-med-005', 1, 'A', 'MED-03-A', 'sala-pm-med-02', 'libre', NOW()),
('cama-pm-med-006', 1, 'B', 'MED-03-B', 'sala-pm-med-02', 'ocupada', NOW()),
('cama-pm-med-007', 2, 'A', 'MED-04-A', 'sala-pm-med-02', 'libre', NOW()),
('cama-pm-med-008', 2, 'B', 'MED-04-B', 'sala-pm-med-02', 'libre', NOW());

-- Cirugía (salas compartidas, 4 camas por sala)
INSERT INTO cama (id, numero, letra, identificador, sala_id, estado, estado_updated_at) VALUES
-- Sala 1
('cama-pm-cir-001', 1, 'A', 'CIR-01-A', 'sala-pm-cir-01', 'libre', NOW()),
('cama-pm-cir-002', 1, 'B', 'CIR-01-B', 'sala-pm-cir-01', 'libre', NOW()),
('cama-pm-cir-003', 2, 'A', 'CIR-02-A', 'sala-pm-cir-01', 'libre', NOW()),
('cama-pm-cir-004', 2, 'B', 'CIR-02-B', 'sala-pm-cir-01', 'libre', NOW());

-- ============================================
-- 6. INSERTAR PACIENTES
-- ============================================
INSERT INTO paciente (
    id, nombre, run, sexo, edad, edad_categoria, es_embarazada,
    diagnostico, tipo_enfermedad, tipo_aislamiento, tipo_paciente, hospital_id,
    cama_id, en_lista_espera, estado_lista_espera, complejidad_requerida,
    created_at, updated_at
) VALUES
-- Paciente 1: Adulto mayor con neumonía en UCI
('paciente-001', 'Juan Pérez García', '12345678-K', 'hombre', 75, 'adulto_mayor', FALSE,
'Neumonía bacteriana', 'medica', 'ninguno', 'urgencia', 'hospital-pm-001',
'cama-pm-uci-002', FALSE, 'asignado', 'alta',
NOW(), NOW()),

-- Paciente 2: Adulto con apendicitis en Cirugía
('paciente-002', 'María Rodríguez López', '23456789-9', 'mujer', 42, 'adulto', FALSE,
'Apendicitis aguda', 'quirurgica', 'ninguno', 'urgencia', 'hospital-pm-001',
'cama-pm-med-006', FALSE, 'asignado', 'media',
NOW(), NOW()),

-- Paciente 3: Adulto en Medicina
('paciente-003', 'Carlos Silva Moreno', '34567890-8', 'hombre', 58, 'adulto', FALSE,
'Diabetes tipo 2 con complicaciones', 'medica', 'ninguno', 'hospitalizado', 'hospital-pm-001',
'cama-pm-med-003', FALSE, 'asignado', 'baja',
NOW(), NOW()),

-- Paciente 4: En lista de espera UTI
('paciente-004', 'Rosa García Díaz', '45678901-7', 'mujer', 68, 'adulto_mayor', FALSE,
'EPOC descompensado', 'medica', 'gotitas', 'urgencia', 'hospital-pm-001',
NULL, TRUE, 'esperando', 'media',
NOW(), NOW()),

-- Paciente 5: En lista de espera UCI
('paciente-005', 'Fernando Valenzuela López', '56789012-6', 'hombre', 72, 'adulto_mayor', FALSE,
'Sepsis, insuficiencia respiratoria', 'medica', 'contacto', 'urgencia', 'hospital-pm-001',
NULL, TRUE, 'buscando', 'alta',
NOW(), NOW()),

-- Paciente 6: Paciente derivado
('paciente-006', 'Andrea Muñoz Torres', '67890123-5', 'mujer', 35, 'adulto', FALSE,
'Fractura de fémur', 'traumatologica', 'ninguno', 'derivado', 'hospital-ll-001',
NULL, FALSE, 'asignado', 'media',
NOW(), NOW());

-- ============================================
-- 7. INSERTAR CONFIGURACION DEL SISTEMA
-- ============================================
INSERT INTO configuracionsistema (id, modo_manual, tiempo_limpieza_segundos, tiempo_espera_oxigeno_segundos, updated_at) VALUES
('config-001', FALSE, 60, 120, NOW());

-- ============================================
-- 8. INSERTAR EVENTOS DE PACIENTES
-- ============================================
INSERT INTO evento_paciente (
    id, tipo_evento, timestamp, paciente_id, hospital_id,
    servicio_origen_id, servicio_destino_id, cama_origen_id, cama_destino_id,
    dia_clinico, duracion_segundos
) VALUES
-- Eventos paciente 001 (Juan Pérez)
('evento-001', 'ingreso_urgencia', NOW() - INTERVAL '2 days', 'paciente-001', 'hospital-pm-001',
NULL, 'servicio-pm-uci', NULL, NULL, NOW()::DATE + INTERVAL '8 hours', NULL),

('evento-002', 'cama_asignada', NOW() - INTERVAL '2 days' + INTERVAL '30 minutes', 'paciente-001', 'hospital-pm-001',
NULL, 'servicio-pm-uci', NULL, 'cama-pm-uci-002', NOW()::DATE + INTERVAL '8 hours', 1800),

-- Eventos paciente 002 (María Rodríguez)
('evento-003', 'ingreso_urgencia', NOW() - INTERVAL '5 hours', 'paciente-002', 'hospital-pm-001',
NULL, 'servicio-pm-med', NULL, NULL, NOW()::DATE + INTERVAL '8 hours', NULL),

('evento-004', 'cama_asignada', NOW() - INTERVAL '4 hours', 'paciente-002', 'hospital-pm-001',
NULL, 'servicio-pm-med', NULL, 'cama-pm-med-006', NOW()::DATE + INTERVAL '8 hours', 3600),

-- Eventos paciente 004 (Rosa García - en lista espera)
('evento-005', 'ingreso_urgencia', NOW() - INTERVAL '12 hours', 'paciente-004', 'hospital-pm-001',
NULL, 'servicio-pm-med', NULL, NULL, NOW()::DATE + INTERVAL '8 hours', NULL),

('evento-006', 'lista_espera_iniciada', NOW() - INTERVAL '12 hours', 'paciente-004', 'hospital-pm-001',
NULL, 'servicio-pm-uti', NULL, NULL, NOW()::DATE + INTERVAL '8 hours', NULL),

-- Evento paciente 005 (Fernando Valenzuela - en lista espera)
('evento-007', 'ingreso_urgencia', NOW() - INTERVAL '24 hours', 'paciente-005', 'hospital-pm-001',
NULL, 'servicio-pm-med', NULL, NULL, NOW()::DATE + INTERVAL '8 hours' - INTERVAL '1 day', NULL),

('evento-008', 'busqueda_cama_iniciada', NOW() - INTERVAL '18 hours', 'paciente-005', 'hospital-pm-001',
NULL, 'servicio-pm-uci', NULL, NULL, NOW()::DATE + INTERVAL '8 hours', NULL);

-- ============================================
-- 9. INSERTAR LOGS DE ACTIVIDAD
-- ============================================
INSERT INTO logactividad (id, tipo, descripcion, hospital_id, paciente_id, cama_id, created_at) VALUES
('log-001', 'asignacion', 'Paciente Juan Pérez asignado a cama UCI-01-02', 'hospital-pm-001', 'paciente-001', 'cama-pm-uci-002', NOW() - INTERVAL '2 days'),
('log-002', 'asignacion', 'Paciente María Rodríguez asignado a cama MED-03-B', 'hospital-pm-001', 'paciente-002', 'cama-pm-med-006', NOW() - INTERVAL '4 hours'),
('log-003', 'lista_espera', 'Rosa García ingresada a lista de espera para UTI', 'hospital-pm-001', 'paciente-004', NULL, NOW() - INTERVAL '12 hours'),
('log-004', 'lista_espera', 'Fernando Valenzuela ingresado a lista de espera para UCI', 'hospital-pm-001', 'paciente-005', NULL, NOW() - INTERVAL '24 hours'),
('log-005', 'limpieza', 'Cama UCI-01-03 marcada para limpieza', 'hospital-pm-001', NULL, 'cama-pm-uci-003', NOW() - INTERVAL '1 hour');

-- ============================================
-- VERIFICACIÓN DE DATOS INSERTADOS
-- ============================================
-- Descomenta las siguientes consultas para verificar que los datos fueron insertados:

-- SELECT COUNT(*) as total_hospitales FROM hospital;
-- SELECT COUNT(*) as total_usuarios FROM usuarios;
-- SELECT COUNT(*) as total_servicios FROM servicio;
-- SELECT COUNT(*) as total_salas FROM sala;
-- SELECT COUNT(*) as total_camas FROM cama;
-- SELECT COUNT(*) as total_pacientes FROM paciente;
-- SELECT COUNT(*) as total_eventos FROM evento_paciente;
-- SELECT COUNT(*) as total_logs FROM logactividad;

-- ============================================
-- CONSULTAS ÚTILES PARA PRUEBA
-- ============================================

-- Ver estado de camas por servicio
-- SELECT
--     srv.nombre as servicio,
--     COUNT(c.id) as total_camas,
--     SUM(CASE WHEN c.estado = 'libre' THEN 1 ELSE 0 END) as camas_libres,
--     SUM(CASE WHEN c.estado = 'ocupada' THEN 1 ELSE 0 END) as camas_ocupadas
-- FROM cama c
-- JOIN sala s ON c.sala_id = s.id
-- JOIN servicio srv ON s.servicio_id = srv.id
-- GROUP BY srv.id, srv.nombre;

-- Ver pacientes con sus camas asignadas
-- SELECT
--     p.nombre,
--     p.run,
--     p.tipo_paciente,
--     c.identificador as cama,
--     srv.nombre as servicio
-- FROM paciente p
-- LEFT JOIN cama c ON p.cama_id = c.id
-- LEFT JOIN sala s ON c.sala_id = s.id
-- LEFT JOIN servicio srv ON s.servicio_id = srv.id
-- WHERE p.hospital_id = 'hospital-pm-001';

-- Ver lista de espera
-- SELECT
--     nombre,
--     run,
--     tipo_paciente,
--     complejidad_requerida,
--     timestamp_lista_espera
-- FROM paciente
-- WHERE en_lista_espera = TRUE
-- ORDER BY prioridad_calculada DESC;
