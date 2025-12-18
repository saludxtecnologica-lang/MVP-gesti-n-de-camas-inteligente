import type {
  Hospital,
  Cama,
  Paciente,
  PacienteCreate,
  PacienteUpdate,
  ConfiguracionSistema,
  EstadisticasGlobales,
  ListaEsperaItem,
  DerivadoItem,
  DerivacionAccion,
  CamaBloquearRequest,
  PrioridadExplicacion
} from '../types/Index';

// Obtener URL base de la API
function getApiBase(): string {
  if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  return 'http://localhost:8000';
}

const API_BASE = getApiBase();

// Tipo para respuesta genérica del backend
interface MessageResponse {
  success: boolean;
  message: string;
  data?: Record<string, unknown>;
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  // Asegurar que el endpoint comience con /api
  const url = `${API_BASE}${endpoint.startsWith('/api') ? endpoint : `/api${endpoint}`}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers
    }
  });

  if (!response.ok) {
    let errorMessage = `Error ${response.status}: ${response.statusText}`;
    
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail
            .map((err: { loc?: string[]; msg?: string }) => {
              const field = err.loc ? err.loc.join('.') : 'campo';
              return `${field}: ${err.msg || 'error de validación'}`;
            })
            .join('; ');
        } else if (typeof errorData.detail === 'object') {
          errorMessage = JSON.stringify(errorData.detail);
        }
      } else if (errorData.error) {
        errorMessage = errorData.error;
      } else if (errorData.message) {
        errorMessage = errorData.message;
      }
    } catch {
      // Si no se puede parsear el JSON, usar el mensaje por defecto
    }
    
    throw new Error(errorMessage);
  }

  return response.json();
}

// ============================================
// HOSPITALES
// ============================================

export async function getHospitales(): Promise<Hospital[]> {
  return fetchApi<Hospital[]>('/hospitales');
}

export async function getHospital(id: string): Promise<Hospital> {
  return fetchApi<Hospital>(`/hospitales/${id}`);
}

// ============================================
// CAMAS
// ============================================

export async function getCamasHospital(hospitalId: string): Promise<Cama[]> {
  return fetchApi<Cama[]>(`/hospitales/${hospitalId}/camas`);
}

export async function getCama(id: string): Promise<Cama> {
  return fetchApi<Cama>(`/camas/${id}`);
}

export async function bloquearCama(camaId: string, data: CamaBloquearRequest): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/camas/${camaId}/bloquear`, {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

// ============================================
// PACIENTES - CRUD
// ============================================

export async function crearPaciente(data: PacienteCreate): Promise<Paciente> {
  return fetchApi<Paciente>('/pacientes', {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

export async function actualizarPaciente(id: string, data: PacienteUpdate): Promise<Paciente> {
  return fetchApi<Paciente>(`/pacientes/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  });
}

export async function getPaciente(id: string): Promise<Paciente> {
  return fetchApi<Paciente>(`/pacientes/${id}`);
}

// ============================================
// TRASLADOS - Rutas: /api/traslados/*
// ============================================

/**
 * Completa el traslado de un paciente a su cama asignada.
 */
export async function completarTraslado(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/traslados/completar/${pacienteId}`, {
    method: 'POST'
  });
}

/**
 * FUNCIÓN PRINCIPAL DE CANCELACIÓN
 * 
 * Cancela un traslado o derivación. El backend determina automáticamente
 * el tipo de cancelación según el estado del paciente y sus camas.
 * 
 * Flujos posibles:
 * 1. Desde cama origen (TRASLADO_SALIENTE): paciente vuelve a CAMA_EN_ESPERA, sale de lista
 * 2. Desde cama destino (TRASLADO_ENTRANTE): paciente vuelve a lista de espera
 * 3. Derivación desde destino: paciente vuelve a lista de derivación
 * 4. Derivación desde origen: cama vuelve a OCUPADA, se cancela todo
 * 5. Paciente nuevo: se elimina del sistema
 */
export async function cancelarTraslado(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/traslados/cancelar/${pacienteId}`, {
    method: 'POST'
  });
}

/**
 * CASO 1: Cancelar traslado específicamente desde la cama de origen.
 * 
 * Resultado:
 * - Paciente vuelve a cama actual en estado CAMA_EN_ESPERA
 * - Sale de lista de espera
 * - Queda listo para iniciar nueva búsqueda manualmente
 */
export async function cancelarTrasladoDesdeOrigen(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/traslados/cancelar-desde-origen/${pacienteId}`, {
    method: 'POST'
  });
}

/**
 * CASO 2: Cancelar traslado específicamente desde la cama de destino.
 * 
 * Resultado:
 * - Se libera cama destino
 * - Paciente permanece en lista de espera buscando otra cama
 */
export async function cancelarTrasladoDesdeDestino(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/traslados/cancelar-desde-destino/${pacienteId}`, {
    method: 'POST'
  });
}

// ============================================
// BÚSQUEDA DE CAMA - Rutas: /api/pacientes/*
// ============================================

export async function buscarCamaPaciente(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/pacientes/${pacienteId}/buscar-cama`, {
    method: 'POST'
  });
}

export async function cancelarBusquedaCama(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/pacientes/${pacienteId}/cancelar-busqueda`, {
    method: 'POST'
  });
}

// ============================================
// ALTA - Rutas: /api/pacientes/*
// ============================================

export async function iniciarAlta(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/pacientes/${pacienteId}/iniciar-alta`, {
    method: 'POST'
  });
}

export async function ejecutarAlta(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/pacientes/${pacienteId}/ejecutar-alta`, {
    method: 'POST'
  });
}

export async function cancelarAlta(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/pacientes/${pacienteId}/cancelar-alta`, {
    method: 'POST'
  });
}

/**
 * Omite el periodo de espera por desactivación de oxígeno.
 * 
 * El sistema evaluará inmediatamente si el paciente:
 * - Requiere cambio de cama
 * - Califica para alta
 * - Permanece estable
 */
export async function omitirPausaOxigeno(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/pacientes/${pacienteId}/omitir-pausa-oxigeno`, {
    method: 'POST'
  });
}

// ============================================
// DERIVACIONES - Rutas: /api/derivaciones/*
// ============================================

/**
 * Acepta o rechaza una derivación pendiente.
 */
export async function accionDerivacion(pacienteId: string, accion: DerivacionAccion): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/derivaciones/${pacienteId}/accion`, {
    method: 'POST',
    body: JSON.stringify({
      accion: accion.accion,
      motivo_rechazo: accion.motivo_rechazo
    })
  });
}

