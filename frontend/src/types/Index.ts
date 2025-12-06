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

// Interfaces
export interface Hospital {
  id: number;
  nombre: string;
  codigo: string;
  es_centro_referencia: boolean;
}

export interface Servicio {
  id: number;
  hospital_id: number;
  nombre: string;
  tipo: TipoServicioEnum;
  es_uci: boolean;
  es_uti: boolean;
  permite_pediatria: boolean;
  prioridad: number;
}

export interface Sala {
  id: number;
  servicio_id: number;
  nombre: string;
  es_individual: boolean;
  sexo_asignado: SexoEnum | null;
}

export interface Cama {
  id: number;
  sala_id: number;
  identificador: string;
  estado: EstadoCamaEnum;
  paciente_id: number | null;
  paciente_entrante_id: number | null;
  bloqueada_motivo: string | null;
  limpieza_inicio: string | null;
  // Relaciones expandidas
  sala?: Sala & { servicio?: Servicio };
  paciente?: Paciente;
  paciente_entrante?: Paciente;
}

export interface Paciente {
  id: number;
  nombre: string;
  run: string;
  sexo: SexoEnum;
  edad: number;
  edad_categoria: EdadCategoriaEnum;
  diagnostico: string;
  tipo_enfermedad: TipoEnfermedadEnum;
  tipo_aislamiento: TipoAislamientoEnum;
  complejidad: ComplejidadEnum;
  tipo_paciente: TipoPacienteEnum;
  embarazada: boolean;
  hospital_id: number;
  cama_actual_id: number | null;
  
  // Requerimientos clínicos
  req_kinesioterapia: boolean;
  req_control_sangre_1x: boolean;
  req_curaciones: boolean;
  req_tratamiento_ev_2x: boolean;
  req_tratamiento_ev_3x: boolean;
  req_control_sangre_2x: boolean;
  req_o2_naricera: boolean;
  req_dolor_eva_7: boolean;
  req_o2_multiventuri: boolean;
  req_curaciones_complejas: boolean;
  req_aspiracion: boolean;
  req_observacion: boolean;
  req_observacion_motivo: string | null;
  req_irrigacion_vesical: boolean;
  req_procedimiento_invasivo: boolean;
  req_procedimiento_invasivo_detalle: string | null;
  req_drogas_vasoactivas: boolean;
  req_sedacion: boolean;
  req_monitorizacion: boolean;
  req_monitorizacion_motivo: string | null;
  req_o2_reservorio: boolean;
  req_dialisis: boolean;
  req_cnaf: boolean;
  req_bic_insulina: boolean;
  req_vmni: boolean;
  req_vmi: boolean;
  req_procuramiento_o2: boolean;
  
  // Casos especiales
  caso_socio_sanitario: boolean;
  caso_socio_judicial: boolean;
  caso_espera_cardiocirugia: boolean;
  
  // Notas y documentos
  notas_adicionales: string | null;
  documento_adjunto: string | null;
  
  // Derivación
  derivacion_solicitada: boolean;
  derivacion_hospital_destino_id: number | null;
  derivacion_motivo: string | null;
  derivacion_estado: string | null;
  derivacion_rechazo_motivo: string | null;
  
  // Alta
  alta_solicitada: boolean;
  alta_motivo: string | null;
  
  // Lista espera
  estado_lista_espera: EstadoListaEsperaEnum | null;
  lista_espera_inicio: string | null;
  cama_asignada_id: number | null;
  
  // Timestamps
  created_at: string;
  updated_at: string;
  
  // Relaciones
  hospital?: Hospital;
  cama_actual?: Cama;
  cama_asignada?: Cama;
}

export interface ConfiguracionSistema {
  id: number;
  modo_manual: boolean;
  tiempo_limpieza_segundos: number;
}

// Request/Response types
export interface PacienteCreate {
  nombre: string;
  run: string;
  sexo: SexoEnum;
  edad: number;
  diagnostico: string;
  tipo_enfermedad: TipoEnfermedadEnum;
  tipo_aislamiento: TipoAislamientoEnum;
  embarazada?: boolean;
  hospital_id: number;
  
  // Requerimientos
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
  req_observacion_motivo?: string;
  req_irrigacion_vesical?: boolean;
  req_procedimiento_invasivo?: boolean;
  req_procedimiento_invasivo_detalle?: string;
  req_drogas_vasoactivas?: boolean;
  req_sedacion?: boolean;
  req_monitorizacion?: boolean;
  req_monitorizacion_motivo?: string;
  req_o2_reservorio?: boolean;
  req_dialisis?: boolean;
  req_cnaf?: boolean;
  req_bic_insulina?: boolean;
  req_vmni?: boolean;
  req_vmi?: boolean;
  req_procuramiento_o2?: boolean;
  
  // Casos especiales
  caso_socio_sanitario?: boolean;
  caso_socio_judicial?: boolean;
  caso_espera_cardiocirugia?: boolean;
  
  notas_adicionales?: string;
  
  // Derivación
  derivacion_solicitada?: boolean;
  derivacion_hospital_destino_id?: number;
  derivacion_motivo?: string;
  
  // Alta
  alta_solicitada?: boolean;
  alta_motivo?: string;
}

export interface PacienteUpdate extends Partial<PacienteCreate> {}

export interface DerivacionAccion {
  accion: 'aceptar' | 'rechazar';
  motivo_rechazo?: string;
}

export interface TrasladoManual {
  paciente_id: number;
  cama_destino_id: number;
}

export interface IntercambioRequest {
  paciente1_id: number;
  paciente2_id: number;
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
  hospital_id: number;
  hospital_nombre: string;
  total_camas: number;
  camas_libres: number;
  camas_ocupadas: number;
  camas_traslado: number;
  camas_limpieza: number;
  camas_bloqueadas: number;
  pacientes_espera: number;
  derivados_pendientes: number;
  porcentaje_ocupacion: number;
}

export interface EstadisticasGlobales {
  hospitales: EstadisticasHospital[];
  totales: {
    total_camas: number;
    camas_libres: number;
    camas_ocupadas: number;
    porcentaje_ocupacion: number;
  };
}

// WebSocket events
export interface WebSocketEvent {
  tipo: string;
  datos: Record<string, unknown>;
  timestamp: string;
}

// Lista espera item
export interface ListaEsperaItem {
  paciente: Paciente;
  prioridad: number;
  tiempo_espera_minutos: number;
  estado: EstadoListaEsperaEnum;
}

// Derivado item
export interface DerivadoItem {
  paciente: Paciente;
  hospital_origen: Hospital;
  motivo: string;
  prioridad: number;
  tiempo_en_lista_minutos: number;
}