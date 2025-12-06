import React, { useEffect, useState } from 'react';
import { FileText, Clock, MapPin, AlertCircle, CheckCircle, Download } from 'lucide-react';
import type { Paciente, PrioridadExplicacion } from '../types/Index';
import * as api from '../services/api';

interface PacienteDetalleProps {
  paciente: Paciente;
  onReevaluar: () => void;
  onClose: () => void;
}

export function PacienteDetalle({ paciente, onReevaluar, onClose }: PacienteDetalleProps) {
  const [prioridad, setPrioridad] = useState<PrioridadExplicacion | null>(null);

  useEffect(() => {
    if (paciente.estado_lista_espera) {
      api.getPrioridadPaciente(paciente.id)
        .then(setPrioridad)
        .catch(console.error);
    }
  }, [paciente.id, paciente.estado_lista_espera]);

  const formatFecha = (fecha: string) => {
    return new Date(fecha).toLocaleString('es-CL', {
      dateStyle: 'medium',
      timeStyle: 'short'
    });
  };

  const getEdadCategoria = () => {
    switch (paciente.edad_categoria) {
      case 'pediatrico': return 'Pediátrico (0-14)';
      case 'adulto': return 'Adulto (15-59)';
      case 'adulto_mayor': return 'Adulto mayor (60+)';
      default: return paciente.edad_categoria;
    }
  };

  const getComplejidadBadge = () => {
    switch (paciente.complejidad) {
      case 'uci': return <span className="badge badge-danger">UCI</span>;
      case 'uti': return <span className="badge badge-warning">UTI</span>;
      case 'baja': return <span className="badge badge-info">Baja</span>;
      default: return <span className="badge badge-secondary">Sin requerimientos</span>;
    }
  };

  const getAislamientoBadge = () => {
    if (paciente.tipo_aislamiento === 'ninguno') return null;
    const colores: Record<string, string> = {
      contacto: 'badge-info',
      gotitas: 'badge-warning',
      aereo: 'badge-danger',
      ambiente_protegido: 'badge-purple',
      especial: 'badge-danger'
    };
    return (
      <span className={`badge ${colores[paciente.tipo_aislamiento] || 'badge-secondary'}`}>
        Aislamiento: {paciente.tipo_aislamiento.replace('_', ' ')}
      </span>
    );
  };

  const renderRequerimientos = () => {
    const reqs: string[] = [];
    
    // UCI
    if (paciente.req_vmi) reqs.push('VMI');
    if (paciente.req_procuramiento_o2) reqs.push('Procuramiento O2');
    
    // UTI
    if (paciente.req_drogas_vasoactivas) reqs.push('Drogas vasoactivas');
    if (paciente.req_sedacion) reqs.push('Sedación');
    if (paciente.req_monitorizacion) reqs.push(`Monitorización${paciente.req_monitorizacion_motivo ? ` (${paciente.req_monitorizacion_motivo})` : ''}`);
    if (paciente.req_o2_reservorio) reqs.push('O2 reservorio');
    if (paciente.req_dialisis) reqs.push('Diálisis');
    if (paciente.req_cnaf) reqs.push('CNAF');
    if (paciente.req_bic_insulina) reqs.push('BIC insulina');
    if (paciente.req_vmni) reqs.push('VMNI');
    
    // Baja
    if (paciente.req_tratamiento_ev_3x) reqs.push('Tratamiento EV 3+x/día');
    if (paciente.req_control_sangre_2x) reqs.push('Control sangre 2+x/día');
    if (paciente.req_o2_naricera) reqs.push('O2 naricera');
    if (paciente.req_dolor_eva_7) reqs.push('Dolor EVA ≥7');
    if (paciente.req_o2_multiventuri) reqs.push('O2 multiventuri');
    if (paciente.req_curaciones_complejas) reqs.push('Curaciones complejas');
    if (paciente.req_aspiracion) reqs.push('Aspiración');
    if (paciente.req_observacion) reqs.push(`Observación${paciente.req_observacion_motivo ? ` (${paciente.req_observacion_motivo})` : ''}`);
    if (paciente.req_irrigacion_vesical) reqs.push('Irrigación vesical');
    if (paciente.req_procedimiento_invasivo) reqs.push(`Procedimiento invasivo${paciente.req_procedimiento_invasivo_detalle ? ` (${paciente.req_procedimiento_invasivo_detalle})` : ''}`);
    
    // No definen
    if (paciente.req_kinesioterapia) reqs.push('Kinesioterapia');
    if (paciente.req_control_sangre_1x) reqs.push('Control sangre 1x/día');
    if (paciente.req_curaciones) reqs.push('Curaciones');
    if (paciente.req_tratamiento_ev_2x) reqs.push('Tratamiento EV ≤2x/día');
    
    return reqs.length > 0 ? reqs : ['Sin requerimientos especiales'];
  };

  return (
    <div className="paciente-detalle">
      {/* Encabezado */}
      <div className="detalle-header">
        <div className="detalle-info-principal">
          <h2>{paciente.nombre}</h2>
          <p className="run">RUN: {paciente.run}</p>
        </div>
        <div className="detalle-badges">
          {getComplejidadBadge()}
          {getAislamientoBadge()}
          {paciente.embarazada && <span className="badge badge-pink">Embarazada</span>}
        </div>
      </div>

      {/* Información general */}
      <section className="detalle-section">
        <h3>Información General</h3>
        <div className="detalle-grid">
          <div className="detalle-item">
            <label>Edad</label>
            <span>{paciente.edad} años ({getEdadCategoria()})</span>
          </div>
          <div className="detalle-item">
            <label>Sexo</label>
            <span>{paciente.sexo === 'hombre' ? 'Masculino' : 'Femenino'}</span>
          </div>
          <div className="detalle-item">
            <label>Tipo de paciente</label>
            <span>{paciente.tipo_paciente}</span>
          </div>
          <div className="detalle-item">
            <label>Hospital</label>
            <span>{paciente.hospital?.nombre || `ID: ${paciente.hospital_id}`}</span>
          </div>
        </div>
      </section>

      {/* Información clínica */}
      <section className="detalle-section">
        <h3>Información Clínica</h3>
        <div className="detalle-grid">
          <div className="detalle-item full-width">
            <label>Diagnóstico</label>
            <p>{paciente.diagnostico}</p>
          </div>
          <div className="detalle-item">
            <label>Tipo de enfermedad</label>
            <span>{paciente.tipo_enfermedad}</span>
          </div>
          <div className="detalle-item">
            <label>Aislamiento</label>
            <span>{paciente.tipo_aislamiento === 'ninguno' ? 'No requiere' : paciente.tipo_aislamiento.replace('_', ' ')}</span>
          </div>
        </div>
      </section>

      {/* Requerimientos */}
      <section className="detalle-section">
        <h3>Requerimientos Clínicos</h3>
        <ul className="requerimientos-lista">
          {renderRequerimientos().map((req, i) => (
            <li key={i}>
              <CheckCircle size={14} className="icon-success" />
              {req}
            </li>
          ))}
        </ul>
      </section>

      {/* Casos especiales */}
      {(paciente.caso_socio_sanitario || paciente.caso_socio_judicial || paciente.caso_espera_cardiocirugia) && (
        <section className="detalle-section">
          <h3>Casos Especiales</h3>
          <div className="casos-especiales">
            {paciente.caso_socio_sanitario && (
              <span className="badge badge-warning">Socio-sanitario</span>
            )}
            {paciente.caso_socio_judicial && (
              <span className="badge badge-warning">Socio-judicial</span>
            )}
            {paciente.caso_espera_cardiocirugia && (
              <span className="badge badge-warning">Espera cardiocirugía</span>
            )}
          </div>
        </section>
      )}

      {/* Ubicación */}
      <section className="detalle-section">
        <h3><MapPin size={16} /> Ubicación</h3>
        {paciente.cama_actual ? (
          <div className="ubicacion-info">
            <p><strong>Cama:</strong> {paciente.cama_actual.identificador}</p>
            {paciente.cama_actual.sala?.servicio && (
              <p><strong>Servicio:</strong> {paciente.cama_actual.sala.servicio.nombre}</p>
            )}
            {paciente.cama_actual.sala && (
              <p><strong>Sala:</strong> {paciente.cama_actual.sala.nombre}</p>
            )}
          </div>
        ) : paciente.cama_asignada ? (
          <div className="ubicacion-info pending">
            <AlertCircle size={16} />
            <p>Cama asignada: <strong>{paciente.cama_asignada.identificador}</strong> (pendiente traslado)</p>
          </div>
        ) : (
          <p className="sin-ubicacion">Sin cama asignada - En lista de espera</p>
        )}
      </section>

      {/* Prioridad (si está en lista de espera) */}
      {prioridad && (
        <section className="detalle-section">
          <h3>Prioridad en Lista de Espera</h3>
          <div className="prioridad-info">
            <div className="prioridad-total">
              <span className="prioridad-numero">{prioridad.puntuacion_total}</span>
              <span className="prioridad-label">Puntos totales</span>
            </div>
            <div className="prioridad-desglose">
              <div className="desglose-item">
                <span>Tipo paciente ({prioridad.desglose.tipo_paciente.valor})</span>
                <span>+{prioridad.desglose.tipo_paciente.puntos}</span>
              </div>
              <div className="desglose-item">
                <span>Complejidad ({prioridad.desglose.complejidad.valor})</span>
                <span>+{prioridad.desglose.complejidad.puntos}</span>
              </div>
              <div className="desglose-item">
                <span>Tiempo espera ({prioridad.desglose.tiempo_espera.minutos} min)</span>
                <span>+{prioridad.desglose.tiempo_espera.puntos}</span>
              </div>
              {prioridad.desglose.boosts.map((boost, i) => (
                <div key={i} className="desglose-item boost">
                  <span>{boost.nombre}</span>
                  <span>+{boost.puntos}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Derivación */}
      {paciente.derivacion_solicitada && (
        <section className="detalle-section">
          <h3>Derivación</h3>
          <div className="derivacion-info">
            <p><strong>Estado:</strong> {paciente.derivacion_estado}</p>
            <p><strong>Motivo:</strong> {paciente.derivacion_motivo}</p>
            {paciente.derivacion_rechazo_motivo && (
              <p className="rechazo"><strong>Motivo rechazo:</strong> {paciente.derivacion_rechazo_motivo}</p>
            )}
          </div>
        </section>
      )}

      {/* Notas adicionales */}
      {paciente.notas_adicionales && (
        <section className="detalle-section">
          <h3>Notas Adicionales</h3>
          <p className="notas">{paciente.notas_adicionales}</p>
        </section>
      )}

      {/* Documento adjunto */}
      {paciente.documento_adjunto && (
        <section className="detalle-section">
          <h3>Documento Adjunto</h3>
          <a
            href={api.getDocumentoUrl(paciente.documento_adjunto)}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary"
          >
            <Download size={16} /> Ver documento
          </a>
        </section>
      )}

      {/* Timestamps */}
      <section className="detalle-section timestamps">
        <div className="timestamp-item">
          <Clock size={14} />
          <span>Registrado: {formatFecha(paciente.created_at)}</span>
        </div>
        <div className="timestamp-item">
          <Clock size={14} />
          <span>Actualizado: {formatFecha(paciente.updated_at)}</span>
        </div>
      </section>

      {/* Acciones */}
      <div className="detalle-actions">
        <button className="btn btn-secondary" onClick={onClose}>
          Cerrar
        </button>
        <button className="btn btn-primary" onClick={onReevaluar}>
          <FileText size={16} /> Reevaluar
        </button>
      </div>
    </div>
  );
}