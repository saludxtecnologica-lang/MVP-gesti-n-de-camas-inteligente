import { useState } from 'react';
import { User, FileText, Stethoscope, AlertTriangle, RefreshCw, Send } from 'lucide-react';
import { Modal, Badge, Button } from '../common';
import { useModal } from '../../context/ModalContext';
import type { Paciente } from '../../types';
import { 
  formatComplejidad, 
  formatTipoAislamiento, 
  formatTipoEnfermedad,
  formatSexo,
  safeJsonParse 
} from '../../utils';
import { getDocumentoUrl } from '../../services/api';
import { ModalDerivacionDirecta } from './ModalDerivacionDirecta';

interface ModalPacienteProps {
  isOpen: boolean;
  onClose: () => void;
  paciente: Paciente | null;
}

export function ModalPaciente({ isOpen, onClose, paciente }: ModalPacienteProps) {
  const { openModal } = useModal();
  
  // Estado para modal de derivación
  const [modalDerivacionAbierto, setModalDerivacionAbierto] = useState(false);
  
  if (!paciente) return null;

  // Parsear todos los requerimientos
  const casosEspeciales = safeJsonParse(paciente.casos_especiales);
  const reqNoDefinen = safeJsonParse(paciente.requerimientos_no_definen);
  const reqBaja = safeJsonParse(paciente.requerimientos_baja);
  const reqUti = safeJsonParse(paciente.requerimientos_uti);
  const reqUci = safeJsonParse(paciente.requerimientos_uci);

  // Combinar todos los requerimientos clínicos actuales
  const todosRequerimientos = [
    ...reqUci.map((req: string) => ({ req, nivel: 'UCI', color: 'red' })),
    ...reqUti.map((req: string) => ({ req, nivel: 'UTI', color: 'orange' })),
    ...reqBaja.map((req: string) => ({ req, nivel: 'Baja', color: 'yellow' })),
    ...reqNoDefinen.map((req: string) => ({ req, nivel: 'No define', color: 'gray' }))
  ];

  // Verificar si el paciente ya tiene una derivación activa
  const tieneDerivacionActiva = paciente.derivacion_solicitada && 
    (paciente.derivacion_estado === 'pendiente' || paciente.derivacion_estado === 'aceptada');

  // Handler para reevaluar - usa openModal directamente
  const handleReevaluar = () => {
    if (paciente) {
      onClose(); // Cerrar este modal primero
      openModal('reevaluar', { paciente }); // Abrir modal de reevaluar
    }
  };

  // Handler para abrir modal de derivación
  const handleAbrirDerivacion = () => {
    setModalDerivacionAbierto(true);
  };

  // Handler cuando se completa la derivación
  const handleDerivacionCompletada = () => {
    setModalDerivacionAbierto(false);
    onClose();
  };

  return (
    <>
      <Modal isOpen={isOpen} onClose={onClose} title="Información del Paciente" size="lg">
        <div className="space-y-6">
          
          {/* ============================================ */}
          {/* SECCIÓN: DATOS DEL PACIENTE */}
          {/* ============================================ */}
          <section>
            <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <User className="w-4 h-4" />
              Datos del Paciente
            </h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Nombre:</span>
                <span className="ml-2 font-medium">{paciente.nombre}</span>
              </div>
              <div>
                <span className="text-gray-500">Edad:</span>
                <span className="ml-2 font-medium">{paciente.edad} años</span>
              </div>
              <div>
                <span className="text-gray-500">RUN:</span>
                <span className="ml-2 font-medium">{paciente.run}</span>
              </div>
              <div>
                <span className="text-gray-500">Sexo:</span>
                <span className="ml-2 font-medium">{formatSexo(paciente.sexo)}</span>
              </div>
              {paciente.es_embarazada && (
                <div className="col-span-2">
                  <Badge variant="purple">Embarazada</Badge>
                </div>
              )}
            </div>
          </section>

          {/* ============================================ */}
          {/* SECCIÓN: INFORMACIÓN CLÍNICA */}
          {/* ============================================ */}
          <section>
            <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <Stethoscope className="w-4 h-4" />
              Información Clínica
            </h4>
            <div className="space-y-3 text-sm">
              <div>
                <span className="text-gray-500">Diagnóstico:</span>
                <p className="mt-1 text-gray-800 bg-gray-50 p-2 rounded">{paciente.diagnostico || 'Sin diagnóstico registrado'}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-gray-500">Tipo de Enfermedad:</span>
                  <p className="mt-1 font-medium">{formatTipoEnfermedad(paciente.tipo_enfermedad)}</p>
                </div>
                <div>
                  <span className="text-gray-500">Aislamiento:</span>
                  <Badge 
                    variant={paciente.tipo_aislamiento !== 'ninguno' ? 'danger' : 'default'} 
                    className="ml-2"
                  >
                    {formatTipoAislamiento(paciente.tipo_aislamiento)}
                  </Badge>
                </div>
              </div>
              <div>
                <span className="text-gray-500">Complejidad Requerida:</span>
                <Badge 
                  variant={
                    paciente.complejidad_requerida === 'uci' ? 'danger' :
                    paciente.complejidad_requerida === 'uti' ? 'warning' :
                    'default'
                  }
                  className="ml-2"
                >
                  {formatComplejidad(paciente.complejidad_requerida || 'ninguna')}
                </Badge>
              </div>
            </div>
          </section>

          {/* ============================================ */}
          {/* SECCIÓN: REQUERIMIENTOS CLÍNICOS ACTUALES */}
          {/* ============================================ */}
          {todosRequerimientos.length > 0 && (
            <section>
              <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Requerimientos Clínicos Actuales
              </h4>
              <div className="space-y-2 text-sm">
                {reqUci.length > 0 && (
                  <div className="p-2 bg-red-50 rounded-lg border border-red-200">
                    <span className="text-red-700 font-medium">UCI:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {reqUci.map((req: string, idx: number) => (
                        <span key={idx} className="px-2 py-0.5 bg-red-100 text-red-800 text-xs rounded">
                          {req}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {reqUti.length > 0 && (
                  <div className="p-2 bg-orange-50 rounded-lg border border-orange-200">
                    <span className="text-orange-700 font-medium">UTI:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {reqUti.map((req: string, idx: number) => (
                        <span key={idx} className="px-2 py-0.5 bg-orange-100 text-orange-800 text-xs rounded">
                          {req}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {reqBaja.length > 0 && (
                  <div className="p-2 bg-yellow-50 rounded-lg border border-yellow-200">
                    <span className="text-yellow-700 font-medium">Baja Complejidad:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {reqBaja.map((req: string, idx: number) => (
                        <span key={idx} className="px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded">
                          {req}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {reqNoDefinen.length > 0 && (
                  <div className="p-2 bg-gray-50 rounded-lg border border-gray-200">
                    <span className="text-gray-600 font-medium">No definen complejidad:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {reqNoDefinen.map((req: string, idx: number) => (
                        <span key={idx} className="px-2 py-0.5 bg-gray-100 text-gray-700 text-xs rounded">
                          {req}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Campos especiales de observación y monitorización */}
              {paciente.motivo_observacion && (
                <div className="mt-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                  <span className="font-medium text-yellow-800">Observación Clínica:</span>
                  <p className="text-yellow-700 mt-1">{paciente.motivo_observacion}</p>
                  {paciente.justificacion_observacion && (
                    <p className="text-yellow-600 text-xs mt-1">
                      <span className="font-medium">Justificación:</span> {paciente.justificacion_observacion}
                    </p>
                  )}
                </div>
              )}
              {paciente.motivo_monitorizacion && (
                <div className="mt-3 p-3 bg-orange-50 rounded-lg border border-orange-200">
                  <span className="font-medium text-orange-800">Monitorización Continua:</span>
                  <p className="text-orange-700 mt-1">{paciente.motivo_monitorizacion}</p>
                  {paciente.justificacion_monitorizacion && (
                    <p className="text-orange-600 text-xs mt-1">
                      <span className="font-medium">Justificación:</span> {paciente.justificacion_monitorizacion}
                    </p>
                  )}
                </div>
              )}
            </section>
          )}

          {/* ============================================ */}
          {/* SECCIÓN: REQUERIMIENTOS ESPECIALES (Casos Especiales) */}
          {/* ============================================ */}
          {casosEspeciales.length > 0 && (
            <section>
              <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                Requerimientos Especiales
              </h4>
              <div className="flex flex-wrap gap-2">
                {casosEspeciales.map((caso: string, idx: number) => (
                  <Badge key={idx} variant="warning">{caso}</Badge>
                ))}
              </div>
            </section>
          )}

          {/* ============================================ */}
          {/* SECCIÓN: NOTAS ADICIONALES */}
          {/* ============================================ */}
          {paciente.notas_adicionales && (
            <section>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Notas Adicionales</h4>
              <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded">
                {paciente.notas_adicionales}
              </p>
            </section>
          )}

          {/* ============================================ */}
          {/* SECCIÓN: DOCUMENTO ADJUNTO */}
          {/* ============================================ */}
          {paciente.documento_adjunto && (
            <section>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Documento Adjunto</h4>
              <a
                href={getDocumentoUrl(paciente.documento_adjunto)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 hover:underline"
              >
                <FileText className="w-4 h-4" />
                Ver documento
              </a>
            </section>
          )}

          {/* ============================================ */}
          {/* SECCIÓN: ESTADO DE DERIVACIÓN (si existe) */}
          {/* ============================================ */}
          {paciente.derivacion_solicitada && (
            <section className="bg-purple-50 p-4 rounded-lg border border-purple-200">
              <h4 className="text-sm font-semibold text-purple-800 mb-2 flex items-center gap-2">
                <Send className="w-4 h-4" />
                Derivación en Proceso
              </h4>
              <div className="text-sm text-purple-700 space-y-1">
                <p>
                  <span className="font-medium">Estado:</span>{' '}
                  <Badge variant={paciente.derivacion_estado === 'aceptada' ? 'success' : 'info'}>
                    {paciente.derivacion_estado}
                  </Badge>
                </p>
                {paciente.derivacion_motivo && (
                  <p><span className="font-medium">Motivo:</span> {paciente.derivacion_motivo}</p>
                )}
              </div>
            </section>
          )}

          {/* ============================================ */}
          {/* SECCIÓN: ALTA SOLICITADA (si existe) */}
          {/* ============================================ */}
          {paciente.alta_solicitada && (
            <section className="bg-teal-50 p-4 rounded-lg border border-teal-200">
              <h4 className="text-sm font-semibold text-teal-800 mb-2">Alta Solicitada</h4>
              {paciente.alta_motivo && (
                <p className="text-sm text-teal-700">
                  <span className="font-medium">Motivo:</span> {paciente.alta_motivo}
                </p>
              )}
            </section>
          )}

          {/* ============================================ */}
          {/* BOTONES DE ACCIÓN: REEVALUAR Y DERIVAR */}
          {/* ============================================ */}
          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button variant="secondary" onClick={onClose}>
              Cerrar
            </Button>
            <Button 
              variant="primary" 
              onClick={handleReevaluar}
              icon={<RefreshCw className="w-4 h-4" />}
            >
              Reevaluar
            </Button>
            <Button 
              variant="warning" 
              onClick={handleAbrirDerivacion}
              icon={<Send className="w-4 h-4" />}
              disabled={tieneDerivacionActiva}
              title={tieneDerivacionActiva ? 'Ya existe una derivación en proceso' : 'Solicitar derivación'}
            >
              Derivar
            </Button>
          </div>
        </div>
      </Modal>

      {/* ============================================ */}
      {/* MODAL DE DERIVACIÓN */}
      {/* ============================================ */}
      <ModalDerivacionDirecta
        isOpen={modalDerivacionAbierto}
        onClose={() => setModalDerivacionAbierto(false)}
        paciente={paciente}
        onDerivacionCompletada={handleDerivacionCompletada}
      />
    </>
  );
}