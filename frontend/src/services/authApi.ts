/**
 * API Client de Autenticación
 * Maneja todas las llamadas al backend relacionadas con auth.
 */

import {
  LoginRequest,
  LoginResponse,
  User,
  AuthTokens,
  RegisterRequest,
  PasswordChangeRequest,
  RolInfo,
} from '../types/auth';

// ============================================
// CONFIGURACIÓN
// ============================================

const getApiBase = (): string => {
  return import.meta.env.VITE_API_URL || 'http://localhost:8000';
};

// ============================================
// TOKEN STORAGE
// ============================================

const TOKEN_KEY = 'auth_tokens';
const USER_KEY = 'auth_user';

export const tokenStorage = {
  getTokens: (): AuthTokens | null => {
    const stored = localStorage.getItem(TOKEN_KEY);
    return stored ? JSON.parse(stored) : null;
  },
  
  setTokens: (tokens: AuthTokens): void => {
    localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
  },
  
  clearTokens: (): void => {
    localStorage.removeItem(TOKEN_KEY);
  },
  
  getAccessToken: (): string | null => {
    const tokens = tokenStorage.getTokens();
    return tokens?.access_token || null;
  },
  
  getRefreshToken: (): string | null => {
    const tokens = tokenStorage.getTokens();
    return tokens?.refresh_token || null;
  },
  
  getUser: (): User | null => {
    const stored = localStorage.getItem(USER_KEY);
    return stored ? JSON.parse(stored) : null;
  },
  
  setUser: (user: User): void => {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  
  clearUser: (): void => {
    localStorage.removeItem(USER_KEY);
  },
  
  clearAll: (): void => {
    tokenStorage.clearTokens();
    tokenStorage.clearUser();
  },
};

// ============================================
// FETCH HELPERS
// ============================================

interface FetchOptions extends RequestInit {
  skipAuth?: boolean;
}

/**
 * Fetch con manejo de autenticación automático
 */
export async function authFetch<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { skipAuth = false, ...fetchOptions } = options;
  const url = `${getApiBase()}${endpoint}`;
  
  // Headers por defecto
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...fetchOptions.headers,
  };
  
  // Añadir token de auth si existe y no se salta
  if (!skipAuth) {
    const token = tokenStorage.getAccessToken();
    if (token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }
  }
  
  const response = await fetch(url, {
    ...fetchOptions,
    headers,
  });
  
  // Manejar errores de autenticación
  if (response.status === 401) {
    // Solo intentar refrescar si no es el endpoint de refresh o logout
    const isRefreshEndpoint = endpoint.includes('/auth/refresh');
    const isLogoutEndpoint = endpoint.includes('/auth/logout');

    if (!isRefreshEndpoint && !isLogoutEndpoint) {
      // Intentar refrescar token una sola vez
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        // Reintentar con nuevo token
        const newToken = tokenStorage.getAccessToken();
        if (newToken) {
          (headers as Record<string, string>)['Authorization'] = `Bearer ${newToken}`;

          const retryResponse = await fetch(url, {
            ...fetchOptions,
            headers,
          });

          if (!retryResponse.ok) {
            // Si falla el reintento, forzar logout
            tokenStorage.clearAll();
            window.dispatchEvent(new CustomEvent('auth:logout'));
            throw new Error('Sesión expirada. Por favor, inicia sesión nuevamente.');
          }

          return retryResponse.json();
        }
      }
    }

    // No se pudo refrescar o es un endpoint de auth, limpiar y forzar logout
    tokenStorage.clearAll();
    window.dispatchEvent(new CustomEvent('auth:logout'));
    throw new Error('Sesión expirada. Por favor, inicia sesión nuevamente.');
  }
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Error ${response.status}`);
  }
  
  return response.json();
}

// ============================================
// REFRESH TOKEN
// ============================================

let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;
let lastRefreshAttempt = 0;
const REFRESH_COOLDOWN = 5000; // 5 segundos entre intentos

async function refreshAccessToken(): Promise<boolean> {
  const now = Date.now();

  // Evitar múltiples refreshes simultáneos
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }

  // Evitar intentos demasiado frecuentes
  if (now - lastRefreshAttempt < REFRESH_COOLDOWN) {
    console.warn('Refresh token cooldown activo, esperando...');
    return false;
  }

  const refreshToken = tokenStorage.getRefreshToken();
  if (!refreshToken) {
    console.warn('No hay refresh token disponible');
    return false;
  }

  lastRefreshAttempt = now;
  isRefreshing = true;

  refreshPromise = (async () => {
    try {
      console.log('Intentando refrescar access token...');
      const response = await fetch(`${getApiBase()}/api/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        console.error('Refresh token falló:', response.status, response.statusText);
        // Limpiar tokens inválidos
        tokenStorage.clearAll();
        return false;
      }

      const tokens: AuthTokens = await response.json();
      tokenStorage.setTokens(tokens);
      console.log('Access token refrescado exitosamente');
      return true;
    } catch (error) {
      console.error('Error al refrescar token:', error);
      // Limpiar tokens en caso de error
      tokenStorage.clearAll();
      return false;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

// ============================================
// AUTH API
// ============================================

export const authApi = {
  /**
   * Login con username y password
   */
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const response = await fetch(`${getApiBase()}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Error al iniciar sesión');
    }
    
    const data: LoginResponse = await response.json();
    
    // Guardar tokens y usuario
    tokenStorage.setTokens(data.tokens);
    tokenStorage.setUser(data.user);
    
    return data;
  },
  
  /**
   * Logout
   */
  logout: async (): Promise<void> => {
    const refreshToken = tokenStorage.getRefreshToken();
    
    if (refreshToken) {
      try {
        await authFetch('/api/auth/logout', {
          method: 'POST',
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      } catch {
        // Ignorar errores de logout
      }
    }
    
    tokenStorage.clearAll();
  },
  
  /**
   * Logout de todas las sesiones
   */
  logoutAll: async (): Promise<void> => {
    try {
      await authFetch('/api/auth/logout-all', { method: 'POST' });
    } finally {
      tokenStorage.clearAll();
    }
  },
  
  /**
   * Obtener usuario actual
   */
  getMe: async (): Promise<User> => {
    return authFetch<User>('/api/auth/me');
  },
  
  /**
   * Cambiar contraseña
   */
  changePassword: async (data: PasswordChangeRequest): Promise<void> => {
    await authFetch('/api/auth/me/password', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    tokenStorage.clearAll();
  },
  
  /**
   * Obtener permisos del usuario actual
   */
  getMyPermissions: async (): Promise<string[]> => {
    return authFetch<string[]>('/api/auth/me/permisos');
  },
  
  /**
   * Verificar un permiso específico
   */
  checkPermission: async (permiso: string): Promise<boolean> => {
    const response = await authFetch<{ success: boolean }>('/api/auth/check-permission', {
      method: 'POST',
      body: JSON.stringify({ permiso }),
    });
    return response.success;
  },
  
  /**
   * Listar roles disponibles
   */
  getRoles: async (): Promise<RolInfo[]> => {
    return authFetch<RolInfo[]>('/api/auth/roles', { skipAuth: true });
  },
  
  // ============================================
  // ADMIN: GESTIÓN DE USUARIOS
  // ============================================
  
  /**
   * Listar usuarios (admin)
   */
  listUsers: async (filters?: {
    hospital_id?: string;
    rol?: string;
    is_active?: boolean;
  }): Promise<User[]> => {
    const params = new URLSearchParams();
    if (filters?.hospital_id) params.append('hospital_id', filters.hospital_id);
    if (filters?.rol) params.append('rol', filters.rol);
    if (filters?.is_active !== undefined) params.append('is_active', String(filters.is_active));
    
    const query = params.toString();
    return authFetch<User[]>(`/api/auth/usuarios${query ? `?${query}` : ''}`);
  },
  
  /**
   * Crear usuario (admin)
   */
  createUser: async (data: RegisterRequest): Promise<User> => {
    return authFetch<User>('/api/auth/usuarios', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  
  /**
   * Obtener usuario por ID (admin)
   */
  getUser: async (userId: string): Promise<User> => {
    return authFetch<User>(`/api/auth/usuarios/${userId}`);
  },
  
  /**
   * Actualizar usuario (admin)
   */
  updateUser: async (userId: string, data: Partial<User>): Promise<User> => {
    return authFetch<User>(`/api/auth/usuarios/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },
  
  /**
   * Eliminar (desactivar) usuario (admin)
   */
  deleteUser: async (userId: string): Promise<void> => {
    await authFetch(`/api/auth/usuarios/${userId}`, { method: 'DELETE' });
  },
  
  /**
   * Resetear contraseña de usuario (admin)
   */
  resetUserPassword: async (userId: string): Promise<{ temp_password: string }> => {
    const response = await authFetch<{ data: { temp_password: string } }>(
      `/api/auth/usuarios/${userId}/reset-password`,
      { method: 'PUT' }
    );
    return response.data;
  },
};

// ============================================
// EXPORT DEFAULT
// ============================================

export default authApi;