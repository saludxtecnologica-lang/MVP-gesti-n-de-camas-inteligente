/**
 * API Client con Autenticación
 * 
 * ESTRUCTURA CORRECTA:
 * 1. Imports
 * 2. Configuración y helpers de auth
 * 3. fetchApi (UNA SOLA VEZ)
 * 4. Objeto api
 * 5. Funciones individuales
 * 6. Objetos xxxApi que usan el objeto api
 */

import { tokenStorage } from './authApi';
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
  PrioridadExplicacion,
  MessageResponse,
  SexoEnum,
  TipoPacienteEnum,
  ComplejidadEnum,
  TipoEnfermedadEnum,
  TipoAislamientoEnum,
  EstadoListaEsperaEnum,
  EstadoCamaEnum,
  InfoTraslado,
  HospitalConTelefonos
} from '../types';

// ============================================
// 1. CONFIGURACIÓN BASE
// ============================================

export function getApiBase(): string {
  if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  return 'http://localhost:8000';
}

const API_BASE = getApiBase();

export function getWebSocketUrl(): string {
  try {
    const apiUrl = new URL(API_BASE);
    const wsProtocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProtocol}//${apiUrl.host}/api/ws`;
  } catch {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProtocol}//localhost:8000/api/ws`;
  }
}

// ============================================
// 2. HELPERS DE AUTENTICACIÓN
// ============================================

const dispatchLogout = () => {
  window.dispatchEvent(new CustomEvent('auth:logout'));
};

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: boolean) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (success: boolean) => {
  failedQueue.forEach(prom => {
    if (success) {
      prom.resolve(true);
    } else {
      prom.reject(new Error('Token refresh failed'));
    }
  });
  failedQueue = [];
};

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = tokenStorage.getRefreshToken();
  
  if (!refreshToken) {
    return false;
  }

  if (isRefreshing) {
    return new Promise((resolve, reject) => {
      failedQueue.push({ resolve, reject });
    });
  }

  isRefreshing = true;

  try {
    const response = await fetch(`${getApiBase()}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      processQueue(false);
      return false;
    }

    const tokens = await response.json();
    tokenStorage.setTokens(tokens);
    processQueue(true);
    return true;
  } catch {
    processQueue(false);
    return false;
  } finally {
    isRefreshing = false;
  }
}

// ============================================
// 3. FETCH API (ÚNICA DEFINICIÓN)
// ============================================

interface FetchApiOptions {
  skipAuth?: boolean;
  retryOnUnauthorized?: boolean;
}

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {},
  authOptions: FetchApiOptions = {}
): Promise<T> {
  const { skipAuth = false, retryOnUnauthorized = true } = authOptions;
  
  // Construir URL - manejar diferentes formatos de endpoint
  let url: string;
  if (endpoint.startsWith('http')) {
    url = endpoint;
  } else if (endpoint.startsWith('/api')) {
    url = `${API_BASE}${endpoint}`;
  } else {
    url = `${API_BASE}/api${endpoint}`;
  }

  // Construir headers
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  // Añadir token de autorización si existe y no se salta
  if (!skipAuth) {
    const token = tokenStorage.getAccessToken();
    if (token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }
  }

  // Hacer la petición
  let response = await fetch(url, {
    ...options,
    headers,
  });

  // Manejar 401 Unauthorized
  if (response.status === 401 && retryOnUnauthorized && !skipAuth) {
    const refreshed = await refreshAccessToken();
    
    if (refreshed) {
      const newToken = tokenStorage.getAccessToken();
      if (newToken) {
        (headers as Record<string, string>)['Authorization'] = `Bearer ${newToken}`;
      }
      
      response = await fetch(url, {
        ...options,
        headers,
      });
    } else {
      tokenStorage.clearAll();
      dispatchLogout();
      throw new Error('Sesión expirada. Por favor, inicia sesión nuevamente.');
    }
  }

  // Manejar errores
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
        }
      } else if (errorData.message) {
        errorMessage = errorData.message;
      }
    } catch {
      // Si no se puede parsear JSON, usar mensaje por defecto
    }
    
    throw new Error(errorMessage);
  }

  // Parsear respuesta
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }
  
  return response.text() as unknown as T;
}

// ============================================
// 4. OBJETO API (DEFINIDO ANTES DE USARSE)
// ============================================

export const api = {
  get: <T>(endpoint: string, options?: FetchApiOptions) =>
    fetchApi<T>(endpoint, { method: 'GET' }, options),

  post: <T>(endpoint: string, data?: unknown, options?: FetchApiOptions) =>
    fetchApi<T>(
      endpoint,
      {
        method: 'POST',
        body: data ? JSON.stringify(data) : undefined,
      },
      options
    ),

  put: <T>(endpoint: string, data?: unknown, options?: FetchApiOptions) =>
    fetchApi<T>(
      endpoint,
      {
        method: 'PUT',
        body: data ? JSON.stringify(data) : undefined,
      },
      options
    ),

  patch: <T>(endpoint: string, data?: unknown, options?: FetchApiOptions) =>
    fetchApi<T>(
      endpoint,
      {
        method: 'PATCH',
        body: data ? JSON.stringify(data) : undefined,
      },
      options
    ),

  delete: <T>(endpoint: string, options?: FetchApiOptions) =>
    fetchApi<T>(endpoint, { method: 'DELETE' }, options),
};

// ============================================
// 5. FUNCIONES INDIVIDUALES
// ============================================

// ----- HOSPITALES -----
export async function getHospitales(): Promise<Hospital[]> {
  return fetchApi<Hospital[]>('/hospitales');
}

export async function getHospital(id: string): Promise<Hospital> {
  return fetchApi<Hospital>(`/hospitales/${id}`);
}

// ----- CAMAS -----
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

// ----- PACIENTES -----
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

// ----- TRASLADOS -----
export async function completarTraslado(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/traslados/${pacienteId}/completar`, {
    method: 'POST'
  });
}

