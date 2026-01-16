# Sistema de Recopilación de Datos y Estadísticas Avanzadas

Este documento describe el nuevo sistema completo de recopilación de datos y estadísticas implementado en el MVP de gestión de camas inteligentes.

## 📋 Tabla de Contenidos

1. [Descripción General](#descripción-general)
2. [Instalación y Configuración](#instalación-y-configuración)
3. [Arquitectura](#arquitectura)
4. [Métricas Disponibles](#métricas-disponibles)
5. [Endpoints de API](#endpoints-de-api)
6. [Uso desde Frontend](#uso-desde-frontend)
7. [Ejemplos de Uso](#ejemplos-de-uso)

## 🎯 Descripción General

El sistema recopila y analiza automáticamente todos los eventos importantes del flujo de pacientes, permitiendo obtener métricas detalladas sobre:

- **Ingresos y Egresos**: Diarios por red, hospital y servicios
- **Tiempos**: Promedios, máximos y mínimos de todos los procesos
- **Tasas de Ocupación**: Por red, hospital y servicios
- **Flujos**: Traslados y derivaciones más frecuentes
- **Demanda**: Servicios con mayor demanda
- **Casos Especiales**: Seguimiento de pacientes con requerimientos especiales
- **Subutilización**: Identificación de recursos infrautilizados
- **Trazabilidad**: Historial completo del recorrido del paciente

## 🚀 Instalación y Configuración

### 1. Ejecutar Migración de Base de Datos

```bash
# Desde el directorio backend
cd backend
alembic upgrade head
```

Esto creará la tabla `evento_paciente` que registra todos los eventos del sistema.

### 2. Verificar que el Backend Esté Funcionando

```bash
# Levantar el backend
docker-compose up -d
```

### 3. Acceder a la Documentación de la API

Una vez levantado el sistema, puedes acceder a:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🏗️ Arquitectura

### Componentes Principales

#### 1. **Modelo de Eventos** (`backend/app/models/evento_paciente.py`)

Registra todos los eventos importantes:
- Ingresos (urgencia, ambulatorio)
- Asignaciones de cama
- Traslados (iniciado, confirmado, completado)
- Derivaciones (solicitada, aceptada, rechazada, completada)
- Altas (sugerida, iniciada, completada)
- Fallecimientos

#### 2. **Servicio de Eventos** (`backend/app/services/evento_service.py`)

Proporciona métodos para registrar eventos automáticamente:
- `registrar_ingreso()`
- `registrar_traslado_iniciado()`
- `registrar_derivacion_solicitada()`
- Y muchos más...

#### 3. **Servicio de Estadísticas** (`backend/app/services/estadisticas_service.py`)

Calcula todas las métricas solicitadas:
- `calcular_ingresos_red()`
- `calcular_tiempo_espera_cama()`
- `calcular_tasa_ocupacion_hospital()`
- `obtener_trazabilidad_paciente()`
- Y muchos más...

#### 4. **Endpoints de API** (`backend/app/api/estadisticas.py`)

Expone todas las estadísticas a través de endpoints REST.

## 📊 Métricas Disponibles

### 1. Ingresos Diarios

#### Ingresos de la Red
Suma de todos los pacientes nuevos en todos los hospitales (urgencia + ambulatorio).

#### Ingresos por Hospital
Todos los pacientes que llegan al hospital:
- Pacientes nuevos (urgencia/ambulatorio)
- Derivados aceptados de otros hospitales

#### Ingresos por Servicio
Todos los pacientes que llegan a un servicio:
- Desde urgencias
- Desde ambulatorio
- Traslados de otros servicios
- Derivaciones de otros hospitales

### 2. Egresos Diarios

#### Egresos de la Red
Suma de todos los pacientes que salen definitivamente del sistema (altas + fallecidos).

#### Egresos por Hospital
Pacientes que salen del hospital:
- Altas
- Fallecidos
- Derivados a otros hospitales

#### Egresos por Servicio
Pacientes que salen del servicio:
- Traslados a otros servicios
- Altas
- Fallecidos
- Derivaciones

### 3. Tiempos (Promedio, Máximo, Mínimo)

| Métrica | Descripción | Inicio | Fin |
|---------|-------------|--------|-----|
| **Espera de Cama** | Tiempo que un paciente espera desde que inicia búsqueda hasta que se asigna cama | Búsqueda iniciada | Cama asignada |
| **Espera de Derivación** | Tiempo esperando respuesta de derivación | Derivación solicitada | Aceptada/Rechazada |
| **Traslado Saliente** | Tiempo con cama origen en espera de cama destino | Traslado iniciado | Traslado completado |
| **Confirmación de Traslado** | Tiempo en estado "cama en espera" | Cama en espera inicio | Cama en espera fin |
| **Alta Sugerida** | Tiempo desde sugerencia hasta inicio de alta | Alta sugerida | Alta iniciada |
| **Alta Completada** | Tiempo desde inicio hasta completar alta | Alta iniciada | Alta completada |
| **Egreso de Fallecido** | Tiempo desde marcado como fallecido hasta egreso | Fallecido marcado | Fallecido egresado |
| **Hospitalización en Establecimiento** | Tiempo total hospitalizado en el mismo hospital | Ingreso al hospital | Egreso del hospital |
| **Hospitalización en Red** | Tiempo total hospitalizado en cualquier hospital | Primer ingreso a red | Último egreso de red |
| **Tiempo por Servicio** | Tiempo en un servicio específico | Entrada al servicio | Salida del servicio |

**Variaciones de Hospitalización:**
- **Con casos especiales**: Solo pacientes que tuvieron requerimientos especiales
- **Sin casos especiales**: Solo pacientes que nunca tuvieron requerimientos especiales

### 4. Tasas de Ocupación

Calculadas como: `(camas_ocupadas / total_camas) × 100`

- **Red**: Tasa global de toda la red de hospitales
- **Hospital**: Tasa de un hospital específico
- **Servicio**: Tasa de un servicio específico

### 5. Flujos Más Repetidos

Identifica los traslados y derivaciones más frecuentes:
- Traslados entre servicios
- Derivaciones entre hospitales

### 6. Servicios con Mayor Demanda

Determina qué servicios tienen:
- Mayor tasa de ocupación
- Más pacientes en espera compatibles
- Score de demanda combinado

### 7. Casos Especiales

Cuenta pacientes con:
- Cardiocirugía
- Caso social
- Caso socio-judicial

### 8. Recursos Subutilizados

#### Camas Subutilizadas
Identifica camas que permanecen libres por más tiempo del normal.

#### Servicios Subutilizados
Identifica servicios con mayor tasa de camas libres al final del día clínico.

### 9. Trazabilidad del Paciente

Muestra el recorrido completo del paciente:
- Todos los servicios por donde pasó
- Tiempo en cada servicio (días y horas)
- Fechas de entrada y salida

**Nota**: Esta información aparece en el cuadro resumen del paciente.

## 🔌 Endpoints de API

### Estadísticas Completas

```http
GET /api/estadisticas/avanzadas/completas?dias=7
```

Retorna todas las estadísticas en una sola llamada.

### Ingresos y Egresos

```http
# Ingresos
GET /api/estadisticas/ingresos/red?dias=1
GET /api/estadisticas/ingresos/hospital/{hospital_id}?dias=1
GET /api/estadisticas/ingresos/servicio/{servicio_id}?dias=1

# Egresos
GET /api/estadisticas/egresos/red?dias=1
GET /api/estadisticas/egresos/hospital/{hospital_id}?dias=1
GET /api/estadisticas/egresos/servicio/{servicio_id}?dias=1
```

### Tiempos

```http
GET /api/estadisticas/tiempos/espera-cama?dias=7
GET /api/estadisticas/tiempos/derivacion-pendiente?dias=7
GET /api/estadisticas/tiempos/traslado-saliente?dias=7
GET /api/estadisticas/tiempos/confirmacion-traslado?dias=7
GET /api/estadisticas/tiempos/alta?dias=7
GET /api/estadisticas/tiempos/fallecido?dias=7
GET /api/estadisticas/tiempos/hospitalizacion?hospital_id={id}&solo_casos_especiales={true|false|null}&dias=30
```

### Tasas de Ocupación

```http
GET /api/estadisticas/ocupacion/red
GET /api/estadisticas/ocupacion/hospital/{hospital_id}
GET /api/estadisticas/ocupacion/servicio/{servicio_id}
```

### Flujos y Demanda

```http
GET /api/estadisticas/flujos/mas-repetidos?dias=30&limite=10
GET /api/estadisticas/demanda/servicios
```

### Casos Especiales

```http
GET /api/estadisticas/casos-especiales?hospital_id={id}
```

### Subutilización

```http
GET /api/estadisticas/subutilizacion/camas?hospital_id={id}&dias=1
GET /api/estadisticas/subutilizacion/servicios?hospital_id={id}
```

### Trazabilidad

```http
GET /api/estadisticas/trazabilidad/paciente/{paciente_id}
```

## 💻 Uso desde Frontend

### 1. Importar Tipos

```typescript
import {
  EstadisticasCompletas,
  TiempoEstadistica,
  TasaOcupacion,
  TrazabilidadServicio,
} from '../types/types';
```

### 2. Llamar a la API

```typescript
// Obtener todas las estadísticas
const response = await fetch('/api/estadisticas/avanzadas/completas?dias=7');
const data: EstadisticasCompletas = await response.json();

// Obtener trazabilidad de un paciente
const trazabilidad = await fetch(`/api/estadisticas/trazabilidad/paciente/${pacienteId}`);
const historial: TrazabilidadServicio[] = await trazabilidad.json();
```

### 3. Mostrar en Componentes

```typescript
// Mostrar tiempos promedio
{data.tiempo_espera_cama && (
  <div>
    <h3>Tiempo de Espera de Cama</h3>
    <p>Promedio: {formatSeconds(data.tiempo_espera_cama.promedio)}</p>
    <p>Máximo: {formatSeconds(data.tiempo_espera_cama.maximo)}</p>
    <p>Mínimo: {formatSeconds(data.tiempo_espera_cama.minimo)}</p>
  </div>
)}

// Mostrar trazabilidad
{trazabilidad.map((paso, index) => (
  <div key={index}>
    <h4>{paso.servicio_nombre}</h4>
    <p>Duración: {paso.duracion_dias} días, {paso.duracion_horas} horas</p>
    <p>Entrada: {new Date(paso.entrada).toLocaleString()}</p>
    <p>Salida: {paso.salida === 'Actual' ? 'Actual' : new Date(paso.salida).toLocaleString()}</p>
  </div>
))}
```

### 4. Exportar Datos

Para permitir descarga de estadísticas:

```typescript
const exportarCSV = (data: any, filename: string) => {
  const csv = convertToCSV(data);
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
};
```

## 📝 Ejemplos de Uso

### Ejemplo 1: Dashboard de Ingresos/Egresos del Día

```typescript
const DashboardIngresosEgresos = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch('/api/estadisticas/avanzadas/completas?dias=1')
      .then(res => res.json())
      .then(setData);
  }, []);

  return (
    <div>
      <h2>Ingresos y Egresos del Día</h2>
      <div className="stats-grid">
        <StatCard
          title="Ingresos de la Red"
          value={data?.ingresos_red?.total || 0}
        />
        <StatCard
          title="Egresos de la Red"
          value={data?.egresos_red?.total || 0}
        />
      </div>
    </div>
  );
};
```

### Ejemplo 2: Análisis de Tiempos

```typescript
const AnalisisTiempos = () => {
  const [tiempos, setTiempos] = useState<TiempoEstadistica | null>(null);

  useEffect(() => {
    fetch('/api/estadisticas/tiempos/espera-cama?dias=7')
      .then(res => res.json())
      .then(setTiempos);
  }, []);

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  return (
    <div>
      <h2>Análisis de Tiempos de Espera de Cama</h2>
      {tiempos && (
        <table>
          <thead>
            <tr>
              <th>Métrica</th>
              <th>Valor</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Promedio</td>
              <td>{formatTime(tiempos.promedio)}</td>
            </tr>
            <tr>
              <td>Máximo</td>
              <td>{formatTime(tiempos.maximo)}</td>
            </tr>
            <tr>
              <td>Mínimo</td>
              <td>{formatTime(tiempos.minimo)}</td>
            </tr>
            <tr>
              <td>Cantidad</td>
              <td>{tiempos.cantidad}</td>
            </tr>
          </tbody>
        </table>
      )}
    </div>
  );
};
```

### Ejemplo 3: Trazabilidad del Paciente

```typescript
const TrazabilidadPaciente = ({ pacienteId }: { pacienteId: string }) => {
  const [trazabilidad, setTrazabilidad] = useState<TrazabilidadServicio[]>([]);

  useEffect(() => {
    fetch(`/api/estadisticas/trazabilidad/paciente/${pacienteId}`)
      .then(res => res.json())
      .then(setTrazabilidad);
  }, [pacienteId]);

  return (
    <div>
      <h3>Historial del Paciente</h3>
      <div className="timeline">
        {trazabilidad.map((paso, index) => (
          <div key={index} className="timeline-item">
            <h4>{paso.servicio_nombre}</h4>
            <p>
              <strong>Duración:</strong> {paso.duracion_dias} días, {paso.duracion_horas} horas
            </p>
            <p>
              <strong>Entrada:</strong> {new Date(paso.entrada).toLocaleString()}
            </p>
            <p>
              <strong>Salida:</strong>{' '}
              {paso.salida === 'Actual'
                ? 'Actualmente aquí'
                : new Date(paso.salida).toLocaleString()}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};
```

## 🔄 Integración con Servicios Existentes

Para que los eventos se registren automáticamente, es necesario integrar el `EventoService` en los servicios existentes:

### Ejemplo: Integración en Servicio de Traslado

```python
from app.services.evento_service import EventoService

async def iniciar_traslado(paciente, cama_destino_id, session):
    # ... lógica de traslado ...

    # Registrar evento
    await EventoService.registrar_traslado_iniciado(
        session=session,
        paciente=paciente,
        cama_origen_id=paciente.cama_id,
        cama_destino_id=cama_destino_id
    )

    return resultado
```

## ⚙️ Configuración del Día Clínico

El sistema define un **día clínico** como un período de 24 horas que inicia a las **8:00 AM**.

Esto significa que:
- Un evento a las 7:59 AM del día 16 pertenece al día clínico del día 15
- Un evento a las 8:00 AM del día 16 pertenece al día clínico del día 16

Esta configuración es importante para los cálculos de ocupación y subutilización.

## 🎨 Visualización de Datos

Se recomienda usar las siguientes librerías para visualización:

- **Recharts**: Para gráficos de líneas y barras
- **Chart.js**: Para gráficos circulares
- **Material-UI DataGrid**: Para tablas con paginación y ordenamiento
- **React-CSV**: Para exportación de datos

## 📚 Referencias

- **Documentación de la API**: http://localhost:8000/docs
- **Código fuente del servicio de estadísticas**: `backend/app/services/estadisticas_service.py`
- **Código fuente del servicio de eventos**: `backend/app/services/evento_service.py`
- **Modelos de datos**: `backend/app/models/evento_paciente.py`

## 🐛 Troubleshooting

### Error: "tabla evento_paciente no existe"

**Solución**: Ejecutar la migración de base de datos:
```bash
cd backend
alembic upgrade head
```

### Los eventos no se están registrando

**Solución**: Asegurarse de que los servicios existentes estén llamando a `EventoService` en las operaciones correspondientes.

### Las estadísticas muestran ceros

**Solución**: Los cálculos dependen de eventos registrados. Si el sistema es nuevo, las estadísticas estarán vacías hasta que se registren eventos.

## 📄 Licencia

Este sistema es parte del MVP de gestión de camas inteligentes.
