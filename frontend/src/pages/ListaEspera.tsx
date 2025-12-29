import React, { useState, useMemo } from 'react';
import { Clock, User, Search, X, Eye, FileText, AlertTriangle, Send, BedDouble } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { useModal } from '../context/ModalContext';
import { Badge, Spinner, Modal, Button } from '../components/common';
import { 
  formatTiempoEspera, 
  formatComplejidad, 
  formatTipoPaciente 
} from '../utils';
import * as api from '../services/api';

export function ListaEspera() {
  const { listaEspera, loading, showAlert, recargarTodo, configuracion, camas } = useApp();
  const { openModal } = useModal();
  const [filtroOrigen, setFiltroOrigen] = useState<string>('todos');
  const [busqueda, setBusqueda] = useState('');
  
  // Estado para modal de confirmación de cancelar
  const [showCancelarModal, setShowCancelarModal] = useState(false);
  const [pacienteCancelar, setPacienteCancelar] = useState<typeof listaEspera[0] | null>(null);
  const [procesando, setProcesando] = useState(false);

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

  const handleVerPaciente = (item: typeof listaEspera[0]) => {
    if (item.paciente) {
      openModal('verPaciente', { paciente: item.paciente });
    }
  };

  const handleReevaluar = (item: typeof listaEspera[0]) => {
    if (item.paciente) {
      openModal('reevaluar', { paciente: item.paciente });
    }
  };

  // Mostrar modal de confirmación antes de cancelar
  const handleMostrarCancelar = (item: typeof listaEspera[0]) => {
    setPacienteCancelar(item);
    setShowCancelarModal(true);
  };

  // Helper para determinar si es derivado (usando propiedades existentes)
  const esItemDerivado = (item: typeof listaEspera[0]): boolean => {
    return item.origen_tipo === 'derivado' || 
           item.paciente?.derivacion_estado === 'aceptada' ||
           String(item.paciente?.tipo_paciente) === 'derivado';
  };

  // Helper para determinar si tiene cama actual (usando propiedades existentes)
  const tieneCamaActual = (item: typeof listaEspera[0]): boolean => {
    return !!(item.paciente?.cama_id);
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

  // Obtener mensaje descriptivo según tipo de paciente
  const getMensajeCancelacion = (item: typeof listaEspera[0] | null): string => {
    if (!item) return '';
    
    const esDerivado = esItemDerivado(item);
    const tieneCama = tieneCamaActual(item);
    
    if (esDerivado) {
      return `El paciente volverá a la lista de "Derivados Pendientes" donde podrá ser aceptado o rechazado nuevamente. La cama en el hospital de origen volverá al estado "En espera de derivación".`;
    } else if (tieneCama) {
      return `El paciente volverá a su cama actual con estado "Cama en espera". Podrá iniciar una nueva búsqueda de cama cuando lo requiera.`;
    } else {
      return `El paciente será removido de la lista de espera. Si es necesario, deberá ser registrado nuevamente.`;
    }
  };

  // Confirmar cancelación
  const handleConfirmarCancelar = async () => {
    if (!pacienteCancelar) return;
    
    const pacienteId = pacienteCancelar.paciente_id || pacienteCancelar.paciente?.id || '';
    
    // Guardar posición del scroll
    const scrollPosition = window.scrollY;
    
    try {
      setProcesando(true);
      const result = await api.egresarDeLista(pacienteId);
      showAlert('success', result.message || 'Paciente removido de lista');
      setShowCancelarModal(false);
      setPacienteCancelar(null);
      await recargarTodo();
      
      // Restaurar posición del scroll
      requestAnimationFrame(() => {
        window.scrollTo(0, scrollPosition);
      });
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al cancelar');
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
              {/* NUEVA COLUMNA: Destino */}
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
              const complejidad = getComplejidad(item);
              const servicioDestino = getServicioDestino(item);
              const camaDestinoInfo = getCamaDestinoInfo(item);
              const esAsignado = item.estado_lista === 'asignado';
              
              return (
                <tr key={item.paciente_id || paciente?.id} className="hover:bg-gray-50">
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
                  {/* Columna Origen - MEJORADA para hospitalizados */}
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
                  {/* NUEVA COLUMNA: Destino */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="text-sm">
                      {esAsignado && camaDestinoInfo ? (
                        // Paciente asignado - mostrar cama destino
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
                        // Paciente buscando - mostrar servicio destino
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
                  <td className="px-4 py-3 whitespace-nowrap text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => handleVerPaciente(item)}
                        className="p-1.5 text-gray-600 hover:bg-gray-100 rounded"
                        title="Ver paciente"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleReevaluar(item)}
                        className="p-1.5 text-blue-600 hover:bg-blue-50 rounded"
                        title="Reevaluar"
                      >
                        <FileText className="w-4 h-4" />
                      </button>
                      {/* Botón cancelar siempre visible */}
                      <button
                        onClick={() => handleMostrarCancelar(item)}
                        className="p-1.5 text-red-600 hover:bg-red-50 rounded"
                        title="Cancelar búsqueda"
                      >
                        <X className="w-4 h-4" />
                      </button>
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

      {/* Modal de confirmación para cancelar */}
      <Modal
        isOpen={showCancelarModal}
        onClose={() => {
          setShowCancelarModal(false);
          setPacienteCancelar(null);
        }}
        title="Confirmar Cancelación"
        size="md"
      >
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-4 bg-yellow-50 rounded-lg">
            <AlertTriangle className="w-6 h-6 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-yellow-800">
                ¿Está seguro que desea cancelar la búsqueda de cama?
              </p>
              <p className="text-sm text-yellow-700 mt-1">
                Paciente: <strong>{pacienteCancelar?.nombre || pacienteCancelar?.paciente?.nombre}</strong>
              </p>
            </div>
          </div>
          
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-600">
              {getMensajeCancelacion(pacienteCancelar)}
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button
              variant="secondary"
              onClick={() => {
                setShowCancelarModal(false);
                setPacienteCancelar(null);
              }}
            >
              Volver
            </Button>
            <Button
              variant="danger"
              onClick={handleConfirmarCancelar}
              loading={procesando}
            >
              Confirmar Cancelación
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}