import React, { useState, useMemo } from 'react';
import { Search, User, BedDouble } from 'lucide-react';
import { Modal, Button, Badge, Spinner } from '../common';
import { useApp } from '../../context/AppContext';
import type { Cama } from '../../types';
import { formatComplejidad, formatEstado } from '../../utils';
import * as api from '../../services/api';

interface ModalAsignacionManualProps {
  isOpen: boolean;
  onClose: () => void;
  cama: Cama | null;
}

export function ModalAsignacionManual({ isOpen, onClose, cama }: ModalAsignacionManualProps) {
  const { listaEspera, camas, showAlert, recargarTodo } = useApp();
  const [modo, setModo] = useState<'lista' | 'cama'>('lista');
  const [busqueda, setBusqueda] = useState('');
  const [loading, setLoading] = useState(false);
  const [seleccionado, setSeleccionado] = useState<string | null>(null);

  // Filtrar lista de espera
  const listaFiltrada = useMemo(() => {
    if (!busqueda) return listaEspera;
    const termino = busqueda.toLowerCase();
    return listaEspera.filter(item =>
      item.nombre?.toLowerCase().includes(termino) ||
      item.run?.toLowerCase().includes(termino) ||
      item.paciente?.nombre?.toLowerCase().includes(termino)
    );
  }, [listaEspera, busqueda]);

  // Filtrar camas libres
  const camasLibres = useMemo(() => {
    return camas.filter(c => c.estado === 'libre');
  }, [camas]);

  const handleAsignarDesdeLista = async (pacienteId: string) => {
    if (!cama) return;
    try {
      setLoading(true);
      const result = await api.asignarManualDesdeLista(pacienteId, cama.id);
      showAlert('success', result.message || 'Paciente asignado');
      await recargarTodo();
      onClose();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al asignar');
    } finally {
      setLoading(false);
    }
  };

  const handleAsignarDesdeCama = async (camaDestinoId: string) => {
    if (!cama?.paciente) return;
    try {
      setLoading(true);
      const result = await api.asignarManualDesdeCama(cama.paciente.id, camaDestinoId);
      showAlert('success', result.message || 'Traslado iniciado');
      await recargarTodo();
      onClose();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al asignar');
    } finally {
      setLoading(false);
    }
  };

  if (!cama) return null;

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose} 
      title={cama.estado === 'libre' ? 'Asignar Paciente a Cama' : 'Asignar Nueva Cama'}
      size="lg"
    >
      <div className="space-y-4">
        {/* Info de la cama actual */}
        <div className="bg-gray-50 p-3 rounded-lg">
          <div className="flex items-center gap-2">
            <BedDouble className="w-5 h-5 text-gray-600" />
            <span className="font-medium">{cama.identificador}</span>
            <Badge>{formatEstado(cama.estado)}</Badge>
          </div>
          {cama.paciente && (
            <p className="text-sm text-gray-600 mt-1">
              Paciente actual: {cama.paciente.nombre}
            </p>
          )}
        </div>

        {/* Tabs de modo */}
        {cama.estado === 'ocupada' && (
          <div className="flex border-b">
            <button
              onClick={() => setModo('cama')}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
                modo === 'cama'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Seleccionar Cama Destino
            </button>
          </div>
        )}

        {/* Búsqueda */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder={modo === 'lista' ? 'Buscar paciente...' : 'Buscar cama...'}
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Lista de pacientes */}
        {cama.estado === 'libre' && (
          <div className="max-h-80 overflow-y-auto border rounded-lg">
            {listaFiltrada.length === 0 ? (
              <div className="p-4 text-center text-gray-500">
                No hay pacientes en lista de espera
              </div>
            ) : (
              <div className="divide-y">
                {listaFiltrada.map((item) => (
                  <div
                    key={item.paciente_id || item.paciente?.id}
                    className={`p-3 flex items-center justify-between hover:bg-gray-50 cursor-pointer ${
                      seleccionado === (item.paciente_id || item.paciente?.id) ? 'bg-blue-50' : ''
                    }`}
                    onClick={() => setSeleccionado(item.paciente_id || item.paciente?.id || null)}
                  >
                    <div className="flex items-center gap-3">
                      <User className="w-8 h-8 text-gray-400" />
                      <div>
                        <p className="text-sm font-medium">
                          {item.nombre || item.paciente?.nombre}
                        </p>
                        <p className="text-xs text-gray-500">
                          {item.run || item.paciente?.run}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge variant={
                        item.paciente?.complejidad_requerida === 'uci' ? 'danger' :
                        item.paciente?.complejidad_requerida === 'uti' ? 'warning' :
                        'default'
                      }>
                        {formatComplejidad(item.paciente?.complejidad_requerida || 'ninguna')}
                      </Badge>
                      <p className="text-xs text-gray-500 mt-1">
                        Prioridad: {item.prioridad}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Lista de camas (para traslado) */}
        {cama.estado === 'ocupada' && modo === 'cama' && (
          <div className="max-h-80 overflow-y-auto border rounded-lg">
            {camasLibres.length === 0 ? (
              <div className="p-4 text-center text-gray-500">
                No hay camas libres disponibles
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-2 p-2">
                {camasLibres.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => setSeleccionado(c.id)}
                    className={`p-3 border rounded-lg text-left hover:bg-gray-50 ${
                      seleccionado === c.id ? 'bg-blue-50 border-blue-500' : ''
                    }`}
                  >
                    <p className="font-medium text-sm">{c.identificador}</p>
                    <p className="text-xs text-gray-500">{c.servicio_nombre}</p>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Botones */}
        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            variant="primary"
            disabled={!seleccionado || loading}
            loading={loading}
            onClick={() => {
              if (cama.estado === 'libre') {
                handleAsignarDesdeLista(seleccionado!);
              } else {
                handleAsignarDesdeCama(seleccionado!);
              }
            }}
          >
            {cama.estado === 'libre' ? 'Asignar Paciente' : 'Iniciar Traslado'}
          </Button>
        </div>
      </div>
    </Modal>
  );
}