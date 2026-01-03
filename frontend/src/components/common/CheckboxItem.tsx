import React from 'react';
import { HelpCircle, Clock } from 'lucide-react';
import { Tooltip } from './Tooltip';
import { OPCIONES_TIEMPO_HORAS } from '../constants/requerimientosConstants';

// ============================================
// CHECKBOX BÁSICO CON TOOLTIP
// ============================================

interface CheckboxItemProps {
  checked: boolean;
  onChange: () => void;
  label: string;
  tooltip?: string;
  disabled?: boolean;
}

export function CheckboxItem({ 
  checked, 
  onChange, 
  label,
  tooltip,
  disabled = false
}: CheckboxItemProps) {
  return (
    <label className={`flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}>
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
      />
      <span className="text-sm text-gray-700">{label}</span>
      {tooltip && (
        <Tooltip content={tooltip} position="top" iconSize="sm" />
      )}
    </label>
  );
}

// ============================================
// CHECKBOX CON SELECTOR DE TIEMPO
// Para monitorización y observación clínica
// ============================================

interface CheckboxWithTimeProps {
  checked: boolean;
  onChange: () => void;
  label: string;
  tooltip?: string;
  tiempoHoras: number | null;
  onTiempoChange: (horas: number | null) => void;
  tiempoInicio?: string | null; // ISO datetime
  tiempoRestante?: number | null; // segundos
  disabled?: boolean;
}

export function CheckboxWithTime({ 
  checked, 
  onChange, 
  label,
  tooltip,
  tiempoHoras,
  onTiempoChange,
  tiempoInicio,
  tiempoRestante,
  disabled = false
}: CheckboxWithTimeProps) {
  // Formatear tiempo restante
  const formatTiempoRestante = (segundos: number): string => {
    if (segundos <= 0) return 'Completado';
    
    const horas = Math.floor(segundos / 3600);
    const minutos = Math.floor((segundos % 3600) / 60);
    
    if (horas > 0) {
      return `${horas}h ${minutos}m restantes`;
    }
    return `${minutos} min restantes`;
  };

  // Formatear tiempo transcurrido
  const calcularTiempoTranscurrido = (): string | null => {
    if (!tiempoInicio || !tiempoHoras) return null;
    
    const inicio = new Date(tiempoInicio);
    const ahora = new Date();
    const transcurridoMs = ahora.getTime() - inicio.getTime();
    const transcurridoMin = Math.floor(transcurridoMs / 60000);
    const totalMin = tiempoHoras * 60;
    
    const horas = Math.floor(transcurridoMin / 60);
    const minutos = transcurridoMin % 60;
    
    return `${horas}h ${minutos}m de ${tiempoHoras}h`;
  };

  const tiempoTranscurrido = calcularTiempoTranscurrido();

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <label className={`flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}>
          <input
            type="checkbox"
            checked={checked}
            onChange={onChange}
            disabled={disabled}
            className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700">{label}</span>
        </label>
        
        {tooltip && (
          <Tooltip content={tooltip} position="top" iconSize="sm" />
        )}
        
        {/* Selector de tiempo cuando está marcado */}
        {checked && (
          <div className="flex items-center gap-2 ml-2">
            <Clock className="w-4 h-4 text-gray-500" />
            <select
              value={tiempoHoras || ''}
              onChange={(e) => onTiempoChange(e.target.value ? parseInt(e.target.value) : null)}
              className="text-xs border rounded px-2 py-1 focus:ring-2 focus:ring-blue-500"
              disabled={disabled}
            >
              <option value="">Seleccionar tiempo...</option>
              {OPCIONES_TIEMPO_HORAS.map(opt => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
      
      {/* Mostrar tiempo restante/transcurrido si hay timer activo */}
      {checked && tiempoHoras && tiempoInicio && (
        <div className="ml-6 flex items-center gap-2 text-xs">
          <Clock className="w-3 h-3 text-blue-500" />
          <span className="text-blue-600">
            {tiempoRestante !== null && tiempoRestante !== undefined 
              ? formatTiempoRestante(tiempoRestante)
              : tiempoTranscurrido
            }
          </span>
        </div>
      )}
    </div>
  );
}

// ============================================
// BADGE DE TIEMPO PARA VISUALIZACIÓN
// ============================================

interface TimeBadgeProps {
  tiempoHoras: number;
  tiempoInicio: string;
  tiempoRestante?: number;
  label: string;
}

export function TimeBadge({ 
  tiempoHoras, 
  tiempoInicio, 
  tiempoRestante,
  label 
}: TimeBadgeProps) {
  const formatTiempo = (segundos: number): string => {
    if (segundos <= 0) return 'Completado';
    
    const horas = Math.floor(segundos / 3600);
    const minutos = Math.floor((segundos % 3600) / 60);
    
    if (horas > 0) {
      return `${horas}h ${minutos}m`;
    }
    return `${minutos}m`;
  };

  const calcularPorcentaje = (): number => {
    if (!tiempoRestante) return 100;
    const totalSegundos = tiempoHoras * 3600;
    const transcurrido = totalSegundos - tiempoRestante;
    return Math.min(100, Math.round((transcurrido / totalSegundos) * 100));
  };

  const porcentaje = calcularPorcentaje();
  const esCompletado = tiempoRestante !== undefined && tiempoRestante <= 0;

  return (
    <div className={`inline-flex items-center gap-2 px-2 py-1 rounded text-xs ${
      esCompletado 
        ? 'bg-green-100 text-green-800' 
        : 'bg-blue-100 text-blue-800'
    }`}>
      <Clock className="w-3 h-3" />
      <span>{label}:</span>
      <span className="font-medium">
        {tiempoRestante !== undefined 
          ? formatTiempo(tiempoRestante)
          : `${tiempoHoras}h programadas`
        }
      </span>
      {!esCompletado && (
        <div className="w-16 h-1.5 bg-blue-200 rounded-full overflow-hidden">
          <div 
            className="h-full bg-blue-600 transition-all duration-300"
            style={{ width: `${porcentaje}%` }}
          />
        </div>
      )}
    </div>
  );
}

export default CheckboxItem;