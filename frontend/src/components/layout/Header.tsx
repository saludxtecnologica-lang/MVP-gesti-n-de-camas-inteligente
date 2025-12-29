import React from 'react';
import { 
  BedDouble, 
  List, 
  Send, 
  BarChart3, 
  Settings, 
  UserPlus,
  Wifi,
  WifiOff
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { useModal } from '../../context/ModalContext';

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

  const navItems: { key: Vista; label: string; icon: React.ElementType; badge?: number }[] = [
    { key: 'dashboard', label: 'Camas', icon: BedDouble },
    { key: 'listaEspera', label: 'Lista Espera', icon: List, badge: listaEspera.length },
    { key: 'derivados', label: 'Derivados', icon: Send, badge: derivados.length },
    { key: 'estadisticas', label: 'Estadísticas', icon: BarChart3 }
  ];

  return (
    <header className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          {/* Logo y título */}
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-gray-800">
              Gestión de Camas
            </h1>
            
            {/* Selector de hospital */}
            <select
              value={hospitalSeleccionado?.id || ''}
              onChange={(e) => {
                const hospital = hospitales.find(h => h.id === e.target.value);
                setHospitalSeleccionado(hospital || null);
              }}
              className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500"
            >
              {hospitales.map(hospital => (
                <option key={hospital.id} value={hospital.id}>
                  {hospital.nombre}
                </option>
              ))}
            </select>

            {/* Indicador modo */}
            {configuracion?.modo_manual && (
              <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs font-medium">
                Modo Manual
              </span>
            )}
          </div>

          {/* Navegación */}
          <nav className="flex items-center gap-1">
            {navItems.map(item => {
              const Icon = item.icon;
              const isActive = vistaActual === item.key;
              return (
                <button
                  key={item.key}
                  onClick={() => onCambiarVista(item.key)}
                  className={`
                    flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors
                    ${isActive 
                      ? 'bg-blue-100 text-blue-700' 
                      : 'text-gray-600 hover:bg-gray-100'
                    }
                  `}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                  {item.badge !== undefined && item.badge > 0 && (
                    <span className="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full">
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
          </div>
        </div>
      </div>
    </header>
  );
}