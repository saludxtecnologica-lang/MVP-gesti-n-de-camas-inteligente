import React from 'react';
import { Clock, Eye, X, Search, RefreshCw, Users } from 'lucide-react';
import type { ListaEsperaItem, Paciente, Hospital, EstadoListaEsperaEnum } from '../types/Index';

interface ListaEsperaProps {
  items: ListaEsperaItem[];
  hospitalActual: Hospital | null;
  onVerPaciente: (paciente: Paciente) => void;
  onCancelarBusqueda: (pacienteId: string) => void;
  onRefresh: () => void;
}

export function ListaEspera({
  items,
  hospitalActual,
  onVerPaciente,
  onCancelarBusqueda,
  onRefresh
}: ListaEsperaProps) {
  if (!hospitalActual) {
    return (
      <div className="empty-state">
        <Users size={48} />
        <h2>Seleccione un hospital</h2>
        <p>Elija un hospital para ver su lista de espera</p>
      </div>
    );
  }

  const getEstadoBadge = (estado: EstadoListaEsperaEnum | string) => {
    switch (estado) {
      case 'esperando':
        return <span className="badge badge-warning">Esperando</span>;
      case 'buscando':
        return <span className="badge badge-info">Buscando cama</span>;
      case 'asignado':
        return <span className="badge badge-success">Cama asignada</span>;
      default:
        return <span className="badge badge-secondary">{estado}</span>;
    }
  };

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
    <div className="lista-espera-container">
      <div className="lista-header">
        <div className="lista-titulo">
          <Users size={24} />
          <h2>Lista de Búsqueda de Cama</h2>
          <span className="badge badge-primary">{items.length} pacientes</span>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={onRefresh}>
          <RefreshCw size={16} /> Actualizar
        </button>
      </div>

      {items.length === 0 ? (
        <div className="empty-state">
          <Search size={48} />
          <h3>Sin pacientes en espera</h3>
          <p>No hay pacientes buscando cama en este momento</p>
        </div>
      ) : (
        <div className="lista-tabla">
          <table>
            <thead>
              <tr>
                <th>Prioridad</th>
                <th>Paciente</th>
                <th>Complejidad</th>
                <th>Tiempo espera</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => (
                <tr key={item.paciente?.id || item.paciente_id || index} className={`estado-${item.estado || item.estado_lista}`}>
                  <td className="prioridad-cell">
                    <span className="prioridad-numero">{index + 1}</span>
                    <span className="prioridad-puntos">{item.prioridad} pts</span>
                  </td>
                  <td>
                    <div className="paciente-info">
                      <span className="paciente-nombre">{item.paciente?.nombre || item.nombre}</span>
                      <span className="paciente-run">{item.paciente?.run || item.run}</span>
                    </div>
                  </td>
                  <td>
                    <span className={`badge badge-complejidad-${item.paciente?.complejidad || 'ninguna'}`}>
                      {(item.paciente?.complejidad || 'ninguna').toUpperCase()}
                    </span>
                  </td>
                  <td className="tiempo-cell">
                    <Clock size={14} />
                    <span>{formatTiempoEspera(item.tiempo_espera_minutos || item.tiempo_espera_min || 0)}</span>
                  </td>
                  <td>{getEstadoBadge(item.estado || item.estado_lista || 'esperando')}</td>
                  <td className="acciones-cell">
                    {item.paciente && (
                      <button
                        className="btn btn-sm btn-secondary"
                        onClick={() => onVerPaciente(item.paciente)}
                        title="Ver detalle"
                      >
                        <Eye size={14} />
                      </button>
                    )}
                    {(item.estado || item.estado_lista) !== 'asignado' && (
                      <button
                        className="btn btn-sm btn-danger"
                        onClick={() => onCancelarBusqueda(item.paciente?.id || item.paciente_id || '')}
                        title="Cancelar búsqueda"
                      >
                        <X size={14} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="lista-footer">
        <p className="lista-info">
          <Clock size={14} />
          La lista se actualiza automáticamente cada 5 segundos
        </p>
        <p className="lista-info">
          <Search size={14} />
          Los pacientes se ordenan por prioridad (mayor puntuación = mayor prioridad)
        </p>
      </div>
    </div>
  );
}
