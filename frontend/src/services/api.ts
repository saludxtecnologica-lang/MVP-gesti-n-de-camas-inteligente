import type {
  Hospital,
  Servicio,
  Cama,
  Paciente,
  PacienteCreate,
  PacienteUpdate,
  ConfiguracionSistema,
  DerivacionAccion,
  TrasladoManual,
  IntercambioRequest,
  CamaBloquearRequest,
  PrioridadExplicacion,
  EstadisticasGlobales,
  ListaEsperaItem,
  DerivadoItem
} from '../types/Index';

const API_BASE = '/api';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Error desconocido' }));
    throw new ApiError(response.status, error.detail || 'Error en la solicitud');
  }
  return response.json();
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers
    },
    ...options
  });
  return handleResponse<T>(response);
}

// ==================== HOSPITALES ====================
export async function getHospitales(): Promise<Hospital[]> {
  return fetchApi<Hospital[]>('/hospitales');
}

export async function getHospital(id: number): Promise<Hospital> {
  return fetchApi<Hospital>(`/hospitales/${id}`);
}

export async function getServiciosHospital(hospitalId: number): Promise<Servicio[]> {
  return fetchApi<Servicio[]>(`/hospitales/${hospitalId}/servicios`);
}

export async function getCamasHospital(hospitalId: number): Promise<Cama[]> {
  return fetchApi<Cama[]>(`/hospitales/${hospitalId}/camas`);
}

// ==================== CAMAS ====================
export async function bloquearCama(
  camaId: number,
  data: CamaBloquearRequest
): Promise<Cama> {
  return fetchApi<Cama>(`/camas/${camaId}/bloquear`, {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

// ==================== PACIENTES ====================
export async function crearPaciente(data: PacienteCreate): Promise<Paciente> {
  return fetchApi<Paciente>('/pacientes', {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

export async function getPaciente(id: number): Promise<Paciente> {
  return fetchApi<Paciente>(`/pacientes/${id}`);
}

export async function actualizarPaciente(
  id: number,
  data: PacienteUpdate
): Promise<Paciente> {
  return fetchApi<Paciente>(`/pacientes/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  });
}

export async function getPrioridadPaciente(id: number): Promise<PrioridadExplicacion> {
  return fetchApi<PrioridadExplicacion>(`/pacientes/${id}/prioridad`);
}

// ==================== LISTA DE ESPERA ====================
export async function getListaEspera(hospitalId: number): Promise<ListaEsperaItem[]> {
  return fetchApi<ListaEsperaItem[]>(`/hospitales/${hospitalId}/lista-espera`);
}

export async function buscarCamaPaciente(pacienteId: number): Promise<{ mensaje: string }> {
  return fetchApi<{ mensaje: string }>(`/pacientes/${pacienteId}/buscar-cama`, {
    method: 'POST'
  });
}

export async function cancelarBusquedaCama(pacienteId: number): Promise<{ mensaje: string }> {
  return fetchApi<{ mensaje: string }>(`/pacientes/${pacienteId}/cancelar-busqueda`, {
    method: 'POST'
  });
}

// ==================== TRASLADOS ====================
export async function completarTraslado(pacienteId: number): Promise<{ mensaje: string }> {
  return fetchApi<{ mensaje: string }>(`/traslados/completar/${pacienteId}`, {
    method: 'POST'
  });
}

export async function cancelarTraslado(pacienteId: number): Promise<{ mensaje: string }> {
  return fetchApi<{ mensaje: string }>(`/traslados/cancelar/${pacienteId}`, {
    method: 'POST'
  });
}

// ==================== DERIVACIONES ====================
export async function getDerivados(hospitalId: number): Promise<DerivadoItem[]> {
  return fetchApi<DerivadoItem[]>(`/hospitales/${hospitalId}/derivados`);
}

export async function accionDerivacion(
  pacienteId: number,
  data: DerivacionAccion
): Promise<{ mensaje: string }> {
  return fetchApi<{ mensaje: string }>(`/derivaciones/${pacienteId}/accion`, {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

export async function confirmarEgresoDerivacion(
  pacienteId: number
): Promise<{ mensaje: string }> {
  return fetchApi<{ mensaje: string }>(`/derivaciones/${pacienteId}/confirmar-egreso`, {
    method: 'POST'
  });
}

// ==================== ALTAS ====================
export async function iniciarAlta(pacienteId: number): Promise<{ mensaje: string }> {
  return fetchApi<{ mensaje: string }>(`/pacientes/${pacienteId}/iniciar-alta`, {
    method: 'POST'
  });
}

export async function ejecutarAlta(pacienteId: number): Promise<{ mensaje: string }> {
  return fetchApi<{ mensaje: string }>(`/pacientes/${pacienteId}/ejecutar-alta`, {
    method: 'POST'
  });
}

export async function cancelarAlta(pacienteId: number): Promise<{ mensaje: string }> {
  return fetchApi<{ mensaje: string }>(`/pacientes/${pacienteId}/cancelar-alta`, {
    method: 'POST'
  });
}

// ==================== CONFIGURACIÓN ====================
export async function getConfiguracion(): Promise<ConfiguracionSistema> {
  return fetchApi<ConfiguracionSistema>('/configuracion');
}

export async function actualizarConfiguracion(
  data: Partial<ConfiguracionSistema>
): Promise<ConfiguracionSistema> {
  return fetchApi<ConfiguracionSistema>('/configuracion', {
    method: 'PUT',
    body: JSON.stringify(data)
  });
}

// ==================== MODO MANUAL ====================
export async function trasladoManual(data: TrasladoManual): Promise<{ mensaje: string }> {
  return fetchApi<{ mensaje: string }>('/manual/trasladar', {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

export async function intercambiarPacientes(
  data: IntercambioRequest
): Promise<{ mensaje: string }> {
  return fetchApi<{ mensaje: string }>('/manual/intercambiar', {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

// ==================== ESTADÍSTICAS ====================
export async function getEstadisticas(): Promise<EstadisticasGlobales> {
  return fetchApi<EstadisticasGlobales>('/estadisticas');
}

// ==================== DOCUMENTOS ====================
export async function subirDocumento(
  pacienteId: number,
  file: File
): Promise<{ mensaje: string; filename: string }> {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_BASE}/pacientes/${pacienteId}/documento`, {
    method: 'POST',
    body: formData
  });
  
  return handleResponse<{ mensaje: string; filename: string }>(response);
}

export function getDocumentoUrl(filename: string): string {
  return `${API_BASE}/documentos/${filename}`;
}

export async function eliminarDocumento(pacienteId: number): Promise<{ mensaje: string }> {
  return fetchApi<{ mensaje: string }>(`/pacientes/${pacienteId}/documento`, {
    method: 'DELETE'
  });
}

// ==================== HEALTH ====================
export async function healthCheck(): Promise<{ status: string; database: string }> {
  return fetchApi<{ status: string; database: string }>('/health');
}

export { ApiError };