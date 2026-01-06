// ============================================
// TIPOS DE AUTENTICACIÓN
// ============================================

/**
 * Roles disponibles en el sistema - Sistema RBAC Multinivel.
 * Debe coincidir con RolEnum del backend.
 *
 * Capa 1 - Administración y Red (Nivel Global):
 *   - PROGRAMADOR: Equipo técnico con acceso total
 *   - DIRECTIVO_RED: Equipo directivo con visión de toda la red (solo lectura)
 *
 * Capa 2 - Gestión Local (Nivel Hospitalario):
 *   - DIRECTIVO_HOSPITAL: Directivos del hospital (solo lectura de su hospital)
 *   - GESTOR_CAMAS: Equipo de gestión de camas (Puerto Montt)
 *
 * Capa 3 - Clínica (Nivel Servicio):
 *   - MEDICO: Médico por servicio
 *   - ENFERMERA: Enfermero/a o Matrón/a por servicio
 *   - TENS: Técnico de enfermería de nivel superior
 */
export enum RolEnum {
  // Capa 1: Administración y Red
  PROGRAMADOR = "programador",
  DIRECTIVO_RED = "directivo_red",

  // Capa 2: Gestión Local
  DIRECTIVO_HOSPITAL = "directivo_hospital",
  GESTOR_CAMAS = "gestor_camas",

  // Capa 3: Clínica
  MEDICO = "medico",
  ENFERMERA = "enfermera",
  TENS = "tens",

  // Roles de servicio específicos
  JEFE_SERVICIO = "jefe_servicio",
  SUPERVISORA_ENFERMERIA = "supervisora_enfermeria",
  URGENCIAS = "urgencias",
  JEFE_URGENCIAS = "jefe_urgencias",
  AMBULATORIO = "ambulatorio",

  // Roles especializados
  DERIVACIONES = "derivaciones",
  ESTADISTICAS = "estadisticas",
  VISUALIZADOR = "visualizador",
  LIMPIEZA = "limpieza",

  // Aliases para compatibilidad
  SUPER_ADMIN = "programador",
  ADMIN = "gestor_camas",
  COORDINADOR_RED = "directivo_red",
  COORDINADOR_CAMAS = "gestor_camas",
  OPERADOR = "visualizador",
}

/**
 * Permisos granulares del sistema según especificación RBAC.
 * Debe coincidir con PermisoEnum del backend.
 */
export enum PermisoEnum {
  // Pacientes
  PACIENTE_CREAR = "paciente:crear",
  PACIENTE_VER = "paciente:ver",
  PACIENTE_EDITAR = "paciente:editar",
  PACIENTE_ELIMINAR = "paciente:eliminar",
  PACIENTE_REEVALUAR = "paciente:reevaluar", // Médico, Enfermera

  // Camas
  CAMA_VER = "cama:ver",
  CAMA_BLOQUEAR = "cama:bloquear",
  CAMA_DESBLOQUEAR = "cama:desbloquear",
  CAMA_ASIGNAR = "cama:asignar",

  // Lista de Espera y Búsqueda de Cama
  LISTA_ESPERA_VER = "lista_espera:ver",
  LISTA_ESPERA_GESTIONAR = "lista_espera:gestionar",
  LISTA_ESPERA_PRIORIZAR = "lista_espera:priorizar",
  BUSQUEDA_CAMA_INICIAR = "busqueda_cama:iniciar", // Solo Médico

  // Traslados
  TRASLADO_INICIAR = "traslado:iniciar", // Médico
  TRASLADO_ACEPTAR = "traslado:aceptar", // Enfermera
  TRASLADO_CONFIRMAR = "traslado:confirmar", // Enfermera (mismo que aceptar)
  TRASLADO_COMPLETAR = "traslado:completar", // Médico, Enfermera, TENS
  TRASLADO_CANCELAR = "traslado:cancelar", // Médico, Enfermera
  TRASLADO_VER = "traslado:ver",

