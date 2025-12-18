import React, { useState, useEffect } from 'react';
import { X, Search, Bed, Check, AlertCircle } from 'lucide-react';
import type { Cama, Paciente } from '../types/Index';
import { EstadoCamaEnum } from '../types/Index';
import * as api from '../services/api';

interface ModalAsignacionManualProps {
  isOpen: boolean;
  paciente: Paciente | null;
  hospitalId: string;
  onClose: () => void;
  onAsignar: (pacienteId: string, camaId: string) => Promise<void>;
  titulo?: string;
}

export function ModalAsignacionManual({
  isOpen,
  paciente,
  hospitalId,
  onClose,
  onAsignar,
  titulo = "Asignar Cama Manualmente"
}: ModalAsignacionManualProps) {
  const [camas, setCamas] = useState<Cama[]>([]);
  const [camaSeleccionada, setCamaSeleccionada] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingCamas, setLoadingCamas] = useState(false);
  const [filtroServicio, setFiltroServicio] = useState<string>('todos');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && hospitalId) {
      cargarCamasLibres();
    }
  }, [isOpen, hospitalId]);

  useEffect(() => {
    // Limpiar selección al cerrar
    if (!isOpen) {
      setCamaSeleccionada(null);
      setFiltroServicio('todos');
      setError(null);
    }
  }, [isOpen]);

  const cargarCamasLibres = async () => {
    setLoadingCamas(true);
    try {
      const todasLasCamas = await api.getCamasHospital(hospitalId);
      // Filtrar solo camas libres
      const camasLibres = todasLasCamas.filter(
        c => c.estado === EstadoCamaEnum.LIBRE
      );
      setCamas(camasLibres);
    } catch (err) {
      setError('Error al cargar camas disponibles');
      console.error(err);
    } finally {
      setLoadingCamas(false);
    }
  };

  const handleAsignar = async () => {
    if (!camaSeleccionada || !paciente) return;

    setLoading(true);
    setError(null);
    try {
      await onAsignar(paciente.id, camaSeleccionada);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al asignar cama');
    } finally {
      setLoading(false);
    }
  };

  // Obtener servicios únicos para filtro
  const serviciosUnicos = [...new Set(camas.map(c => c.servicio_nombre || 'Sin servicio'))];

  // Filtrar camas por servicio
  const camasFiltradas = filtroServicio === 'todos' 
    ? camas 
    : camas.filter(c => c.servicio_nombre === filtroServicio);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-container modal-lg">
        <div className="modal-header">
          <h2>
            <Bed size={24} />
            {titulo}
          </h2>
          <button className="btn-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {/* Información del paciente */}
          {paciente && (
            <div className="paciente-info-box">
              <h3>Paciente a asignar</h3>
              <div className="info-grid">
                <div className="info-item">
                  <span className="label">Nombre:</span>
                  <span className="value">{paciente.nombre}</span>
                </div>
                <div className="info-item">
                  <span className="label">RUN:</span>
                  <span className="value">{paciente.run}</span>
                </div>
                <div className="info-item">
                  <span className="label">Complejidad:</span>
                  <span className={`badge badge-complejidad-${paciente.complejidad_requerida || 'ninguna'}`}>
                    {(paciente.complejidad_requerida || 'ninguna').toUpperCase()}
                  </span>
                </div>
                <div className="info-item">
                  <span className="label">Tipo enfermedad:</span>
                  <span className="value">{paciente.tipo_enfermedad}</span>
                </div>
              </div>
              {paciente.cama_id && (
                <div className="warning-box">
                  <AlertCircle size={16} />
                  <span>El paciente tiene cama actual. Se creará un traslado.</span>
                </div>
              )}
            </div>
          )}

          {/* Filtro de servicio */}
          <div className="filtro-container">
            <label>Filtrar por servicio:</label>
            <select 
              value={filtroServicio} 
              onChange={(e) => setFiltroServicio(e.target.value)}
              className="select-filtro"
            >
              <option value="todos">Todos los servicios</option>
              {serviciosUnicos.map(servicio => (
                <option key={servicio} value={servicio}>{servicio}</option>
              ))}
            </select>
          </div>

          {/* Lista de camas */}
          {loadingCamas ? (
            <div className="loading-state">
              <div className="spinner" />
              <span>Cargando camas disponibles...</span>
            </div>
          ) : camasFiltradas.length === 0 ? (
            <div className="empty-state">
              <Search size={48} />
              <h3>No hay camas disponibles</h3>
              <p>No se encontraron camas libres en este hospital</p>
            </div>
          ) : (
            <div className="selector-cama-manual">
              {camasFiltradas.map(cama => (
                <div
                  key={cama.id}
                  className={`cama-opcion ${camaSeleccionada === cama.id ? 'seleccionada' : ''}`}
                  onClick={() => setCamaSeleccionada(cama.id)}
                >
                  <div className="cama-info">
                    <span className="cama-id">{cama.identificador}</span>
                    <span className="cama-servicio">
                      {cama.servicio_nombre} - {cama.servicio_tipo}
                    </span>
                    {cama.sala_es_individual && (
                      <span className="badge badge-info">Individual</span>
                    )}
                    {cama.sala_sexo_asignado && (
                      <span className="badge badge-secondary">
                        Sala {cama.sala_sexo_asignado}
                      </span>
                    )}
                  </div>
                  {camaSeleccionada === cama.id && (
                    <Check size={20} className="check-icon" />
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="error-box">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button 
            className="btn btn-secondary" 
            onClick={onClose}
            disabled={loading}
          >
            Cancelar
          </button>
          <button
            className="btn btn-primary"
            onClick={handleAsignar}
            disabled={!camaSeleccionada || loading}
          >
            {loading ? (
              <>
                <span className="spinner-sm" />
                Asignando...
              </>
            ) : (
              <>
                <Check size={16} />
                Asignar Cama
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}


