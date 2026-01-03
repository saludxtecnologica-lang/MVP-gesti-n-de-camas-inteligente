// ============================================
// ENUMS
// ============================================

import { ReactNode } from "react";

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
  DERIVACION_CONFIRMADA = "derivacion_confirmada",
  FALLECIDO = 'fallecido',
}

export enum EstadoListaEsperaEnum {
  ESPERANDO = "esperando",
  BUSCANDO = "buscando",
  ASIGNADO = "asignado",
  CANCELADO = "cancelado"
}

// ============================================
// INTERFACES PRINCIPALES
// ============================================

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
  telefono_urgencias?: string | null;
  telefono_ambulatorio?: string | null;
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
  telefono?: string | null;
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
  bloqueada_motivo: ReactNode;
  id: string;
  numero: number;
  letra: string;
  identificador: string;
  estado: EstadoCamaEnum;
  mensaje_estado?: string | null;
  cama_asignada_destino?: string | null;
  sala_id: string;
  servicio_nombre?: string | null;
  servicio_tipo?: string | null;
  sala_nombre?: string;
  sala_es_individual?: boolean;
  sala_sexo_asignado?: string;
  paciente?: Paciente | null;
  paciente_entrante?: Paciente | null;
}

export interface Paciente {
  rut: string;
  prevision: any;
  requiere_aislamiento: any;
  requiere_oxigeno: any;
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
  es_embarazada?: boolean;
  hospital_id: string;
  cama_actual_id?: string | null;
  cama_id?: string | null;
  cama_destino_id?: string | null;
  en_lista_espera?: boolean;
  estado_lista_espera?: EstadoListaEsperaEnum | string | null;
  prioridad_calculada?: number;
  tiempo_espera_min?: number;
  requiere_nueva_cama?: boolean;
  requerimientos_no_definen?: string[];
  requerimientos_baja?: string[];
  requerimientos_uti?: string[];
  requerimientos_uci?: string[];
  motivo_observacion?: string | null;
  justificacion_observacion?: string | null;
  procedimiento_invasivo?: string | null;
  preparacion_quirurgica_detalle?: string | null;
  motivo_monitorizacion?: string | null;
  justificacion_monitorizacion?: string | null;
  casos_especiales?: string[];
  notas_adicionales?: string | null;
  documento_adjunto?: string | null;
  derivacion_solicitada?: boolean;
  derivacion_hospital_destino_id?: string | null;
  derivacion_motivo?: string | null;
  derivacion_estado?: string | null;
  derivacion_rechazo_motivo?: string | null;
  derivacion_motivo_rechazo?: string | null;
  alta_solicitada?: boolean;
  alta_motivo?: string | null;
  timestamp_lista_espera?: string | null;
  lista_espera_inicio?: string | null;
  cama_asignada_id?: string | null;
  esperando_evaluacion_oxigeno?: boolean;
  created_at?: string;
  updated_at?: string;
  hospital?: Hospital;
  cama_actual?: Cama;
  cama_asignada?: Cama;
  origen_tipo?: string | null;
  origen_hospital_nombre?: string | null;
  origen_servicio_nombre?: string | null;
  servicio_destino?: string | null;
  
  // ============================================
  // Timer de observación clínica
  // ============================================
  observacion_tiempo_horas?: number | null;
  observacion_inicio?: string | null;
  observacion_tiempo_restante?: number | null;
  
  // ============================================
  // Timer de monitorización
  // ============================================
  monitorizacion_tiempo_horas?: number | null;
  monitorizacion_inicio?: string | null;
  monitorizacion_tiempo_restante?: number | null;
  
  // ============================================
  // Motivo ingreso ambulatorio
  // ============================================
  motivo_ingreso_ambulatorio?: string | null;

  fallecido?: boolean;
  causa_fallecimiento?: string;
  fallecido_at?: string;
}

export interface ConfiguracionSistema {
  id?: string;
  modo_manual: boolean;
  // CAMBIADO: Ahora en minutos
  tiempo_limpieza_minutos: number;
  tiempo_espera_oxigeno_minutos: number;
  