  // Derivaciones
  DERIVACION_SOLICITAR = "derivacion:solicitar", // Médico
  DERIVACION_REALIZAR = "derivacion:realizar", // Médico (realizar/aceptar/rechazar)
  DERIVACION_ACEPTAR = "derivacion:aceptar", // Médico
  DERIVACION_RECHAZAR = "derivacion:rechazar", // Médico
  DERIVACION_VER = "derivacion:ver",
  DERIVACION_CANCELAR = "derivacion:cancelar", // Médico

  // Altas y Egresos
  ALTA_SUGERIR = "alta:sugerir", // Médico (seleccionar "Dar Alta")
  ALTA_EJECUTAR = "alta:ejecutar", // Enfermera (estado "Cama Alta")
  ALTA_CANCELAR = "alta:cancelar",
  EGRESO_REGISTRAR = "egreso:registrar", // Enfermera (Fallecido/Derivación Confirmada)

  // Modo Manual
  MODO_MANUAL_ASIGNAR = "modo_manual:asignar",
  MODO_MANUAL_INTERCAMBIAR = "modo_manual:intercambiar",

  // Pausas de Oxígeno
  PAUSA_OXIGENO_OMITIR = "pausa_oxigeno:omitir", // Médico, Enfermera

  // Registros
  REGISTRO_ELIMINAR = "registro:eliminar", // Médico, Enfermera

  // Configuración
  CONFIGURACION_VER = "configuracion:ver",
  CONFIGURACION_EDITAR = "configuracion:editar",

  // Estadísticas
  ESTADISTICAS_VER = "estadisticas:ver",
  ESTADISTICAS_EXPORTAR = "estadisticas:exportar",

  // Usuarios
  USUARIOS_VER = "usuarios:ver",
  USUARIOS_CREAR = "usuarios:crear",
  USUARIOS_EDITAR = "usuarios:editar",
  USUARIOS_ELIMINAR = "usuarios:eliminar",

  // Hospitales
  HOSPITAL_VER = "hospital:ver",
  HOSPITAL_EDITAR = "hospital:editar",
  HOSPITAL_TELEFONOS = "hospital:telefonos",

  // Fallecimiento
  FALLECIMIENTO_REGISTRAR = "fallecimiento:registrar",
  FALLECIMIENTO_CANCELAR = "fallecimiento:cancelar",

  // Limpieza
  LIMPIEZA_MARCAR = "limpieza:marcar",
  LIMPIEZA_COMPLETAR = "limpieza:completar",

  // Dashboard
  DASHBOARD_VER = "dashboard:ver", // No disponible para Urgencias y Ambulatorio

  // Adjuntos y Resumen
  RESUMEN_VER = "resumen:ver", // Médico, Enfermera (ver documentos adjuntos)
}

// ============================================
// INTERFACES
// ============================================

/**
 * Usuario autenticado
 */
export interface User {
  id: string;
  username: string;
  email: string;
  nombre_completo: string;
  rol: RolEnum;
  hospital_id: string | null;
  servicio_id: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login: string | null;
  permisos: string[];
}

/**
 * Tokens de autenticación
 */
export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

/**
 * Respuesta de login
 */
export interface LoginResponse {
  user: User;
  tokens: AuthTokens;
  message: string;
}

/**
 * Request de login
 */
export interface LoginRequest {
  username: string;
  password: string;
  remember_me?: boolean;
}

/**
 * Request de registro (admin)
 */
export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  nombre_completo: string;
  rol: RolEnum;
  hospital_id?: string;
  servicio_id?: string;
}

/**
 * Request de cambio de contraseña
 */
export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

/**
 * Información de rol
 */
export interface RolInfo {
  rol: RolEnum;
  nombre: string;
  descripcion: string;
  permisos: string[];
}

/**
 * Estado de autenticación
 */
