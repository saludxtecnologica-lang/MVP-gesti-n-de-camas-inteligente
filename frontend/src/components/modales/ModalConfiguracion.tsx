/**
 * MODAL DE CONFIGURACIÓN ACTUALIZADO
 * REEMPLAZAR: src/components/modales/ModalConfiguracion.tsx
 * 
 * Incluye:
 * - Configuración de modo manual
 * - Tiempos de limpieza y oxígeno
 * - Teléfonos de urgencias y ambulatorio POR HOSPITAL
 * - Teléfonos por servicio
 * 
 * CORRECCIONES:
 * - Cambio de icono Hospital a Building (Hospital no existe en lucide-react)
 * - hospitalSeleccionado es de tipo Hospital | null, se usa .id para acceder al ID
 */
import React, { useState, useEffect } from 'react';
import { Settings, Volume2, Phone, Building2, ChevronDown, ChevronRight, Save, Building } from 'lucide-react';
import { Modal, Button, Spinner } from '../common';
import { useApp } from '../../context/AppContext';
import * as api from '../../services/api';

// ============================================
// INTERFACES
// ============================================
interface ServicioConTelefono {
  id: string;
  nombre: string;
  codigo: string;
  tipo: string;
  hospital_id: string;
  telefono: string | null;
  total_camas: number;
  camas_libres: number;
}

interface HospitalConTelefonos {
  id: string;
  nombre: string;
  codigo: string;
  es_central: boolean;
  telefono_urgencias: string | null;
  telefono_ambulatorio: string | null;
  servicios: ServicioConTelefono[];
}

interface ModalConfiguracionProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ModalConfiguracion({ isOpen, onClose }: ModalConfiguracionProps) {
  const { configuracion, setConfiguracion, showAlert, testSound, hospitalSeleccionado, hospitales } = useApp();
  const [loading, setLoading] = useState(false);
  const [loadingTelefonos, setLoadingTelefonos] = useState(false);
  const [savingTelefonos, setSavingTelefonos] = useState(false);
  
  // Estado del formulario principal (configuración global)
  const [formData, setFormData] = useState({
    modo_manual: false,
    tiempo_limpieza_minutos: 5,
    tiempo_espera_oxigeno_minutos: 30
  });

  // Estado para teléfonos del hospital seleccionado
  const [hospitalTelefonos, setHospitalTelefonos] = useState<HospitalConTelefonos | null>(null);
  const [telefonoUrgencias, setTelefonoUrgencias] = useState('');
  const [telefonoAmbulatorio, setTelefonoAmbulatorio] = useState('');
  const [telefonosServicios, setTelefonosServicios] = useState<Record<string, string>>({});
  
  // Secciones expandibles
  const [seccionTelefonosAbierta, setSeccionTelefonosAbierta] = useState(false);

  // Obtener el ID del hospital seleccionado (hospitalSeleccionado es Hospital | null)
  const hospitalSeleccionadoId = hospitalSeleccionado?.id || null;

  // Cargar configuración inicial
  useEffect(() => {
    if (configuracion) {
      setFormData({
        modo_manual: configuracion.modo_manual,
        tiempo_limpieza_minutos: configuracion.tiempo_limpieza_minutos || 5,
        tiempo_espera_oxigeno_minutos: configuracion.tiempo_espera_oxigeno_minutos || 30
      });
    }
  }, [configuracion]);

  // Cargar teléfonos cuando se abre la sección
  useEffect(() => {
    if (seccionTelefonosAbierta && hospitalSeleccionadoId) {
      cargarTelefonosHospital();
    }
  }, [seccionTelefonosAbierta, hospitalSeleccionadoId]);

