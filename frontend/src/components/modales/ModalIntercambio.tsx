import React, { useState, useMemo } from 'react';
import { Search, User, BedDouble, ArrowRightLeft } from 'lucide-react';
import { Modal, Button, Badge } from '../common';
import { useApp } from '../../context/AppContext';
import type { Cama } from '../../types';
import { formatComplejidad } from '../../utils';
import * as api from '../../services/api';

interface ModalIntercambioProps {
  isOpen: boolean;
  onClose: () => void;
  cama: Cama | null;
}

export function ModalIntercambio({ isOpen, onClose, cama }: ModalIntercambioProps) {
  const { camas, showAlert, recargarTodo } = useApp();
  const [busqueda, setBusqueda] = useState('');
  const [loading, setLoading] = useState(false);
  const [seleccionado, setSeleccionado] = useState<string | null>(null);

  // Filtrar camas ocupadas (excluyendo la actual)
  const camasOcupadas = useMemo(() => {
    return camas.filter(c => 
      c.estado === 'ocupada' && 
      c.id !== cama?.id &&
      c.paciente
    );
  }, [camas, cama]);

  // Filtrar por búsqueda
  const camasFiltradas = useMemo(() => {
    if (!busqueda) return camasOcupadas;
    const termino = busqueda.toLowerCase();
    return camasOcupadas.filter(c =>
      c.identificador.toLowerCase().includes(termino) ||
      c.paciente?.nombre?.toLowerCase().includes(termino) ||
      c.paciente?.run?.toLowerCase().includes(termino) ||
      c.servicio_nombre?.toLowerCase().includes(termino)
    );
  }, [camasOcupadas, busqueda]);

  const handleIntercambiar = async () => {
    if (!cama?.paciente || !seleccionado) return;
    
    const camaDestino = camas.find(c => c.id === seleccionado);
    if (!camaDestino?.paciente) return;

    try {
      setLoading(true);
      const result = await api.intercambiarPacientes(cama.paciente.id, camaDestino.paciente.id);
      showAlert('success', result.message || 'Intercambio realizado');
      await recargarTodo();
      onClose();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al intercambiar');
    } finally {
      setLoading(false);
    }
  };

  if (!cama || !cama.paciente) return null;

  const camaSeleccionada = seleccionado ? camas.find(c => c.id === seleccionado) : null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Intercambiar Pacientes" size="lg">
      <div className="space-y-4">
        {/* Info de la cama actual */}
        <div className="bg-blue-50 p-4 rounded-lg">
          <h4 className="text-sm font-medium text-blue-800 mb-2">Cama Actual</h4>
          <div className="flex items-center gap-3">
            <BedDouble className="w-6 h-6 text-blue-600" />
            <div>
              <p className="font-medium">{cama.identificador}</p>
              <p className="text-sm text-blue-700">{cama.servicio_nombre}</p>
            </div>
            <div className="ml-auto text-right">
              <p className="text-sm font-medium">{cama.paciente.nombre}</p>
              <Badge variant={
                cama.paciente.complejidad_requerida === 'uci' ? 'danger' :
                cama.paciente.complejidad_requerida === 'uti' ? 'warning' :
                'default'
              }>
                {formatComplejidad(cama.paciente.complejidad_requerida || 'ninguna')}
              </Badge>
            </div>
          </div>
        </div>

        {/* Flecha de intercambio */}
        <div className="flex justify-center">
          <ArrowRightLeft className="w-8 h-8 text-gray-400" />
        </div>

        {/* Cama seleccionada para intercambio */}
        {camaSeleccionada ? (
          <div className="bg-green-50 p-4 rounded-lg">
            <h4 className="text-sm font-medium text-green-800 mb-2">Cama de Intercambio</h4>
            <div className="flex items-center gap-3">
              <BedDouble className="w-6 h-6 text-green-600" />
              <div>
                <p className="font-medium">{camaSeleccionada.identificador}</p>
                <p className="text-sm text-green-700">{camaSeleccionada.servicio_nombre}</p>
              </div>
              <div className="ml-auto text-right">
                <p className="text-sm font-medium">{camaSeleccionada.paciente?.nombre}</p>
                <Badge variant={
                  camaSeleccionada.paciente?.complejidad_requerida === 'uci' ? 'danger' :
                  camaSeleccionada.paciente?.complejidad_requerida === 'uti' ? 'warning' :
                  'default'
                }>
                  {formatComplejidad(camaSeleccionada.paciente?.complejidad_requerida || 'ninguna')}
                </Badge>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-gray-50 p-4 rounded-lg text-center text-gray-500">
            Seleccione una cama para intercambiar
          </div>
        )}

        {/* Búsqueda */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar por cama, paciente o servicio..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Lista de camas */}
        <div className="max-h-60 overflow-y-auto border rounded-lg">
          {camasFiltradas.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              No hay camas disponibles para intercambio
            </div>
          ) : (
            <div className="divide-y">
              {camasFiltradas.map((c) => (
                <div
                  key={c.id}
                  className={`p-3 flex items-center justify-between hover:bg-gray-50 cursor-pointer ${
                    seleccionado === c.id ? 'bg-green-50' : ''
                  }`}
                  onClick={() => setSeleccionado(c.id)}
                >
                  <div className="flex items-center gap-3">
                    <BedDouble className="w-6 h-6 text-gray-400" />
                    <div>
                      <p className="text-sm font-medium">{c.identificador}</p>
                      <p className="text-xs text-gray-500">{c.servicio_nombre}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm">{c.paciente?.nombre}</p>
                    <Badge variant={
                      c.paciente?.complejidad_requerida === 'uci' ? 'danger' :
                      c.paciente?.complejidad_requerida === 'uti' ? 'warning' :
                      'default'
                    }>
                      {formatComplejidad(c.paciente?.complejidad_requerida || 'ninguna')}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Botones */}
        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            variant="warning"
            disabled={!seleccionado || loading}
            loading={loading}
            onClick={handleIntercambiar}
            icon={<ArrowRightLeft className="w-4 h-4" />}
          >
            Intercambiar Pacientes
          </Button>
        </div>
      </div>
    </Modal>
  );
}