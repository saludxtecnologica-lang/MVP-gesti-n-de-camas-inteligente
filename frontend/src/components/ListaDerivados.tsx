import React from 'react';
import { Clock, Eye, Check, X, ArrowRightLeft, RefreshCw, Building2 } from 'lucide-react';
import type { DerivadoItem, Paciente, Hospital } from '../types/Index';

interface ListaDerivadosProps {
  items: DerivadoItem[];
  hospitalActual: Hospital | null;
  onVerPaciente: (paciente: Paciente) => void;
  onAceptar: (pacienteId: string) => void;
  onRechazar: (pacienteId: string) => void;
  onRefresh: () => void;
}

export function ListaDerivados({
  items,
  hospitalActual,
  onVerPaciente,
  onAceptar,
  onRechazar,
  onRefresh
}: ListaDerivadosProps) {
  if (!hospitalActual) {
    return (
      <div className="empty-state">
        <ArrowRightLeft size={48} />
        <h2>Seleccione un hospital</h2>
        <p>Elija un hospital para ver las derivaciones pendientes</p>
      </div>
    );
  }

  const formatTiempoEspera = (minutos: number) => {
    if (minutos < 60) {
      return `${minutos} min`;
    }
    const horas = Math.floor(minutos / 60);
    const mins = minutos % 60;
    if (horas < 24) {
      return `${horas}h ${mins}m`;
    }
    const dias = Math.floor(horas / 24);
    const hrs = horas % 24;
    return `${dias}d ${hrs}h`;
  };

  return (
    <div className="lista-derivados-container">
      <div className="lista-header">
        <div className="lista-titulo">
          <ArrowRightLeft size={24} />
          <h2>Derivaciones Pendientes</h2>
          <span className="badge badge-primary">{items.length} solicitudes</span>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={onRefresh}>
          <RefreshCw size={16} /> Actualizar
        </button>
      </div>

      {items.length === 0 ? (
        <div className="empty-state">
          <Check size={48} />
          <h3>Sin derivaciones pendientes</h3>
          <p>No hay solicitudes de derivación para este hospital</p>
        </div>
      ) : (
        <div className="derivados-grid">
          {items.map((item, index) => (
            <div key={item.paciente?.id || item.paciente_id || index} className="derivado-card">
              <div className="derivado-header">
                <span className="prioridad-badge">#{index + 1}</span>
                <span className="prioridad-puntos">{item.prioridad} pts</span>
              </div>
              
              <div className="derivado-paciente">
                <h3>{item.paciente?.nombre || item.nombre}</h3>
                <span className="run">{item.paciente?.run || item.run}</span>
              </div>

              <div className="derivado-origen">
                <Building2 size={14} />
                <span>Desde: <strong>{item.hospital_origen?.nombre || item.hospital_origen_nombre}</strong></span>
              </div>

              <div className="derivado-info">
                <div className="info-item">
                  <label>Complejidad</label>
                  <span className={`badge badge-complejidad-${item.paciente?.complejidad || 'ninguna'}`}>
                    {(item.paciente?.complejidad || 'ninguna').toUpperCase()}
                  </span>
                </div>
                <div className="info-item">
                  <label>Edad</label>
                  <span>{item.paciente?.edad || 'N/A'} años</span>
                </div>
                <div className="info-item">
                  <label>En lista</label>
                  <span className="tiempo">
                    <Clock size={12} />
                    {formatTiempoEspera(item.tiempo_en_lista_minutos || item.tiempo_en_lista_min || 0)}
                  </span>
                </div>
              </div>

              <div className="derivado-motivo">
                <label>Motivo de derivación:</label>
                <p>{item.motivo || item.motivo_derivacion}</p>
              </div>

              {item.paciente?.tipo_aislamiento && item.paciente.tipo_aislamiento !== 'ninguno' && (
                <div className="derivado-aislamiento">
                  <span className="badge badge-warning">
                    Aislamiento: {item.paciente.tipo_aislamiento.replace('_', ' ')}
                  </span>
                </div>
              )}

              <div className="derivado-actions">
                {item.paciente && (
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => onVerPaciente(item.paciente)}
                  >
                    <Eye size={14} /> Ver detalle
                  </button>
                )}
                <button
                  className="btn btn-sm btn-success"
                  onClick={() => onAceptar(item.paciente?.id || item.paciente_id || '')}
                >
                  <Check size={14} /> Aceptar
                </button>
                <button
                  className="btn btn-sm btn-danger"
                  onClick={() => onRechazar(item.paciente?.id || item.paciente_id || '')}
                >
                  <X size={14} /> Rechazar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="lista-footer">
        <p className="lista-info">
          <ArrowRightLeft size={14} />
          Las derivaciones se ordenan por prioridad clínica
        </p>
        <p className="lista-info">
          <Clock size={14} />
          Al aceptar, el paciente entrará a la lista de espera de este hospital
        </p>
      </div>
    </div>
  );
}
