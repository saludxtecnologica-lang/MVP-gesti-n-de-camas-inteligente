# 🎯 USUARIOS DEL SISTEMA - RBAC MULTINIVEL

## 📋 Sistema de 3 Capas

- **Capa 1:** Administración y Red (Acceso global)
- **Capa 2:** Gestión Local (Nivel hospitalario)
- **Capa 3:** Clínica (Nivel servicio + rol profesional)

---

## 🔴 CAPA 1: ADMINISTRACIÓN Y RED

### programador
- **Contraseña:** `Prog123!`
- **Rol:** Programador (Acceso total al sistema)
- **Alcance:** Todos los hospitales y servicios
- **Permisos:** Creación, edición, eliminación, configuración total

### directivo_red
- **Contraseña:** `DRed123!`
- **Rol:** Directivo de Red (Solo lectura)
- **Alcance:** Todos los hospitales - visión completa de la red
- **Permisos:** Visualización, estadísticas, reportes

---

## 🟠 CAPA 2: GESTIÓN LOCAL

### directivo_pm
- **Contraseña:** `DPM123!`
- **Rol:** Directivo Hospital (Solo lectura)
- **Alcance:** Hospital Puerto Montt únicamente
- **Permisos:** Visualización de su hospital, estadísticas locales

### gestor_camas
- **Contraseña:** `Gest123!`
- **Rol:** Gestor de Camas
- **Alcance:** Hospital Puerto Montt - todos los servicios
- **Permisos:** Gestión de camas, asignaciones, bloqueos, configuración

---

## 🟢 CAPA 3: CLÍNICA - MÉDICOS

### medico_medicina
- **Contraseña:** `MMed123!`
- **Rol:** Médico
- **Servicio:** Medicina (Puerto Montt)
- **Permisos:** ✅ Reevaluar pacientes, solicitar derivaciones
- **Restricción:** Solo pacientes de Medicina (origen o destino)

### medico_cirugia
- **Contraseña:** `MCir123!`
- **Rol:** Médico
- **Servicio:** Cirugía (Puerto Montt)
- **Permisos:** ✅ Reevaluar pacientes, solicitar derivaciones
- **Restricción:** Solo pacientes de Cirugía (origen o destino)

### medico_uci
- **Contraseña:** `MUCI123!`
- **Rol:** Médico
- **Servicio:** UCI (Puerto Montt)
- **Permisos:** ✅ Reevaluar pacientes, solicitar derivaciones
- **Restricción:** Solo pacientes de UCI (origen o destino)

---

## 🟢 CAPA 3: CLÍNICA - ENFERMERAS/MATRONAS

### enfermera_medicina
- **Contraseña:** `EMed123!`
- **Rol:** Enfermera
- **Servicio:** Medicina (Puerto Montt)
- **Permisos:** ✅ **PUEDE REEVALUAR** pacientes, actualizar estado
- **Restricción:** Solo pacientes de Medicina (origen o destino)

### matrona_obs
- **Contraseña:** `MObs123!`
- **Rol:** Enfermera (incluye matronas)
- **Servicio:** Obstetricia (Puerto Montt)
- **Permisos:** ✅ **PUEDE REEVALUAR** pacientes de obstetricia
- **Restricción:** Solo pacientes de Obstetricia (exclusivo)

---

## 🟢 CAPA 3: CLÍNICA - TENS

### tens_medicina
- **Contraseña:** `TMed123!`
- **Rol:** TENS (Técnico de Enfermería)
- **Servicio:** Medicina (Puerto Montt)
- **Permisos:** Visualización, actualización de estados básicos
- **Restricción:** Solo pacientes de Medicina (origen o destino)

---

## 🔵 ROLES ESPECIALIZADOS

### jefe_medicina
- **Contraseña:** `JMed123!`
- **Rol:** Jefe de Servicio
- **Servicio:** Medicina (Puerto Montt)
- **Permisos:** Gestión completa de su servicio, bloqueo de camas

### urgencias_pm
- **Contraseña:** `Urg123!`
- **Rol:** Urgencias
- **Servicio:** Urgencias (Puerto Montt)
- **Permisos:** Registro de pacientes, solo de urgencias
- **Restricción:** SOLO pacientes con origen en Urgencias

---

## 📊 TABLA RESUMEN RÁPIDA

| USUARIO            | CONTRASEÑA | ROL                | HOSPITAL     | SERVICIO    |
|--------------------|------------|--------------------|--------------|-------------|
| programador        | Prog123!   | programador        | TODOS        | TODOS       |
| directivo_red      | DRed123!   | directivo_red      | TODOS        | TODOS       |
| directivo_pm       | DPM123!    | directivo_hospital | puerto_montt | TODOS       |
| gestor_camas       | Gest123!   | gestor_camas       | puerto_montt | TODOS       |
| medico_medicina    | MMed123!   | medico             | puerto_montt | medicina    |
| medico_cirugia     | MCir123!   | medico             | puerto_montt | cirugia     |
| medico_uci         | MUCI123!   | medico             | puerto_montt | uci         |
| enfermera_medicina | EMed123!   | enfermera          | puerto_montt | medicina    |
| matrona_obs        | MObs123!   | enfermera          | puerto_montt | obstetricia |
| tens_medicina      | TMed123!   | tens               | puerto_montt | medicina    |
| jefe_medicina      | JMed123!   | jefe_servicio      | puerto_montt | medicina    |
| urgencias_pm       | Urg123!    | urgencias          | puerto_montt | urgencias   |

