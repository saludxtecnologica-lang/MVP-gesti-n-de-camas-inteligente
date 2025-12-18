import React, { useState, useEffect } from 'react';
import { X, ArrowLeftRight, Check, AlertCircle, User } from 'lucide-react';
import type { Cama, Paciente } from '../types/Index';
import { EstadoCamaEnum } from '../types/Index';
import * as api from '../services/api';

interface ModalIntercambioProps {
  isOpen: boolean;
  pacienteOrigen: Paciente | null;
  hospitalId: string;
  onClose: () => void;
  onIntercambiar: (pacienteAId: string, pacienteBId: string) => Promise<void>;
}

interface PacienteConCama {
  paciente: Paciente;
  cama: Cama;
}

export function ModalIntercambio({
  isOpen,
  pacienteOrigen,
  hospitalId,
  onClose,
  onIntercambiar
}: ModalIntercambioProps) {
  const [pacientesDisponibles, setPacientesDisponibles] = useState<PacienteConCama[]>([]);
  const [pacienteSeleccionado, setPacienteSeleccionado] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingPacientes, setLoadingPacientes] = useState(false);
  const [filtroServicio, setFiltroServicio] = useState<string>('todos');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && hospitalId) {
      cargarPacientesIntercambiables();
    }
  }, [isOpen, hospitalId]);

  useEffect(() => {
    if (!isOpen) {
      setPacienteSeleccionado(null);
      setFiltroServicio('todos');
      setError(null);
    }
  }, [isOpen]);

  const cargarPacientesIntercambiables = async () => {
    setLoadingPacientes(true);
    try {
      const camas = await api.getCamasHospital(hospitalId);
      
      // Filtrar camas con pacientes que pueden intercambiarse
      const estadosIntercambiables = [
        EstadoCamaEnum.OCUPADA,
        EstadoCamaEnum.CAMA_EN_ESPERA,
        EstadoCamaEnum.ALTA_SUGERIDA,
        EstadoCamaEnum.TRASLADO_SALIENTE
      ];
      
      const pacientesConCama: PacienteConCama[] = camas
        .filter(c => 
          estadosIntercambiables.includes(c.estado as EstadoCamaEnum) &&
          c.paciente &&
          c.paciente.id !== pacienteOrigen?.id // Excluir paciente origen
        )
        .map(c => ({
          paciente: c.paciente!,
          cama: c
        }));
      
      setPacientesDisponibles(pacientesConCama);
    } catch (err) {
      setError('Error al cargar pacientes disponibles');
      console.error(err);
    } finally {
      setLoadingPacientes(false);
    }
  };

  const handleIntercambiar = async () => {
    if (!pacienteSeleccionado || !pacienteOrigen) return;

    setLoading(true);
    setError(null);
    try {
      await onIntercambiar(pacienteOrigen.id, pacienteSeleccionado);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al intercambiar pacientes');
    } finally {
      setLoading(false);
    }
  };

  // Obtener servicios únicos
  const serviciosUnicos = [...new Set(pacientesDisponibles.map(p => p.cama.servicio_nombre || 'Sin servicio'))];

  // Filtrar por servicio
  const pacientesFiltrados = filtroServicio === 'todos'
    ? pacientesDisponibles
    : pacientesDisponibles.filter(p => p.cama.servicio_nombre === filtroServicio);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-container modal-lg">
        <div className="modal-header">
          <h2>
            <ArrowLeftRight size={24} />
            Intercambiar Pacientes
          </h2>
          <button className="btn-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {/* Información del paciente origen */}
          {pacienteOrigen && (
            <div className="paciente-info-box paciente-origen">
              <h3>
                <User size={16} />
                Paciente A (origen)
              </h3>
              <div className="info-grid">
                <div className="info-item">
                  <span className="label">Nombre:</span>
                  <span className="value">{pacienteOrigen.nombre}</span>
                </div>
                <div className="info-item">
                  <span className="label">RUN:</span>
                  <span className="value">{pacienteOrigen.run}</span>
                </div>
                <div className="info-item">
                  <span className="label">Complejidad:</span>
                  <span className={`badge badge-complejidad-${pacienteOrigen.complejidad_requerida || 'ninguna'}`}>
                    {(pacienteOrigen.complejidad_requerida || 'ninguna').toUpperCase()}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Indicador de intercambio */}
          <div className="intercambio-indicator">
            <ArrowLeftRight size={32} />
            <span>Seleccione el paciente B para intercambiar</span>
          </div>

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

          {/* Lista de pacientes disponibles */}
          {loadingPacientes ? (
            <div className="loading-state">
              <div className="spinner" />
              <span>Cargando pacientes...</span>
            </div>
          ) : pacientesFiltrados.length === 0 ? (
            <div className="empty-state">
              <User size={48} />
              <h3>No hay pacientes disponibles</h3>
              <p>No se encontraron otros pacientes con cama para intercambiar</p>
            </div>
          ) : (
            <div className="selector-paciente-intercambio">
              {pacientesFiltrados.map(({ paciente, cama }) => (
                <div
                  key={paciente.id}
                  className={`paciente-opcion ${pacienteSeleccionado === paciente.id ? 'seleccionado' : ''}`}
                  onClick={() => setPacienteSeleccionado(paciente.id)}
                >
                  <div className="paciente-info">
                    <div className="paciente-nombre-row">
                      <span className="paciente-nombre">{paciente.nombre}</span>
                      <span className="paciente-run">{paciente.run}</span>
                    </div>
                    <div className="paciente-cama-row">
                      <span className="cama-badge">
                        Cama: {cama.identificador}
                      </span>
                      <span className="servicio-badge">
                        {cama.servicio_nombre}
                      </span>
                      <span className={`badge badge-complejidad-${paciente.complejidad_requerida || 'ninguna'}`}>
                        {(paciente.complejidad_requerida || 'ninguna').toUpperCase()}
                      </span>
                    </div>
                  </div>
                  {pacienteSeleccionado === paciente.id && (
                    <Check size={20} className="check-icon" />
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Resumen del intercambio */}
          {pacienteSeleccionado && pacienteOrigen && (
            <div className="resumen-intercambio">
              <h4>Resumen del intercambio:</h4>
              <div className="resumen-row">
                <span className="resumen-paciente">{pacienteOrigen.nombre}</span>
                <ArrowLeftRight size={16} />
                <span className="resumen-paciente">
                  {pacientesFiltrados.find(p => p.paciente.id === pacienteSeleccionado)?.paciente.nombre}
                </span>
              </div>
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
            className="btn btn-warning"
            onClick={handleIntercambiar}
            disabled={!pacienteSeleccionado || loading}
          >
            {loading ? (
              <>
                <span className="spinner-sm" />
                Intercambiando...
              </>
            ) : (
              <>
                <ArrowLeftRight size={16} />
                Confirmar Intercambio
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

