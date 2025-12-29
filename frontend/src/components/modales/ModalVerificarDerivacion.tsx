import { useState, useEffect } from 'react';
import { 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  Building2,
  AlertCircle
} from 'lucide-react';
import { Modal, Button } from '../common';
import * as api from '../../services/api';

// ============================================
// TIPOS
// ============================================

interface ModalVerificarDerivacionProps {
  isOpen: boolean;
  onClose: () => void;
  pacienteId: string | null;
  pacienteNombre: string;
  hospitalDestinoId: string;
  hospitalDestinoNombre: string;
  onConfirmar: () => void;  // Se llama si la derivación es viable y el usuario confirma
}

// ============================================
// COMPONENTE
// ============================================

export function ModalVerificarDerivacion({
  isOpen,
  onClose,
  pacienteId,
  pacienteNombre,
  hospitalDestinoId,
  hospitalDestinoNombre,
  onConfirmar
}: ModalVerificarDerivacionProps) {
  const [loading, setLoading] = useState(true);
  const [esViable, setEsViable] = useState(false);
  const [mensaje, setMensaje] = useState('');
  const [motivosRechazo, setMotivosRechazo] = useState<string[]>([]);
  
  // Verificar viabilidad al abrir
  useEffect(() => {
    if (isOpen && pacienteId && hospitalDestinoId) {
      verificarViabilidad();
    }
  }, [isOpen, pacienteId, hospitalDestinoId]);
  
  const verificarViabilidad = async () => {
    if (!pacienteId || !hospitalDestinoId) return;
    
    setLoading(true);
    try {
      const resultado = await api.verificarViabilidadDerivacion(
        pacienteId,
        hospitalDestinoId
      );
      
      setEsViable(resultado.es_viable);
      setMensaje(resultado.mensaje);
      setMotivosRechazo(resultado.motivos_rechazo || []);
      
    } catch (error) {
      console.error('Error verificando viabilidad:', error);
      setEsViable(false);
      setMensaje('Error al verificar la viabilidad de la derivación');
      setMotivosRechazo([error instanceof Error ? error.message : 'Error desconocido']);
    } finally {
      setLoading(false);
    }
  };
  
  const handleConfirmar = () => {
    if (esViable) {
      onConfirmar();
    }
  };
  
  // ============================================
  // RENDER
  // ============================================
  
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Verificación de derivación"
      size="md"
    >
      <div className="p-6 space-y-6">
        {/* Info del paciente y hospital */}
        <div className="bg-gray-50 rounded-lg p-4 space-y-2">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-500">Paciente:</span>
            <span className="font-medium text-gray-800">{pacienteNombre}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Building2 className="w-4 h-4 text-gray-400" />
            <span className="text-gray-500">Hospital destino:</span>
            <span className="font-medium text-gray-800">{hospitalDestinoNombre}</span>
          </div>
        </div>
        
        {/* Estado de carga */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-8">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mb-4"></div>
            <p className="text-gray-600">Verificando viabilidad de la derivación...</p>
          </div>
        ) : (
          <>
            {/* Resultado */}
            {esViable ? (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <CheckCircle className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-semibold text-green-800">
                      Derivación viable
                    </h3>
                    <p className="text-sm text-green-700 mt-1">
                      {mensaje}
                    </p>
                    <p className="text-sm text-green-600 mt-2">
                      El hospital destino cuenta con las capacidades necesarias para atender al paciente.
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <XCircle className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <h3 className="font-semibold text-red-800">
                      Derivación no viable
                    </h3>
                    <p className="text-sm text-red-700 mt-1">
                      {mensaje}
                    </p>
                    
                    {motivosRechazo.length > 0 && (
                      <div className="mt-3 space-y-2">
                        <p className="text-sm font-medium text-red-800">
                          Motivos:
                        </p>
                        <ul className="list-disc list-inside text-sm text-red-700 space-y-1">
                          {motivosRechazo.map((motivo, idx) => (
                            <li key={idx}>{motivo}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
            
            {/* Nota informativa para no viable */}
            {!esViable && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-amber-700">
                  Considere derivar a un hospital que cuente con las capacidades requeridas 
                  o contactar a la coordinación para gestionar la derivación.
                </p>
              </div>
            )}
          </>
        )}
        
        {/* Botones */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          <Button variant="secondary" onClick={onClose}>
            {esViable ? 'Cancelar' : 'Cerrar'}
          </Button>
          {esViable && !loading && (
            <Button 
              variant="primary" 
              onClick={handleConfirmar}
            >
              Continuar con derivación
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}

export default ModalVerificarDerivacion;