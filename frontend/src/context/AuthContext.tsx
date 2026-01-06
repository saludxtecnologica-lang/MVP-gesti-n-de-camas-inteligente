/**
 * AuthContext - Contexto de autenticación para React
 * Maneja el estado de autenticación global de la aplicación.
 */

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from 'react';

// Tipos de autenticación
import type {
  User,
  AuthTokens,
  LoginRequest,
  AuthContextType,
  PermisoEnum,
} from '../types/auth';

// API de autenticación
import { authApi, tokenStorage } from '../services/authApi';

// ============================================
// CONTEXTO
// ============================================

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ============================================
// PROVIDER
// ============================================

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [tokens, setTokens] = useState<AuthTokens | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Estado derivado
  const isAuthenticated = !!user && !!tokens;

  // ============================================
  // INICIALIZACIÓN
  // ============================================

  useEffect(() => {
    const initAuth = async () => {
      setIsLoading(true);
      
      try {
        // Recuperar tokens del storage
        const storedTokens = tokenStorage.getTokens();
        const storedUser = tokenStorage.getUser();
        
        if (storedTokens && storedUser) {
          setTokens(storedTokens);
          setUser(storedUser);
          
          // Verificar que el token siga siendo válido
          try {
            const freshUser = await authApi.getMe();
            setUser(freshUser);
            tokenStorage.setUser(freshUser);
          } catch {
            // Token inválido, limpiar
            tokenStorage.clearAll();
            setTokens(null);
            setUser(null);
          }
        }
      } catch (err) {
        console.error('Error initializing auth:', err);
      } finally {
        setIsLoading(false);
      }
    };
    
    initAuth();
    
    // Escuchar eventos de logout forzado
    const handleLogout = () => {
      setUser(null);
      setTokens(null);
    };
    
    window.addEventListener('auth:logout', handleLogout);
    return () => window.removeEventListener('auth:logout', handleLogout);
  }, []);

  // ============================================
  // ACCIONES
  // ============================================

  const login = useCallback(async (credentials: LoginRequest): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await authApi.login(credentials);
      setUser(response.user);
      setTokens(response.tokens);
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error al iniciar sesión';
      setError(message);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    
    try {
      await authApi.logout();
    } finally {
      setUser(null);
      setTokens(null);
      setIsLoading(false);
    }
  }, []);

  const refreshToken = useCallback(async (): Promise<boolean> => {
    const refreshTokenValue = tokenStorage.getRefreshToken();
    
    if (!refreshTokenValue) {
      return false;
    }
    
    try {
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshTokenValue }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to refresh token');
      }
      
      const newTokens: AuthTokens = await response.json();
      setTokens(newTokens);
      tokenStorage.setTokens(newTokens);
      return true;
    } catch {
      // Refresh falló, hacer logout
      await logout();
      return false;
    }
  }, [logout]);

  const updateUser = useCallback(async (): Promise<void> => {
    if (!isAuthenticated) return;
    
    try {
      const freshUser = await authApi.getMe();
      setUser(freshUser);
      tokenStorage.setUser(freshUser);
    } catch (err) {
      console.error('Error updating user:', err);
    }
  }, [isAuthenticated]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // ============================================
  // VALOR DEL CONTEXTO
  // ============================================

  const value: AuthContextType = {
    user,
    tokens,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    refreshToken,
    updateUser,
    clearError,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// ============================================
// HOOK PRINCIPAL
// ============================================

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  
  if (context === undefined) {
    throw new Error('useAuth debe usarse dentro de un AuthProvider');
  }
  
  return context;
}

// ============================================
// HOOKS DE PERMISOS
// ============================================

/**
 * Hook para verificar si el usuario tiene un permiso específico
 */
export function usePermission(permiso: PermisoEnum | string): boolean {
  const { user } = useAuth();
  
  if (!user) return false;
  
  return user.permisos.includes(permiso);
}

/**
 * Hook para verificar si el usuario tiene al menos uno de los permisos
 */
export function useAnyPermission(permisos: (PermisoEnum | string)[]): boolean {
  const { user } = useAuth();
  
  if (!user) return false;
  
  return permisos.some(p => user.permisos.includes(p));
}

/**
 * Hook para verificar si el usuario tiene todos los permisos
 */
export function useAllPermissions(permisos: (PermisoEnum | string)[]): boolean {
  const { user } = useAuth();
  
  if (!user) return false;
  
  return permisos.every(p => user.permisos.includes(p));
}

/**
 * Hook para obtener la lista de permisos del usuario
 */
export function usePermissions(): string[] {
  const { user } = useAuth();
  return user?.permisos || [];
}

// ============================================
// HOOKS DE ROL
// ============================================

/**
 * Hook para verificar si el usuario tiene un rol específico
 */
export function useRole(rol: string): boolean {
  const { user } = useAuth();
  return user?.rol === rol;
}

/**
 * Hook para verificar si el usuario tiene uno de los roles
 */
export function useAnyRole(roles: string[]): boolean {
  const { user } = useAuth();
  return !!user && roles.includes(user.rol);
}

/**
 * Hook para obtener el rol del usuario
 */
export function useCurrentRole(): string | null {
  const { user } = useAuth();
  return user?.rol || null;
}

// ============================================
// EXPORT
// ============================================

export default AuthContext;
