import { useState, useEffect, useRef } from 'react';
import { 
  Search, 
  Building2, 
  Bed, 
  Send, 
  X, 
  AlertTriangle,
  CheckCircle,
  ArrowLeft,
  Upload,
  FileText,
  Paperclip,
  MapPin
} from 'lucide-react';
import { Modal, Button } from '../common';
import { useApp } from '../../context/AppContext';
import * as api from '../../services/api';
import type { Paciente, Hospital } from '../../types';

// ============================================
// TIPOS
// ============================================

interface CamaDisponibleRed {
  cama_id: string;
  cama_identificador: string;
  hospital_id: string;
  hospital_nombre: string;
  hospital_codigo: string;
  servicio_id: string;
  servicio_nombre: string;
  servicio_tipo: string;
  sala_id: string;
  sala_numero: number;
  sala_es_individual: boolean;
}

interface ModalBusquedaCamaRedProps {
  isOpen: boolean;
  onClose: () => void;
  paciente: Paciente | null;
  onDerivacionCompletada?: () => void;
}

// Estados del flujo
type FlujoEstado = 
  | 'verificando'      // Verificando disponibilidad en hospital actual
  | 'sin_tipo_cama'    // No hay tipo de cama en hospital actual
  | 'buscando_red'     // Buscando en la red
  | 'resultados'       // Mostrando camas encontradas
  | 'sin_resultados'   // No se encontraron camas
  | 'formulario_derivacion';  // Formulario para derivar

// ============================================
// COMPONENTE PRINCIPAL
// ============================================

