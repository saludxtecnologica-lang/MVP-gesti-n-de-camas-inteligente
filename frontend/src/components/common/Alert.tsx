import React from 'react';
import { CheckCircle, XCircle, AlertCircle, Info, X } from 'lucide-react';
import type { AlertType } from '../../types';

interface AlertProps {
  tipo: AlertType;
  mensaje: string;
  onClose?: () => void;
}

const alertStyles: Record<AlertType, { bg: string; border: string; text: string; icon: typeof CheckCircle }> = {
  success: {
    bg: 'bg-green-50',
    border: 'border-green-500',
    text: 'text-green-800',
    icon: CheckCircle
  },
  error: {
    bg: 'bg-red-50',
    border: 'border-red-500',
    text: 'text-red-800',
    icon: XCircle
  },
  warning: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-500',
    text: 'text-yellow-800',
    icon: AlertCircle
  },
  info: {
    bg: 'bg-blue-50',
    border: 'border-blue-500',
    text: 'text-blue-800',
    icon: Info
  }
};

export function Alert({ tipo, mensaje, onClose }: AlertProps) {
  const style = alertStyles[tipo];
  const Icon = style.icon;

  return (
    <div className={`fixed top-4 right-4 z-50 ${style.bg} ${style.text} border-l-4 ${style.border} p-4 rounded shadow-lg max-w-md`}>
      <div className="flex items-start">
        <Icon className="w-5 h-5 mr-3 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="text-sm">{mensaje}</p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="ml-4 text-current opacity-70 hover:opacity-100"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}