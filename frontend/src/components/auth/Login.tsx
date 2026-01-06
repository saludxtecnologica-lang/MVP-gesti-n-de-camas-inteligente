/**
 * Componentes de Login
 */

import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import type { LoginRequest } from '../../types/auth';

// ============================================
// LOGIN PAGE (Página completa)
// ============================================

export function LoginPage() {
  const { login, isLoading, error, clearError } = useAuth();
  const [formData, setFormData] = useState<LoginRequest>({
    username: '',
    password: '',
    remember_me: false,
  });
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    await login(formData);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Logo y título */}
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-white rounded-full flex items-center justify-center shadow-lg">
            <svg className="h-10 w-10 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
          </div>
          <h2 className="mt-6 text-3xl font-extrabold text-white">
            Sistema de Gestión de Camas
          </h2>
          <p className="mt-2 text-sm text-blue-200">
            Ingresa tus credenciales para acceder
          </p>
        </div>

        {/* Formulario */}
        <div className="bg-white rounded-xl shadow-2xl p-8">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {/* Error */}
            {error && (
              <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Usuario */}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700">
                Usuario o Email
              </label>
              <div className="mt-1 relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
                <input
                  id="username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  required
                  value={formData.username}
                  onChange={handleChange}
                  className="appearance-none block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  placeholder="usuario"
                />
              </div>
            </div>

            {/* Contraseña */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Contraseña
              </label>
              <div className="mt-1 relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={formData.password}
                  onChange={handleChange}
                  className="appearance-none block w-full pl-10 pr-10 py-3 border border-gray-300 rounded-lg placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <svg className="h-5 w-5 text-gray-400 hover:text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5 text-gray-400 hover:text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {/* Recordarme */}
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  id="remember_me"
                  name="remember_me"
                  type="checkbox"
                  checked={formData.remember_me}
                  onChange={handleChange}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label htmlFor="remember_me" className="ml-2 block text-sm text-gray-700">
                  Recordarme
                </label>
              </div>
            </div>

            {/* Botón de login */}
            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-semibold rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {isLoading ? (
                  <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : (
                  'Iniciar Sesión'
                )}
              </button>
            </div>
          </form>

          {/* Credenciales de prueba */}
          <div className="mt-6 border-t border-gray-200 pt-6">
            <p className="text-xs text-gray-500 text-center mb-3">
              Credenciales de prueba:
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-gray-50 p-2 rounded">
                <span className="font-medium text-gray-700">Admin:</span>
                <br />
                <code className="text-blue-600">admin / Admin123!</code>
              </div>
              <div className="bg-gray-50 p-2 rounded">
                <span className="font-medium text-gray-700">Gestor:</span>
                <br />
                <code className="text-blue-600">gestor / Gestor123!</code>
              </div>
              <div className="bg-gray-50 p-2 rounded">
                <span className="font-medium text-gray-700">Médico:</span>
                <br />
                <code className="text-blue-600">medico / Medico123!</code>
              </div>
              <div className="bg-gray-50 p-2 rounded">
                <span className="font-medium text-gray-700">Enfermera:</span>
                <br />
                <code className="text-blue-600">enfermera / Enfermera123!</code>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-sm text-blue-200">
          © 2024 Sistema de Gestión Hospitalaria
        </p>
      </div>
    </div>
  );
}

// ============================================
// USER BADGE (Para mostrar en el header)
// ============================================

interface UserBadgeProps {
  className?: string;
}

export function UserBadge({ className = '' }: UserBadgeProps) {
  const { user, logout, isLoading } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  if (!user) return null;

  const getRolColor = (rol: string): string => {
    const colors: Record<string, string> = {
      super_admin: 'bg-purple-100 text-purple-800',
      admin: 'bg-red-100 text-red-800',
      gestor_camas: 'bg-blue-100 text-blue-800',
      medico: 'bg-green-100 text-green-800',
      enfermera: 'bg-pink-100 text-pink-800',
      urgencias: 'bg-orange-100 text-orange-800',
    };
    return colors[rol] || 'bg-gray-100 text-gray-800';
  };

  const getRolNombre = (rol: string): string => {
    const nombres: Record<string, string> = {
      super_admin: 'Super Admin',
      admin: 'Administrador',
      gestor_camas: 'Gestor de Camas',
      coordinador_camas: 'Coordinador',
      medico: 'Médico',
      jefe_servicio: 'Jefe de Servicio',
      enfermera: 'Enfermera',
      supervisora_enfermeria: 'Supervisora',
      urgencias: 'Urgencias',
      jefe_urgencias: 'Jefe Urgencias',
      derivaciones: 'Derivaciones',
      coordinador_red: 'Coord. Red',
      ambulatorio: 'Ambulatorio',
      estadisticas: 'Estadísticas',
      visualizador: 'Visualizador',
      operador: 'Operador',
      limpieza: 'Limpieza',
    };
    return nombres[rol] || rol;
  };

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setMenuOpen(!menuOpen)}
        className="flex items-center space-x-2 bg-white rounded-lg px-3 py-2 shadow-sm hover:shadow-md transition border border-gray-200"
      >
        {/* Avatar */}
        <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center text-white font-semibold text-sm">
          {user.nombre_completo.charAt(0).toUpperCase()}
        </div>
        
        {/* Info */}
        <div className="hidden sm:block text-left">
          <p className="text-sm font-medium text-gray-900 truncate max-w-[120px]">
            {user.nombre_completo.split(' ')[0]}
          </p>
          <span className={`text-xs px-1.5 py-0.5 rounded ${getRolColor(user.rol)}`}>
            {getRolNombre(user.rol)}
          </span>
        </div>

        {/* Chevron */}
        <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {menuOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setMenuOpen(false)}
          />
          
          {/* Menu */}
          <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 z-20">
            <div className="p-3 border-b border-gray-100">
              <p className="text-sm font-medium text-gray-900">{user.nombre_completo}</p>
              <p className="text-xs text-gray-500">{user.email}</p>
              <span className={`inline-block mt-1 text-xs px-2 py-0.5 rounded ${getRolColor(user.rol)}`}>
                {getRolNombre(user.rol)}
              </span>
            </div>
            
            <div className="p-2">
              <button
                onClick={async () => {
                  setMenuOpen(false);
                  await logout();
                }}
                disabled={isLoading}
                className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-md transition flex items-center"
              >
                <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                Cerrar Sesión
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default LoginPage;