export async function cancelarTraslado(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/traslados/${pacienteId}/cancelar`, {
    method: 'POST'
  });
}

export async function cancelarTrasladoDesdeOrigen(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/traslados/${pacienteId}/cancelar-desde-origen`, {
    method: 'POST'
  });
}

export async function cancelarTrasladoDesdeDestino(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/traslados/${pacienteId}/cancelar-desde-destino`, {
    method: 'POST'
  });
}

export async function cancelarTrasladoConfirmado(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/traslados/${pacienteId}/cancelar-confirmado`, {
    method: 'POST'
  });
}

// ----- BÚSQUEDA DE CAMA -----
export async function buscarCamaPaciente(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/pacientes/${pacienteId}/buscar-cama`, {
    method: 'POST'
  });
}

export async function cancelarBusquedaCama(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/pacientes/${pacienteId}/cancelar-busqueda`, {
    method: 'DELETE'
  });
}

// ----- ALTAS -----
export async function iniciarAlta(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/altas/${pacienteId}/iniciar`, {
    method: 'POST'
  });
}

export async function ejecutarAlta(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/altas/${pacienteId}/ejecutar`, {
    method: 'POST'
  });
}

export async function cancelarAlta(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/altas/${pacienteId}/cancelar`, {
    method: 'POST'
  });
}

// ----- PAUSA DE OXÍGENO -----
export interface EstadoPausaOxigeno {
  paciente_id: string;
  en_pausa: boolean;
  tiempo_total_segundos: number;
  tiempo_restante_segundos: number;
  tiempo_transcurrido_segundos: number;
  requiere_nueva_cama: boolean;
  puede_buscar_cama: boolean;
  inicio_pausa: string | null;
}

export async function getEstadoPausaOxigeno(pacienteId: string): Promise<EstadoPausaOxigeno> {
  return fetchApi<EstadoPausaOxigeno>(`/pacientes/${pacienteId}/estado-pausa-oxigeno`);
}

export async function omitirPausaOxigeno(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/pacientes/${pacienteId}/omitir-pausa-oxigeno`, {
    method: 'POST'
  });
}

// ----- DERIVACIONES -----
export async function accionDerivacion(pacienteId: string, data: DerivacionAccion): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/derivaciones/${pacienteId}/accion`, {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

export async function confirmarEgresoDerivacion(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/derivaciones/${pacienteId}/confirmar-egreso`, {
    method: 'POST'
  });
}

