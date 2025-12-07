// Enums
export enum TipoPacienteEnum {
  HOSPITALIZADO = "hospitalizado",
  URGENCIA = "urgencia",
  DERIVADO = "derivado",
  AMBULATORIO = "ambulatorio"
}

export enum SexoEnum {
  HOMBRE = "hombre",
  MUJER = "mujer"
}

export enum EdadCategoriaEnum {
  PEDIATRICO = "pediatrico",
  ADULTO = "adulto",
  ADULTO_MAYOR = "adulto_mayor"
}

export enum TipoEnfermedadEnum {
  MEDICA = "medica",
  QUIRURGICA = "quirurgica",
  TRAUMATOLOGICA = "traumatologica",
  NEUROLOGICA = "neurologica",
  UROLOGICA = "urologica",
  GERIATRICA = "geriatrica",
  GINECOLOGICA = "ginecologica",
  OBSTETRICA = "obstetrica"
}

export enum TipoAislamientoEnum {
  NINGUNO = "ninguno",
  CONTACTO = "contacto",
  GOTITAS = "gotitas",
  AEREO = "aereo",
  AMBIENTE_PROTEGIDO = "ambiente_protegido",
  ESPECIAL = "especial"
}

export enum ComplejidadEnum {
  UCI = "uci",
  UTI = "uti",
  BAJA = "baja",
  NINGUNA = "ninguna"
}

export enum TipoServicioEnum {
  UCI = "uci",
  UTI = "uti",
  MEDICINA = "medicina",
  CIRUGIA = "cirugia",
  OBSTETRICIA = "obstetricia",
  PEDIATRIA = "pediatria",
  AISLAMIENTO = "aislamiento",
  MEDICO_QUIRURGICO = "medico_quirurgico"
}

export enum EstadoCamaEnum {
  LIBRE = "libre",
  OCUPADA = "ocupada",
  TRASLADO_ENTRANTE = "traslado_entrante",
  CAMA_EN_ESPERA = "cama_en_espera",
  TRASLADO_SALIENTE = "traslado_saliente",
  TRASLADO_CONFIRMADO = "traslado_confirmado",
  ALTA_SUGERIDA = "alta_sugerida",
  CAMA_ALTA = "cama_alta",
  EN_LIMPIEZA = "en_limpieza",
  BLOQUEADA = "bloqueada",
  ESPERA_DERIVACION = "espera_derivacion",
  DERIVACION_CONFIRMADA = "derivacion_confirmada"
}

export enum EstadoListaEsperaEnum {
  ESPERANDO = "esperando",
  BUSCANDO = "buscando",
  ASIGNADO = "asignado",
  CANCELADO = "cancelado"
}

// Interfaces - IDs son strings (UUIDs del backend)
export interface Hospital {
  id: string;
  nombre: string;
  codigo: string;
  es_centro_referencia?: boolean;
  es_central?: boolean;
  total_camas?: number;
  camas_libres?: number;
  camas_ocupadas?: number;
  pacientes_en_espera?: number;
  pacientes_derivados?: number;
}

export interface Servicio {
  id: string;
  hospital_id: string;
  nombre: string;
  codigo?: string;
  tipo: TipoServicioEnum;
  es_uci?: boolean;
  es_uti?: boolean;
  permite_pediatria?: boolean;
  prioridad?: number;
}

export interface Sala {
  id: string;
  servicio_id: string;
  nombre?: string;
  numero?: number;
  es_individual: boolean;
  sexo_asignado: SexoEnum | null;
  servicio?: Servicio;
}

export interface Cama {
  id: string;
  sala_id: string;
  numero?: number;
  letra?: string;
  identificador: string;
  estado: EstadoCamaEnum;
  paciente_id?: string | null;
  paciente_entrante_id?: string | null;
  bloqueada_motivo?: string | null;
  mensaje_estado?: string | null;
  limpieza_inicio?: string | null;
  cama_asignada_destino?: string | null;
  
  // Campos que el backend envía directamente (CamaResponse en schemas.py)
  servicio_nombre?: string;
  servicio_tipo?: TipoServicioEnum;
  sala_es_individual?: boolean;
  sala_sexo_asignado?: SexoEnum | null;
  
  // Relaciones expandidas
  sala?: Sala;
  paciente?: Paciente;
  paciente_entrante?: Paciente;
}

export interface Paciente {
  id: string;
  nombre: string;
  run: string;
  sexo: SexoEnum;
  edad: number;
  edad_categoria?: EdadCategoriaEnum;
  diagnostico: string;
  tipo_enfermedad: TipoEnfermedadEnum;
  tipo_aislamiento: TipoAislamientoEnum;
  complejidad?: ComplejidadEnum;
  complejidad_requerida?: ComplejidadEnum;
  tipo_paciente: TipoPacienteEnum;
  embarazada?: boolean;
  es_embarazada?: boolean; // Alias del backend
  hospital_id: string;
  cama_actual_id?: string | null;
  cama_id?: string | null; // Alias del backend
  cama_destino_id?: string | null;
  en_lista_espera?: boolean;
  estado_lista_espera?: EstadoListaEsperaEnum | string | null;
  prioridad_calculada?: number;
  tiempo_espera_min?: number;
  requiere_nueva_cama?: boolean;
  
