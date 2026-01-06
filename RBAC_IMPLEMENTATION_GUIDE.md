# Guía de Implementación RBAC - Sistema de Gestión de Camas

## ✅ Estado de Implementación

El sistema RBAC Multinivel ha sido **implementado completamente** en el código. Los componentes principales incluyen:

### Backend ✅ Implementado
- ✅ Modelo de usuarios con nuevos roles y permisos
- ✅ Servicio RBAC con lógica de filtrado por servicio/hospital
- ✅ Dependencies de autenticación y autorización
- ✅ Mapeo completo de permisos por rol

### Frontend ✅ Implementado
- ✅ Tipos TypeScript actualizados con nuevos roles y permisos
- ✅ Botón de logout y menú de usuario en Header
- ✅ Contexto de autenticación con hooks de permisos

## 🔐 Sistema de Permisos

### Capa 1: Administración y Red (Global)
| Rol | Acceso | Restricciones |
|-----|--------|---------------|
| **PROGRAMADOR** | Todos los hospitales | Acceso total sin restricciones |
| **DIRECTIVO_RED** | Todos los hospitales | ⚠️ **SOLO LECTURA** - Bloqueo total de escritura |

### Capa 2: Gestión Local (Hospitalario)
| Rol | Acceso | Restricciones |
|-----|--------|---------------|
| **DIRECTIVO_HOSPITAL** | Su hospital | ⚠️ **SOLO LECTURA** - Sin cambios operativos |
| **GESTOR_CAMAS** | Puerto Montt | ❌ NO puede reevaluar clínicamente ni registrar pacientes |

### Capa 3: Clínica (Servicio)
| Rol | Acceso | Capacidades |
|-----|--------|-------------|
| **MEDICO** | Su servicio | Reevaluación, derivaciones, búsqueda de cama, sugerir altas |
| **ENFERMERA** | Su servicio | Reevaluación, aceptar traslados, ejecutar altas, egresos |
| **TENS** | Su servicio | **SOLO** completar traslados (sin docs clínicos) |

## 👥 Usuarios de Prueba

### Para Probar el Sistema

```bash
# Capa 1 - Administración y Red
Usuario: programador
Password: Programador123!
→ Acceso total al sistema

Usuario: directivo_red
Password: DirectivoRed123!
→ Solo lectura de todos los hospitales (NO puede editar/crear)

# Capa 2 - Gestión Local
Usuario: directivo_hospital_pm
Password: DirectivoPM123!
→ Solo lectura de Puerto Montt (NO puede editar/crear)

Usuario: gestor_camas
Password: GestorCamas123!
→ Gestión de Puerto Montt (NO puede reevaluar pacientes)

# Capa 3 - Clínica
Usuario: medico_medicina
Password: MedicoMed123!
→ Médico de Medicina (puede reevaluar, derivar, buscar cama)

Usuario: enfermera_medicina
Password: EnfermeraMed123!
→ Enfermera de Medicina (puede reevaluar, aceptar traslados, dar altas)

Usuario: tens_medicina
Password: TensMed123!
→ TENS de Medicina (SOLO completar traslados, sin ver docs clínicos)

# Servicios Especiales
Usuario: urgencias_pm
Password: UrgenciasPM123!
→ Urgencias (SIN dashboard de camas, solo crear pacientes de urgencia)

Usuario: ambulatorio
Password: Ambulatorio123!
→ Ambulatorio (SIN dashboard de camas, solo crear pacientes ambulatorios)
```

## 🚀 Cómo Aplicar Restricciones en los Endpoints

### 1. Aplicar Permisos de Solo Lectura

Para roles que NO deben poder crear/editar (DIRECTIVO_RED, DIRECTIVO_HOSPITAL):

```python
from app.core.auth_dependencies import (
    get_current_user,
    require_permissions,
    require_not_readonly
)
from app.core.rbac_service import rbac_service

# Endpoint de creación - requiere que NO sea solo lectura
@router.post("", response_model=PacienteResponse)
async def crear_paciente(
    paciente_data: PacienteCreate,
    current_user: Usuario = Depends(require_not_readonly()),  # ← Verifica que NO sea solo lectura
    session: Session = Depends(get_session)
):
    # Verificar permiso específico
    if not current_user.tiene_permiso(PermisoEnum.PACIENTE_CREAR):
        raise HTTPException(status_code=403, detail="No tienes permiso para crear pacientes")

    # Tu lógica existente...
```

