import React, { useEffect, useState, useCallback } from 'react';
import { FileText, Clock, MapPin, AlertCircle, CheckCircle, Download, XCircle, Loader } from 'lucide-react';
import type { Paciente, PrioridadExplicacion } from '../types/Index';
import * as api from '../services/api';

interface PacienteDetalleProps {
  paciente: Paciente;
  onReevaluar: () => void;
  onClose: () => void;
}


export function PacienteDetalle({ paciente, onReevaluar, onClose }: PacienteDetalleProps) {
  const [prioridad, setPrioridad] = useState<PrioridadExplicacion | null>(null);
  const [errorPrioridad, setErrorPrioridad] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Validación temprana del objeto paciente
  const pacienteValido = paciente && typeof paciente === 'object' && paciente.id;

  //  Función de parseo seguro de JSON (por si los requerimientos vienen como strings)
  const safeJsonParse = useCallback((value: unknown, defaultValue: unknown[] = []): unknown[] => {
    if (!value) return defaultValue;
    if (Array.isArray(value)) return value;
    if (typeof value === 'string') {
      try {
        const parsed = JSON.parse(value);
        return Array.isArray(parsed) ? parsed : defaultValue;
      } catch {
        return defaultValue;
      }
    }
    return defaultValue;
  }, []);

  // Obtener valores con fallbacks seguros
  const getNombre = useCallback(() => {
    return paciente?.nombre || 'Sin nombre';
  }, [paciente?.nombre]);

  const getRun = useCallback(() => {
    return paciente?.run || 'No disponible';
  }, [paciente?.run]);

  const getEdad = useCallback(() => {
    const edad = paciente?.edad;
    return typeof edad === 'number' ? edad : 0;
  }, [paciente?.edad]);

  const getSexo = useCallback(() => {
    return paciente?.sexo || 'No especificado';
  }, [paciente?.sexo]);

  // useEffect con manejo de errores robusto
  useEffect(() => {
    // No hacer nada si el paciente no es válido
    if (!pacienteValido) {
      console.warn('PacienteDetalle: paciente no válido', paciente);
      setError('Datos del paciente incompletos');
      return;
    }

    const cargarPrioridad = async () => {
      // Solo cargar prioridad si el paciente está en lista de espera
      const enListaEspera = paciente?.en_lista_espera === true || 
                            paciente?.estado_lista_espera === 'esperando' || 
                            paciente?.estado_lista_espera === 'buscando';
      
      if (!enListaEspera) {
        return;
      }

      setLoading(true);
      setErrorPrioridad(false);

      try {
        const data = await api.getPrioridadPaciente(paciente.id);
        setPrioridad(data);
      } catch (err) {
        console.error('Error cargando prioridad:', err);
        setErrorPrioridad(true);
        // No propagar el error, solo marcar que hubo un problema
      } finally {
        setLoading(false);
      }
    };

    cargarPrioridad();
  }, [paciente?.id, paciente?.en_lista_espera, paciente?.estado_lista_espera, pacienteValido]);

  // Si hay error de validación, mostrar mensaje y botón de cierre
  if (error || !pacienteValido) {
    return (
      <div className="paciente-detalle error-state">
        <div className="error-container">
          <XCircle size={48} className="error-icon" />
          <h3>No se pueden mostrar los datos</h3>
          <p>{error || 'Información del paciente no disponible'}</p>
          <button className="btn btn-secondary" onClick={onClose}>
            Cerrar
          </button>
        </div>
      </div>
    );
  }

  const formatFecha = (fecha: string | undefined | null) => {
    if (!fecha) return 'No disponible';
    try {
      return new Date(fecha).toLocaleString('es-CL', {
        dateStyle: 'medium',
        timeStyle: 'short'
      });
    } catch {
      return String(fecha);
    }
  };

  const getEdadCategoria = () => {
    const categoria = paciente?.edad_categoria;
    const edad = getEdad();
    
    if (!categoria) {
      // Calcular basado en edad
      if (edad < 15) return 'Pediátrico (0-14)';
      if (edad < 60) return 'Adulto (15-59)';
      return 'Adulto mayor (60+)';
    }
    switch (categoria) {
      case 'pediatrico': return 'Pediátrico (0-14)';
      case 'adulto': return 'Adulto (15-59)';
      case 'adulto_mayor': return 'Adulto mayor (60+)';
      default: return String(categoria);
    }
  };

  // Obtener complejidad del paciente (puede venir como complejidad o complejidad_requerida)
  const getComplejidad = () => {
    return paciente?.complejidad || paciente?.complejidad_requerida || 'ninguna';
  };

  const getComplejidadBadge = () => {
    const complejidad = getComplejidad();
    switch (complejidad) {
      case 'uci': return <span className="badge badge-danger">UCI</span>;
      case 'uti': return <span className="badge badge-warning">UTI</span>;
      case 'baja': return <span className="badge badge-info">Baja</span>;
      default: return <span className="badge badge-secondary">Sin requerimientos</span>;
    }
  };

  const getAislamientoBadge = () => {
    const tipoAislamiento = paciente?.tipo_aislamiento;
    if (!tipoAislamiento || tipoAislamiento === 'ninguno') return null;
    const colores: Record<string, string> = {
      contacto: 'badge-info',
      gotitas: 'badge-warning',
      aereo: 'badge-danger',
      ambiente_protegido: 'badge-purple',
      especial: 'badge-danger'
    };
    return (
      <span className={`badge ${colores[tipoAislamiento] || 'badge-secondary'}`}>
        Aislamiento: {tipoAislamiento.replace('_', ' ')}
      </span>
    );
  };

  // Verificar si está embarazada (backend usa es_embarazada, frontend puede usar embarazada)
  const estaEmbarazada = () => {
    return paciente?.es_embarazada === true || paciente?.embarazada === true;
  };

  const renderRequerimientos = () => {
    const reqs: string[] = [];
    
    // CORRECCIÓN: Usar safeJsonParse para manejar casos donde vienen como strings
    const reqsUci = safeJsonParse(paciente?.requerimientos_uci) as string[];
    const reqsUti = safeJsonParse(paciente?.requerimientos_uti) as string[];
    const reqsBaja = safeJsonParse(paciente?.requerimientos_baja) as string[];
    const reqsNoDefinen = safeJsonParse(paciente?.requerimientos_no_definen) as string[];

    // Primero, verificar si hay listas de requerimientos del backend
    if (reqsUci && reqsUci.length > 0) {
      reqsUci.forEach((r: string) => {
        switch(r) {
          case 'vmi': reqs.push('VMI'); break;
          case 'procuramiento_o2': reqs.push('Procuramiento O2'); break;
          default: reqs.push(r);
        }
      });
    }
    
    if (reqsUti && reqsUti.length > 0) {
      reqsUti.forEach((r: string) => {
        switch(r) {
          case 'drogas_vasoactivas': reqs.push('Drogas vasoactivas'); break;
          case 'sedacion': reqs.push('Sedación'); break;
          case 'monitorizacion': reqs.push(`Monitorización${paciente?.justificacion_observacion ? ` (${paciente.justificacion_observacion})` : ''}`); break;
          case 'o2_reservorio': reqs.push('O2 reservorio'); break;
          case 'dialisis': reqs.push('Diálisis'); break;
          case 'cnaf': reqs.push('CNAF'); break;
          case 'bic_insulina': reqs.push('BIC insulina'); break;
          case 'vmni': reqs.push('VMNI'); break;
          default: reqs.push(r);
        }
      });
    }
    
    if (reqsBaja && reqsBaja.length > 0) {
      reqsBaja.forEach((r: string) => {
        switch(r) {
          case 'tratamiento_ev_3x': reqs.push('Tratamiento EV 3+x/día'); break;
          case 'control_sangre_2x': reqs.push('Control sangre 2+x/día'); break;
          case 'o2_naricera': reqs.push('O2 naricera'); break;
          case 'dolor_eva_7': reqs.push('Dolor EVA ≥7'); break;
          case 'o2_multiventuri': reqs.push('O2 multiventuri'); break;
          case 'curaciones_complejas': reqs.push('Curaciones complejas'); break;
          case 'aspiracion': reqs.push('Aspiración'); break;
          case 'observacion': reqs.push(`Observación${paciente?.motivo_observacion ? ` (${paciente.motivo_observacion})` : ''}`); break;
          case 'irrigacion_vesical': reqs.push('Irrigación vesical'); break;
          case 'procedimiento_invasivo': reqs.push(`Procedimiento invasivo${paciente?.procedimiento_invasivo ? ` (${paciente.procedimiento_invasivo})` : ''}`); break;
          default: reqs.push(r);
        }
      });
    }
    
    if (reqsNoDefinen && reqsNoDefinen.length > 0) {
      reqsNoDefinen.forEach((r: string) => {
        switch(r) {
          case 'kinesioterapia': reqs.push('Kinesioterapia'); break;
          case 'control_sangre_1x': reqs.push('Control sangre 1x/día'); break;
          case 'curaciones': reqs.push('Curaciones'); break;
          case 'tratamiento_ev_2x': reqs.push('Tratamiento EV ≤2x/día'); break;
          default: reqs.push(r);
        }
      });
    }
    
    // Si no hay listas, verificar booleanos individuales (formato antiguo)
    if (reqs.length === 0) {
      // UCI
      if (paciente?.req_vmi) reqs.push('VMI');
      if (paciente?.req_procuramiento_o2) reqs.push('Procuramiento O2');
      
      // UTI
      if (paciente?.req_drogas_vasoactivas) reqs.push('Drogas vasoactivas');
      if (paciente?.req_sedacion) reqs.push('Sedación');
      if (paciente?.req_monitorizacion) {
        reqs.push(`Monitorización${paciente?.req_monitorizacion_motivo ? ` (${paciente.req_monitorizacion_motivo})` : ''}`);
      }
      if (paciente?.req_o2_reservorio) reqs.push('O2 reservorio');
      if (paciente?.req_dialisis) reqs.push('Diálisis');
      if (paciente?.req_cnaf) reqs.push('CNAF');
      if (paciente?.req_bic_insulina) reqs.push('BIC insulina');
      if (paciente?.req_vmni) reqs.push('VMNI');
      
      // Baja
      if (paciente?.req_tratamiento_ev_3x) reqs.push('Tratamiento EV 3+x/día');
      if (paciente?.req_control_sangre_2x) reqs.push('Control sangre 2+x/día');
      if (paciente?.req_o2_naricera) reqs.push('O2 naricera');
      if (paciente?.req_dolor_eva_7) reqs.push('Dolor EVA ≥7');
      if (paciente?.req_o2_multiventuri) reqs.push('O2 multiventuri');
      if (paciente?.req_curaciones_complejas) reqs.push('Curaciones complejas');
      if (paciente?.req_aspiracion) reqs.push('Aspiración');
      if (paciente?.req_observacion) {
        reqs.push(`Observación${paciente?.req_observacion_motivo ? ` (${paciente.req_observacion_motivo})` : ''}`);
      }
      if (paciente?.req_irrigacion_vesical) reqs.push('Irrigación vesical');
      if (paciente?.req_procedimiento_invasivo) {
        reqs.push(`Procedimiento invasivo${paciente?.req_procedimiento_invasivo_detalle ? ` (${paciente.req_procedimiento_invasivo_detalle})` : ''}`);
      }
      
      // No definen
      if (paciente?.req_kinesioterapia) reqs.push('Kinesioterapia');
      if (paciente?.req_control_sangre_1x) reqs.push('Control sangre 1x/día');
      if (paciente?.req_curaciones) reqs.push('Curaciones');
      if (paciente?.req_tratamiento_ev_2x) reqs.push('Tratamiento EV ≤2x/día');
    }
    
    return reqs.length > 0 ? reqs : ['Sin requerimientos especiales'];
  };

  // Obtener cama actual (puede venir como cama_id o cama_actual_id)
  const getCamaId = () => {
    return paciente?.cama_id || paciente?.cama_actual_id;
  };

  // Obtener casos especiales de forma segura
  const getCasosEspeciales = () => {
    return safeJsonParse(paciente?.casos_especiales) as string[];
  };

  // Verificar si hay casos especiales
  const tieneCasosEspeciales = () => {
    const casos = getCasosEspeciales();
    return paciente?.caso_socio_sanitario || 
           paciente?.caso_socio_judicial || 
           paciente?.caso_espera_cardiocirugia || 
           (casos && casos.length > 0);
  };

  return (
    <div className="paciente-detalle">
      {/* Indicador de carga */}
      {loading && (
        <div className="loading-overlay">
          <Loader className="spin" size={24} />
          <span>Cargando información...</span>
        </div>
      )}

      {/* Encabezado */}
      <div className="detalle-header">
        <div className="detalle-info-principal">
          <h2>{getNombre()}</h2>
          <p className="run">RUN: {getRun()}</p>
        </div>
        <div className="detalle-badges">
          {getComplejidadBadge()}
          {getAislamientoBadge()}
          {estaEmbarazada() && <span className="badge badge-pink">Embarazada</span>}
        </div>
      </div>

      {/* Información general */}
      <section className="detalle-section">
        <h3>Información General</h3>
        <div className="detalle-grid">
          <div className="detalle-item">
            <label>Edad</label>
            <span>{getEdad()} años ({getEdadCategoria()})</span>
          </div>
          <div className="detalle-item">
            <label>Sexo</label>
            <span>{getSexo() === 'hombre' ? 'Masculino' : getSexo() === 'mujer' ? 'Femenino' : getSexo()}</span>
          </div>
          <div className="detalle-item">
            <label>Tipo de paciente</label>
            <span>{paciente?.tipo_paciente || 'No especificado'}</span>
          </div>
          <div className="detalle-item">
            <label>Hospital</label>
            <span>{paciente?.hospital?.nombre || (paciente?.hospital_id ? `ID: ${paciente.hospital_id}` : 'No especificado')}</span>
          </div>
        </div>
      </section>

      {/* Información clínica */}
      <section className="detalle-section">
        <h3>Información Clínica</h3>
        <div className="detalle-grid">
          <div className="detalle-item full-width">
            <label>Diagnóstico</label>
            <p>{paciente?.diagnostico || 'No especificado'}</p>
          </div>
          <div className="detalle-item">
            <label>Tipo de enfermedad</label>
            <span>{paciente?.tipo_enfermedad || 'No especificado'}</span>
          </div>
          <div className="detalle-item">
            <label>Aislamiento</label>
            <span>
              {!paciente?.tipo_aislamiento || paciente?.tipo_aislamiento === 'ninguno' 
                ? 'No requiere' 
                : paciente.tipo_aislamiento.replace('_', ' ')}
            </span>
          </div>
          <div className="detalle-item">
            <label>Complejidad</label>
            <span>{getComplejidad().toUpperCase()}</span>
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
      {tieneCasosEspeciales() && (
        <section className="detalle-section">
          <h3>Casos Especiales</h3>
          <div className="casos-especiales">
            {/* Formato lista de strings */}
            {getCasosEspeciales().includes('socio_sanitario') && (
              <span className="badge badge-warning">Socio-sanitario</span>
            )}
            {getCasosEspeciales().includes('socio_judicial') && (
              <span className="badge badge-warning">Socio-judicial</span>
            )}
            {getCasosEspeciales().includes('espera_cardiocirugia') && (
              <span className="badge badge-warning">Espera cardiocirugía</span>
            )}
            {/* Formato booleanos */}
            {paciente?.caso_socio_sanitario && !getCasosEspeciales().includes('socio_sanitario') && (
              <span className="badge badge-warning">Socio-sanitario</span>
            )}
            {paciente?.caso_socio_judicial && !getCasosEspeciales().includes('socio_judicial') && (
              <span className="badge badge-warning">Socio-judicial</span>
            )}
            {paciente?.caso_espera_cardiocirugia && !getCasosEspeciales().includes('espera_cardiocirugia') && (
              <span className="badge badge-warning">Espera cardiocirugía</span>
            )}
          </div>
        </section>
      )}

      {/* Ubicación */}
      <section className="detalle-section">
        <h3><MapPin size={16} /> Ubicación</h3>
        {getCamaId() ? (
          <div className="ubicacion-info">
            <p><strong>Cama ID:</strong> {getCamaId()}</p>
            {paciente?.cama_actual?.identificador && (
              <p><strong>Identificador:</strong> {paciente.cama_actual.identificador}</p>
            )}
            {paciente?.cama_actual?.sala?.servicio && (
              <p><strong>Servicio:</strong> {paciente.cama_actual.sala.servicio.nombre}</p>
            )}
          </div>
        ) : paciente?.cama_destino_id ? (
          <div className="ubicacion-info pending">
            <AlertCircle size={16} />
            <p>Cama asignada: <strong>{paciente.cama_destino_id}</strong> (pendiente traslado)</p>
          </div>
        ) : (
          <p className="sin-ubicacion">Sin cama asignada - En lista de espera</p>
        )}
      </section>

      {/* Estado en lista de espera */}
      {(paciente?.en_lista_espera || paciente?.estado_lista_espera) && (
        <section className="detalle-section">
          <h3>Estado Lista de Espera</h3>
          <div className="detalle-grid">
            <div className="detalle-item">
              <label>Estado</label>
              <span className="badge badge-info">
                {paciente?.estado_lista_espera || 'En espera'}
              </span>
            </div>
            {paciente?.prioridad_calculada !== undefined && paciente?.prioridad_calculada !== null && (
              <div className="detalle-item">
                <label>Prioridad</label>
                <span>{Number(paciente.prioridad_calculada).toFixed(1)} pts</span>
              </div>
            )}
            {paciente?.tiempo_espera_min !== undefined && paciente?.tiempo_espera_min !== null && (
              <div className="detalle-item">
                <label>Tiempo en espera</label>
                <span>{paciente.tiempo_espera_min} min</span>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Prioridad detallada (si está en lista de espera) */}
      {prioridad && !errorPrioridad && (
        <section className="detalle-section">
          <h3>Desglose de Prioridad</h3>
          <div className="prioridad-info">
            <div className="prioridad-total">
              <span className="prioridad-numero">{prioridad.puntuacion_total}</span>
              <span className="prioridad-label">Puntos totales</span>
            </div>
            <div className="prioridad-desglose">
              <div className="desglose-item">
                <span>Tipo paciente ({prioridad.desglose?.tipo_paciente?.valor || 'N/A'})</span>
                <span>+{prioridad.desglose?.tipo_paciente?.puntos || 0}</span>
              </div>
              <div className="desglose-item">
                <span>Complejidad ({prioridad.desglose?.complejidad?.valor || 'N/A'})</span>
                <span>+{prioridad.desglose?.complejidad?.puntos || 0}</span>
              </div>
              <div className="desglose-item">
                <span>Tiempo espera ({prioridad.desglose?.tiempo_espera?.minutos || 0} min)</span>
                <span>+{prioridad.desglose?.tiempo_espera?.puntos || 0}</span>
              </div>
              {prioridad.desglose?.boosts?.map((boost, i) => (
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
      {(paciente?.derivacion_solicitada || paciente?.derivacion_estado) && (
        <section className="detalle-section">
          <h3>Derivación</h3>
          <div className="derivacion-info">
            <p><strong>Estado:</strong> {paciente?.derivacion_estado || 'Pendiente'}</p>
            {paciente?.derivacion_motivo && (
              <p><strong>Motivo:</strong> {paciente.derivacion_motivo}</p>
            )}
            {(paciente?.derivacion_rechazo_motivo || paciente?.derivacion_motivo_rechazo) && (
              <p className="rechazo"><strong>Motivo rechazo:</strong> {paciente?.derivacion_rechazo_motivo || paciente?.derivacion_motivo_rechazo}</p>
            )}
          </div>
        </section>
      )}

      {/* Notas adicionales */}
      {paciente?.notas_adicionales && (
        <section className="detalle-section">
          <h3>Notas Adicionales</h3>
          <p className="notas">{paciente.notas_adicionales}</p>
        </section>
      )}

      {/* Documento adjunto */}
      {paciente?.documento_adjunto && (
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
        {paciente?.created_at && (
          <div className="timestamp-item">
            <Clock size={14} />
            <span>Registrado: {formatFecha(paciente.created_at)}</span>
          </div>
        )}
        {paciente?.updated_at && (
          <div className="timestamp-item">
            <Clock size={14} />
            <span>Actualizado: {formatFecha(paciente.updated_at)}</span>
          </div>
        )}
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