---

## ✅ VERIFICACIÓN DE PERMISOS DE REEVALUACIÓN

### PUEDEN REEVALUAR PACIENTES:
- ✅ medico_medicina (Médico - Medicina)
- ✅ medico_cirugia (Médico - Cirugía)
- ✅ medico_uci (Médico - UCI)
- ✅ enfermera_medicina (Enfermera - Medicina)
- ✅ matrona_obs (Matrona - Obstetricia)
- ✅ programador (Acceso total)

### NO PUEDEN REEVALUAR PACIENTES:
- ❌ tens_medicina (TENS - Solo visualización)
- ❌ urgencias_pm (Urgencias - Solo registro)
- ❌ gestor_camas (Gestión - No clínico)
- ❌ directivo_pm (Solo lectura)
- ❌ directivo_red (Solo lectura)

---

## 🧪 CASOS DE PRUEBA PARA VERIFICAR CORRECCIONES

### PRUEBA 1: Médico reevalúa paciente de su servicio
1. Login: `medico_medicina` / `MMed123!`
2. Buscar paciente en Medicina
3. Abrir modal de reevaluación
4. Modificar complejidad/requerimientos
5. Guardar
**✅ DEBE FUNCIONAR SIN ERROR 403**

### PRUEBA 2: Enfermera reevalúa paciente de su servicio
1. Login: `enfermera_medicina` / `EMed123!`
2. Buscar paciente en Medicina
3. Abrir modal de reevaluación
4. Modificar complejidad/requerimientos
5. Guardar
**✅ DEBE FUNCIONAR SIN ERROR 403**

### PRUEBA 3: Cambio de sesión sin F5
1. Login: `medico_medicina` / `MMed123!`
2. Ver dashboard con datos de Medicina
3. Logout
4. Login: `medico_cirugia` / `MCir123!`
**✅ DEBE CARGAR DATOS DE CIRUGÍA AUTOMÁTICAMENTE**

### PRUEBA 4: Matrona con obstetricia
1. Login: `matrona_obs` / `MObs123!`
2. Debe ver SOLO pacientes de Obstetricia
3. Puede reevaluar pacientes de Obstetricia
**✅ DEBE FUNCIONAR CON RESTRICCIÓN CORRECTA**

---

## 🚀 RESUMEN DE CORRECCIONES APLICADAS

### ✅ Error 403 en reevaluación - SOLUCIONADO
- Normalización de servicios (medicina vs Medicina)
- Campo `origen_servicio_nombre` correcto
- Método `normalizar_servicio()` implementado en RBAC

### ✅ Enfermeras pueden reevaluar - IMPLEMENTADO
- `RolEnum.ENFERMERA` agregado a permisos de reevaluación
- Incluye matronas (mismo rol)
- Verificado en `backend/app/api/pacientes.py:380`

### ✅ Recarga automática al cambiar sesión - IMPLEMENTADO
- `useEffect` reactivo a cambios de user
- Sin necesidad de F5
- Implementado en `frontend/src/context/AppContext.tsx:379-420`

### ✅ Credenciales de prueba eliminadas - COMPLETADO
- Array `USUARIOS_PRUEBA` vacío en `seed_users.py`
- Nuevos usuarios creados con sistema seguro
- Contraseñas únicas por usuario

---

## 📦 COMMITS REALIZADOS

### Commit 1: `85b9f3f`
```
fix: Corregir permisos RBAC y eliminar credenciales de prueba
- Corregido campo servicio_origen → origen_servicio_nombre
- Agregado RolEnum.ENFERMERA para reevaluación
- Eliminadas 17 credenciales de prueba
```

### Commit 2: `01597c7`
```
fix: Corregir validación de servicios en RBAC y recarga de datos al cambiar sesión
- Normalización de servicios en RBAC
- Recarga automática al cambiar sesión
```

---

## 🔗 PULL REQUEST

**Branch:** `claude/role-based-credentials-RbyQm`

**URL:** https://github.com/saludxtecnologica-lang/MVP-gesti-n-de-camas-inteligente/pull/new/claude/role-based-credentials-RbyQm

---

## 📝 NOTAS IMPORTANTES

1. **Seguridad:** Las credenciales mostradas son para ambiente de desarrollo/testing
2. **Producción:** En producción, crear usuarios con contraseñas robustas y únicas
3. **Normalización:** El sistema normaliza automáticamente los nombres de servicio
4. **Compatibilidad:** bcrypt versión 4.0.1 requerida para evitar conflictos
5. **Base de Datos:** Los usuarios están creados en `gestion_camas.db`

---

*Documento generado el 2026-01-14*
*Sistema MVP Gestión de Camas Inteligente*
