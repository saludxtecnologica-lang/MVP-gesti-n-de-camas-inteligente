/**
 * Constantes de requerimientos clínicos
 * 
 * Este archivo centraliza:
 * - Tooltips informativos para cada requerimiento
 * - Leyendas visuales actualizadas
 * - Mapeo de IDs a nombres de visualización
 */

// ============================================
// TOOLTIPS INFORMATIVOS
// ============================================

export const TOOLTIPS = {
  // Título de sección
  seccion_no_definen: 'Prestaciones que se pueden entregar en otros recintos como CESFAM u HODOM.',
  
  // Requerimientos que NO definen complejidad
  req_monitorizacion: 'Control de signos vitales cada 4 horas o menos.',
  req_tratamiento_ev_ocasional: '1 o 2 veces al día, independiente del tipo de medicamento.',
  req_examen_sangre_ocasional: 'Control 1 vez al día.',
  req_rehabilitacion_funcional: 'Con kinesiólogo, fonoaudiólogo y/o terapeuta ocupacional.',
  
  // Requerimientos de baja complejidad
  req_tratamiento_ev_frecuente: '3 veces al día o más, independiente del tipo de medicamento.',
  req_tratamiento_infusion_continua: 'Fleboclisis, BIC analgesia, etc.',
  req_examen_sangre_frecuente: 'Control 2 veces al día o más.',
  req_curaciones_alta_complejidad: 'Gran quemados, uso de VAC, etc.',
  req_preparacion_quirurgica: 'Cirugía dentro de las próximas 48 horas.',
  
  // Aislamientos
  aislamiento_especial: 'KPC, C. difficile, COVID-19, Hanta, otros',
} as const;

// ============================================
// LEYENDAS VISUALES DE REQUERIMIENTOS
// Mapeo de ID interno -> Texto visual en formulario
// ============================================

export const LEYENDAS_REQUERIMIENTOS = {
  // No definen complejidad
  'Kinesioterapia respiratoria': 'Kinesioterapia respiratoria',
  'Exámenes de sangre ocasionales': 'Exámen de sangre ocasional',
  'Curaciones simples o complejas': 'Curaciones simples o complejas',
  'Tratamiento EV ocasional': 'Tratamiento endovenoso ocasional',
  'Rehabilitación funcional': 'Rehabilitación funcional/motora',
  
  // Baja complejidad
  'Tratamiento EV frecuente': 'Tratamiento endovenoso frecuente',
  'Tratamiento infusión continua': 'Tratamiento con infusión continua',
  'Exámenes de sangre frecuentes': 'Exámen de sangre frecuente',
  'O2 por naricera': 'Oxígeno por naricera',
  'Dolor EVA ≥ 7': 'Dolor ENA ≥ 7',
  'O2 por Multiventuri': 'Oxígeno por mascarilla multiventuri',
  'Curaciones de alta complejidad': 'Curaciones de alta complejidad',
  'Aspiración de secreciones': 'Aspiración invasiva de secreciones',
  'Observación clínica': 'Observación clínica',
  'Irrigación vesical continua': 'Irrigación vesical continua',
  'Procedimiento invasivo quirúrgico': 'Procedimiento invasivo o quirúrgico en las últimas 24 horas',
  'Preparación quirúrgica': 'Preparación quirúrgica',
  'Nutrición parenteral': 'Nutrición parenteral',
  
  // UTI
  'Droga vasoactiva': 'Droga vasoactiva',
  'Sedación': 'Sedación',
  'Monitorización continua': 'Monitorización',
  'O2 con reservorio': 'Oxígeno por mascarilla de reservorio',
  'Diálisis aguda': 'Diálisis aguda',
  'CNAF': 'CNAF (Cánula Nasal de Alto Flujo)',
  'BIC insulina': 'BIC insulina',
  'VMNI': 'VMNI (Ventilación Mecánica No Invasiva)',
  
  // UCI
  'VMI': 'VMI (Ventilación Mecánica Invasiva)',
  'Procuramiento de órganos': 'Procuramiento de órganos y tejidos',
} as const;

// ============================================
// OPCIONES DE MOTIVO DE INGRESO AMBULATORIO
// ============================================

export const MOTIVOS_INGRESO_AMBULATORIO = [
  { value: 'estabilizacion_clinica', label: 'Estabilización clínica', prioridadUrgencia: true },
  { value: 'tratamiento', label: 'Tratamiento', prioridadUrgencia: false },
] as const;

// ============================================
// OPCIONES DE TIEMPO PARA MONITORIZACIÓN Y OBSERVACIÓN
// ============================================

export const OPCIONES_TIEMPO_HORAS = [
  { value: 1, label: '1 hora' },
  { value: 2, label: '2 horas' },
  { value: 4, label: '4 horas' },
  { value: 6, label: '6 horas' },
  { value: 8, label: '8 horas' },
  { value: 12, label: '12 horas' },
  { value: 24, label: '24 horas' },
  { value: 48, label: '48 horas' },
  { value: 72, label: '72 horas' },
] as const;

// ============================================
// HELPER PARA OBTENER LEYENDA
// ============================================

export function obtenerLeyenda(id: string): string {
  return LEYENDAS_REQUERIMIENTOS[id as keyof typeof LEYENDAS_REQUERIMIENTOS] || id;
}

// ============================================
// HELPER PARA OBTENER TOOLTIP
// ============================================

export function obtenerTooltip(id: string): string | undefined {
  return TOOLTIPS[id as keyof typeof TOOLTIPS];
}