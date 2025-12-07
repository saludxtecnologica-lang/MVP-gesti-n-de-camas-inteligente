import React from 'react';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';

interface AlertProps {
  tipo: 'success' | 'error' | 'info';
  mensaje: string;
  onClose?: () => void;
}

export function Alert({ tipo, mensaje, onClose }: AlertProps) {
  const getIcon = () => {
    switch (tipo) {
      case 'success':
        return <CheckCircle size={20} />;
      case 'error':
        return <AlertCircle size={20} />;
      case 'info':
      default:
        return <Info size={20} />;
    }
  };

  return (
    <div className={`alert alert-${tipo}`}>
      <div className="alert-icon">
        {getIcon()}
      </div>
      <div className="alert-content">
        {mensaje}
      </div>
      {onClose && (
        <button className="alert-close" onClick={onClose} aria-label="Cerrar">
          <X size={18} />
        </button>
      )}
    </div>
  );
}
