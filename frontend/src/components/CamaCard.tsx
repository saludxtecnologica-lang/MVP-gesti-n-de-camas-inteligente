import React from 'react';
import { Eye, Check, X, Search, FileText, ArrowRight, LogOut, Lock, Unlock } from 'lucide-react';
import type { Cama, Paciente } from '../types/Index';
import { EstadoCamaEnum } from '../types/Index';

interface CamaCardProps {
  cama: Cama;
  modoManual: boolean;
  onVerPaciente: (paciente: Paciente) => void;
  onReevaluar: (paciente: Paciente) => void;
  onCompletarTraslado: (pacienteId: string) => void;
  onCancelarTraslado: (pacienteId: string) => void;
  onBuscarNuevaCama: (pacienteId: string) => void;
  onIniciarAlta: (pacienteId: string) => void;
  onDarAlta: (pacienteId: string) => void;
  onCancelarAlta: (pacienteId: string) => void;
  onConfirmarEgreso: (pacienteId: string) => void;
  onBloquear: (camaId: string, bloquear: boolean) => void;
}

export function CamaCard({
  cama,
  modoManual,
  onVerPaciente,
  onReevaluar,
  onCompletarTraslado,
  onCancelarTraslado,
  onBuscarNuevaCama,
  onIniciarAlta,
  onDarAlta,
  onCancelarAlta,
  onConfirmarEgreso,
  onBloquear
}: CamaCardProps) {
  const paciente = cama.paciente || cama.paciente_entrante;
  
  const getEstadoTexto = () => {
    switch (cama.estado) {
      case EstadoCamaEnum.LIBRE:
        return 'Disponible';
      case EstadoCamaEnum.OCUPADA:
        return 'Ocupada';
      case EstadoCamaEnum.TRASLADO_ENTRANTE:
        return 'Paciente asignado - Pendiente llegada';
      case EstadoCamaEnum.CAMA_EN_ESPERA:
        return 'Paciente requiere nueva cama';
      case EstadoCamaEnum.TRASLADO_SALIENTE:
        return 'Esperando nueva cama';
      case EstadoCamaEnum.TRASLADO_CONFIRMADO:
        return 'Nueva cama asignada - Listo para traslado';
      case EstadoCamaEnum.ALTA_SUGERIDA:
        return 'Alta sugerida';
      case EstadoCamaEnum.CAMA_ALTA:
        return 'Alta pendiente';
      case EstadoCamaEnum.EN_LIMPIEZA:
        return 'En limpieza';
      case EstadoCamaEnum.BLOQUEADA:
        return cama.bloqueada_motivo ? `Bloqueada: ${cama.bloqueada_motivo}` : 'Bloqueada';
      case EstadoCamaEnum.ESPERA_DERIVACION:
        return 'Derivación solicitada';
      case EstadoCamaEnum.DERIVACION_CONFIRMADA:
        return 'Derivación aceptada - Pendiente egreso';
      default:
        return cama.estado;
    }
  };

  const renderBotones = () => {
    const botones: React.ReactNode[] = [];

    switch (cama.estado) {
      case EstadoCamaEnum.LIBRE:
        botones.push(
          <button
            key="bloquear"
            className="btn btn-sm btn-secondary"
            onClick={() => onBloquear(cama.id, true)}
          >
            <Lock size={14} /> Bloquear
          </button>
        );
        break;

      case EstadoCamaEnum.OCUPADA:
        if (paciente) {
          botones.push(
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(paciente)}
            >
              <Eye size={14} /> Ver
            </button>,
            <button
              key="reevaluar"
              className="btn btn-sm btn-primary"
              onClick={() => onReevaluar(paciente)}
            >
              <FileText size={14} /> Reevaluar
            </button>
          );
        }
        break;

      case EstadoCamaEnum.TRASLADO_ENTRANTE:
        if (cama.paciente_entrante) {
          botones.push(
            <button
              key="completar"
              className="btn btn-sm btn-success"
              onClick={() => onCompletarTraslado(cama.paciente_entrante!.id)}
            >
              <Check size={14} /> Completar
            </button>,
            <button
              key="cancelar"
              className="btn btn-sm btn-danger"
              onClick={() => onCancelarTraslado(cama.paciente_entrante!.id)}
            >
              <X size={14} /> Cancelar
            </button>,
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(cama.paciente_entrante!)}
            >
              <Eye size={14} /> Ver
            </button>
          );
        }
        break;

      case EstadoCamaEnum.CAMA_EN_ESPERA:
        if (paciente) {
          botones.push(
            <button
              key="buscar"
              className="btn btn-sm btn-primary"
              onClick={() => onBuscarNuevaCama(paciente.id)}
            >
              <Search size={14} /> Buscar cama
            </button>,
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(paciente)}
            >
              <Eye size={14} /> Ver
            </button>,
            <button
              key="reevaluar"
              className="btn btn-sm btn-secondary"
              onClick={() => onReevaluar(paciente)}
            >
              <FileText size={14} /> Reevaluar
            </button>
          );
        }
        break;

      case EstadoCamaEnum.TRASLADO_SALIENTE:
        if (paciente) {
          botones.push(
            <button
              key="cancelar"
              className="btn btn-sm btn-danger"
              onClick={() => onCancelarTraslado(paciente.id)}
            >
              <X size={14} /> Cancelar
            </button>,
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(paciente)}
            >
              <Eye size={14} /> Ver
            </button>
          );
        }
        break;

      case EstadoCamaEnum.TRASLADO_CONFIRMADO:
        if (paciente) {
          botones.push(
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(paciente)}
            >
              <Eye size={14} /> Ver
            </button>,
            <button
              key="cancelar"
              className="btn btn-sm btn-danger"
              onClick={() => onCancelarTraslado(paciente.id)}
            >
              <X size={14} /> Cancelar
            </button>
          );
        }
        break;

      case EstadoCamaEnum.ALTA_SUGERIDA:
        if (paciente) {
          botones.push(
            <button
              key="iniciar-alta"
              className="btn btn-sm btn-primary"
              onClick={() => onIniciarAlta(paciente.id)}
            >
              <ArrowRight size={14} /> Iniciar alta
            </button>,
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(paciente)}
            >
              <Eye size={14} /> Ver
            </button>,
            <button
              key="reevaluar"
              className="btn btn-sm btn-secondary"
              onClick={() => onReevaluar(paciente)}
            >
              <FileText size={14} /> Reevaluar
            </button>
          );
        }
        break;

      case EstadoCamaEnum.CAMA_ALTA:
        if (paciente) {
          botones.push(
            <button
              key="dar-alta"
              className="btn btn-sm btn-success"
              onClick={() => onDarAlta(paciente.id)}
            >
              <LogOut size={14} /> Dar alta
            </button>,
            <button
              key="cancelar"
              className="btn btn-sm btn-danger"
              onClick={() => onCancelarAlta(paciente.id)}
            >
              <X size={14} /> Cancelar
            </button>
          );
        }
        break;

      case EstadoCamaEnum.BLOQUEADA:
        botones.push(
          <button
            key="desbloquear"
            className="btn btn-sm btn-secondary"
            onClick={() => onBloquear(cama.id, false)}
          >
            <Unlock size={14} /> Desbloquear
          </button>
        );
        break;

      case EstadoCamaEnum.ESPERA_DERIVACION:
        if (paciente) {
          botones.push(
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(paciente)}
            >
              <Eye size={14} /> Ver
            </button>,
            <button
              key="cancelar"
              className="btn btn-sm btn-danger"
              onClick={() => onCancelarTraslado(paciente.id)}
            >
              <X size={14} /> Cancelar
            </button>
          );
        }
        break;

      case EstadoCamaEnum.DERIVACION_CONFIRMADA:
        if (paciente) {
          botones.push(
            <button
              key="ver"
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(paciente)}
            >
              <Eye size={14} /> Ver
            </button>,
            <button
              key="confirmar-egreso"
              className="btn btn-sm btn-success"
              onClick={() => onConfirmarEgreso(paciente.id)}
            >
              <Check size={14} /> Confirmar egreso
            </button>,
            <button
              key="cancelar"
              className="btn btn-sm btn-danger"
              onClick={() => onCancelarTraslado(paciente.id)}
            >
              <X size={14} /> Cancelar
            </button>
          );
        }
        break;

      case EstadoCamaEnum.EN_LIMPIEZA:
        // Sin botones durante limpieza
        break;
    }

    return botones;
  };

  return (
    <div className={`cama-card cama-card-${cama.estado}`}>
      <div className="cama-card-id">{cama.identificador}</div>
      
      {paciente && (
        <div className="cama-card-paciente">
          {paciente.nombre}
        </div>
      )}
      
      <div className="cama-card-estado">
        {getEstadoTexto()}
        {cama.estado === EstadoCamaEnum.TRASLADO_CONFIRMADO && paciente?.cama_asignada && (
          <span style={{ display: 'block', marginTop: '4px', fontWeight: 500 }}>
            → {paciente.cama_asignada.identificador}
          </span>
        )}
      </div>
      
      <div className="cama-card-actions">
        {renderBotones()}
      </div>
    </div>
  );
}
