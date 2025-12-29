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
  EstadoCamaEnum
} from '../types';

// ============================================
// CONFIGURACIÓN BASE
// ============================================

export function getApiBase(): string {
  if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  return 'http://localhost:8000';
}

const API_BASE = getApiBase();

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
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
        }
      } else if (errorData.message) {
        errorMessage = errorData.message;
      }
    } catch {
      // Si no se puede parsear JSON, usar mensaje por defecto
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
// TRASLADOS
// ============================================

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

// ============================================
// Cancelar traslado confirmado
// ============================================

export async function cancelarTrasladoConfirmado(pacienteId: string): Promise<MessageResponse> {
  return fetchApi<MessageResponse>(`/traslados/${pacienteId}/cancelar-confirmado`, {
    method: 'POST'
  });
}

// ============================================
// BÚSQUEDA DE CAMA
// ============================================

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

// ============================================
// ALTA
// ============================================

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

// ============================================
// PAUSA DE OXÍGENO
// ============================================

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

// ============================================
// DERIVACIONES
// ============================================

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

// ============================================
// MODO MANUAL
// ============================================

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

// ============================================
// TIPOS EXTENDIDOS PARA LISTA DE ESPERA
// ============================================

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
  // Campos adicionales
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
    // Campos adicionales mapeados
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

// ============================================
// TIPOS EXTENDIDOS PARA DERIVADOS
// ============================================

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
  // Campos adicionales
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
    // Campos adicionales
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

// ============================================
// SOLICITAR DERIVACIÓN 
// ============================================

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

// ============================================
// DERIVADOS ENVIADOS (A OTROS HOSPITALES)
// ============================================

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

// ============================================
// VERIFICACIÓN DE VIABILIDAD DE DERIVACIÓN
// ============================================

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

// ============================================
// VERIFICACIÓN DE DISPONIBILIDAD TIPO CAMA
// ============================================

export interface VerificacionDisponibilidadTipoCama {
  tiene_tipo_cama: boolean;
  mensaje: string;
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

// ============================================
// BÚSQUEDA DE CAMAS EN LA RED
// ============================================

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

export async function buscarCamasEnRed(
  pacienteId: string
): Promise<ResultadoBusquedaRed> {
  return fetchApi<ResultadoBusquedaRed>(
    `/pacientes/${pacienteId}/buscar-camas-red`
  );
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

export function getDocumentoUrl(filename: string, forceInline: boolean = true): string {
  const cleanFilename = filename.includes('/') 
    ? filename.split('/').pop() 
    : filename;
  
  const url = `${API_BASE}/api/documentos/${encodeURIComponent(cleanFilename || filename)}`;
  
  // Añadir parámetro para indicar visualización inline (si el backend lo soporta)
  return forceInline ? `${url}?inline=true` : url;
}

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