  // DEPRECADOS - mantener por compatibilidad temporal
  tiempo_limpieza_segundos?: number;  // @deprecated usar tiempo_limpieza_minutos
  tiempo_espera_oxigeno_segundos?: number;  // @deprecated usar tiempo_espera_oxigeno_minutos
}

// ============================================
// REQUEST/RESPONSE TYPES
// ============================================

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
  requerimientos_no_definen?: string[];
  requerimientos_baja?: string[];
  requerimientos_uti?: string[];
  requerimientos_uci?: string[];
  casos_especiales?: string[];
  motivo_observacion?: string;
  justificacion_observacion?: string;
  motivo_monitorizacion?: string;
  justificacion_monitorizacion?: string;
  procedimiento_invasivo?: string;
  preparacion_quirurgica_detalle?: string;
  tipo_paciente: TipoPacienteEnum;
  hospital_id: string;
  derivacion_hospital_destino_id?: string;
  derivacion_motivo?: string;
  alta_solicitada?: boolean;
  alta_motivo?: string;
  observacion_tiempo_horas?: number | null;
  monitorizacion_tiempo_horas?: number | null;
  motivo_ingreso_ambulatorio?: string | null;
}

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
  motivo_monitorizacion?: string;
  justificacion_monitorizacion?: string;
  procedimiento_invasivo?: string;
  preparacion_quirurgica_detalle?: string;
  derivacion_hospital_destino_id?: string;
  derivacion_motivo?: string;
  alta_solicitada?: boolean;
  alta_motivo?: string;
  observacion_tiempo_horas?: number | null;
  monitorizacion_tiempo_horas?: number | null;
  fallecido?: boolean;
  causa_fallecimiento?: string;
}

export interface PacienteFormData {
  nombre: string;
  run: string;
  sexo: SexoEnum;
  edad: number | string;
  es_embarazada: boolean;
  diagnostico: string;
  tipo_enfermedad: TipoEnfermedadEnum;
  tipo_aislamiento: TipoAislamientoEnum;
  notas_adicionales: string;
  tipo_paciente: TipoPacienteEnum;
  hospital_id: string;
  motivo_ingreso_ambulatorio: string;
  
  // Requerimientos que no definen complejidad
  req_kinesioterapia_respiratoria: boolean;
  req_examen_sangre_ocasional: boolean;
  req_curaciones_simples_complejas: boolean;
  req_tratamiento_ev_ocasional: boolean;
  req_rehabilitacion_funcional: boolean;
  
  // Requerimientos baja complejidad
  req_tratamiento_ev_frecuente: boolean;
  req_tratamiento_infusion_continua: boolean;
  req_examen_sangre_frecuente: boolean;
  req_o2_naricera: boolean;
  req_dolor_eva_7: boolean;
  req_o2_multiventuri: boolean;
  req_curaciones_alta_complejidad: boolean;
  req_aspiracion_secreciones: boolean;
  req_observacion_clinica: boolean;
  req_observacion_motivo: string;
  req_observacion_justificacion: string;
  req_observacion_tiempo_horas: number | null;  
  req_irrigacion_vesical_continua: boolean;
  req_procedimiento_invasivo_quirurgico: boolean;
  req_procedimiento_invasivo_detalle: string;
  req_preparacion_quirurgica: boolean;  
  req_preparacion_quirurgica_detalle: string;
  req_nutricion_parenteral: boolean;  
  
  // Requerimientos UTI
  req_droga_vasoactiva: boolean;
  req_sedacion: boolean;
  req_monitorizacion: boolean;
  req_monitorizacion_motivo: string;
  req_monitorizacion_justificacion: string;
  req_monitorizacion_tiempo_horas: number | null;  // NUEVO
  req_o2_reservorio: boolean;
  req_dialisis_aguda: boolean;
  req_cnaf: boolean;
  req_bic_insulina: boolean;
  req_vmni: boolean;
  
  // Requerimientos UCI
  req_vmi: boolean;
  req_procuramiento_organos: boolean;
  
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
  
  // Documento
  documento_adjunto: File | null;
  documento_nombre: string;
}

export interface DerivacionAccion {
  accion: 'aceptar' | 'rechazar';
  motivo_rechazo?: string;
}

export interface CamaBloquearRequest {
  bloquear: boolean;
  motivo?: string;
}

