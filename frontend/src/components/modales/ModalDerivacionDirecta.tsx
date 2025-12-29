import { useState, useEffect, useRef } from 'react';
import { 
  Building2, 
  Send, 
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  FileText,
  Upload,
  Paperclip,
  X
} from 'lucide-react';
import { Modal, Button, Badge } from '../common';
import { useApp } from '../../context/AppContext';
import * as api from '../../services/api';
import type { Paciente } from '../../types';
import { formatComplejidad } from '../../utils';

// ============================================
// TIPOS
// ============================================

interface ModalDerivacionDirectaProps {
  isOpen: boolean;
  onClose: () => void;
  paciente: Paciente | null;
  onDerivacionCompletada?: () => void;
}

interface EstadoViabilidad {
  verificando: boolean;
  verificado: boolean;
  esViable: boolean;
  mensaje: string;
  motivosRechazo: string[];
}

const estadoViabilidadInicial: EstadoViabilidad = {
  verificando: false,
  verificado: false,
  esViable: false,
  mensaje: '',
  motivosRechazo: []
};

// ============================================
// COMPONENTE PRINCIPAL
// ============================================

export function ModalDerivacionDirecta({
  isOpen,
  onClose,
  paciente,
  onDerivacionCompletada
}: ModalDerivacionDirectaProps) {
  const { hospitales, hospitalSeleccionado, showAlert, recargarTodo } = useApp();
  
  // Estados del formulario
  const [hospitalDestinoId, setHospitalDestinoId] = useState('');
  const [motivoDerivacion, setMotivoDerivacion] = useState('');
  const [documento, setDocumento] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Estado de viabilidad
  const [viabilidad, setViabilidad] = useState<EstadoViabilidad>(estadoViabilidadInicial);
  
  // Hospitales disponibles para derivación (excluyendo el actual)
  const hospitalesDerivacion = hospitales.filter(h => h.id !== hospitalSeleccionado?.id);
  
  // Reset al abrir
  useEffect(() => {
    if (isOpen) {
      setHospitalDestinoId('');
      setMotivoDerivacion('');
      setDocumento(null);
      setViabilidad(estadoViabilidadInicial);
    }
  }, [isOpen]);
  
  // Verificar viabilidad cuando cambia el hospital destino
  useEffect(() => {
    const verificarViabilidad = async () => {
      if (!hospitalDestinoId || !paciente) {
        setViabilidad(estadoViabilidadInicial);
        return;
      }

      setViabilidad(prev => ({ ...prev, verificando: true, verificado: false }));

      try {
        const resultado = await api.verificarViabilidadDerivacion(
          paciente.id,
          hospitalDestinoId
        );

        setViabilidad({
          verificando: false,
          verificado: true,
          esViable: resultado.es_viable,
          mensaje: resultado.mensaje,
          motivosRechazo: resultado.motivos_rechazo || []
        });
      } catch (error) {
        console.error('Error verificando viabilidad:', error);
        setViabilidad({
          verificando: false,
          verificado: true,
          esViable: false,
          mensaje: 'Error al verificar viabilidad',
          motivosRechazo: [error instanceof Error ? error.message : 'Error desconocido']
        });
      }
    };

    // Debounce para evitar llamadas excesivas
    const timeoutId = setTimeout(verificarViabilidad, 300);
    return () => clearTimeout(timeoutId);
  }, [hospitalDestinoId, paciente?.id]);
  
  // ============================================
  // MANEJO DE DOCUMENTO
  // ============================================
  
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        showAlert('error', 'Solo se permiten archivos PDF');
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        showAlert('error', 'El archivo no debe superar 10MB');
        return;
      }
      setDocumento(file);
    }
  };
  
  const handleRemoveFile = () => {
    setDocumento(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };
  
  // ============================================
  // SOLICITAR DERIVACIÓN
  // ============================================
  
  const handleSolicitarDerivacion = async () => {
    if (!paciente || !hospitalDestinoId) return;
    
    if (!motivoDerivacion.trim()) {
      showAlert('error', 'Debe ingresar un motivo de derivación');
      return;
    }
    
    if (!viabilidad.esViable) {
      showAlert('error', 'La derivación no es viable al hospital seleccionado');
      return;
    }
    
    setLoading(true);
    try {
      // Primero subir documento si existe
      if (documento) {
        const formData = new FormData();
        formData.append('file', documento);
        
        const response = await fetch(
          `${api.getApiBase()}/api/pacientes/${paciente.id}/documento`,
          {
            method: 'POST',
            body: formData
          }
        );
        
        if (!response.ok) {
          throw new Error('Error al subir documento');
        }
      }
      
      // Solicitar derivación
      const hospitalDestino = hospitalesDerivacion.find(h => h.id === hospitalDestinoId);
      await api.solicitarDerivacion(paciente.id, {
        hospital_destino_id: hospitalDestinoId,
        motivo: motivoDerivacion
      });
      
      showAlert('success', `Derivación solicitada a ${hospitalDestino?.nombre || 'hospital destino'}`);
      
      // Recargar datos
      await recargarTodo();
      
      // Callback y cerrar
      if (onDerivacionCompletada) {
        onDerivacionCompletada();
      }
      onClose();
      
    } catch (error) {
      console.error('Error al solicitar derivación:', error);
      showAlert('error', error instanceof Error ? error.message : 'Error al solicitar derivación');
    } finally {
      setLoading(false);
    }
  };
  
  // Verificar si se puede enviar
  const puedeEnviar = () => {
    if (!hospitalDestinoId) return false;
    if (!motivoDerivacion.trim()) return false;
    if (viabilidad.verificando) return false;
    if (!viabilidad.verificado) return false;
    return viabilidad.esViable;
  };
  
  if (!paciente) return null;
  
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Solicitar Derivación"
      size="md"
    >
      <div className="space-y-6">
        {/* Info del paciente */}
        <div className="bg-gray-50 rounded-lg p-4 space-y-2">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-800">{paciente.nombre}</p>
              <p className="text-sm text-gray-600">RUN: {paciente.run}</p>
            </div>
            <Badge 
              variant={
                paciente.complejidad_requerida === 'uci' ? 'danger' :
                paciente.complejidad_requerida === 'uti' ? 'warning' :
                'default'
              }
            >
              {formatComplejidad(paciente.complejidad_requerida || 'ninguna')}
            </Badge>
          </div>
          {paciente.diagnostico && (
            <p className="text-sm text-gray-600 mt-2">
              <span className="font-medium">Diagnóstico:</span> {paciente.diagnostico}
            </p>
          )}
        </div>
        
        {/* Selección de hospital destino */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Hospital destino <span className="text-red-500">*</span>
          </label>
          <select
            value={hospitalDestinoId}
            onChange={(e) => setHospitalDestinoId(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
          >
            <option value="">Seleccionar hospital...</option>
            {hospitalesDerivacion.map(h => (
              <option key={h.id} value={h.id}>{h.nombre}</option>
            ))}
          </select>
        </div>
        
        {/* Indicador de viabilidad */}
        {hospitalDestinoId && (
          <div>
            {viabilidad.verificando ? (
              <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-100 p-4 rounded-lg">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Verificando viabilidad de derivación...</span>
              </div>
            ) : viabilidad.verificado && (
              viabilidad.esViable ? (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="font-medium text-green-800">Derivación viable</h4>
                      <p className="text-sm text-green-700 mt-1">{viabilidad.mensaje}</p>
                      <p className="text-sm text-green-600 mt-2">
                        El hospital destino cuenta con las capacidades necesarias para atender al paciente.
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <h4 className="font-medium text-red-800">Derivación NO viable</h4>
                      <p className="text-sm text-red-700 mt-1">{viabilidad.mensaje}</p>
                      
                      {viabilidad.motivosRechazo.length > 0 && (
                        <div className="mt-3 space-y-1">
                          <p className="text-sm font-medium text-red-800">Motivos:</p>
                          <ul className="list-disc list-inside text-sm text-red-700 space-y-1">
                            {viabilidad.motivosRechazo.map((motivo, idx) => (
                              <li key={idx}>{motivo}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            )}
            
            {/* Nota informativa para no viable */}
            {viabilidad.verificado && !viabilidad.esViable && (
              <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-amber-700">
                  Considere derivar a un hospital que cuente con las capacidades requeridas 
                  o contactar a la coordinación para gestionar la derivación.
                </p>
              </div>
            )}
          </div>
        )}
        
        {/* Motivo de derivación */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Motivo de derivación <span className="text-red-500">*</span>
          </label>
          <textarea
            value={motivoDerivacion}
            onChange={(e) => setMotivoDerivacion(e.target.value)}
            rows={3}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            placeholder="Describa el motivo de la derivación..."
          />
        </div>
        
        {/* Documento adjunto */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Documento adjunto (opcional)
          </label>
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-4">
            {!documento ? (
              <div className="text-center">
                <Upload className="mx-auto h-8 w-8 text-gray-400" />
                <p className="mt-2 text-sm text-gray-600">
                  Adjuntar documento (solo PDF, máx. 10MB)
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  onChange={handleFileSelect}
                  className="hidden"
                  id="file-upload-derivacion"
                />
                <label
                  htmlFor="file-upload-derivacion"
                  className="mt-2 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-purple-600 bg-purple-50 rounded-lg cursor-pointer hover:bg-purple-100"
                >
                  <Paperclip className="w-4 h-4" />
                  Seleccionar archivo
                </label>
              </div>
            ) : (
              <div className="flex items-center justify-between bg-gray-50 p-3 rounded-lg">
                <div className="flex items-center gap-3">
                  <FileText className="w-8 h-8 text-red-500" />
                  <div>
                    <p className="text-sm font-medium text-gray-800">{documento.name}</p>
                    <p className="text-xs text-gray-500">PDF</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleRemoveFile}
                  className="p-1 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded"
                  title="Eliminar archivo"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            )}
          </div>
        </div>
        
        {/* Botones de acción */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            variant="primary"
            onClick={handleSolicitarDerivacion}
            loading={loading}
            disabled={!puedeEnviar()}
            icon={<Send className="w-4 h-4" />}
          >
            Solicitar Derivación
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export default ModalDerivacionDirecta;