export function ModalBusquedaCamaRed({ 
  isOpen, 
  onClose, 
  paciente,
  onDerivacionCompletada 
}: ModalBusquedaCamaRedProps) {
  const { showAlert, recargarTodo } = useApp();
  
  // Estados
  const [estado, setEstado] = useState<FlujoEstado>('verificando');
  const [mensajeNoDisponible, setMensajeNoDisponible] = useState('');
  const [camasEncontradas, setCamasEncontradas] = useState<CamaDisponibleRed[]>([]);
  const [camaSeleccionada, setCamaSeleccionada] = useState<CamaDisponibleRed | null>(null);
  const [loading, setLoading] = useState(false);
  
  // Formulario de derivación
  const [motivoDerivacion, setMotivoDerivacion] = useState('');
  const [documento, setDocumento] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Reset al abrir
  useEffect(() => {
    if (isOpen && paciente) {
      setEstado('verificando');
      setCamasEncontradas([]);
      setCamaSeleccionada(null);
      setMotivoDerivacion('');
      setDocumento(null);
      verificarDisponibilidad();
    }
  }, [isOpen, paciente?.id]);
  
  // ============================================
  // VERIFICACIÓN INICIAL
  // ============================================
  
  const verificarDisponibilidad = async () => {
    if (!paciente) return;
    
    setLoading(true);
    try {
      const resultado = await api.verificarDisponibilidadTipoCama(paciente.id);
      
      if (resultado.tiene_tipo_cama) {
        // El hospital tiene el tipo de cama, proceder con búsqueda normal
        // Esto no debería pasar si llegamos aquí, pero manejamos el caso
        onClose();
        showAlert('info', 'El hospital cuenta con el tipo de cama requerido');
      } else {
        // No hay tipo de cama en este hospital
        setMensajeNoDisponible(resultado.mensaje);
        setEstado('sin_tipo_cama');
      }
    } catch (error) {
      console.error('Error verificando disponibilidad:', error);
      showAlert('error', 'Error al verificar disponibilidad');
      onClose();
    } finally {
      setLoading(false);
    }
  };
  
  // ============================================
  // BÚSQUEDA EN RED
  // ============================================
  
  const buscarEnRed = async () => {
    if (!paciente) return;
    
    setLoading(true);
    setEstado('buscando_red');
    
    try {
      const resultado = await api.buscarCamasEnRed(paciente.id);
      
      if (resultado.encontradas) {
        setCamasEncontradas(resultado.camas);
        setEstado('resultados');
      } else {
        setEstado('sin_resultados');
      }
    } catch (error) {
      console.error('Error buscando en red:', error);
      showAlert('error', 'Error al buscar camas en la red');
      setEstado('sin_tipo_cama');
    } finally {
      setLoading(false);
    }
  };
  
  // ============================================
  // SELECCIÓN DE CAMA
  // ============================================
  
  const seleccionarCama = (cama: CamaDisponibleRed) => {
    setCamaSeleccionada(cama);
    setEstado('formulario_derivacion');
  };
  
  const volverAResultados = () => {
    setCamaSeleccionada(null);
    setEstado('resultados');
  };
  
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
  
  const solicitarDerivacion = async () => {
    if (!paciente || !camaSeleccionada) return;
    
    if (!motivoDerivacion.trim()) {
      showAlert('error', 'Debe ingresar un motivo de derivación');
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
      await api.solicitarDerivacion(paciente.id, {
        hospital_destino_id: camaSeleccionada.hospital_id,
        motivo: motivoDerivacion
      });
      
      showAlert('success', `Derivación solicitada a ${camaSeleccionada.hospital_nombre}`);
      
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
  
  // ============================================
  // CANCELAR (mantener cama en espera)
  // ============================================
  
  const cancelarYCerrar = () => {
    // La cama de origen permanece en estado CAMA_EN_ESPERA
    onClose();
  };
  
  // ============================================
  // RENDER SEGÚN ESTADO
  // ============================================
  
  const renderContenido = () => {
    switch (estado) {
      case 'verificando':
      case 'buscando_red':
        return (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
            <p className="text-gray-600">
              {estado === 'verificando' 
                ? 'Verificando disponibilidad...' 
                : 'Buscando camas en la red hospitalaria...'}
            </p>
          </div>
        );
        
      case 'sin_tipo_cama':
        return (
          <div className="space-y-6">
            {/* Alerta */}
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-start gap-3">
              <AlertTriangle className="w-6 h-6 text-amber-500 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-amber-800">
                  Tipo de cama no disponible en este hospital
                </h3>
                <p className="text-sm text-amber-700 mt-1">
                  {mensajeNoDisponible}
                </p>
              </div>
            </div>
            
            {/* Botones */}
            <div className="flex justify-center gap-4">
              <Button
                variant="primary"
                onClick={buscarEnRed}
                loading={loading}
                icon={<Search className="w-4 h-4" />}
              >
                Buscar en otro hospital
              </Button>
              <Button
                variant="secondary"
                onClick={cancelarYCerrar}
              >
                Cancelar
              </Button>
            </div>
            
            <p className="text-xs text-gray-500 text-center">
              Al cancelar, la cama de origen quedará en estado "Cama en espera"
            </p>
          </div>
        );
        
      case 'resultados':
        return (
          <div className="space-y-4">
            {/* Header */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-3">
              <CheckCircle className="w-6 h-6 text-green-500" />
              <div>
                <h3 className="font-semibold text-green-800">Camas encontradas</h3>
                <p className="text-sm text-green-700">
                  Se encontraron {camasEncontradas.length} cama(s) disponible(s) en la red
                </p>
              </div>
            </div>
            
            {/* Lista de camas */}
            <div className="max-h-80 overflow-y-auto space-y-2">
              {camasEncontradas.map((cama) => (
                <div 
                  key={cama.cama_id}
                  className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Building2 className="w-4 h-4 text-blue-600" />
                        <span className="font-semibold text-gray-800">
                          {cama.hospital_nombre}
                        </span>
                        <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">
                          {cama.hospital_codigo}
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div className="flex items-center gap-1.5 text-gray-600">
                          <Bed className="w-3.5 h-3.5" />
                          <span>Cama: {cama.cama_identificador}</span>
                        </div>
                        <div className="flex items-center gap-1.5 text-gray-600">
                          <MapPin className="w-3.5 h-3.5" />
                          <span>Servicio: {cama.servicio_nombre}</span>
                        </div>
                        <div className="text-gray-500">
                          Tipo: {cama.servicio_tipo}
                        </div>
                        <div className="text-gray-500">
                          Sala: {cama.sala_es_individual ? 'Individual' : 'Compartida'}
                        </div>
                      </div>
                    </div>
                    
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => seleccionarCama(cama)}
                      icon={<Send className="w-3.5 h-3.5" />}
                    >
                      Iniciar derivación
                    </Button>
                  </div>
                </div>
              ))}
            </div>
            
            {/* Botón cancelar */}
            <div className="flex justify-end pt-4 border-t">
              <Button variant="secondary" onClick={cancelarYCerrar}>
                Cancelar
              </Button>
            </div>
          </div>
        );
        
      case 'sin_resultados':
        return (
          <div className="space-y-6">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
              <AlertTriangle className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-red-800">
                  Sin camas disponibles en la red
                </h3>
                <p className="text-sm text-red-700 mt-1">
                  No se encontraron camas compatibles en ningún hospital de la red en este momento.
                </p>
              </div>
            </div>
            
            <div className="flex justify-center">
              <Button variant="secondary" onClick={cancelarYCerrar}>
                Cerrar
              </Button>
            </div>
            
            <p className="text-xs text-gray-500 text-center">
              La cama de origen permanecerá en estado "Cama en espera"
            </p>
          </div>
        );
        
      case 'formulario_derivacion':
        if (!camaSeleccionada) return null;
        
        return (
          <div className="space-y-6">
            {/* Botón volver */}
            <button
              onClick={volverAResultados}
              className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
            >
              <ArrowLeft className="w-4 h-4" />
              Volver a las camas disponibles
            </button>
            
            {/* Info hospital destino */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-semibold text-blue-800 mb-2">
                Derivar a:
              </h3>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="flex items-center gap-1.5">
                  <Building2 className="w-4 h-4 text-blue-600" />
                  <span className="font-medium">{camaSeleccionada.hospital_nombre}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Bed className="w-4 h-4 text-blue-600" />
                  <span>Cama {camaSeleccionada.cama_identificador}</span>
                </div>
                <div className="text-gray-600">
                  Servicio: {camaSeleccionada.servicio_nombre}
                </div>
                <div className="text-gray-600">
                  Tipo: {camaSeleccionada.servicio_tipo}
                </div>
              </div>
            </div>
            
            {/* Formulario */}
            <div className="space-y-4">
              {/* Motivo */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Motivo de derivación <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={motivoDerivacion}
                  onChange={(e) => setMotivoDerivacion(e.target.value)}
                  rows={4}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                  placeholder="Describa el motivo de la derivación..."
                />
              </div>
              
              {/* Documento adjunto */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
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
                        className="mt-2 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg cursor-pointer hover:bg-blue-100"
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
                          <p className="text-xs text-gray-500">
                            {(documento.size / 1024 / 1024).toFixed(2)} MB
                          </p>
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
            </div>
            
            {/* Botones */}
            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button
                variant="secondary"
                onClick={volverAResultados}
              >
                Cancelar
              </Button>
              <Button
                variant="primary"
                onClick={solicitarDerivacion}
                loading={loading}
                disabled={!motivoDerivacion.trim()}
                icon={<Send className="w-4 h-4" />}
              >
                Derivar paciente
              </Button>
            </div>
          </div>
        );
        
      default:
        return null;
    }
  };
  
  // ============================================
  // RENDER
  // ============================================
  
  const getTitle = () => {
    switch (estado) {
      case 'verificando':
        return 'Verificando disponibilidad';
      case 'sin_tipo_cama':
        return 'Tipo de cama no disponible';
      case 'buscando_red':
        return 'Buscando en la red';
      case 'resultados':
        return 'Camas disponibles en la red';
      case 'sin_resultados':
        return 'Sin resultados';
      case 'formulario_derivacion':
        return 'Solicitar derivación';
      default:
        return 'Búsqueda de cama';
    }
  };
  
  return (
    <Modal
      isOpen={isOpen}
      onClose={cancelarYCerrar}
      title={getTitle()}
      size={estado === 'resultados' ? 'lg' : 'md'}
    >
      <div className="p-4">
        {/* Info del paciente */}
        {paciente && (
          <div className="mb-4 p-3 bg-gray-50 rounded-lg border">
            <p className="text-sm font-medium text-gray-800">
              Paciente: {paciente.nombre}
            </p>
            <p className="text-xs text-gray-500">
              RUN: {paciente.run} | Complejidad: {paciente.complejidad_requerida || 'No definida'}
            </p>
          </div>
        )}
        
        {renderContenido()}
      </div>
    </Modal>
  );
}

export default ModalBusquedaCamaRed;