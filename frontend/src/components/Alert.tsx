import React from 'react';
import { X, AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react';

type AlertType = 'success' | 'error' | 'warning' | 'info';

interface AlertProps {
  tipo: AlertType;
  mensaje: string;
  onClose?: () => void;
}

const icons = {
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info
};

export function Alert({ tipo, mensaje, onClose }: AlertProps) {
  const Icon = icons[tipo];

  return (
    <div className={`alert alert-${tipo}`}>
      <Icon size={20} />
      <span style={{ flex: 1 }}>{mensaje}</span>
      {onClose && (
        <button 
          onClick={onClose}
          style={{ 
            background: 'none', 
            border: 'none', 
            cursor: 'pointer',
            padding: '4px'
          }}
        >
          <X size={16} />
        </button>
      )}
    </div>
  );
}