export interface MessageResponse {
  success: boolean;
  message: string;
  data?: Record<string, unknown>;
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

export interface EstadisticasGlobales {
  hospitales: EstadisticasHospital[];
  total_camas_sistema: number;
  total_pacientes_sistema: number;
  ocupacion_promedio: number;
}

export interface WebSocketEvent {
  hospital_id?: string;
  reload?: boolean;
  mensaje?: string;
  tipo: string;
  datos?: Record<string, unknown>;
  timestamp?: string;
  play_sound?: boolean;
  notification_type?: string;
  message?: string;
  paciente_id?: string;
  cama_id?: string;
  derivacion_id?: string;
  cantidad?: number;
  cama_ids?: string[];
  [key: string]: unknown;

  // ============================================
  // CAMPOS TTS
  // ============================================
  
  // Flag que indica si el evento tiene datos TTS
  tts_habilitado?: boolean;
  
  // Identificador de la cama (ej: "505-A")
  cama_identificador?: string;
  
  // Identificador de la cama de origen para traslados
  cama_origen_identificador?: string;
  
  // Nombre del paciente
  paciente_nombre?: string;
  
  // ID del servicio de origen (para filtrado)
  servicio_origen_id?: string;
  
  // Nombre del servicio de origen (para mensaje hablado)
  servicio_origen_nombre?: string;
  
  // ID del servicio de destino (para filtrado)
  servicio_destino_id?: string;
  
  // Nombre del servicio de destino (para mensaje hablado)
  servicio_destino_nombre?: string;
  
  // ID del hospital de origen (derivaciones)
  hospital_origen_id?: string;
  
  // Nombre del hospital de origen (derivaciones)
  hospital_origen_nombre?: string;
  
  // ID del hospital de destino (derivaciones)
  hospital_destino_id?: string;
  
  // Nombre del hospital de destino (derivaciones)
  hospital_destino_nombre?: string;
}

export interface ListaEsperaItem {
  paciente: Paciente;
  prioridad: number;
  tiempo_espera_minutos: number;
  estado: EstadoListaEsperaEnum;
  paciente_id?: string;
  nombre?: string;
  run?: string;
  posicion?: number;
  tiempo_espera_min?: number;
  estado_lista?: string;
  origen_tipo?: 'derivado' | 'hospitalizado' | 'urgencia' | 'ambulatorio' | null;
  origen_hospital_nombre?: string | null;
  origen_hospital_codigo?: string | null;
  origen_servicio_nombre?: string | null;
  origen_cama_identificador?: string | null;
  servicio_destino?: string | null;
}

export interface DerivadoItem {
  paciente: Paciente;
  hospital_origen: Hospital;
  motivo: string;
  prioridad: number;
  tiempo_en_lista_minutos: number;
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

// ============================================
// TIPOS DE ALERTA
// ============================================

export type AlertType = 'success' | 'error' | 'info' | 'warning';

export interface AlertState {
  tipo: AlertType;
  mensaje: string;
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

// ============================================
// NUEVA INTERFACE: Información de traslado
// ============================================
export interface InfoTraslado {
  // Origen
  origen_tipo: 'hospitalizado' | 'urgencia' | 'ambulatorio' | 'derivado' | null;
  origen_hospital_nombre?: string | null;
  origen_hospital_codigo?: string | null;
  origen_servicio_nombre?: string | null;
  origen_servicio_telefono?: string | null;
  origen_cama_identificador?: string | null;
  
  // Destino
  destino_servicio_nombre?: string | null;
  destino_servicio_telefono?: string | null;
  destino_cama_identificador?: string | null;
  destino_hospital_nombre?: string | null;
  
  // Estado
  tiene_cama_origen: boolean;
  tiene_cama_destino: boolean;
  en_traslado: boolean;
}

// ============================================
// Servicio con teléfono (para configuración)
// ============================================
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

// ============================================
// Hospital con teléfonos completos
// ============================================
export interface HospitalConTelefonos {
  id: string;
  nombre: string;
  codigo: string;
  es_central: boolean;
  telefono_urgencias: string | null;
  telefono_ambulatorio: string | null;
  servicios: ServicioConTelefono[];
}