  // Requerimientos clínicos (formato frontend - booleanos) - TODOS OPCIONALES
  req_kinesioterapia?: boolean;
  req_control_sangre_1x?: boolean;
  req_curaciones?: boolean;
  req_tratamiento_ev_2x?: boolean;
  req_tratamiento_ev_3x?: boolean;
  req_control_sangre_2x?: boolean;
  req_o2_naricera?: boolean;
  req_dolor_eva_7?: boolean;
  req_o2_multiventuri?: boolean;
  req_curaciones_complejas?: boolean;
  req_aspiracion?: boolean;
  req_observacion?: boolean;
  req_observacion_motivo?: string | null;
  req_irrigacion_vesical?: boolean;
  req_procedimiento_invasivo?: boolean;
  req_procedimiento_invasivo_detalle?: string | null;
  req_drogas_vasoactivas?: boolean;
  req_sedacion?: boolean;
  req_monitorizacion?: boolean;
  req_monitorizacion_motivo?: string | null;
  req_o2_reservorio?: boolean;
  req_dialisis?: boolean;
  req_cnaf?: boolean;
  req_bic_insulina?: boolean;
  req_vmni?: boolean;
  req_vmi?: boolean;
  req_procuramiento_o2?: boolean;
  
  // Requerimientos como listas (formato del backend)
  requerimientos_no_definen?: string[];
  requerimientos_baja?: string[];
  requerimientos_uti?: string[];
  requerimientos_uci?: string[];
  
  // Campos adicionales del backend
  motivo_observacion?: string | null;
  justificacion_observacion?: string | null;
  procedimiento_invasivo?: string | null;
  
  // Casos especiales - OPCIONALES
  caso_socio_sanitario?: boolean;
  caso_socio_judicial?: boolean;
  caso_espera_cardiocirugia?: boolean;
  casos_especiales?: string[];
  
  // Notas y documentos
  notas_adicionales?: string | null;
  documento_adjunto?: string | null;
  
  // Derivación - OPCIONALES
  derivacion_solicitada?: boolean;
  derivacion_hospital_destino_id?: string | null;
  derivacion_motivo?: string | null;
  derivacion_estado?: string | null;
  derivacion_rechazo_motivo?: string | null;
  derivacion_motivo_rechazo?: string | null; // Alias
  
  // Alta - OPCIONALES
  alta_solicitada?: boolean;
  alta_motivo?: string | null;
  
  // Lista espera
  timestamp_lista_espera?: string | null;
  lista_espera_inicio?: string | null;
  cama_asignada_id?: string | null;
  
  // Timestamps
  created_at?: string;
  updated_at?: string;
  
  // Relaciones
  hospital?: Hospital;
  cama_actual?: Cama;
  cama_asignada?: Cama;
}

export interface ConfiguracionSistema {
  id?: string;
  modo_manual: boolean;
  tiempo_limpieza_segundos: number;
}

// Request/Response types - Coincide con PacienteCreate del backend (schemas.py)
export interface PacienteCreate {
  nombre: string;
  run: string;
  sexo: SexoEnum;
  edad: number;
  es_embarazada?: boolean;
  diagnostico: string;
  tipo_enfermedad: TipoEnfermedadEnum;
  tipo_aislamiento?: TipoAislamientoEnum;
  notas_adicionales?: string;
  
  // Requerimientos clínicos como listas de strings (formato del backend)
  requerimientos_no_definen?: string[];
  requerimientos_baja?: string[];
  requerimientos_uti?: string[];
  requerimientos_uci?: string[];
  casos_especiales?: string[];
  
  // Campos especiales
  motivo_observacion?: string;
  justificacion_observacion?: string;
  procedimiento_invasivo?: string;
  
  // Tipo de paciente (requerido por el backend)
  tipo_paciente: TipoPacienteEnum;
  hospital_id: string;
  
  // Derivación
  derivacion_hospital_destino_id?: string;
  derivacion_motivo?: string;
  
  // Alta
  alta_solicitada?: boolean;
  alta_motivo?: string;
}

// Interfaz auxiliar para el formulario (con checkboxes individuales)
export interface PacienteFormData {
  nombre: string;
  run: string;
  sexo: SexoEnum;
  edad: number;
  es_embarazada: boolean;
  diagnostico: string;
  tipo_enfermedad: TipoEnfermedadEnum;
  tipo_aislamiento: TipoAislamientoEnum;
  notas_adicionales: string;
  tipo_paciente: TipoPacienteEnum;
  hospital_id: string;
  
  // Requerimientos que no definen complejidad
  req_kinesioterapia: boolean;
  req_control_sangre_1x: boolean;
  req_curaciones: boolean;
  req_tratamiento_ev_2x: boolean;
  
