import React, { useState } from 'react';
import {
  BedDouble,
  List,
  Send,
  BarChart3,
  Settings,
  UserPlus,
  Wifi,
  WifiOff,
  User,
  LogOut,
  ChevronDown
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { useModal } from '../../context/ModalContext';
import { useAuth } from '../../context/AuthContext';
import { ROL_NOMBRES, ROL_COLORES } from '../../types/auth';

type Vista = 'dashboard' | 'listaEspera' | 'derivados' | 'estadisticas';

interface HeaderProps {
  vistaActual: Vista;
  onCambiarVista: (vista: Vista) => void;
}

export function Header({ vistaActual, onCambiarVista }: HeaderProps) {
  const {
    hospitales,
    hospitalSeleccionado,
    setHospitalSeleccionado,
    configuracion,
    wsConnected,
    listaEspera,
    derivados
  } = useApp();
  const { openModal } = useModal();
  const { user, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const navItems: { key: Vista; label: string; icon: React.ElementType; badge?: number }[] = [
    { key: 'dashboard', label: 'Camas', icon: BedDouble },
    { key: 'listaEspera', label: 'Lista Espera', icon: List, badge: listaEspera.length },
    { key: 'derivados', label: 'Derivados', icon: Send, badge: derivados.length },
    { key: 'estadisticas', label: 'Estadísticas', icon: BarChart3 }
  ];

  return (
    <header className="bg-white shadow-sm border-b">
      <div className="max-w-[1920px] mx-auto px-4 py-3">
        <div className="flex items-center justify-between gap-6">
          {/* Logo y título */}
          <div className="flex items-center gap-4 flex-shrink-0">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Overmaind-Flow
            </h1>

            {/* Selector de hospital */}
            <select
              value={hospitalSeleccionado?.id || ''}
              onChange={(e) => {
                const hospital = hospitales.find(h => h.id === e.target.value);
                setHospitalSeleccionado(hospital || null);
              }}
              className="border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 font-medium min-w-[200px]"
            >
              {hospitales.map(hospital => (
                <option key={hospital.id} value={hospital.id}>
                  {hospital.nombre}
                </option>
              ))}
            </select>

            {/* Indicador modo */}
            {configuracion?.modo_manual && (
              <span className="bg-yellow-100 text-yellow-800 px-3 py-1.5 rounded-lg text-sm font-semibold">
                Modo Manual
              </span>
            )}
          </div>

          {/* Navegación */}
          <nav className="flex items-center gap-3 flex-grow justify-center">
            {navItems.map(item => {
              const Icon = item.icon;
              const isActive = vistaActual === item.key;
              return (
                <button
                  key={item.key}
                  onClick={() => onCambiarVista(item.key)}
                  className={`
                    flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold transition-colors
                    ${isActive
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:bg-gray-100'
                    }
                  `}
                >
                  <Icon className="w-5 h-5" />
                  {item.label}
                  {item.badge !== undefined && item.badge > 0 && (
                    <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full font-bold">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Acciones */}
          <div className="flex items-center gap-2">
            {/* Estado conexión */}
            <div className={`flex items-center gap-1 px-2 py-1 rounded text-xs ${
              wsConnected ? 'text-green-600' : 'text-red-600'
            }`}>
              {wsConnected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
              {wsConnected ? 'Conectado' : 'Desconectado'}
            </div>

            {/* Nuevo paciente */}
            <button
              onClick={() => openModal('paciente')}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              <UserPlus className="w-4 h-4" />
              Nuevo Paciente
            </button>

            {/* Configuración */}
            <button
              onClick={() => openModal('configuracion')}
              className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <Settings className="w-5 h-5" />
            </button>

            {/* Usuario - Dropdown */}
            {user && (
              <div className="relative">
                <button
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="flex items-center gap-2 px-3 py-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white text-sm font-medium">
                    {user.nombre_completo.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex flex-col items-start">
                    <span className="text-sm font-medium text-gray-700">{user.nombre_completo}</span>
                    <span className={`text-xs px-2 py-0.5 rounded ${ROL_COLORES[user.rol]} text-white`}>
                      {ROL_NOMBRES[user.rol]}
                    </span>
                  </div>
                  <ChevronDown className="w-4 h-4 text-gray-500" />
                </button>

                {/* Dropdown Menu */}
                {showUserMenu && (
                  <>
                    {/* Backdrop para cerrar al hacer click fuera */}
                    <div
                      className="fixed inset-0 z-10"
                      onClick={() => setShowUserMenu(false)}
                    />

                    {/* Menú */}
                    <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-20">
                      {/* Info del usuario */}
                      <div className="px-4 py-3 border-b border-gray-100">
                        <p className="text-sm font-medium text-gray-900">{user.nombre_completo}</p>
                        <p className="text-xs text-gray-500">{user.email}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          Hospital: {user.hospital_id || 'Todos'}
                        </p>
                        {user.servicio_id && (
                          <p className="text-xs text-gray-500">
                            Servicio: {user.servicio_id}
                          </p>
                        )}
                      </div>

                      {/* Opciones */}
                      <button
                        onClick={async () => {
                          setShowUserMenu(false);
                          await logout();
                        }}
                        className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                      >
                        <LogOut className="w-4 h-4" />
                        Cerrar Sesión
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}