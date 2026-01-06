// ============================================
// TIPOS DE AUTENTICACIÓN
// ============================================

/**
 * Roles disponibles en el sistema.
 * Debe coincidir con RolEnum del backend.
 */
export enum RolEnum {
  SUPER_ADMIN = "super_admin",
  ADMIN = "admin",
  GESTOR_CAMAS = "gestor_camas",
  COORDINADOR_CAMAS = "coordinador_camas",
  MEDICO = "medico",
  JEFE_SERVICIO = "jefe_servicio",
  ENFERMERA = "enfermera",
  SUPERVISORA_ENFERMERIA = "supervisora",
  URGENCIAS = "urgencias",
  JEFE_URGENCIAS = "jefe_urgencias",
  DERIVACIONES = "derivaciones",
  COORDINADOR_RED = "coordinador_red",
  AMBULATORIO = "ambulatorio",
  ESTADISTICAS = "estadisticas",
  VISUALIZADOR = "visualizador",
  OPERADOR = "operador",
  LIMPIEZA = "limpieza",
}

/**
 * Permisos granulares del sistema.
 * Debe coincidir con PermisoEnum del backend.
 */
export enum PermisoEnum {
  // Pacientes
  PACIENTE_CREAR = "paciente:crear",
  PACIENTE_VER = "paciente:ver",
  PACIENTE_EDITAR = "paciente:editar",
  PACIENTE_ELIMINAR = "paciente:eliminar",
  
  // Camas
  CAMA_VER = "cama:ver",
  CAMA_BLOQUEAR = "cama:bloquear",
  CAMA_DESBLOQUEAR = "cama:desbloquear",
  CAMA_ASIGNAR = "cama:asignar",
  
  // Lista de espera
  LISTA_ESPERA_VER = "lista_espera:ver",
  LISTA_ESPERA_GESTIONAR = "lista_espera:gestionar",
  LISTA_ESPERA_PRIORIZAR = "lista_espera:priorizar",
  
  // Traslados
  TRASLADO_INICIAR = "traslado:iniciar",
  TRASLADO_CONFIRMAR = "traslado:confirmar",
  TRASLADO_CANCELAR = "traslado:cancelar",
  TRASLADO_VER = "traslado:ver",
  
  // Derivaciones
  DERIVACION_SOLICITAR = "derivacion:solicitar",
  DERIVACION_ACEPTAR = "derivacion:aceptar",
  DERIVACION_RECHAZAR = "derivacion:rechazar",
  DERIVACION_VER = "derivacion:ver",
  DERIVACION_CANCELAR = "derivacion:cancelar",
  
  // Altas
  ALTA_SOLICITAR = "alta:solicitar",
  ALTA_EJECUTAR = "alta:ejecutar",
  ALTA_CANCELAR = "alta:cancelar",
  
  // Modo manual
  MODO_MANUAL_ASIGNAR = "modo_manual:asignar",
  MODO_MANUAL_INTERCAMBIAR = "modo_manual:intercambiar",
  
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
 * Nombres amigables de los roles
 */
export const ROL_NOMBRES: Record<RolEnum, string> = {
  [RolEnum.SUPER_ADMIN]: "Super Administrador",
  [RolEnum.ADMIN]: "Administrador",
  [RolEnum.GESTOR_CAMAS]: "Gestor de Camas",
  [RolEnum.COORDINADOR_CAMAS]: "Coordinador de Camas",
  [RolEnum.MEDICO]: "Médico",
  [RolEnum.JEFE_SERVICIO]: "Jefe de Servicio",
  [RolEnum.ENFERMERA]: "Enfermera/o",
  [RolEnum.SUPERVISORA_ENFERMERIA]: "Supervisora Enfermería",
  [RolEnum.URGENCIAS]: "Urgencias",
  [RolEnum.JEFE_URGENCIAS]: "Jefe Urgencias",
  [RolEnum.DERIVACIONES]: "Derivaciones",
  [RolEnum.COORDINADOR_RED]: "Coordinador de Red",
  [RolEnum.AMBULATORIO]: "Ambulatorio",
  [RolEnum.ESTADISTICAS]: "Estadísticas",
  [RolEnum.VISUALIZADOR]: "Visualizador",
  [RolEnum.OPERADOR]: "Operador",
  [RolEnum.LIMPIEZA]: "Limpieza",
};

/**
 * Colores de badges por rol
 */
export const ROL_COLORES: Record<RolEnum, string> = {
  [RolEnum.SUPER_ADMIN]: "bg-purple-600",
  [RolEnum.ADMIN]: "bg-red-600",
  [RolEnum.GESTOR_CAMAS]: "bg-blue-600",
  [RolEnum.COORDINADOR_CAMAS]: "bg-blue-500",
  [RolEnum.MEDICO]: "bg-green-600",
  [RolEnum.JEFE_SERVICIO]: "bg-green-700",
  [RolEnum.ENFERMERA]: "bg-teal-500",
  [RolEnum.SUPERVISORA_ENFERMERIA]: "bg-teal-600",
  [RolEnum.URGENCIAS]: "bg-orange-500",
  [RolEnum.JEFE_URGENCIAS]: "bg-orange-600",
  [RolEnum.DERIVACIONES]: "bg-yellow-600",
  [RolEnum.COORDINADOR_RED]: "bg-yellow-700",
  [RolEnum.AMBULATORIO]: "bg-cyan-500",
  [RolEnum.ESTADISTICAS]: "bg-indigo-500",
  [RolEnum.VISUALIZADOR]: "bg-gray-500",
  [RolEnum.OPERADOR]: "bg-slate-500",
  [RolEnum.LIMPIEZA]: "bg-amber-500",
};