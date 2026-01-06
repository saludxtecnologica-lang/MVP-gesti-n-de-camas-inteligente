// ============================================
// PARSERS - Única fuente de verdad
// ============================================

export function safeJsonParse(value: string | string[] | null | undefined): string[] {
  if (!value) return [];
  if (Array.isArray(value)) return value;
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function getNestedValue(obj: unknown, ...paths: string[]): unknown {
  for (const path of paths) {
    const keys = path.split('.');
    let value: unknown = obj;
    for (const key of keys) {
      if (value === null || value === undefined) break;
      value = (value as Record<string, unknown>)[key];
    }
    if (value !== null && value !== undefined) return value;
  }
  return undefined;
}

// ============================================
// VALIDATORS - Única fuente de verdad
// ============================================

export function validarFormatoRun(run: string): boolean {
  if (!run) return false;
  const pattern = /^\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]$/;
  return pattern.test(run.trim());
}

export function formatearRun(run: string): string {
  const cleaned = run.replace(/[^\dkK]/gi, '');
  if (cleaned.length < 2) return cleaned;
  const dv = cleaned.slice(-1);
  const numbers = cleaned.slice(0, -1);
  const formatted = numbers.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `${formatted}-${dv}`;
}

export function validarEdad(edad: number | string): boolean {
  const edadNum = typeof edad === 'string' ? parseInt(edad, 10) : edad;
  return !isNaN(edadNum) && edadNum >= 0 && edadNum <= 120;
}

// ============================================
// FORMATTERS
// ============================================

export function formatTiempoEspera(minutos: number): string {
  if (minutos < 60) {
    return `${minutos} min`;
  }
  const horas = Math.floor(minutos / 60);
  const mins = minutos % 60;
  if (mins === 0) {
    return `${horas}h`;
  }
  return `${horas}h ${mins}m`;
}

export function formatEstado(estado: string): string {
  const estados: Record<string, string> = {
    libre: 'Libre',
    ocupada: 'Ocupada',
    traslado_entrante: 'Traslado Entrante',
    traslado_saliente: 'Traslado Saliente',
    traslado_confirmado: 'Traslado Confirmado',
    cama_en_espera: 'En Espera',
    alta_sugerida: 'Alta Sugerida',
    cama_alta: 'Alta Médica',
    en_limpieza: 'En Limpieza',
    bloqueada: 'Bloqueada',
    espera_derivacion: 'Espera Derivación',
    derivacion_confirmada: 'Derivación Confirmada',
    // ============================================
    // NUEVO: Estado FALLECIDO
    // ============================================
    fallecido: 'Fallecido'
  };
  return estados[estado] || estado;
}

export function formatComplejidad(complejidad: string): string {
  const complejidades: Record<string, string> = {
    uci: 'UCI',
    uti: 'UTI',
    baja: 'Baja',
    ninguna: 'Ninguna'
  };
  return complejidades[complejidad] || complejidad;
}

export function formatTipoAislamiento(tipo: string): string {
  const tipos: Record<string, string> = {
    ninguno: 'Sin aislamiento',
    contacto: 'Contacto',
    gotitas: 'Gotitas',
    aereo: 'Aéreo',
    ambiente_protegido: 'Ambiente Protegido',
    especial: 'Especial'
  };
  return tipos[tipo] || tipo;
}

export function formatSexo(sexo: string): string {
  return sexo === 'hombre' ? 'H' : sexo === 'mujer' ? 'M' : sexo;
}

export function formatTipoPaciente(tipo: string): string {
  const tipos: Record<string, string> = {
    hospitalizado: 'Hospitalizado',
    urgencia: 'Urgencia',
    derivado: 'Derivado',
    ambulatorio: 'Ambulatorio'
  };
  return tipos[tipo] || tipo;
}

export function formatTipoEnfermedad(tipo: string): string {
  const tipos: Record<string, string> = {
    medica: 'Médica',
    quirurgica: 'Quirúrgica',
    traumatologica: 'Traumatológica',
    neurologica: 'Neurológica',
    urologica: 'Urológica',
    geriatrica: 'Geriátrica',
    ginecologica: 'Ginecológica',
    obstetrica: 'Obstétrica'
  };
  return tipos[tipo] || tipo;
}

// ============================================
// CONSTANTS
// ============================================

export const COLORES_ESTADO: Record<string, string> = {
  libre: 'bg-gray-50 border-gray-300 text-gray-600',
  ocupada: 'bg-green-50 border-green-500 text-green-700',
  traslado_entrante: 'bg-yellow-50 border-yellow-400 text-yellow-700',
  traslado_saliente: 'bg-pink-50 border-pink-400 text-pink-700',
  traslado_confirmado: 'bg-orange-50 border-orange-500 text-orange-700',
  cama_en_espera: 'bg-purple-50 border-purple-500 text-purple-700',
  alta_sugerida: 'bg-blue-50 border-blue-500 text-blue-700',
  cama_alta: 'bg-orange-50 border-orange-500 text-orange-700',
  en_limpieza: 'bg-red-50 border-red-500 text-red-700',
  bloqueada: 'bg-red-50 border-red-600 text-red-800',
  espera_derivacion: 'bg-indigo-50 border-indigo-500 text-indigo-700',
  derivacion_confirmada: 'bg-pink-50 border-pink-500 text-pink-700',
  // ============================================
  // NUEVO: Estado FALLECIDO
  // ============================================
  fallecido: 'bg-gray-800 text-gray-100 border-gray-900',
};

export const COLORES_COMPLEJIDAD: Record<string, string> = {
  uci: 'bg-red-500 text-white',
  uti: 'bg-orange-500 text-white',
  baja: 'bg-yellow-500 text-black',
  ninguna: 'bg-gray-300 text-gray-700'
};

// ============================================
// HELPERS
// ============================================

export function classNames(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}

export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}