### 2. Filtrar Pacientes por Servicio/Hospital

Para aplicar el filtrado según la capa del usuario:

```python
from app.core.rbac_service import rbac_service

@router.get("/lista-espera", response_model=List[PacienteResponse])
async def obtener_lista_espera(
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Obtener todos los pacientes en lista de espera
    query = select(Paciente).where(Paciente.estado_traslado == "en_busqueda")

    # Aplicar filtros según el rol del usuario
    if current_user.rol in rbac_service.ROLES_ACCESO_SERVICIO:
        # Filtrar por servicio del usuario
        pacientes = []
        for paciente in session.exec(query).all():
            if rbac_service.puede_ver_paciente(
                current_user,
                paciente.servicio_origen,
                paciente.servicio_destino,
                paciente.hospital_id
            ):
                pacientes.append(paciente)
    elif current_user.hospital_id:
        # Filtrar por hospital
        query = query.where(Paciente.hospital_id == current_user.hospital_id)
        pacientes = session.exec(query).all()
    else:
        # Acceso global
        pacientes = session.exec(query).all()

    return pacientes
```

### 3. Verificar Acceso al Dashboard

Para roles que NO tienen dashboard (URGENCIAS, AMBULATORIO):

```python
from app.core.auth_dependencies import require_dashboard_access

@router.get("/dashboard")
async def obtener_dashboard(
    current_user: Usuario = Depends(require_dashboard_access()),  # ← Verifica acceso al dashboard
    session: Session = Depends(get_session)
):
    # Tu lógica de dashboard...
```

### 4. Verificar Permisos de Reevaluación

Solo MEDICO y ENFERMERA pueden reevaluar:

```python
@router.put("/{paciente_id}")
async def actualizar_paciente(
    paciente_id: str,
    paciente_data: PacienteUpdate,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Si está intentando reevaluar, verificar permiso
    if paciente_data.dict(exclude_unset=True):  # Si hay cambios clínicos
        if not current_user.tiene_permiso(PermisoEnum.PACIENTE_REEVALUAR):
            raise HTTPException(
                status_code=403,
                detail="Solo médicos y enfermeras pueden reevaluar pacientes"
            )

    # Tu lógica existente...
```

### 5. Verificar Permisos de Modo Manual

Solo en Puerto Montt (GESTOR_CAMAS) o hospitales periféricos (JEFE_SERVICIO medicoquirúrgico):

```python
from app.core.auth_dependencies import require_modo_manual_access

@router.post("/modo-manual/{hospital_id}")
async def activar_modo_manual(
    hospital_id: str,
    current_user: Usuario = Depends(require_modo_manual_access(hospital_id)),
    session: Session = Depends(get_session)
):
    # Tu lógica de modo manual...
```

## 🎯 Funciones Disponibles en el Servicio RBAC

```python
from app.core.rbac_service import rbac_service

# Verificar acceso a hospital
puede_hospital = rbac_service.puede_acceder_hospital(usuario, "puerto_montt")

# Verificar acceso a servicio
puede_servicio = rbac_service.puede_acceder_servicio(usuario, "medicina")

# Verificar si puede ver un paciente específico
puede_ver = rbac_service.puede_ver_paciente(
    usuario,
    paciente_servicio_origen="urgencias",
    paciente_servicio_destino="medicina",
    paciente_hospital_id="puerto_montt"
)

# Verificar acceso al dashboard
tiene_dashboard = rbac_service.tiene_acceso_dashboard(usuario)

# Verificar si es solo lectura
es_readonly = rbac_service.es_solo_lectura(usuario)

# Verificar restricción de escritura (lanza excepción si es solo lectura)
rbac_service.verificar_restriccion_escritura(usuario, "crear paciente")

# Verificar modo manual
puede_modo_manual = rbac_service.puede_usar_modo_manual(usuario, "puerto_montt")

# Verificar bloqueo de camas
puede_bloquear = rbac_service.puede_bloquear_camas(usuario, "llanquihue")
```

## 🎨 Uso de Permisos en el Frontend

### Ocultar botones según permisos:

