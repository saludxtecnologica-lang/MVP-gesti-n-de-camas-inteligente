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

export async function completarTraslado(pacienteId: string): Promise<MessageResponse> {
  // RUTA CORRECTA: /api/traslados/completar/{paciente_id}
  return fetchApi<MessageResponse>(`/traslados/completar/${pacienteId}`, {
    method: 'POST'
  });
}

export async function cancelarTraslado(pacienteId: string): Promise<MessageResponse> {
  // RUTA CORRECTA: /api/traslados/cancelar/{paciente_id}
  return fetchApi<MessageResponse>(`/traslados/cancelar/${pacienteId}`, {
    method: 'POST'
  });
}

// ============================================
// BÚSQUEDA DE CAMA - Rutas: /api/pacientes/*
// ============================================

export async function buscarCamaPaciente(pacienteId: string): Promise<MessageResponse> {
  // RUTA: /api/pacientes/{paciente_id}/buscar-cama
  return fetchApi<MessageResponse>(`/pacientes/${pacienteId}/buscar-cama`, {
    method: 'POST'
  });
}

export async function cancelarBusquedaCama(pacienteId: string): Promise<MessageResponse> {
  // RUTA: /api/pacientes/{paciente_id}/cancelar-busqueda
  return fetchApi<MessageResponse>(`/pacientes/${pacienteId}/cancelar-busqueda`, {
    method: 'POST'
  });
}

// ============================================
// ALTA - Rutas: /api/pacientes/*
// ============================================

export async function iniciarAlta(pacienteId: string): Promise<MessageResponse> {
  // RUTA: /api/pacientes/{paciente_id}/iniciar-alta
  return fetchApi<MessageResponse>(`/pacientes/${pacienteId}/iniciar-alta`, {
    method: 'POST'
  });
}

export async function ejecutarAlta(pacienteId: string): Promise<MessageResponse> {
  // RUTA: /api/pacientes/{paciente_id}/ejecutar-alta
  return fetchApi<MessageResponse>(`/pacientes/${pacienteId}/ejecutar-alta`, {
    method: 'POST'
  });
}

export async function cancelarAlta(pacienteId: string): Promise<MessageResponse> {
  // RUTA: /api/pacientes/{paciente_id}/cancelar-alta
  return fetchApi<MessageResponse>(`/pacientes/${pacienteId}/cancelar-alta`, {
    method: 'POST'
  });
}

// ============================================
// DERIVACIONES - Rutas: /api/derivaciones/*
// ============================================

export async function accionDerivacion(pacienteId: string, accion: DerivacionAccion): Promise<MessageResponse> {
  // RUTA CORRECTA: /api/derivaciones/{paciente_id}/accion
  return fetchApi<MessageResponse>(`/derivaciones/${pacienteId}/accion`, {
    method: 'POST',
    body: JSON.stringify({
      accion: accion.accion,
      motivo_rechazo: accion.motivo_rechazo
    })
  });
}

export async function confirmarEgresoDerivacion(pacienteId: string): Promise<MessageResponse> {
  // RUTA CORRECTA: /api/derivaciones/{paciente_id}/confirmar-egreso
  return fetchApi<MessageResponse>(`/derivaciones/${pacienteId}/confirmar-egreso`, {
    method: 'POST'
  });
}

// ============================================
// LISTA DE ESPERA
// ============================================

export async function getListaEspera(hospitalId: string): Promise<ListaEsperaItem[]> {
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
    }>;
  }
  
  const response = await fetchApi<ListaEsperaResponse>(`/hospitales/${hospitalId}/lista-espera`);
  
  // Convertir al formato esperado por el frontend
  return response.pacientes.map(p => ({
    paciente_id: p.paciente_id,
    nombre: p.nombre,
    run: p.run,
    prioridad: p.prioridad,
    posicion: p.posicion,
    tiempo_espera_min: p.tiempo_espera_min,
    tiempo_espera_minutos: p.tiempo_espera_min,
    estado_lista: p.estado_lista,
    estado: p.estado_lista as any,
    paciente: {
      id: p.paciente_id,
      nombre: p.nombre,
      run: p.run,
      sexo: p.sexo as any,
      edad: p.edad,
      tipo_paciente: p.tipo_paciente as any,
      complejidad: p.complejidad as any,
      tipo_enfermedad: p.tipo_enfermedad as any,
      tipo_aislamiento: p.tipo_aislamiento as any
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
