import React, { useState, useMemo, useEffect } from 'react';
import { Clock, Eye, X, Search, RefreshCw, Users, UserPlus, LogOut, ArrowLeft, Filter } from 'lucide-react';
import type { ListaEsperaItem, Paciente, Hospital, EstadoListaEsperaEnum } from '../types/Index';

interface ListaEsperaProps {
  items: ListaEsperaItem[];
  hospitalActual: Hospital | null;
  modoManual?: boolean;
  onVerPaciente: (paciente: Paciente) => void;
  onCancelarBusqueda: (pacienteId: string) => void;
  onRefresh: () => void;
  // Handlers para modo manual
  onAsignarManual?: (pacienteId: string) => void;
  onEgresarDeLista?: (pacienteId: string) => void;
}

export function ListaEspera({
  items,
  hospitalActual,
  modoManual = false,
  onVerPaciente,
  onCancelarBusqueda,
  onRefresh,
  onAsignarManual,
  onEgresarDeLista
}: ListaEsperaProps) {
  // Estados para filtros
  const [filtroOrigen, setFiltroOrigen] = useState<string>('todos');
  const [filtroDestino, setFiltroDestino] = useState<string>('todos');

  // 🔍 DIAGNÓSTICO: Ver qué datos llegan (solo una vez al montar y cuando cambian items)
  useEffect(() => {
    if (items.length > 0) {
      console.log('=== DIAGNÓSTICO LISTA ESPERA ===');
      console.log('Total items:', items.length);
      console.log('Primer item completo:', items[0]);
      console.log('Estructura del primer item:', {
        origen_tipo: items[0].origen_tipo,
        origen_servicio_nombre: items[0].origen_servicio_nombre,
        origen_hospital_nombre: items[0].origen_hospital_nombre,
        servicio_destino: items[0].servicio_destino,
        // Verificar si están en otros lugares
        paciente_origen_tipo: (items[0] as any).paciente?.origen_tipo,
        any_origen_tipo: (items[0] as any).tipo_origen,
      });
      console.log('================================');
    }
  }, [items]);

  if (!hospitalActual) {
    return (
      <div className="empty-state">
        <Users size={48} />
        <h2>Seleccione un hospital</h2>
        <p>Elija un hospital para ver su lista de espera</p>
      </div>
    );
  }

  /**
   * 🔧 FUNCIÓN AUXILIAR: Obtener valor de múltiples ubicaciones posibles
   */
  const obtenerValor = (item: any, ...campos: string[]) => {
    for (const campo of campos) {
      const valor = campo.split('.').reduce((obj, key) => obj?.[key], item);
      if (valor !== undefined && valor !== null) {
        return valor;
      }
    }
    return null;
  };

  // Obtener opciones únicas para filtros
  const opcionesOrigen = useMemo(() => {
    const origenes = new Set<string>();
    items.forEach(item => {
      // 🔧 Intentar obtener tipo de múltiples ubicaciones
      const tipo = obtenerValor(item, 'origen_tipo', 'tipo_origen', 'paciente.origen_tipo');
      const hospitalNombre = obtenerValor(item, 'origen_hospital_nombre', 'hospital_origen_nombre', 'paciente.origen_hospital_nombre');
      const servicioNombre = obtenerValor(item, 'origen_servicio_nombre', 'servicio_origen_nombre', 'paciente.origen_servicio_nombre');
      
      if (tipo === 'derivado' && hospitalNombre) {
        origenes.add(`derivado:${hospitalNombre}`);
      } else if (tipo === 'hospitalizado' && servicioNombre) {
        origenes.add(`hospitalizado:${servicioNombre}`);
      } else if (tipo === 'urgencia') {
        origenes.add('urgencia:Urgencia');
      } else if (tipo === 'ambulatorio') {
        origenes.add('ambulatorio:Ambulatorio');
      }
    });
    return Array.from(origenes).sort();
  }, [items]);

  const opcionesDestino = useMemo(() => {
    const destinos = new Set<string>();
    items.forEach(item => {
      const destino = obtenerValor(item, 'servicio_destino', 'destino_servicio', 'paciente.servicio_destino');
      if (destino) {
        destinos.add(destino);
      }
    });
    return Array.from(destinos).sort();
  }, [items]);

  // Filtrar items
  const itemsFiltrados = useMemo(() => {
    return items.filter(item => {
      // Filtro de origen
      if (filtroOrigen !== 'todos') {
        const [tipoFiltro, valorFiltro] = filtroOrigen.split(':');
        const tipo = obtenerValor(item, 'origen_tipo', 'tipo_origen', 'paciente.origen_tipo');
        
        if (tipoFiltro === 'derivado' && tipo === 'derivado') {
          const hospitalNombre = obtenerValor(item, 'origen_hospital_nombre', 'hospital_origen_nombre');
          if (hospitalNombre !== valorFiltro) return false;
        } else if (tipoFiltro === 'hospitalizado' && tipo === 'hospitalizado') {
          const servicioNombre = obtenerValor(item, 'origen_servicio_nombre', 'servicio_origen_nombre');
          if (servicioNombre !== valorFiltro) return false;
        } else if (tipoFiltro === 'urgencia' && tipo !== 'urgencia') {
          return false;
        } else if (tipoFiltro === 'ambulatorio' && tipo !== 'ambulatorio') {
          return false;
        } else if (tipo !== tipoFiltro) {
          return false;
        }
      }

      // Filtro de destino
      if (filtroDestino !== 'todos') {
        const destino = obtenerValor(item, 'servicio_destino', 'destino_servicio', 'paciente.servicio_destino');
        if (destino !== filtroDestino) return false;
      }

      return true;
    });
  }, [items, filtroOrigen, filtroDestino]);

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

  /**
   * Determina el tipo de paciente para mostrar etiqueta apropiada
   */
  const getTipoPacienteInfo = (item: ListaEsperaItem) => {
    const tipoPaciente = item.paciente?.tipo_paciente || '';
    const tieneCama = item.paciente?.cama_id || item.paciente?.cama_actual_id;
    const esDerivado = item.paciente?.derivacion_estado === 'aceptado' || tipoPaciente === 'derivado';
    const esPacienteNuevo = !tieneCama && !esDerivado && 
      (tipoPaciente === 'urgencia' || tipoPaciente === 'ambulatorio');
    
    return {
      esDerivado,
      esPacienteNuevo,
      esHospitalizado: tieneCama && !esDerivado,
      tipoPaciente
    };
  };

  const getTipoPacienteBadge = (item: ListaEsperaItem) => {
    const { esDerivado, esHospitalizado, tipoPaciente } = getTipoPacienteInfo(item);
    
    if (esDerivado) {
      return <span className="badge badge-purple" title="Paciente derivado de otro hospital">Derivado</span>;
    }
    if (esHospitalizado) {
      return <span className="badge badge-info" title="Paciente hospitalizado con cama actual">Hospitalizado</span>;
    }
    if (tipoPaciente === 'urgencia') {
      return <span className="badge badge-danger" title="Paciente de urgencias">Urgencia</span>;
    }
    if (tipoPaciente === 'ambulatorio') {
      return <span className="badge badge-warning" title="Paciente ambulatorio">Ambulatorio</span>;
    }
    return <span className="badge badge-secondary">{tipoPaciente || 'N/A'}</span>;
  };

  /**
   * 🔧 VERSIÓN MEJORADA: Renderiza la información de origen del paciente
   * Intenta obtener datos de múltiples ubicaciones posibles
   */
  const renderOrigen = (item: ListaEsperaItem) => {
    const tipo = obtenerValor(item, 'origen_tipo', 'tipo_origen', 'paciente.origen_tipo');
    const hospitalNombre = obtenerValor(item, 'origen_hospital_nombre', 'hospital_origen_nombre');
    const hospitalCodigo = obtenerValor(item, 'origen_hospital_codigo', 'hospital_origen_codigo');
    const servicioNombre = obtenerValor(item, 'origen_servicio_nombre', 'servicio_origen_nombre');
    const camaId = obtenerValor(item, 'origen_cama_identificador', 'cama_origen_identificador');
    
    if (tipo === 'derivado' && hospitalNombre) {
      return (
        <div className="origen-info">
          <span className="origen-label">Derivado desde:</span>
          <span className="origen-valor">{hospitalCodigo || hospitalNombre}</span>
          {servicioNombre && (
            <span className="origen-detalle">{servicioNombre}</span>
          )}
        </div>
      );
    }
    
    if (tipo === 'hospitalizado' && servicioNombre) {
      return (
        <div className="origen-info">
          <span className="origen-label">Desde:</span>
          <span className="origen-valor">{servicioNombre}</span>
          {camaId && (
            <span className="origen-detalle">Cama {camaId}</span>
          )}
        </div>
      );
    }
    
    if (tipo === 'urgencia') {
      return (
        <div className="origen-info">
          <span className="origen-valor urgencia">Urgencia</span>
        </div>
      );
    }
    
    if (tipo === 'ambulatorio') {
      return (
        <div className="origen-info">
          <span className="origen-valor ambulatorio">Ambulatorio</span>
        </div>
      );
    }
    
    // Si no hay tipo definido, mostrar N/A con información de debug
    return (
      <span className="origen-info origen-desconocido" title={`Debug: tipo=${tipo || 'undefined'}`}>
        N/A
      </span>
    );
  };

  /**
   * 🔧 VERSIÓN MEJORADA: Renderiza el servicio destino
   */
  const renderDestino = (item: ListaEsperaItem) => {
    const destino = obtenerValor(item, 'servicio_destino', 'destino_servicio', 'paciente.servicio_destino');
    
    if (destino) {
      return (
        <span className="servicio-destino badge badge-primary">
          {destino}
        </span>
      );
    }
    
    return (
      <span className="servicio-destino badge badge-secondary">
        N/A
      </span>
    );
  };

  /**
   * Obtiene el texto y estilo del botón de cancelar según el tipo de paciente
   */
  const getBotonCancelarInfo = (item: ListaEsperaItem) => {
    const { esDerivado, esPacienteNuevo, esHospitalizado } = getTipoPacienteInfo(item);
    
    if (esPacienteNuevo) {
      return {
        texto: 'Eliminar',
        icono: <X size={14} />,
        titulo: 'Eliminar paciente del sistema',
        requiereConfirmacion: true,
        mensajeConfirmacion: `¿Está seguro de eliminar al paciente ${item.paciente?.nombre || item.nombre}? Esta acción no se puede deshacer.`
      };
    }
    if (esDerivado) {
      return {
        texto: 'Devolver',
        icono: <ArrowLeft size={14} />,
        titulo: 'Devolver a lista de derivación',
        requiereConfirmacion: false,
        mensajeConfirmacion: ''
      };
    }
    // Hospitalizado
    return {
      texto: 'Cancelar',
      icono: <LogOut size={14} />,
      titulo: 'Cancelar búsqueda - paciente vuelve a su cama',
      requiereConfirmacion: false,
      mensajeConfirmacion: ''
    };
  };

  /**
   * Handler para el botón de cancelar/egresar
   */
  const handleCancelar = (item: ListaEsperaItem) => {
    const pacienteId = item.paciente?.id || item.paciente_id || '';
    const botonInfo = getBotonCancelarInfo(item);
    
    if (botonInfo.requiereConfirmacion) {
      if (window.confirm(botonInfo.mensajeConfirmacion)) {
        if (modoManual && onEgresarDeLista) {
          onEgresarDeLista(pacienteId);
        } else {
          onCancelarBusqueda(pacienteId);
        }
      }
    } else {
      if (modoManual && onEgresarDeLista) {
        onEgresarDeLista(pacienteId);
      } else {
        onCancelarBusqueda(pacienteId);
      }
    }
  };

  /**
   * Renderiza acciones según el modo y tipo de paciente
   */
  const renderAcciones = (item: ListaEsperaItem) => {
    const pacienteId = item.paciente?.id || item.paciente_id || '';
    const botonInfo = getBotonCancelarInfo(item);
    
    if (modoManual) {
      const estado = item.estado || item.estado_lista || 'esperando';
      
      return (
        <>
          {estado !== 'asignado' && (
            <button
              className="btn btn-sm btn-primary"
              onClick={() => onAsignarManual?.(pacienteId)}
              title="Asignar cama manualmente"
            >
              <UserPlus size={14} /> Asignar
            </button>
          )}
          
          <button
            className="btn btn-sm btn-danger"
            onClick={() => handleCancelar(item)}
            title={botonInfo.titulo}
          >
            {botonInfo.icono} {botonInfo.texto}
          </button>
          
          {item.paciente && (
            <button
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(item.paciente)}
              title="Ver detalle"
            >
              <Eye size={14} /> Ver
            </button>
          )}
        </>
      );
    } else {
      return (
        <>
          {item.paciente && (
            <button
              className="btn btn-sm btn-secondary"
              onClick={() => onVerPaciente(item.paciente)}
              title="Ver detalle"
            >
              <Eye size={14} />
            </button>
          )}
          
          <button
            className="btn btn-sm btn-danger"
            onClick={() => handleCancelar(item)}
            title={botonInfo.titulo}
          >
            <X size={14} />
          </button>
        </>
      );
    }
  };

  /**
   * Limpiar filtros
   */
  const limpiarFiltros = () => {
    setFiltroOrigen('todos');
    setFiltroDestino('todos');
  };

  const hayFiltrosActivos = filtroOrigen !== 'todos' || filtroDestino !== 'todos';

  return (
    <div className={`lista-espera-container${modoManual ? ' modo-manual' : ''}`}>
      <div className="lista-header">
        <div className="lista-titulo">
          <Users size={24} />
          <h2>Lista de Búsqueda de Cama</h2>
          <span className="badge badge-primary">{itemsFiltrados.length} de {items.length} pacientes</span>
          {modoManual && (
            <span className="badge badge-warning" style={{ marginLeft: '8px' }}>
              MODO MANUAL
            </span>
          )}
        </div>
        <button className="btn btn-secondary btn-sm" onClick={onRefresh}>
          <RefreshCw size={16} /> Actualizar
        </button>
      </div>

      {/* FILTROS */}
      <div className="lista-filtros">
        <div className="filtro-grupo">
          <Filter size={16} />
          <label htmlFor="filtro-origen">Origen:</label>
          <select
            id="filtro-origen"
            value={filtroOrigen}
            onChange={(e) => setFiltroOrigen(e.target.value)}
            className="filtro-select"
          >
            <option value="todos">Todos los orígenes</option>
            {opcionesOrigen.map(opcion => {
              const [tipo, valor] = opcion.split(':');
              let label = valor;
              if (tipo === 'derivado') label = `Derivado: ${valor}`;
              if (tipo === 'hospitalizado') label = `Servicio: ${valor}`;
              return (
                <option key={opcion} value={opcion}>
                  {label}
                </option>
              );
            })}
          </select>
        </div>

        <div className="filtro-grupo">
          <Filter size={16} />
          <label htmlFor="filtro-destino">Destino:</label>
          <select
            id="filtro-destino"
            value={filtroDestino}
            onChange={(e) => setFiltroDestino(e.target.value)}
            className="filtro-select"
          >
            <option value="todos">Todos los destinos</option>
            {opcionesDestino.map(destino => (
              <option key={destino} value={destino}>
                {destino}
              </option>
            ))}
          </select>
        </div>

        {hayFiltrosActivos && (
          <button
            className="btn btn-sm btn-secondary"
            onClick={limpiarFiltros}
            title="Limpiar filtros"
          >
            <X size={14} /> Limpiar
          </button>
        )}
      </div>

      {itemsFiltrados.length === 0 && items.length > 0 ? (
        <div className="empty-state">
          <Search size={48} />
          <h3>Sin resultados</h3>
          <p>No hay pacientes que coincidan con los filtros seleccionados</p>
          <button className="btn btn-primary" onClick={limpiarFiltros}>
            Limpiar filtros
          </button>
        </div>
      ) : itemsFiltrados.length === 0 ? (
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
                <th>Tipo</th>
                <th>Origen</th>
                <th>Destino</th>
                <th>Complejidad</th>
                <th>Tiempo espera</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {itemsFiltrados.map((item, index) => {
                const { esHospitalizado, esDerivado } = getTipoPacienteInfo(item);
                return (
                  <tr 
                    key={item.paciente?.id || item.paciente_id || index} 
                    className={`estado-${item.estado || item.estado_lista}${esHospitalizado ? ' tiene-cama' : ''}${esDerivado ? ' es-derivado' : ''}`}
                  >
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
                      {getTipoPacienteBadge(item)}
                    </td>
                    <td className="origen-cell">
                      {renderOrigen(item)}
                    </td>
                    <td className="destino-cell">
                      {renderDestino(item)}
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
                      {renderAcciones(item)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="lista-footer">
        {modoManual ? (
          <>
            <p className="lista-info lista-info-manual">
              <UserPlus size={14} />
              Use "Asignar" para asignar manualmente una cama a cada paciente
            </p>
            <p className="lista-info">
              <LogOut size={14} />
              "Cancelar" para hospitalizados, "Devolver" para derivados, "Eliminar" para nuevos
            </p>
          </>
        ) : (
          <>
            <p className="lista-info">
              <Clock size={14} />
              La lista se actualiza automáticamente cada 5 segundos
            </p>
            <p className="lista-info">
              <Search size={14} />
              Los pacientes se ordenan por prioridad (mayor puntuación = mayor prioridad)
            </p>
          </>
        )}
      </div>
    </div>
  );
}