/**
 * Confirma el egreso de un paciente derivado desde el hospital de origen.
 * Usar cuando el paciente derivado ya tiene cama asignada en destino.
 */
export async function confirmarEgresoDerivacion(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/derivaciones/${pacienteId}/confirmar-egreso`, {
    method: 'POST'
  });
}

/**
 * CASO 3: Cancelar derivación desde el hospital de destino.
 * 
 * Usar cuando:
 * - Se cancela desde la cama TRASLADO_ENTRANTE de un paciente derivado
 * - Se cancela desde la lista de espera de un paciente derivado
 * 
 * Resultado:
 * - Se libera cama destino si existe
 * - Paciente vuelve a lista de derivación (estado pendiente)
 * - Cama de origen vuelve de DERIVACION_CONFIRMADA a ESPERA_DERIVACION
 */
export async function cancelarDerivacionDesdeDestino(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/derivaciones/${pacienteId}/cancelar-desde-destino`, {
    method: 'POST'
  });
}

/**
 * CASO 4: Cancelar derivación desde el hospital de origen.
 * 
 * Usar cuando se cancela desde la cama de origen
 * en estado ESPERA_DERIVACION o DERIVACION_CONFIRMADA.
 * 
 * Resultado:
 * - Cama de origen vuelve a OCUPADA
 * - Se cancela todo el flujo de derivación
 * - Paciente permanece en su cama original
 */
export async function cancelarDerivacionDesdeOrigen(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/derivaciones/${pacienteId}/cancelar-desde-origen`, {
    method: 'POST'
  });
}

// ============================================
// ELIMINAR PACIENTE NUEVO
// ============================================

/**
 * CASO 5: Eliminar paciente nuevo (urgencias/ambulatorio) del sistema.
 * 
 * IMPORTANTE: La confirmación debe hacerse en el frontend antes de llamar.
 * 
 * Solo funciona para pacientes:
 * - Sin cama asignada
 * - Tipo URGENCIA o AMBULATORIO
 */
export async function eliminarPacienteNuevo(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/pacientes/${pacienteId}/eliminar`, {
    method: 'DELETE'
  });
}

