import React, { useState, useEffect } from 'react';
import { Clock, User, Check, X, Eye, Building2, Send, ChevronDown, ChevronUp } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { useModal } from '../context/ModalContext';
import { Badge, Spinner, Modal, Button } from '../components/common';
import { formatTiempoEspera, formatComplejidad } from '../utils';
import * as api from '../services/api';

// Tipo para derivados enviados a otros hospitales
interface DerivadoEnviado {
  paciente_id: string;
  nombre: string;
  run: string;
  hospital_destino_id: string;
  hospital_destino_nombre: string;
  motivo_derivacion: string;
  estado_derivacion: string;
  cama_origen_identificador: string | null;
  tiempo_en_proceso_min: number;
  complejidad: string;
  diagnostico: string;
}

export function Derivados() {
  const { derivados, loading, showAlert, recargarTodo, hospitalSeleccionado } = useApp();
  const { openModal } = useModal();
  const [showRechazoModal, setShowRechazoModal] = useState(false);
  const [pacienteRechazo, setPacienteRechazo] = useState<string | null>(null);
  const [motivoRechazo, setMotivoRechazo] = useState('');
  const [procesando, setProcesando] = useState(false);
  
  // Estado para derivados enviados
  const [derivadosEnviados, setDerivadosEnviados] = useState<DerivadoEnviado[]>([]);
  const [loadingEnviados, setLoadingEnviados] = useState(false);
  const [showEnviados, setShowEnviados] = useState(false);

  // Cargar derivados enviados cuando se expande la sección
  useEffect(() => {
    if (showEnviados && hospitalSeleccionado) {
      cargarDerivadosEnviados();
    }
  }, [showEnviados, hospitalSeleccionado]);

  const cargarDerivadosEnviados = async () => {
    if (!hospitalSeleccionado) return;
    
    try {
      setLoadingEnviados(true);
      const data = await api.getDerivadosEnviados(hospitalSeleccionado.id);
      setDerivadosEnviados(data);
    } catch (error) {
      console.error('Error al cargar derivados enviados:', error);
      setDerivadosEnviados([]);
    } finally {
      setLoadingEnviados(false);
    }
  };

  const handleAceptar = async (pacienteId: string) => {
    try {
      setProcesando(true);
      const result = await api.accionDerivacion(pacienteId, { accion: 'aceptar' });
      showAlert('success', result.message || 'Derivación aceptada - paciente en lista de espera');
      await recargarTodo();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al aceptar derivación');
    } finally {
      setProcesando(false);
    }
  };

  const handleRechazar = (pacienteId: string) => {
    setPacienteRechazo(pacienteId);
    setMotivoRechazo('');
    setShowRechazoModal(true);
  };

  const confirmarRechazo = async () => {
    if (!pacienteRechazo || !motivoRechazo.trim()) {
      showAlert('warning', 'Debe ingresar un motivo de rechazo');
      return;
    }

    try {
      setProcesando(true);
      const result = await api.accionDerivacion(pacienteRechazo, { 
        accion: 'rechazar',
        motivo_rechazo: motivoRechazo
      });
      showAlert('success', result.message || 'Derivación rechazada');
      setShowRechazoModal(false);
      await recargarTodo();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al rechazar derivación');
    } finally {
      setProcesando(false);
    }
  };

  const handleVerPaciente = (item: typeof derivados[0]) => {
    if (item.paciente) {
      openModal('verPaciente', { paciente: item.paciente });
    }
  };

  const handleCancelarEnviado = async (pacienteId: string) => {
    try {
      setProcesando(true);
      const result = await api.cancelarDerivacionDesdeOrigen(pacienteId);
      showAlert('success', result.message || 'Derivación cancelada');
      await cargarDerivadosEnviados();
      await recargarTodo();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al cancelar derivación');
    } finally {
      setProcesando(false);
    }
  };

  // Helper para obtener complejidad del item
  const getComplejidad = (item: typeof derivados[0]): string => {
    // Intentar obtener de varias fuentes
    const comp = item.complejidad || item.paciente?.complejidad || item.paciente?.complejidad_requerida;
    if (!comp) return 'ninguna';
    return String(comp);
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
      {/* Header - Derivados pendientes (recibidos) */}
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-semibold text-gray-800">
          Derivaciones Pendientes de Aceptación
          <span className="ml-2 text-sm font-normal text-gray-500">
            ({derivados.length} pacientes)
          </span>
        </h2>
        <p className="text-sm text-gray-500 mt-1">
          Pacientes presentados desde otros hospitales para ser trasladados a este hospital
        </p>
      </div>

      {/* Lista de derivados pendientes */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Paciente
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Hospital Origen
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Motivo
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Complejidad
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Tiempo
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Acciones
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {derivados.map((item) => {
              const complejidad = getComplejidad(item);
              
              return (
                <tr key={item.paciente_id || item.paciente?.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center">
                      <User className="w-8 h-8 text-gray-400 mr-3" />
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {item.nombre || item.paciente?.nombre}
                        </p>
                        <p className="text-xs text-gray-500">
                          {item.run || item.paciente?.run}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex items-center text-sm text-gray-600">
                      <Building2 className="w-4 h-4 mr-2 text-gray-400" />
                      <div>
                        <p>{item.hospital_origen_nombre || item.hospital_origen?.nombre}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-sm text-gray-600 max-w-xs truncate">
                      {item.motivo_derivacion || item.motivo}
                    </p>
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
                    <div className="flex items-center text-sm text-gray-600">
                      <Clock className="w-4 h-4 mr-1" />
                      {formatTiempoEspera(item.tiempo_en_lista_minutos || item.tiempo_en_lista_min || 0)}
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleVerPaciente(item)}
                        className="p-1.5 text-gray-600 hover:bg-gray-100 rounded"
                        title="Ver detalles"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleAceptar(item.paciente_id || item.paciente?.id || '')}
                        disabled={procesando}
                        className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50"
                      >
                        <Check className="w-4 h-4" />
                        Aceptar
                      </button>
                      <button
                        onClick={() => handleRechazar(item.paciente_id || item.paciente?.id || '')}
                        disabled={procesando}
                        className="flex items-center gap-1 px-3 py-1.5 bg-red-600 text-white text-sm rounded hover:bg-red-700 disabled:opacity-50"
                      >
                        <X className="w-4 h-4" />
                        Rechazar
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {derivados.length === 0 && (
          <div className="p-8 text-center text-gray-500">
            No hay derivaciones pendientes de aceptación
          </div>
        )}
      </div>

      {/* Sección colapsable: Derivados enviados a otros hospitales */}
      <div className="bg-white rounded-lg shadow">
        <button
          onClick={() => setShowEnviados(!showEnviados)}
          className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-50 rounded-lg"
        >
          <div>
            <h3 className="font-semibold text-gray-800 flex items-center gap-2">
              <Send className="w-4 h-4 text-blue-600" />
              Pacientes Derivados a Otros Hospitales
            </h3>
            <p className="text-sm text-gray-500">
              Pacientes de este hospital que han sido derivados a otros hospitales
            </p>
          </div>
          {showEnviados ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </button>

        {showEnviados && (
          <div className="border-t">
            {loadingEnviados ? (
              <div className="p-8 flex justify-center">
                <Spinner size="md" />
              </div>
            ) : derivadosEnviados.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                No hay pacientes derivados a otros hospitales
              </div>
            ) : (
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Paciente
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Hospital Destino
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Cama Origen
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Estado
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Tiempo
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Acciones
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {derivadosEnviados.map((item) => (
                    <tr key={item.paciente_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center">
                          <User className="w-8 h-8 text-gray-400 mr-3" />
                          <div>
                            <p className="text-sm font-medium text-gray-900">{item.nombre}</p>
                            <p className="text-xs text-gray-500">{item.run}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center text-sm text-gray-600">
                          <Building2 className="w-4 h-4 mr-2 text-blue-400" />
                          {item.hospital_destino_nombre}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {item.cama_origen_identificador || '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <Badge variant={
                          item.estado_derivacion === 'aceptada' ? 'success' :
                          item.estado_derivacion === 'pendiente' ? 'warning' :
                          'default'
                        }>
                          {item.estado_derivacion === 'aceptada' ? 'Aceptada' :
                           item.estado_derivacion === 'pendiente' ? 'Pendiente' :
                           item.estado_derivacion}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center text-sm text-gray-600">
                          <Clock className="w-4 h-4 mr-1" />
                          {formatTiempoEspera(item.tiempo_en_proceso_min || 0)}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-right">
                        <button
                          onClick={() => handleCancelarEnviado(item.paciente_id)}
                          disabled={procesando}
                          className="flex items-center gap-1 px-3 py-1.5 bg-gray-600 text-white text-sm rounded hover:bg-gray-700 disabled:opacity-50"
                          title="Cancelar derivación y mantener paciente en este hospital"
                        >
                          <X className="w-4 h-4" />
                          Cancelar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

      {/* Modal de rechazo */}
      <Modal
        isOpen={showRechazoModal}
        onClose={() => setShowRechazoModal(false)}
        title="Rechazar Derivación"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Ingrese el motivo del rechazo de la derivación. Este motivo será visible 
            en el hospital de origen.
          </p>
          <textarea
            value={motivoRechazo}
            onChange={(e) => setMotivoRechazo(e.target.value)}
            placeholder="Motivo del rechazo..."
            className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
            rows={3}
          />
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              onClick={() => setShowRechazoModal(false)}
            >
              Cancelar
            </Button>
            <Button
              variant="danger"
              onClick={confirmarRechazo}
              loading={procesando}
            >
              Confirmar Rechazo
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}