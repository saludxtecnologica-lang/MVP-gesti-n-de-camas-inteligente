import React, { useState, useMemo } from 'react';
import { Clock, User, Search, X, FileText, AlertTriangle, Send, BedDouble, Trash2, RotateCcw, Plus } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { useModal } from '../context/ModalContext';
import { Badge, Spinner, Modal, Button } from '../components/common';
import { ModalDerivacionDirecta } from '../components/modales/ModalDerivacionDirecta';
import { 
  formatTiempoEspera, 
  formatComplejidad, 
  formatTipoPaciente 
} from '../utils';
import * as api from '../services/api';
import type { Paciente, Cama } from '../types';

export function ListaEspera() {
  const { listaEspera, loading, showAlert, recargarTodo, configuracion, camas } = useApp();
  const { openModal } = useModal();
  const [filtroOrigen, setFiltroOrigen] = useState<string>('todos');
  const [busqueda, setBusqueda] = useState('');
  
  // Estado para modal de confirmación (cancelar/eliminar)
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [pacienteSeleccionado, setPacienteSeleccionado] = useState<typeof listaEspera[0] | null>(null);
  const [accionPendiente, setAccionPendiente] = useState<'cancelar' | 'eliminar' | 'cancelar_asignacion' | null>(null);
  const [procesando, setProcesando] = useState(false);

  // Estado para modal de derivación
  const [showDerivacionModal, setShowDerivacionModal] = useState(false);
  const [pacienteDerivar, setPacienteDerivar] = useState<Paciente | null>(null);

  // ============================================
  // NUEVO: Estado para modal de asignación manual
  // ============================================
  const [showAsignacionModal, setShowAsignacionModal] = useState(false);
  const [pacienteAsignar, setPacienteAsignar] = useState<typeof listaEspera[0] | null>(null);
  const [busquedaCama, setBusquedaCama] = useState('');
  const [camaSeleccionada, setCamaSeleccionada] = useState<string | null>(null);

  const modoManual = configuracion?.modo_manual ?? false;

  // Obtener orígenes únicos
  const origenes = useMemo(() => {
    const origenesSet = new Set<string>();
    listaEspera.forEach(item => {
      if (item.origen_tipo) {
        origenesSet.add(item.origen_tipo);
      }
    });
    return Array.from(origenesSet);
  }, [listaEspera]);

  // Filtrar lista
  const listaFiltrada = useMemo(() => {
    let resultado = listaEspera;
    
    if (filtroOrigen !== 'todos') {
      resultado = resultado.filter(item => item.origen_tipo === filtroOrigen);
    }
    
    if (busqueda) {
      const termino = busqueda.toLowerCase();
      resultado = resultado.filter(item => 
        item.nombre?.toLowerCase().includes(termino) ||
        item.run?.toLowerCase().includes(termino) ||
        item.paciente?.nombre?.toLowerCase().includes(termino) ||
        item.paciente?.run?.toLowerCase().includes(termino)
      );
    }
    
    return resultado;
  }, [listaEspera, filtroOrigen, busqueda]);

  // ============================================
  // NUEVO: Filtrar camas libres para asignación manual
  // ============================================
  const camasLibresFiltradas = useMemo(() => {
    const libres = camas.filter(c => c.estado === 'libre');
    if (!busquedaCama) return libres;
    
    const termino = busquedaCama.toLowerCase();
    return libres.filter(c => 
      c.identificador?.toLowerCase().includes(termino) ||
      c.servicio_nombre?.toLowerCase().includes(termino)
    );
  }, [camas, busquedaCama]);

  // Helper para obtener información de cama destino
  const getCamaDestinoInfo = (item: typeof listaEspera[0]): { identificador: string; servicio: string } | null => {
    const camaDestinoId = item.paciente?.cama_destino_id;
    if (!camaDestinoId) return null;
    
    const camaDestino = camas.find(c => c.id === camaDestinoId);
    if (!camaDestino) return null;
    
    return {
      identificador: camaDestino.identificador,
      servicio: camaDestino.servicio_nombre || ''
    };
  };

  // Click en fila para ver paciente
  const handleRowClick = (item: typeof listaEspera[0]) => {
    if (item.paciente) {
      openModal('verPaciente', { paciente: item.paciente });
    }
  };

  const handleReevaluar = (item: typeof listaEspera[0], e: React.MouseEvent) => {
    e.stopPropagation(); // Evitar que se dispare el click de la fila
    if (item.paciente) {
      openModal('reevaluar', { paciente: item.paciente });
    }
  };

  const handleDerivar = (item: typeof listaEspera[0], e: React.MouseEvent) => {
    e.stopPropagation(); // Evitar que se dispare el click de la fila
    if (item.paciente) {
      setPacienteDerivar(item.paciente);
      setShowDerivacionModal(true);
    }
  };

  // Helper para determinar si es derivado (usando propiedades existentes)
  const esItemDerivado = (item: typeof listaEspera[0]): boolean => {
    return item.origen_tipo === 'derivado' || 
           item.paciente?.derivacion_estado === 'aceptada' ||
           String(item.paciente?.tipo_paciente) === 'derivado';
  };

  // Helper para determinar si tiene cama actual (cama de origen)
  const tieneCamaActual = (item: typeof listaEspera[0]): boolean => {
    return !!(item.paciente?.cama_id);
  };

  // ============================================
  // NUEVO: Helper para determinar si tiene cama destino asignada
  // ============================================
  const tieneCamaDestinoAsignada = (item: typeof listaEspera[0]): boolean => {
    return !!(item.paciente?.cama_destino_id) || item.estado_lista === 'asignado';
  };

  // ============================================
  // NUEVO: Helper para obtener tipo de paciente
  // ============================================
  const getTipoPaciente = (item: typeof listaEspera[0]): string => {
    // Primero verificar si es derivado
    if (esItemDerivado(item)) return 'derivado';

    // Luego verificar origen_tipo del item
    if (item.origen_tipo) return item.origen_tipo.toLowerCase();

    // Finalmente verificar tipo_paciente del paciente
    if (item.paciente?.tipo_paciente) {
      return String(item.paciente.tipo_paciente).toLowerCase();
    }

    // Si tiene cama de origen, probablemente es hospitalizado
    if (tieneCamaActual(item)) return 'hospitalizado';

    return 'urgencia'; // Default
  };

  // Helper para obtener complejidad (usando propiedades existentes)
  const getComplejidad = (item: typeof listaEspera[0]): string => {
    const comp = item.paciente?.complejidad_requerida || item.paciente?.complejidad;
    if (!comp) return 'ninguna';
    return String(comp);
  };

  // Helper para obtener servicio destino formateado
  const getServicioDestino = (item: typeof listaEspera[0]): string | null => {
    // Primero intentar con servicio_destino del item
    if (item.servicio_destino) {
      return item.servicio_destino;
    }
    // Luego intentar con el paciente
    if (item.paciente?.servicio_destino) {
      return item.paciente.servicio_destino;
    }
    // Inferir del complejidad requerida
    const complejidad = getComplejidad(item);
    if (complejidad === 'alta' || complejidad === 'uci') return 'UCI';
    if (complejidad === 'media' || complejidad === 'uti') return 'UTI';
    if (complejidad === 'baja') return 'Medicina';
    return null;
  };

  // Mostrar modal de confirmación para CANCELAR (volver a cama)
  const handleMostrarCancelar = (item: typeof listaEspera[0], e: React.MouseEvent) => {
    e.stopPropagation();
    setPacienteSeleccionado(item);
    setAccionPendiente('cancelar');
    setShowConfirmModal(true);
  };

  // Mostrar modal de confirmación para ELIMINAR (sin cama)
  const handleMostrarEliminar = (item: typeof listaEspera[0], e: React.MouseEvent) => {
    e.stopPropagation();
    setPacienteSeleccionado(item);
    setAccionPendiente('eliminar');
    setShowConfirmModal(true);
  };

  // ============================================
  // NUEVO: Mostrar modal para cancelar asignación (liberar cama destino)
  // ============================================
  const handleMostrarCancelarAsignacion = (item: typeof listaEspera[0], e: React.MouseEvent) => {
    e.stopPropagation();
    setPacienteSeleccionado(item);
    setAccionPendiente('cancelar_asignacion');
    setShowConfirmModal(true);
  };

  // ============================================
  // NUEVO: Abrir modal de asignación manual
  // ============================================
  const handleAbrirAsignacionManual = (item: typeof listaEspera[0], e: React.MouseEvent) => {
    e.stopPropagation();
    setPacienteAsignar(item);
    setBusquedaCama('');
    setCamaSeleccionada(null);
    setShowAsignacionModal(true);
  };

  // ============================================
  // NUEVO: Ejecutar asignación manual de cama
  // ============================================
  const handleConfirmarAsignacion = async () => {
    if (!pacienteAsignar || !camaSeleccionada) return;
    
    const pacienteId = pacienteAsignar.paciente_id || pacienteAsignar.paciente?.id || '';
    
    try {
      setProcesando(true);
      const result = await api.asignarManualDesdeLista(pacienteId, camaSeleccionada);
      showAlert('success', result.message || 'Cama asignada correctamente');
      setShowAsignacionModal(false);
      setPacienteAsignar(null);
      setCamaSeleccionada(null);
      await recargarTodo();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al asignar cama');
    } finally {
      setProcesando(false);
    }
  };

  // Obtener mensaje descriptivo según acción
  const getMensajeConfirmacion = (): { titulo: string; mensaje: string } => {
    if (!pacienteSeleccionado || !accionPendiente) {
      return { titulo: '', mensaje: '' };
    }
    
    const esDerivado = esItemDerivado(pacienteSeleccionado);
    const tieneCamaDestino = tieneCamaDestinoAsignada(pacienteSeleccionado);
    const tieneCamaOrigen = tieneCamaActual(pacienteSeleccionado);
    
    if (accionPendiente === 'cancelar') {
      if (esDerivado) {
        return {
          titulo: '¿Cancelar búsqueda y volver al estado previo?',
          mensaje: 'El paciente volverá a la lista de "Derivados Pendientes" donde podrá ser aceptado o rechazado nuevamente.'
        };
      }
      return {
        titulo: '¿Cancelar búsqueda y volver a la cama?',
        mensaje: 'El paciente volverá a su cama actual con estado "Ocupada". Podrá iniciar una nueva búsqueda de cama cuando lo requiera.'
      };
    }
    
    if (accionPendiente === 'cancelar_asignacion') {
      if (tieneCamaOrigen) {
        return {
          titulo: '¿Cancelar la asignación de cama?',
          mensaje: 'La cama destino quedará libre. El paciente permanecerá en la lista de espera y su cama de origen quedará en estado "Traslado Saliente" para continuar buscando otra cama.'
        };
      }
      return {
        titulo: '¿Cancelar la asignación de cama?',
        mensaje: 'La cama destino quedará libre. El paciente permanecerá en la lista de espera y podrá ser reevaluado o derivado si es necesario.'
      };
    }
    
    // accionPendiente === 'eliminar'
    return {
      titulo: '¿Eliminar paciente del sistema?',
      mensaje: 'El paciente será eliminado completamente de la lista de espera y del sistema. Esta acción no se puede deshacer. Si es necesario, deberá ser registrado nuevamente.'
    };
  };

  // Confirmar acción
  const handleConfirmarAccion = async () => {
    if (!pacienteSeleccionado || !accionPendiente) return;
    
    const pacienteId = pacienteSeleccionado.paciente_id || pacienteSeleccionado.paciente?.id || '';
    const scrollPosition = window.scrollY;
    
    try {
      setProcesando(true);
      
      let result;
      if (accionPendiente === 'cancelar') {
        // Llamar endpoint para cancelar y volver a cama
        result = await api.cancelarYVolverACama(pacienteId);
      } else if (accionPendiente === 'cancelar_asignacion') {
        // NUEVO: Llamar endpoint para cancelar asignación pero mantener en lista
        result = await api.cancelarAsignacionDesdeLista(pacienteId);
      } else {
        // Llamar endpoint para eliminar paciente sin cama
        result = await api.eliminarPacienteSinCama(pacienteId);
      }
      
      const mensajeExito = accionPendiente === 'cancelar' 
        ? 'Búsqueda cancelada' 
        : accionPendiente === 'cancelar_asignacion'
        ? 'Asignación cancelada - paciente en lista de espera'
        : 'Paciente eliminado';
      
      showAlert('success', result.message || mensajeExito);
      setShowConfirmModal(false);
      setPacienteSeleccionado(null);
      setAccionPendiente(null);
      await recargarTodo();
      
      requestAnimationFrame(() => {
        window.scrollTo(0, scrollPosition);
      });
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al procesar');
    } finally {
      setProcesando(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  const { titulo: tituloConfirmacion, mensaje: mensajeConfirmacion } = getMensajeConfirmacion();

  return (
    <div className="space-y-4">
      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-semibold text-gray-800">
              Lista de Espera
              <span className="ml-2 text-sm font-normal text-gray-500">
                ({listaFiltrada.length} pacientes)
              </span>
            </h2>
            
            {/* Filtro origen */}
            <select
              value={filtroOrigen}
              onChange={(e) => setFiltroOrigen(e.target.value)}
              className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500"
            >
              <option value="todos">Todos los orígenes</option>
              {origenes.map(origen => (
                <option key={origen} value={origen}>
                  {formatTipoPaciente(origen)}
                </option>
              ))}
            </select>
          </div>

          {/* Búsqueda */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por nombre o RUN..."
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              className="pl-10 pr-4 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 w-64"
            />
            {busqueda && (
              <button
                onClick={() => setBusqueda('')}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Lista */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Pos
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Paciente
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Origen
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Destino
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Complejidad
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Prioridad
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Tiempo
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Estado
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Acciones
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {listaFiltrada.map((item, index) => {
              const paciente = item.paciente;
              const esDerivado = esItemDerivado(item);
              const tieneCamaOrigen = tieneCamaActual(item);
              const tieneCamaDestino = tieneCamaDestinoAsignada(item);
              const complejidad = getComplejidad(item);
              const servicioDestino = getServicioDestino(item);
              const camaDestinoInfo = getCamaDestinoInfo(item);
              const esAsignado = item.estado_lista === 'asignado';
              const tipoPaciente = getTipoPaciente(item);

              // ============================================
              // LÓGICA DE BOTONES OPTIMIZADA:
              // - Reevaluar/Derivar: Solo si NO tiene cama destino asignada
              // - Asignar cama (modo manual): Solo si NO tiene cama destino Y modo manual activo
              // - Cancelar asignación: Solo si TIENE cama destino asignada
              // - Cancelar/Volver:
              //   * Para HOSPITALIZADO: Solo si tiene cama origen y vuelve a su cama
              //   * Para DERIVADO: Siempre disponible (vuelve a lista de derivados pendientes)
              // - Eliminar: Solo para URGENCIA/AMBULATORIO sin cama origen ni destino
              // ============================================
              const puedeReevaluarDerivar = !tieneCamaDestino;
              const puedeAsignarCamaManual = modoManual && !tieneCamaDestino;
              const puedeCancelarAsignacion = tieneCamaDestino;

              // CORREGIDO: Cancelar para:
              // - Pacientes con cama origen (hospitalizados)
              // - Pacientes derivados (pueden no tener cama_id pero sí deben poder cancelar)
              const puedeCancelarVolver = (tieneCamaOrigen || esDerivado) && !tieneCamaDestino;

              // Eliminar solo para urgencia/ambulatorio sin cama origen ni destino
              const esUrgenciaOAmbulatorio = tipoPaciente === 'urgencia' || tipoPaciente === 'ambulatorio';
              const puedeEliminar = esUrgenciaOAmbulatorio && !tieneCamaOrigen && !tieneCamaDestino;
              
              return (
                <tr 
                  key={item.paciente_id || paciente?.id} 
                  className="hover:bg-blue-50 cursor-pointer transition-colors"
                  onClick={() => handleRowClick(item)}
                >
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="text-sm font-medium text-gray-900">
                      #{item.posicion || index + 1}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center">
                      <User className="w-8 h-8 text-gray-400 mr-3" />
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {item.nombre || paciente?.nombre}
                        </p>
                        <p className="text-xs text-gray-500">
                          {item.run || paciente?.run}
                        </p>
                      </div>
                    </div>
                  </td>
                  {/* Columna Origen */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="text-sm">
                      {esDerivado ? (
                        <Badge variant="purple">
                          <Send className="w-3 h-3 mr-1" />
                          {item.origen_hospital_nombre || 'Derivado'}
                        </Badge>
                      ) : item.origen_servicio_nombre ? (
                        <div className="flex flex-col">
                          <span className="text-gray-600 font-medium">{item.origen_servicio_nombre}</span>
                          {item.origen_cama_identificador && (
                            <span className="text-xs text-gray-400 flex items-center gap-1">
                              <BedDouble className="w-3 h-3" />
                              {item.origen_cama_identificador}
                            </span>
                          )}
                        </div>
                      ) : (
                        <Badge variant="info">
                          {formatTipoPaciente(item.origen_tipo || String(paciente?.tipo_paciente || ''))}
                        </Badge>
                      )}
                    </div>
                  </td>
                  {/* Columna Destino */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="text-sm">
                      {esAsignado && camaDestinoInfo ? (
                        <div className="flex flex-col">
                          <span className="text-green-600 font-medium flex items-center gap-1">
                            <BedDouble className="w-3 h-3" />
                            {camaDestinoInfo.identificador}
                          </span>
                          {camaDestinoInfo.servicio && (
                            <span className="text-xs text-gray-500">{camaDestinoInfo.servicio}</span>
                          )}
                        </div>
                      ) : servicioDestino ? (
                        <Badge variant={
                          servicioDestino.toLowerCase().includes('uci') ? 'danger' :
                          servicioDestino.toLowerCase().includes('uti') ? 'warning' :
                          servicioDestino.toLowerCase().includes('aislamiento') ? 'purple' :
                          'default'
                        }>
                          {servicioDestino}
                        </Badge>
                      ) : (
                        <span className="text-gray-400 text-xs">-</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <Badge variant={
                      complejidad === 'alta' ? 'danger' :
                      complejidad === 'media' ? 'warning' :
                      'default'
                    }>
                      {formatComplejidad(complejidad)}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="text-sm font-medium text-gray-900">
                      {item.prioridad?.toFixed(1)}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex items-center text-sm text-gray-600">
                      <Clock className="w-4 h-4 mr-1" />
                      {formatTiempoEspera(item.tiempo_espera_minutos || item.tiempo_espera_min || 0)}
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <Badge variant={
                      item.estado_lista === 'asignado' ? 'success' :
                      item.estado_lista === 'buscando' ? 'warning' :
                      'default'
                    }>
                      {item.estado_lista || 'esperando'}
                    </Badge>
                  </td>
                  {/* COLUMNA ACCIONES - ACTUALIZADA */}
                  <td className="px-4 py-3 whitespace-nowrap text-right">
                    <div className="flex items-center justify-end gap-1">
                      {/* Botón Reevaluar - Solo si NO tiene cama destino asignada */}
                      {puedeReevaluarDerivar && (
                        <button
                          onClick={(e) => handleReevaluar(item, e)}
                          className="p-1.5 text-blue-600 hover:bg-blue-50 rounded"
                          title="Reevaluar paciente"
                        >
                          <FileText className="w-4 h-4" />
                        </button>
                      )}
                      
                      {/* Botón Derivar - Solo si NO tiene cama destino asignada */}
                      {puedeReevaluarDerivar && (
                        <button
                          onClick={(e) => handleDerivar(item, e)}
                          className="p-1.5 text-purple-600 hover:bg-purple-50 rounded"
                          title="Derivar a otro hospital"
                        >
                          <Send className="w-4 h-4" />
                        </button>
                      )}
                      
                      {/* NUEVO: Botón Asignar Cama - Solo en modo manual y sin cama destino */}
                      {puedeAsignarCamaManual && (
                        <button
                          onClick={(e) => handleAbrirAsignacionManual(item, e)}
                          className="p-1.5 text-green-600 hover:bg-green-50 rounded"
                          title="Asignar cama manualmente"
                        >
                          <Plus className="w-4 h-4" />
                        </button>
                      )}
                      
                      {/* NUEVO: Botón Cancelar Asignación - Solo si tiene cama destino */}
                      {puedeCancelarAsignacion && (
                        <button
                          onClick={(e) => handleMostrarCancelarAsignacion(item, e)}
                          className="p-1.5 text-orange-600 hover:bg-orange-50 rounded"
                          title="Cancelar asignación de cama"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      )}
                      
                      {/* Botón Cancelar/Volver - Comportamiento según tipo de paciente */}
                      {puedeCancelarVolver && (
                        <button
                          onClick={(e) => handleMostrarCancelar(item, e)}
                          className="p-1.5 text-orange-600 hover:bg-orange-50 rounded"
                          title={esDerivado ? "Cancelar y volver a lista de derivados" : "Cancelar búsqueda y volver a cama"}
                        >
                          <RotateCcw className="w-4 h-4" />
                        </button>
                      )}
                      
                      {/* Botón Eliminar - Solo para urgencia/ambulatorio sin cama origen ni destino */}
                      {puedeEliminar && (
                        <button
                          onClick={(e) => handleMostrarEliminar(item, e)}
                          className="p-1.5 text-red-600 hover:bg-red-50 rounded"
                          title="Eliminar paciente del sistema"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {listaFiltrada.length === 0 && (
          <div className="p-8 text-center text-gray-500">
            No hay pacientes en la lista de espera
          </div>
        )}
      </div>

      {/* Modal de confirmación unificado */}
      <Modal
        isOpen={showConfirmModal}
        onClose={() => {
          setShowConfirmModal(false);
          setPacienteSeleccionado(null);
          setAccionPendiente(null);
        }}
        title={
          accionPendiente === 'eliminar' ? 'Confirmar Eliminación' : 
          accionPendiente === 'cancelar_asignacion' ? 'Confirmar Cancelación de Asignación' :
          'Confirmar Cancelación'
        }
        size="md"
      >
        <div className="space-y-4">
          <div className={`flex items-start gap-3 p-4 rounded-lg ${
            accionPendiente === 'eliminar' ? 'bg-red-50' : 'bg-yellow-50'
          }`}>
            <AlertTriangle className={`w-6 h-6 flex-shrink-0 mt-0.5 ${
              accionPendiente === 'eliminar' ? 'text-red-600' : 'text-yellow-600'
            }`} />
            <div>
              <p className={`font-medium ${
                accionPendiente === 'eliminar' ? 'text-red-800' : 'text-yellow-800'
              }`}>
                {tituloConfirmacion}
              </p>
              <p className="text-sm text-gray-700 mt-1">
                Paciente: <strong>{pacienteSeleccionado?.nombre || pacienteSeleccionado?.paciente?.nombre}</strong>
              </p>
            </div>
          </div>
          
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-600">
              {mensajeConfirmacion}
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button
              variant="secondary"
              onClick={() => {
                setShowConfirmModal(false);
                setPacienteSeleccionado(null);
                setAccionPendiente(null);
              }}
            >
              Volver
            </Button>
            <Button
              variant={accionPendiente === 'eliminar' ? 'danger' : 'warning'}
              onClick={handleConfirmarAccion}
              loading={procesando}
            >
              {accionPendiente === 'eliminar' ? 'Eliminar Paciente' : 
               accionPendiente === 'cancelar_asignacion' ? 'Cancelar Asignación' :
               'Confirmar Cancelación'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* ============================================ */}
      {/* NUEVO: Modal de Asignación Manual de Cama */}
      {/* ============================================ */}
      <Modal
        isOpen={showAsignacionModal}
        onClose={() => {
          setShowAsignacionModal(false);
          setPacienteAsignar(null);
          setCamaSeleccionada(null);
          setBusquedaCama('');
        }}
        title="Asignar Cama Manualmente"
        size="lg"
      >
        <div className="space-y-4">
          {/* Info del paciente */}
          <div className="bg-blue-50 p-3 rounded-lg">
            <div className="flex items-center gap-2">
              <User className="w-5 h-5 text-blue-600" />
              <div>
                <p className="font-medium text-blue-900">
                  {pacienteAsignar?.nombre || pacienteAsignar?.paciente?.nombre}
                </p>
                <p className="text-sm text-blue-700">
                  {pacienteAsignar?.run || pacienteAsignar?.paciente?.run}
                </p>
              </div>
            </div>
          </div>

          {/* Búsqueda de camas */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar cama por identificador o servicio..."
              value={busquedaCama}
              onChange={(e) => setBusquedaCama(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Lista de camas disponibles */}
          <div className="max-h-80 overflow-y-auto border rounded-lg">
            {camasLibresFiltradas.length === 0 ? (
              <div className="p-4 text-center text-gray-500">
                No hay camas libres disponibles
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-2 p-2">
                {camasLibresFiltradas.map((cama) => (
                  <button
                    key={cama.id}
                    onClick={() => setCamaSeleccionada(cama.id)}
                    className={`p-3 border rounded-lg text-left hover:bg-gray-50 transition-colors ${
                      camaSeleccionada === cama.id ? 'bg-blue-50 border-blue-500 ring-2 ring-blue-200' : ''
                    }`}
                  >
                    <p className="font-medium text-sm flex items-center gap-1">
                      <BedDouble className="w-3 h-3" />
                      {cama.identificador}
                    </p>
                    <p className="text-xs text-gray-500">{cama.servicio_nombre}</p>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Botones */}
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button
              variant="secondary"
              onClick={() => {
                setShowAsignacionModal(false);
                setPacienteAsignar(null);
                setCamaSeleccionada(null);
              }}
            >
              Cancelar
            </Button>
            <Button
              variant="primary"
              disabled={!camaSeleccionada || procesando}
              loading={procesando}
              onClick={handleConfirmarAsignacion}
            >
              Asignar Cama
            </Button>
          </div>
        </div>
      </Modal>

      {/* Modal de Derivación Directa */}
      <ModalDerivacionDirecta
        isOpen={showDerivacionModal}
        onClose={() => {
          setShowDerivacionModal(false);
          setPacienteDerivar(null);
        }}
        paciente={pacienteDerivar}
        onDerivacionCompletada={() => {
          setShowDerivacionModal(false);
          setPacienteDerivar(null);
        }}
      />
    </div>
  );
}