// ============================================
// MODO MANUAL
// ============================================

/**
 * Asigna manualmente una cama a un paciente desde la vista de cama
 */
export async function asignarManualDesdeCama(pacienteId: string, camaDestinoId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>('/manual/asignar-desde-cama', {
    method: 'POST',
    body: JSON.stringify({
      paciente_id: pacienteId,
      cama_destino_id: camaDestinoId
    })
  });
}

/**
 * Asigna manualmente una cama a un paciente desde la lista de espera
 */
export async function asignarManualDesdeLista(pacienteId: string, camaDestinoId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>('/manual/asignar-desde-lista', {
    method: 'POST',
    body: JSON.stringify({
      paciente_id: pacienteId,
      cama_destino_id: camaDestinoId
    })
  });
}

/**
 * Realiza un traslado manual directo (modo manual)
 */
export async function trasladoManual(pacienteId: string, camaDestinoId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>('/manual/trasladar', {
    method: 'POST',
    body: JSON.stringify({
      paciente_id: pacienteId,
      cama_destino_id: camaDestinoId
    })
  });
}

/**
 * Intercambia dos pacientes de cama (modo manual)
 */
export async function intercambiarPacientes(pacienteAId: string, pacienteBId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>('/manual/intercambiar', {
    method: 'POST',
    body: JSON.stringify({
      paciente_a_id: pacienteAId,
      paciente_b_id: pacienteBId
    })
  });
}

/**
 * Egresa manualmente a un paciente (modo manual)
 */
export async function egresarManual(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/manual/egresar/${pacienteId}`, {
    method: 'POST'
  });
}

/**
 * Egresa a un paciente de la lista de espera.
 * 
 * Comportamiento según tipo:
 * - Hospitalizado: vuelve a CAMA_EN_ESPERA
 * - Derivado: vuelve a lista de derivación
 * - Nuevo: se elimina del sistema
 */
export async function egresarDeLista(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/manual/egresar-lista/${pacienteId}`, {
    method: 'POST'
  });
}

// ============================================
// LISTA DE ESPERA
// ============================================

export async function getListaEspera(hospitalId: string): Promise<ListaEsperaItem[]> {
  // Interface actualizada con todos los campos de origen y destino
  interface ListaEsperaResponse {
    hospital_id: string;
    total_pacientes: number;
    pacientes: Array<{
      paciente_id: string;
      nombre: string;
      run: string;
      prioridad: number;
      posicion: number;
      tiempo_espera_min: number;
      estado_lista: string;
      tipo_paciente: string;
      complejidad: string;
      sexo: string;
      edad: number;
      tipo_enfermedad: string;
      tipo_aislamiento: string;
      tiene_cama_actual: boolean;
      cama_actual_id: string | null;
      timestamp: string;
      // CAMPOS DE ORIGEN (nuevos - del backend)
      origen_tipo: string | null;
      origen_hospital_nombre: string | null;
      origen_hospital_codigo: string | null;
      origen_servicio_nombre: string | null;
      origen_cama_identificador: string | null;
      // CAMPO DE DESTINO (nuevo - del backend)
      servicio_destino: string | null;
    }>;
  }
  
  const response = await fetchApi<ListaEsperaResponse>(`/hospitales/${hospitalId}/lista-espera`);
  
  // Convertir al formato esperado por el frontend
  // CORRECCIÓN: Ahora incluimos los campos de origen y destino
  return response.pacientes.map(p => ({
    // Campos básicos del item
    paciente_id: p.paciente_id,
    nombre: p.nombre,
    run: p.run,
    prioridad: p.prioridad,
    posicion: p.posicion,
    tiempo_espera_min: p.tiempo_espera_min,
    tiempo_espera_minutos: p.tiempo_espera_min,
    estado_lista: p.estado_lista,
    estado: p.estado_lista as any,
    
    // CORRECCIÓN: Campos de origen - mapeados directamente desde el backend
    origen_tipo: p.origen_tipo,
    origen_hospital_nombre: p.origen_hospital_nombre,
    origen_hospital_codigo: p.origen_hospital_codigo,
    origen_servicio_nombre: p.origen_servicio_nombre,
    origen_cama_identificador: p.origen_cama_identificador,
    
    // CORRECCIÓN: Campo de destino - mapeado directamente desde el backend
    servicio_destino: p.servicio_destino,
    
    // Objeto paciente para compatibilidad con componentes existentes
    paciente: {
      id: p.paciente_id,
      nombre: p.nombre,
      run: p.run,
      sexo: p.sexo as any,
      edad: p.edad,
      tipo_paciente: p.tipo_paciente as any,
      complejidad: p.complejidad as any,
      complejidad_requerida: p.complejidad as any,
      tipo_enfermedad: p.tipo_enfermedad as any,
      tipo_aislamiento: p.tipo_aislamiento as any,
      cama_id: p.cama_actual_id,
      cama_actual_id: p.cama_actual_id,
      // También incluir origen/destino en el objeto paciente para flexibilidad
      origen_tipo: p.origen_tipo,
      origen_hospital_nombre: p.origen_hospital_nombre,
      origen_servicio_nombre: p.origen_servicio_nombre,
      servicio_destino: p.servicio_destino,
      derivacion_estado: p.tipo_paciente === 'derivado' ? 'aceptado' : null
    } as any
  }));
}


