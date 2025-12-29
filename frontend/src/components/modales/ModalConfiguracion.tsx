import React, { useState, useEffect } from 'react';
import { Settings, Volume2 } from 'lucide-react';
import { Modal, Button } from '../common';
import { useApp } from '../../context/AppContext';
import * as api from '../../services/api';

interface ModalConfiguracionProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ModalConfiguracion({ isOpen, onClose }: ModalConfiguracionProps) {
  const { configuracion, setConfiguracion, showAlert, testSound } = useApp();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    modo_manual: false,
    tiempo_limpieza_segundos: 300,
    tiempo_espera_oxigeno_segundos: 1800
  });

  useEffect(() => {
    if (configuracion) {
      setFormData({
        modo_manual: configuracion.modo_manual,
        tiempo_limpieza_segundos: configuracion.tiempo_limpieza_segundos,
        tiempo_espera_oxigeno_segundos: configuracion.tiempo_espera_oxigeno_segundos || 1800
      });
    }
  }, [configuracion]);

  const handleSubmit = async () => {
    try {
      setLoading(true);
      const result = await api.actualizarConfiguracion(formData);
      setConfiguracion(result);
      showAlert('success', 'Configuración actualizada');
      onClose();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al guardar');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Configuración del Sistema" size="md">
      <div className="space-y-6">
        {/* Modo Manual */}
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
          <div>
            <h4 className="font-medium text-gray-800">Modo Manual</h4>
            <p className="text-sm text-gray-500">
              Habilita controles adicionales para asignación manual de camas
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={formData.modo_manual}
              onChange={(e) => setFormData(prev => ({ ...prev, modo_manual: e.target.checked }))}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
          </label>
        </div>

        {/* Tiempo de limpieza */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tiempo de Limpieza (segundos)
          </label>
          <input
            type="number"
            value={formData.tiempo_limpieza_segundos}
            onChange={(e) => setFormData(prev => ({ 
              ...prev, 
              tiempo_limpieza_segundos: parseInt(e.target.value) || 0 
            }))}
            min={0}
            className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            Tiempo que la cama permanece en limpieza después de un alta
          </p>
        </div>

        {/* Tiempo espera oxígeno */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tiempo de Evaluación de Oxígeno (segundos)
          </label>
          <input
            type="number"
            value={formData.tiempo_espera_oxigeno_segundos}
            onChange={(e) => setFormData(prev => ({ 
              ...prev, 
              tiempo_espera_oxigeno_segundos: parseInt(e.target.value) || 0 
            }))}
            min={0}
            className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            Tiempo de espera para reevaluación cuando se desactiva oxígeno
          </p>
        </div>

        {/* Test de sonido */}
        <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg">
          <div>
            <h4 className="font-medium text-gray-800">Probar Sonido</h4>
            <p className="text-sm text-gray-500">
              Reproduce el sonido de notificación
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={testSound}
            icon={<Volume2 className="w-4 h-4" />}
          >
            Probar
          </Button>
        </div>

        {/* Botones */}
        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="primary" onClick={handleSubmit} loading={loading}>
            Guardar Cambios
          </Button>
        </div>
      </div>
    </Modal>
  );
}