  const cargarTelefonosHospital = async () => {
    if (!hospitalSeleccionadoId) return;
    
    try {
      setLoadingTelefonos(true);
      const data = await api.getTelefonosHospital(hospitalSeleccionadoId);
      setHospitalTelefonos(data);
      setTelefonoUrgencias(data.telefono_urgencias || '');
      setTelefonoAmbulatorio(data.telefono_ambulatorio || '');
      
      // Inicializar teléfonos de servicios
      const telefonos: Record<string, string> = {};
      data.servicios.forEach(s => {
        telefonos[s.id] = s.telefono || '';
      });
      setTelefonosServicios(telefonos);
    } catch (error) {
      showAlert('error', 'Error al cargar teléfonos del hospital');
    } finally {
      setLoadingTelefonos(false);
    }
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);
      const result = await api.actualizarConfiguracion({
        modo_manual: formData.modo_manual,
        tiempo_limpieza_minutos: formData.tiempo_limpieza_minutos,
        tiempo_espera_oxigeno_minutos: formData.tiempo_espera_oxigeno_minutos
      });
      setConfiguracion(result);
      showAlert('success', 'Configuración actualizada');
      onClose();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al guardar');
    } finally {
      setLoading(false);
    }
  };

  const handleGuardarTelefonos = async () => {
    if (!hospitalSeleccionadoId) return;
    
    try {
      setSavingTelefonos(true);
      
      // Preparar datos para enviar
      const data = {
        hospital: {
          telefono_urgencias: telefonoUrgencias.trim() || null,
          telefono_ambulatorio: telefonoAmbulatorio.trim() || null
        },
        servicios: {} as Record<string, string | null>
      };
      
      // Convertir teléfonos de servicios
      Object.entries(telefonosServicios).forEach(([servicioId, telefono]) => {
        data.servicios[servicioId] = telefono.trim() || null;
      });
      
      await api.actualizarTelefonosBatch(hospitalSeleccionadoId, data);
      showAlert('success', 'Teléfonos actualizados correctamente');
      
      // Recargar para confirmar cambios
      await cargarTelefonosHospital();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al guardar teléfonos');
    } finally {
      setSavingTelefonos(false);
    }
  };

  // Obtener nombre del hospital seleccionado
  const nombreHospitalSeleccionado = hospitalSeleccionado?.nombre || 'Hospital';

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Configuración del Sistema" size="lg">
      <div className="space-y-6 max-h-[70vh] overflow-y-auto">
        {/* ============================================ */}
        {/* SECCIÓN: MODO MANUAL */}
        {/* ============================================ */}
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

        {/* ============================================ */}
        {/* SECCIÓN: TIEMPOS */}
        {/* ============================================ */}
        <div className="space-y-4">
          <h4 className="font-medium text-gray-700 flex items-center gap-2">
            <Settings className="w-4 h-4" />
            Tiempos del Sistema
          </h4>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tiempo de Limpieza (minutos)
            </label>
            <input
              type="number"
              value={formData.tiempo_limpieza_minutos}
              onChange={(e) => setFormData(prev => ({ 
                ...prev, 
                tiempo_limpieza_minutos: parseInt(e.target.value) || 0 
              }))}
              min={1}
              max={120}
              className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Tiempo que la cama permanece en limpieza después de un alta o egreso
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tiempo de Evaluación de Oxígeno (minutos)
            </label>
            <input
              type="number"
              value={formData.tiempo_espera_oxigeno_minutos}
              onChange={(e) => setFormData(prev => ({ 
                ...prev, 
                tiempo_espera_oxigeno_minutos: parseInt(e.target.value) || 0 
              }))}
              min={1}
              max={120}
              className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Tiempo de espera para reevaluación cuando se desactiva oxígeno
            </p>
          </div>
        </div>

        {/* ============================================ */}
        {/* SECCIÓN: TELÉFONOS DEL HOSPITAL (Expandible) */}
        {/* ============================================ */}
        <div className="border-t pt-4">
          <button
            onClick={() => setSeccionTelefonosAbierta(!seccionTelefonosAbierta)}
            className="w-full flex items-center justify-between p-3 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Phone className="w-4 h-4 text-indigo-600" />
              <span className="font-medium text-indigo-700">
                Teléfonos de Contacto - {nombreHospitalSeleccionado}
              </span>
            </div>
            {seccionTelefonosAbierta ? (
              <ChevronDown className="w-5 h-5 text-indigo-500" />
            ) : (
              <ChevronRight className="w-5 h-5 text-indigo-500" />
            )}
          </button>

          {seccionTelefonosAbierta && (
            <div className="mt-4 space-y-4 pl-2">
              {loadingTelefonos ? (
                <div className="flex justify-center py-4">
                  <Spinner size="md" />
                </div>
              ) : (
                <>
                  {/* Teléfonos del Hospital */}
                  <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                    <h5 className="font-medium text-blue-800 mb-3 flex items-center gap-2">
                      <Building className="w-4 h-4" />
                      Teléfonos Generales del Hospital
                    </h5>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Urgencias
                        </label>
                        <input
                          type="text"
                          value={telefonoUrgencias}
                          onChange={(e) => setTelefonoUrgencias(e.target.value)}
                          placeholder="Ej: 123 456"
                          className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Para pacientes que ingresan desde urgencias
                        </p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Ambulatorio
                        </label>
                        <input
                          type="text"
                          value={telefonoAmbulatorio}
                          onChange={(e) => setTelefonoAmbulatorio(e.target.value)}
                          placeholder="Ej: 789 012"
                          className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Para pacientes ambulatorios
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Teléfonos por Servicio */}
                  <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                    <h5 className="font-medium text-gray-700 mb-3 flex items-center gap-2">
                      <Building2 className="w-4 h-4" />
                      Teléfonos por Servicio
                    </h5>
                    <p className="text-sm text-gray-600 mb-3">
                      Configure el teléfono de contacto para cada servicio. 
                      Esta información se mostrará en el resumen de traslados.
                    </p>
                    
                    {hospitalTelefonos?.servicios && hospitalTelefonos.servicios.length > 0 ? (
                      <div className="grid grid-cols-2 gap-3 max-h-48 overflow-y-auto pr-2">
                        {hospitalTelefonos.servicios.map(servicio => (
                          <div key={servicio.id} className="flex flex-col">
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                              {servicio.nombre}
                            </label>
                            <input
                              type="text"
                              value={telefonosServicios[servicio.id] || ''}
                              onChange={(e) => setTelefonosServicios(prev => ({
                                ...prev,
                                [servicio.id]: e.target.value
                              }))}
                              placeholder="Teléfono"
                              className="w-full border rounded px-2 py-1.5 text-sm focus:ring-2 focus:ring-blue-500"
                            />
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500 text-center py-2">
                        No hay servicios configurados
                      </p>
                    )}
                  </div>

                  {/* Botón Guardar Teléfonos */}
                  <div className="flex justify-end">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleGuardarTelefonos}
                      loading={savingTelefonos}
                      icon={<Save className="w-4 h-4" />}
                    >
                      Guardar Teléfonos
                    </Button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* ============================================ */}
        {/* SECCIÓN: TEST DE SONIDO */}
        {/* ============================================ */}
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

        {/* ============================================ */}
        {/* BOTONES PRINCIPALES */}
        {/* ============================================ */}
        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="primary" onClick={handleSubmit} loading={loading}>
            Guardar Configuración General
          </Button>
        </div>
      </div>
    </Modal>
  );
}