export async function cancelarDerivacion(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/derivaciones/${pacienteId}/cancelar`, {
    method: 'POST'
  });
}

export interface SolicitarDerivacionRequest {
  hospital_destino_id: string;
  motivo: string;
}

export async function solicitarDerivacion(
  pacienteId: string,
  data: SolicitarDerivacionRequest
): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/derivaciones/${pacienteId}/solicitar`, {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

export interface DerivadoEnviadoItem {
  paciente_id: string;
  nombre: string;
  run: string;
  hospital_destino_id: string;
  hospital_destino_nombre: string;
  motivo_derivacion: string;
  estado_derivacion: string;
  cama_origen_identificador: string | null;
  tiempo_en_proceso_min: number;
  complejidad: string;
  diagnostico: string;
}

export async function getDerivadosEnviados(hospitalId: string): Promise<DerivadoEnviadoItem[]> {
  return fetchApi<DerivadoEnviadoItem[]>(`/derivaciones/hospital/${hospitalId}/enviados`);
}

export async function cancelarDerivacionDesdeOrigen(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/derivaciones/${pacienteId}/cancelar-desde-origen`, {
    method: 'POST'
  });
}

export interface VerificacionViabilidadDerivacion {
  es_viable: boolean;
  mensaje: string;
  motivos_rechazo: string[];
  hospital_destino_nombre: string;
  paciente_id: string;
}

export async function verificarViabilidadDerivacion(
  pacienteId: string,
  hospitalDestinoId: string
): Promise<VerificacionViabilidadDerivacion> {
  return fetchApi<VerificacionViabilidadDerivacion>(
    `/derivaciones/${pacienteId}/verificar-viabilidad/${hospitalDestinoId}`
  );
}

export interface VerificacionDisponibilidadTipoCama {
  tiene_tipo_servicio: boolean;  // Si el hospital tiene el tipo de servicio requerido
  tiene_camas_libres: boolean;   // Si hay camas libres en ese servicio
  mensaje: string;               // Mensaje explicativo
  paciente_id: string;
  hospital_id: string;
}

export async function verificarDisponibilidadTipoCama(
  pacienteId: string
): Promise<VerificacionDisponibilidadTipoCama> {
  return fetchApi<VerificacionDisponibilidadTipoCama>(
    `/pacientes/${pacienteId}/verificar-disponibilidad-hospital`
  );
}

// ----- MODO MANUAL -----
export async function asignarManualDesdeCama(pacienteId: string, camaDestinoId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>('/manual/asignar-desde-cama', {
    method: 'POST',
    body: JSON.stringify({
      paciente_id: pacienteId,
      cama_destino_id: camaDestinoId
    })
  });
}

export async function asignarManualDesdeLista(pacienteId: string, camaDestinoId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>('/manual/asignar-desde-lista', {
    method: 'POST',
    body: JSON.stringify({
      paciente_id: pacienteId,
      cama_destino_id: camaDestinoId
    })
  });
}

export async function trasladoManual(pacienteId: string, camaDestinoId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>('/manual/traslado', {
    method: 'POST',
    body: JSON.stringify({
      paciente_id: pacienteId,
      cama_destino_id: camaDestinoId
    })
  });
}

export async function intercambiarPacientes(pacienteAId: string, pacienteBId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>('/manual/intercambiar', {
    method: 'POST',
    body: JSON.stringify({
      paciente_a_id: pacienteAId,
      paciente_b_id: pacienteBId
    })
  });
}

export async function egresarManual(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/manual/egresar/${pacienteId}`, {
    method: 'POST'
  });
}

export async function egresarDeLista(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/manual/egresar-de-lista/${pacienteId}`, {
    method: 'DELETE'
  });
}

// ----- LISTA DE ESPERA -----
export interface ListaEsperaItemExtended {
  paciente_id: string;
  nombre: string;
  run: string;
  prioridad: number;
  posicion: number;
  tiempo_espera_min: number;
  tiempo_espera_minutos: number;
  estado_lista: string;
  estado: EstadoListaEsperaEnum;
  origen_tipo: 'derivado' | 'hospitalizado' | 'urgencia' | 'ambulatorio' | null;
  origen_hospital_nombre: string | null;
  origen_hospital_codigo: string | null;
  origen_servicio_nombre: string | null;
  origen_cama_identificador: string | null;
  servicio_destino: string | null;
  complejidad: string;
  es_derivado: boolean;
  tiene_cama_actual: boolean;
  cama_actual_id: string | null;
  paciente: Paciente;
}

export async function getListaEspera(hospitalId: string): Promise<ListaEsperaItemExtended[]> {
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
      cama_destino_id?: string | null;
      timestamp: string;
      origen_tipo: string | null;
      origen_hospital_nombre: string | null;
      origen_hospital_codigo: string | null;
      origen_servicio_nombre: string | null;
      origen_cama_identificador: string | null;
      servicio_destino: string | null;
      es_derivado?: boolean;
      derivacion_estado?: string | null;
      diagnostico?: string;
    }>;
  }
  
  const response = await fetchApi<ListaEsperaResponse>(`/hospitales/${hospitalId}/lista-espera`);
  
  return response.pacientes.map(p => ({
    paciente_id: p.paciente_id,
    nombre: p.nombre,
    run: p.run,
    prioridad: p.prioridad,
    posicion: p.posicion,
    tiempo_espera_min: p.tiempo_espera_min,
    tiempo_espera_minutos: p.tiempo_espera_min,
    estado_lista: p.estado_lista,
    estado: p.estado_lista as unknown as EstadoListaEsperaEnum,
    origen_tipo: p.origen_tipo as 'derivado' | 'hospitalizado' | 'urgencia' | 'ambulatorio' | null,
    origen_hospital_nombre: p.origen_hospital_nombre,
    origen_hospital_codigo: p.origen_hospital_codigo,
    origen_servicio_nombre: p.origen_servicio_nombre,
    origen_cama_identificador: p.origen_cama_identificador,
    servicio_destino: p.servicio_destino,
    complejidad: p.complejidad,
    es_derivado: p.es_derivado || p.origen_tipo === 'derivado' || p.derivacion_estado === 'aceptada',
    tiene_cama_actual: p.tiene_cama_actual,
    cama_actual_id: p.cama_actual_id,
    paciente: {
      id: p.paciente_id,
      nombre: p.nombre,
      run: p.run,
      sexo: p.sexo as unknown as SexoEnum,
      edad: p.edad,
      tipo_paciente: p.tipo_paciente as unknown as TipoPacienteEnum,
      complejidad: p.complejidad as unknown as ComplejidadEnum,
      complejidad_requerida: p.complejidad as unknown as ComplejidadEnum,
      tipo_enfermedad: p.tipo_enfermedad as unknown as TipoEnfermedadEnum,
      tipo_aislamiento: p.tipo_aislamiento as unknown as TipoAislamientoEnum,
      cama_id: p.cama_actual_id,
      cama_destino_id: p.cama_destino_id,
      origen_tipo: p.origen_tipo,
      origen_hospital_nombre: p.origen_hospital_nombre,
      origen_servicio_nombre: p.origen_servicio_nombre,
      servicio_destino: p.servicio_destino,
      derivacion_estado: p.derivacion_estado || (p.tipo_paciente === 'derivado' ? 'aceptada' : null),
      diagnostico: p.diagnostico
    } as unknown as Paciente
  }));
}

export async function getPrioridadPaciente(pacienteId: string): Promise<PrioridadExplicacion> {
  return fetchApi<PrioridadExplicacion>(`/pacientes/${pacienteId}/prioridad`);
}

// ----- DERIVADOS -----
export interface DerivadoItemExtended {
  paciente_id: string;
  nombre: string;
  run: string;
  prioridad: number;
  tiempo_en_lista_min: number;
  tiempo_en_lista_minutos: number;
  hospital_origen_id: string;
  hospital_origen_nombre: string;
  motivo_derivacion: string;
  motivo: string;
  diagnostico: string;
  complejidad: string;
  tipo_paciente: string;
  cama_origen_identificador: string | null;
  servicio_origen_nombre: string | null;
  hospital_origen: Hospital;
  paciente: Paciente;
}

export async function getDerivados(hospitalId: string): Promise<DerivadoItemExtended[]> {
  interface DerivadoResponse {
    paciente_id: string;
    nombre: string;
    run: string;
    prioridad: number;
    tiempo_en_lista_min: number;
    hospital_origen_id: string;
    hospital_origen_nombre: string;
    hospital_origen_codigo?: string;
    cama_origen_identificador?: string | null;
    servicio_origen_nombre?: string | null;
    motivo_derivacion: string;
    tipo_paciente: string;
    complejidad: string;
    diagnostico: string;
    edad?: number;
    sexo?: string;
  }
  
  const response = await fetchApi<DerivadoResponse[]>(`/hospitales/${hospitalId}/derivados`);
  
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
    cama_origen_identificador: d.cama_origen_identificador || null,
    servicio_origen_nombre: d.servicio_origen_nombre || null,
    hospital_origen: {
      id: d.hospital_origen_id,
      nombre: d.hospital_origen_nombre,
      codigo: d.hospital_origen_codigo
    } as Hospital,
    paciente: {
      id: d.paciente_id,
      nombre: d.nombre,
      run: d.run,
      diagnostico: d.diagnostico,
      complejidad: d.complejidad as unknown as ComplejidadEnum,
      complejidad_requerida: d.complejidad as unknown as ComplejidadEnum,
      tipo_paciente: d.tipo_paciente as unknown as TipoPacienteEnum,
      edad: d.edad,
      sexo: d.sexo as unknown as SexoEnum
    } as Paciente
  }));
}

// ----- BÚSQUEDA EN RED -----
export interface CamaDisponibleRed {
  cama_id: string;
  cama_identificador: string;
  hospital_id: string;
  hospital_nombre: string;
  hospital_codigo: string;
  servicio_id: string;
  servicio_nombre: string;
  servicio_tipo: string;
  sala_id: string;
  sala_numero: number;
  sala_es_individual: boolean;
}

export interface ResultadoBusquedaRed {
  encontradas: boolean;
  cantidad: number;
  camas: CamaDisponibleRed[];
  mensaje: string;
  paciente_id: string;
  hospital_origen_id: string;
}

export async function buscarCamasEnRed(pacienteId: string): Promise<ResultadoBusquedaRed> {
  return fetchApi<ResultadoBusquedaRed>(`/pacientes/${pacienteId}/buscar-camas-red`);
}

export async function cancelarYVolverACama(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/pacientes/${pacienteId}/cancelar-y-volver`, {
    method: 'POST'
  });
}