  // Requerimientos baja complejidad
  req_tratamiento_ev_3x: boolean;
  req_control_sangre_2x: boolean;
  req_o2_naricera: boolean;
  req_dolor_eva_7: boolean;
  req_o2_multiventuri: boolean;
  req_curaciones_complejas: boolean;
  req_aspiracion: boolean;
  req_observacion: boolean;
  req_observacion_motivo: string;
  req_irrigacion_vesical: boolean;
  req_procedimiento_invasivo: boolean;
  req_procedimiento_invasivo_detalle: string;
  
  // Requerimientos UTI
  req_drogas_vasoactivas: boolean;
  req_sedacion: boolean;
  req_monitorizacion: boolean;
  req_monitorizacion_motivo: string;
  req_o2_reservorio: boolean;
  req_dialisis: boolean;
  req_cnaf: boolean;
  req_bic_insulina: boolean;
  req_vmni: boolean;
  
  // Requerimientos UCI
  req_vmi: boolean;
  req_procuramiento_o2: boolean;
  
  // Casos especiales
  caso_socio_sanitario: boolean;
  caso_socio_judicial: boolean;
  caso_espera_cardiocirugia: boolean;
  
  // Derivación
  derivacion_solicitada: boolean;
  derivacion_hospital_destino_id: string;
  derivacion_motivo: string;
  
  // Alta
  alta_solicitada: boolean;
  alta_motivo: string;
}

// PacienteUpdate para reevaluación - coincide con backend
export interface PacienteUpdate {
  diagnostico?: string;
  tipo_enfermedad?: TipoEnfermedadEnum;
  tipo_aislamiento?: TipoAislamientoEnum;
  notas_adicionales?: string;
  es_embarazada?: boolean;
  
  requerimientos_no_definen?: string[];
  requerimientos_baja?: string[];
  requerimientos_uti?: string[];
  requerimientos_uci?: string[];
  casos_especiales?: string[];
  
  motivo_observacion?: string;
  justificacion_observacion?: string;
  procedimiento_invasivo?: string;
  
  derivacion_hospital_destino_id?: string;
  derivacion_motivo?: string;
  
  alta_solicitada?: boolean;
  alta_motivo?: string;
}

export interface DerivacionAccion {
  accion: 'aceptar' | 'rechazar';
  motivo_rechazo?: string;
}

export interface TrasladoManual {
  paciente_id: string;
  cama_destino_id: string;
}

export interface IntercambioRequest {
  paciente1_id: string;
  paciente2_id: string;
}

export interface CamaBloquearRequest {
  bloquear: boolean;
  motivo?: string;
}

export interface PrioridadExplicacion {
  puntuacion_total: number;
  desglose: {
    tipo_paciente: { valor: string; puntos: number };
    complejidad: { valor: string; puntos: number };
    tiempo_espera: { minutos: number; puntos: number };
    boosts: Array<{ nombre: string; puntos: number }>;
  };
}

export interface EstadisticasHospital {
  hospital_id: string;
  hospital_nombre: string;
  total_camas: number;
  camas_libres: number;
  camas_ocupadas: number;
  camas_traslado: number;
  camas_limpieza: number;
  camas_bloqueadas: number;
  pacientes_espera?: number;
  pacientes_en_espera?: number;
  derivados_pendientes?: number;
  pacientes_derivados_pendientes?: number;
  porcentaje_ocupacion?: number;
  ocupacion_porcentaje?: number;
}

// Corregido para coincidir con el backend (EstadisticasGlobalesResponse)
export interface EstadisticasGlobales {
  hospitales: EstadisticasHospital[];
  total_camas_sistema: number;
  total_pacientes_sistema: number;
  ocupacion_promedio: number;
}

// WebSocket events
export interface WebSocketEvent {
  tipo: string;
  datos?: Record<string, unknown>;
  timestamp?: string;
  [key: string]: unknown;
}

// Lista espera item - campos adicionales del backend
export interface ListaEsperaItem {
  paciente: Paciente;
  prioridad: number;
  tiempo_espera_minutos: number;
  estado: EstadoListaEsperaEnum;
  // Campos adicionales que puede enviar el backend
  paciente_id?: string;
  nombre?: string;
  run?: string;
  posicion?: number;
  tiempo_espera_min?: number;
  estado_lista?: string;
}

// Derivado item - campos adicionales del backend
export interface DerivadoItem {
  paciente: Paciente;
  hospital_origen: Hospital;
  motivo: string;
  prioridad: number;
  tiempo_en_lista_minutos: number;
  // Campos adicionales que puede enviar el backend
  paciente_id?: string;
  nombre?: string;
  run?: string;
  hospital_origen_id?: string;
  hospital_origen_nombre?: string;
  motivo_derivacion?: string;
  tiempo_en_lista_min?: number;
  diagnostico?: string;
  complejidad?: string;
  tipo_paciente?: string;
}