export interface AuthState {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

/**
 * Acciones del contexto de auth
 */
export interface AuthActions {
  login: (credentials: LoginRequest) => Promise<boolean>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  updateUser: () => Promise<void>;
  clearError: () => void;
}

/**
 * Contexto completo de auth
 */
export type AuthContextType = AuthState & AuthActions;

// ============================================
// HELPERS DE ROLES
// ============================================

/**
 * Nombres amigables de los roles (Sistema RBAC Multinivel)
 */
export const ROL_NOMBRES: Record<RolEnum, string> = {
  // Capa 1: Administración y Red
  [RolEnum.PROGRAMADOR]: "Equipo Programador",
  [RolEnum.DIRECTIVO_RED]: "Equipo Directivo de Red",

  // Capa 2: Gestión Local
  [RolEnum.DIRECTIVO_HOSPITAL]: "Equipo Directivo Hospital",
  [RolEnum.GESTOR_CAMAS]: "Equipo Gestión de Camas",

  // Capa 3: Clínica
  [RolEnum.MEDICO]: "Médico",
  [RolEnum.ENFERMERA]: "Enfermera/o o Matrón/a",
  [RolEnum.TENS]: "TENS",

  // Roles de servicio específicos
  [RolEnum.JEFE_SERVICIO]: "Jefe de Servicio",
  [RolEnum.SUPERVISORA_ENFERMERIA]: "Supervisora Enfermería",
  [RolEnum.URGENCIAS]: "Urgencias",
  [RolEnum.JEFE_URGENCIAS]: "Jefe Urgencias",
  [RolEnum.AMBULATORIO]: "Ambulatorio",

  // Roles especializados
  [RolEnum.DERIVACIONES]: "Derivaciones",
  [RolEnum.ESTADISTICAS]: "Estadísticas",
  [RolEnum.VISUALIZADOR]: "Visualizador",
  [RolEnum.LIMPIEZA]: "Limpieza",

  // Aliases
  [RolEnum.SUPER_ADMIN]: "Super Administrador",
  [RolEnum.ADMIN]: "Administrador",
  [RolEnum.COORDINADOR_RED]: "Coordinador de Red",
  [RolEnum.COORDINADOR_CAMAS]: "Coordinador de Camas",
  [RolEnum.OPERADOR]: "Operador",
};

/**
 * Colores de badges por rol (Sistema RBAC Multinivel)
 */
export const ROL_COLORES: Record<RolEnum, string> = {
  // Capa 1: Administración y Red (tonos morados/rojos)
  [RolEnum.PROGRAMADOR]: "bg-purple-700",
  [RolEnum.DIRECTIVO_RED]: "bg-red-600",

  // Capa 2: Gestión Local (tonos azules)
  [RolEnum.DIRECTIVO_HOSPITAL]: "bg-blue-500",
  [RolEnum.GESTOR_CAMAS]: "bg-blue-700",

  // Capa 3: Clínica (tonos verdes/teal)
  [RolEnum.MEDICO]: "bg-green-600",
  [RolEnum.ENFERMERA]: "bg-teal-500",
  [RolEnum.TENS]: "bg-teal-400",

  // Roles de servicio específicos (tonos verdes oscuros/naranjas)
  [RolEnum.JEFE_SERVICIO]: "bg-green-700",
  [RolEnum.SUPERVISORA_ENFERMERIA]: "bg-teal-600",
  [RolEnum.URGENCIAS]: "bg-orange-500",
  [RolEnum.JEFE_URGENCIAS]: "bg-orange-600",
  [RolEnum.AMBULATORIO]: "bg-cyan-500",

  // Roles especializados (tonos amarillos/grises)
  [RolEnum.DERIVACIONES]: "bg-yellow-600",
  [RolEnum.ESTADISTICAS]: "bg-indigo-500",
  [RolEnum.VISUALIZADOR]: "bg-gray-500",
  [RolEnum.LIMPIEZA]: "bg-amber-500",

  // Aliases
  [RolEnum.SUPER_ADMIN]: "bg-purple-700",
  [RolEnum.ADMIN]: "bg-red-600",
  [RolEnum.COORDINADOR_RED]: "bg-red-600",
  [RolEnum.COORDINADOR_CAMAS]: "bg-blue-600",
  [RolEnum.OPERADOR]: "bg-gray-500",
};