export async function eliminarPacienteSinCama(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/pacientes/${pacienteId}/eliminar`, {
    method: 'DELETE'
  });
}

// ----- CONFIGURACIÓN -----
export async function getConfiguracion(): Promise<ConfiguracionSistema> {
  return fetchApi<ConfiguracionSistema>('/configuracion');
}

export async function actualizarConfiguracion(data: Partial<ConfiguracionSistema>): Promise<ConfiguracionSistema> {
  return fetchApi<ConfiguracionSistema>('/configuracion', {
    method: 'PUT',
    body: JSON.stringify(data)
  });
}

// ----- ESTADÍSTICAS -----
export async function getEstadisticas(): Promise<EstadisticasGlobales> {
  return fetchApi<EstadisticasGlobales>('/estadisticas');
}

// ----- FALLECIMIENTO -----
export async function completarEgresoFallecido(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/manual/fallecido/${pacienteId}/completar-egreso`, {
    method: 'POST'
  });
}

export async function cancelarFallecimiento(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/manual/fallecido/${pacienteId}/cancelar`, {
    method: 'POST'
  });
}

// ----- CANCELAR ASIGNACIÓN -----
export async function cancelarAsignacionDesdeLista(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/manual/cancelar-asignacion-lista/${pacienteId}`, {
    method: 'POST'
  });
}