export async function getPrioridadPaciente(pacienteId: string): Promise<PrioridadExplicacion> {
  return fetchApi<PrioridadExplicacion>(`/pacientes/${pacienteId}/prioridad`);
}

// ============================================
// DERIVADOS
// ============================================

export async function getDerivados(hospitalId: string): Promise<DerivadoItem[]> {
  interface DerivadoResponse {
    paciente_id: string;
    nombre: string;
    run: string;
    prioridad: number;
    tiempo_en_lista_min: number;
    hospital_origen_id: string;
    hospital_origen_nombre: string;
    motivo_derivacion: string;
    tipo_paciente: string;
    complejidad: string;
    diagnostico: string;
  }
  
  const response = await fetchApi<DerivadoResponse[]>(`/hospitales/${hospitalId}/derivados`);
  
  // Convertir al formato esperado por el frontend
  return response.map(d => ({
    paciente_id: d.paciente_id,
    nombre: d.nombre,
    run: d.run,
    prioridad: d.prioridad,
    tiempo_en_lista_min: d.tiempo_en_lista_min,
    tiempo_en_lista_minutos: d.tiempo_en_lista_min,
    hospital_origen_id: d.hospital_origen_id,
    hospital_origen_nombre: d.hospital_origen_nombre,
    motivo_derivacion: d.motivo_derivacion,
    motivo: d.motivo_derivacion,
    diagnostico: d.diagnostico,
    complejidad: d.complejidad,
    tipo_paciente: d.tipo_paciente,
    hospital_origen: {
      id: d.hospital_origen_id,
      nombre: d.hospital_origen_nombre
    } as any,
    paciente: {
      id: d.paciente_id,
      nombre: d.nombre,
      run: d.run,
      diagnostico: d.diagnostico,
      complejidad: d.complejidad as any,
      tipo_paciente: d.tipo_paciente as any
    } as any
  }));
}

// ============================================
// CONFIGURACIÓN
// ============================================

export async function getConfiguracion(): Promise<ConfiguracionSistema> {
  return fetchApi<ConfiguracionSistema>('/configuracion');
}

export async function actualizarConfiguracion(data: Partial<ConfiguracionSistema>): Promise<ConfiguracionSistema> {
  return fetchApi<ConfiguracionSistema>('/configuracion', {
    method: 'PUT',
    body: JSON.stringify(data)
  });
}

// ============================================
// ESTADÍSTICAS
// ============================================

export async function getEstadisticas(): Promise<EstadisticasGlobales> {
  return fetchApi<EstadisticasGlobales>('/estadisticas');
}

// ============================================
// UTILIDADES
// ============================================

export function getDocumentoUrl(filename: string): string {
  return `${API_BASE}/api/documentos/${filename}`;
}

export function getWebSocketUrl(): string {
  try {
    const apiUrl = new URL(API_BASE);
    const wsProtocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProtocol}//${apiUrl.host}/ws`;
  } catch {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProtocol}//localhost:8000/ws`;
  }
}

export function obtenerListaEspera(hospitalId: string) {
  throw new Error('Function not implemented.');
}