```typescript
import { usePermission, usePermissions, useRole } from '../context/AuthContext';
import { PermisoEnum, RolEnum } from '../types/auth';

function MiComponente() {
  // Hook para verificar un permiso específico
  const puedeCrearPaciente = usePermission(PermisoEnum.PACIENTE_CREAR);
  const puedeReevaluar = usePermission(PermisoEnum.PACIENTE_REEVALUAR);
  const tieneDashboard = usePermission(PermisoEnum.DASHBOARD_VER);

  // Hook para verificar múltiples permisos (AL MENOS UNO)
  const puedeGestionarDerivaciones = useAnyPermission([
    PermisoEnum.DERIVACION_SOLICITAR,
    PermisoEnum.DERIVACION_ACEPTAR,
    PermisoEnum.DERIVACION_RECHAZAR
  ]);

  // Hook para verificar rol
  const esMedico = useRole(RolEnum.MEDICO);
  const esEnfermera = useRole(RolEnum.ENFERMERA);

  return (
    <div>
      {/* Botón solo visible si tiene permiso */}
      {puedeCrearPaciente && (
        <button onClick={crearPaciente}>Crear Paciente</button>
      )}

      {/* Botón solo visible para médicos y enfermeras */}
      {puedeReevaluar && (
        <button onClick={reevaluarPaciente}>Reevaluar</button>
      )}

      {/* Dashboard solo para roles con acceso */}
      {tieneDashboard ? (
        <Dashboard />
      ) : (
        <p>No tienes acceso al dashboard de camas</p>
      )}
    </div>
  );
}
```

### Componentes de protección:

```typescript
import { RequirePermission, RequireAnyPermission, RequireRole } from '../components/auth/ProtectedRoute';

// Mostrar solo si tiene el permiso
<RequirePermission permiso={PermisoEnum.ALTA_SUGERIR}>
  <button>Sugerir Alta</button>
</RequirePermission>

// Mostrar solo si tiene AL MENOS UNO de los permisos
<RequireAnyPermission permisos={[PermisoEnum.DERIVACION_SOLICITAR, PermisoEnum.DERIVACION_ACEPTAR]}>
  <SeccionDerivaciones />
</RequireAnyPermission>

// Mostrar solo para roles específicos
<RequireRole rol={RolEnum.MEDICO}>
  <button>Buscar Cama</button>
</RequireRole>
```

## 📝 Próximos Pasos

Para completar la aplicación del RBAC en todos los endpoints:

1. **Aplicar `require_not_readonly()`** en todos los endpoints de creación/edición
2. **Aplicar filtrado por servicio** en endpoints de lista de pacientes
3. **Verificar permisos específicos** antes de operaciones críticas
4. **Ocultar componentes** en el frontend según permisos del usuario

## 🐛 Debugging

Para verificar qué permisos tiene un usuario:

```python
# En el backend
print(f"Usuario: {usuario.nombre_completo}")
print(f"Rol: {usuario.rol}")
print(f"Permisos: {[p.value for p in usuario.permisos]}")
```

```typescript
// En el frontend
const { user } = useAuth();
console.log('Usuario:', user?.nombre_completo);
console.log('Rol:', user?.rol);
console.log('Permisos:', user?.permisos);
```

## 📚 Archivos Clave

- `/backend/app/models/usuario.py` - Definición de roles y permisos
- `/backend/app/core/rbac_service.py` - Servicio de autorización RBAC
- `/backend/app/core/auth_dependencies.py` - Dependencies de FastAPI
- `/frontend/src/context/AuthContext.tsx` - Contexto de autenticación
- `/frontend/src/types/auth.ts` - Tipos y enums de roles/permisos
- `/frontend/src/components/layout/Header.tsx` - Header con logout

## ✅ Checklist de Seguridad

- [x] Roles y permisos definidos según especificación
- [x] Servicio RBAC con lógica de filtrado
- [x] Dependencies de autenticación/autorización
- [x] Botón de logout en frontend
- [x] Hooks de permisos en frontend
- [ ] Aplicar restricciones en todos los endpoints de escritura
- [ ] Aplicar filtrado de datos en queries
- [ ] Ocultar componentes según permisos
- [ ] Testing con diferentes perfiles de usuario