// ----- TELÉFONOS -----
export interface ServicioConTelefono {
  id: string;
  nombre: string;
  codigo: string;
  tipo: string;
  hospital_id: string;
  telefono: string | null;
  total_camas: number;
  camas_libres: number;
}

export interface InfoTrasladoResponse {
  origen_tipo: string | null;
  origen_hospital_nombre: string | null;
  origen_hospital_codigo: string | null;
  origen_servicio_nombre: string | null;
  origen_servicio_telefono: string | null;
  origen_cama_identificador: string | null;
  destino_servicio_nombre: string | null;
  destino_servicio_telefono: string | null;
  destino_cama_identificador: string | null;
  destino_hospital_nombre: string | null;
  tiene_cama_origen: boolean;
  tiene_cama_destino: boolean;
  en_traslado: boolean;
}

export async function getTelefonosHospital(hospitalId: string): Promise<HospitalConTelefonos> {
  return fetchApi<HospitalConTelefonos>(`/hospitales/${hospitalId}/telefonos`);
}

export async function actualizarTelefonosHospital(
  hospitalId: string,
  telefonos: { telefono_urgencias?: string | null; telefono_ambulatorio?: string | null }
): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/hospitales/${hospitalId}/telefonos`, {
    method: 'PUT',
    body: JSON.stringify(telefonos)
  });
}

export async function getServiciosConTelefonos(hospitalId: string): Promise<ServicioConTelefono[]> {
  return fetchApi<ServicioConTelefono[]>(`/hospitales/${hospitalId}/servicios-telefonos`);
}

export async function actualizarTelefonoServicio(
  hospitalId: string,
  servicioId: string,
  telefono: string | null
): Promise<ServicioConTelefono> {
  return fetchApi<ServicioConTelefono>(`/hospitales/${hospitalId}/servicios/${servicioId}/telefono`, {
    method: 'PUT',
    body: JSON.stringify({ telefono })
  });
}

export interface TelefonosBatchData {
  hospital: {
    telefono_urgencias?: string | null;
    telefono_ambulatorio?: string | null;
  };
  servicios: Record<string, string | null>;
}

export interface TelefonosBatchResponse {
  success: boolean;
  message: string;
  actualizados: string[];
  errores: string[] | null;
}

export async function actualizarTelefonosBatch(
  hospitalId: string,
  data: TelefonosBatchData
): Promise<TelefonosBatchResponse> {
  return fetchApi<TelefonosBatchResponse>(`/hospitales/${hospitalId}/telefonos-batch`, {
    method: 'PUT',
    body: JSON.stringify(data)
  });
}

export async function getInfoTrasladoPaciente(pacienteId: string): Promise<InfoTrasladoResponse | null> {
  try {
    return await fetchApi<InfoTrasladoResponse>(`/pacientes/${pacienteId}/info-traslado`);
  } catch {
    return null;
  }
}

// ----- UTILIDADES -----
export function getDocumentoUrl(filename: string, forceInline: boolean = true): string {
  const cleanFilename = filename.includes('/') 
    ? filename.split('/').pop() 
    : filename;
  
  const url = `${API_BASE}/api/documentos/${encodeURIComponent(cleanFilename || filename)}`;
  return forceInline ? `${url}?inline=true` : url;
}

// ============================================
// 6. OBJETOS xxxApi (USAN `api` QUE YA ESTÁ DEFINIDO)
// ============================================

export const hospitalesApi = {
  getAll: () => api.get<Hospital[]>('/api/hospitales'),
  getById: (id: string) => api.get<Hospital>(`/api/hospitales/${id}`),
  getCamas: (hospitalId: string) => api.get<Cama[]>(`/api/hospitales/${hospitalId}/camas`),
  getListaEspera: (hospitalId: string) => api.get<ListaEsperaItem[]>(`/api/hospitales/${hospitalId}/lista-espera`),
  getDerivados: (hospitalId: string) => api.get<DerivadoItem[]>(`/api/hospitales/${hospitalId}/derivados`),
  getTelefonos: () => api.get<HospitalConTelefonos[]>('/api/hospitales/telefonos'),
  updateTelefono: (hospitalId: string, data: { telefono_urgencias?: string; telefono_ambulatorio?: string }) =>
    api.put<MessageResponse>(`/api/hospitales/${hospitalId}/telefonos`, data),
};

export const camasApi = {
  getById: (id: string) => api.get<Cama>(`/api/camas/${id}`),
  bloquear: (camaId: string, data: CamaBloquearRequest) =>
    api.post<MessageResponse>(`/api/camas/${camaId}/bloquear`, data),
  liberarBloqueo: (camaId: string) =>
    api.post<MessageResponse>(`/api/camas/${camaId}/liberar-bloqueo`),
};

export const pacientesApi = {
  create: (data: PacienteCreate) => api.post<Paciente>('/api/pacientes', data),
  getById: (id: string) => api.get<Paciente>(`/api/pacientes/${id}`),
  update: (id: string, data: PacienteUpdate) => api.put<Paciente>(`/api/pacientes/${id}`, data),
  buscar: (query: string) => api.get<Paciente[]>(`/api/pacientes/buscar?q=${encodeURIComponent(query)}`),
  getInfoTraslado: (pacienteId: string) => api.get<InfoTraslado>(`/api/pacientes/${pacienteId}/info-traslado`),
};

export const trasladosApi = {
  confirmar: (pacienteId: string) => api.post<MessageResponse>(`/api/traslados/${pacienteId}/confirmar`),
  cancelar: (pacienteId: string) => api.post<MessageResponse>(`/api/traslados/${pacienteId}/cancelar`),
  completar: (pacienteId: string) => api.post<MessageResponse>(`/api/traslados/${pacienteId}/completar`),
};

export const altasApi = {
  solicitar: (pacienteId: string, motivo: string) =>
    api.post<MessageResponse>(`/api/altas/${pacienteId}/solicitar`, { motivo }),
  confirmar: (pacienteId: string) => api.post<MessageResponse>(`/api/altas/${pacienteId}/confirmar`),
  cancelar: (pacienteId: string) => api.post<MessageResponse>(`/api/altas/${pacienteId}/cancelar`),
};

export const derivacionesApi = {
  solicitar: (pacienteId: string, hospitalDestinoId: string, motivo: string) =>
    api.post<MessageResponse>(`/api/derivaciones/${pacienteId}/solicitar`, {
      hospital_destino_id: hospitalDestinoId,
      motivo,
    }),
  responder: (pacienteId: string, data: DerivacionAccion) =>
    api.post<MessageResponse>(`/api/derivaciones/${pacienteId}/responder`, data),
  cancelar: (pacienteId: string) => api.post<MessageResponse>(`/api/derivaciones/${pacienteId}/cancelar`),
  buscarCamaRed: (pacienteId: string) =>
    api.get<{ hospitales: Hospital[]; camas_disponibles: number }>(`/api/derivaciones/${pacienteId}/buscar-cama-red`),
};

export const modoManualApi = {
  asignar: (pacienteId: string, camaId: string) =>
    api.post<MessageResponse>('/api/modo-manual/asignar', {
      paciente_id: pacienteId,
      cama_id: camaId,
    }),
  intercambiar: (paciente1Id: string, paciente2Id: string) =>
    api.post<MessageResponse>('/api/modo-manual/intercambiar', {
      paciente1_id: paciente1Id,
      paciente2_id: paciente2Id,
    }),
  getCamasDisponibles: (hospitalId: string) =>
    api.get<Cama[]>(`/api/modo-manual/camas-disponibles/${hospitalId}`),
};

export const configuracionApi = {
  get: () => api.get<ConfiguracionSistema>('/api/configuracion'),
  update: (data: Partial<ConfiguracionSistema>) => api.put<ConfiguracionSistema>('/api/configuracion', data),
  toggleModoManual: (activo: boolean) => api.post<MessageResponse>('/api/configuracion/modo-manual', { activo }),
};

export const estadisticasApi = {
  getGlobales: () => api.get<EstadisticasGlobales>('/api/estadisticas'),
  getHospital: (hospitalId: string) => api.get<EstadisticasGlobales>(`/api/estadisticas/hospital/${hospitalId}`),
};

export const fallecimientoApi = {
  registrar: (pacienteId: string, causa: string) =>
    api.post<MessageResponse>(`/api/fallecimiento/${pacienteId}`, { causa }),
  cancelar: (pacienteId: string) => api.post<MessageResponse>(`/api/fallecimiento/${pacienteId}/cancelar`),
};

export const limpiezaApi = {
  marcar: (camaId: string) => api.post<MessageResponse>(`/api/limpieza/${camaId}/marcar`),
  completar: (camaId: string) => api.post<MessageResponse>(`/api/limpieza/${camaId}/completar`),
};

export const serviciosApi = {
  getByHospital: (hospitalId: string) => api.get<unknown[]>(`/api/servicios/hospital/${hospitalId}`),
  updateTelefono: (servicioId: string, telefono: string) =>
    api.put<MessageResponse>(`/api/servicios/${servicioId}/telefono`, { telefono }),
};

// ============================================
// EXPORT DEFAULT
// ============================================

export default {
  hospitales: hospitalesApi,
  camas: camasApi,
  pacientes: pacientesApi,
  traslados: trasladosApi,
  altas: altasApi,
  derivaciones: derivacionesApi,
  modoManual: modoManualApi,
  configuracion: configuracionApi,
  estadisticas: estadisticasApi,
  fallecimiento: fallecimientoApi,
  limpieza: limpiezaApi,
  servicios: serviciosApi,
};