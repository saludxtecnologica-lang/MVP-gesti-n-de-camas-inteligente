/**
 * ModalDerivadoPaciente.tsx
 * 
 * Modal para visualizar información de pacientes derivados (entrada o salida).
 * Muestra información del paciente + datos de origen/destino de la derivación.
 * 
 * NOTA: Este modal es DIFERENTE de:
 * - ModalPaciente: Ver info genérica de paciente
 * - ModalDerivacionDirecta: CREAR/solicitar una derivación
 * 
 * Este modal es para VER derivaciones existentes con info de origen/destino.
 * 
 * Ubicación: src/components/modales/ModalDerivadoPaciente.tsx
 */
import { useState } from 'react';
import {
  User, FileText, Stethoscope, AlertTriangle, Send,
  Building2, ArrowRight, Eye, Heart, Gavel, Files
} from 'lucide-react';
import { Modal, Badge, Button } from '../common';
import type { Paciente } from '../../types';
import { 
  formatComplejidad, 
  formatTipoAislamiento, 
  formatTipoEnfermedad,
  formatSexo,
  safeJsonParse 
} from '../../utils';
import { getDocumentoUrl } from '../../services/api';

// ============================================
// ICONOS DE CASOS ESPECIALES (reutilizable)
// ============================================
export const ICONOS_CASOS_ESPECIALES: Record<string, { icono: React.ElementType; color: string }> = {
  'Espera cardiocirugía': { icono: Heart, color: 'text-red-500' },
  'Socio-judicial': { icono: Gavel, color: 'text-amber-600' },
  'Socio-sanitario': { icono: Files, color: 'text-blue-500' },
};

// ============================================
// TIPOS
// ============================================
export interface DerivadoInfo {
  hospital_origen_id?: string;
  hospital_origen_nombre?: string;
  hospital_destino_id?: string;
  hospital_destino_nombre?: string;
  cama_origen_identificador?: string | null;
  servicio_origen_nombre?: string | null;
  motivo_derivacion?: string;
  estado_derivacion?: string;
}

interface ModalDerivadoPacienteProps {
  isOpen: boolean;
  onClose: () => void;
  paciente: Paciente | null;
  derivadoInfo?: DerivadoInfo;
  tipo: 'entrada' | 'salida';
}

// ============================================
// COMPONENTE PRINCIPAL
// ============================================
export function ModalDerivadoPaciente({
  isOpen,
  onClose,
  paciente,
  derivadoInfo,
  tipo
}: ModalDerivadoPacienteProps) {
  if (!paciente) return null;

  // Parsear todos los requerimientos
  const casosEspeciales = safeJsonParse(paciente.casos_especiales);
  const reqNoDefinen = safeJsonParse(paciente.requerimientos_no_definen);
  const reqBaja = safeJsonParse(paciente.requerimientos_baja);
  const reqUti = safeJsonParse(paciente.requerimientos_uti);
  const reqUci = safeJsonParse(paciente.requerimientos_uci);

  // Combinar todos los requerimientos clínicos
  const todosRequerimientos = [
    ...reqUci.map((req: string) => ({ req, nivel: 'UCI', color: 'red' })),
    ...reqUti.map((req: string) => ({ req, nivel: 'UTI', color: 'orange' })),
    ...reqBaja.map((req: string) => ({ req, nivel: 'Baja', color: 'yellow' })),
    ...reqNoDefinen.map((req: string) => ({ req, nivel: 'No define', color: 'gray' }))
  ];

  // Título del modal según el tipo
  const titulo = tipo === 'entrada' 
    ? 'Derivación Entrante - Información del Paciente'
    : 'Derivación Saliente - Información del Paciente';

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={titulo} size="lg">
      <div className="space-y-6">
        
        {/* ============================================ */}
        {/* SECCIÓN: INFORMACIÓN DE DERIVACIÓN */}
        {/* ============================================ */}
        <section className="bg-gradient-to-r from-purple-50 to-indigo-50 p-4 rounded-lg border border-purple-200">
          <h4 className="text-sm font-semibold text-purple-800 mb-3 flex items-center gap-2">
            <Send className="w-4 h-4" />
            Información de Derivación
          </h4>
          
          <div className="flex items-center justify-center gap-4 py-3">
            {/* Origen */}
            <div className="text-center">
              <div className="flex items-center justify-center gap-2 mb-1">
                <Building2 className="w-5 h-5 text-purple-600" />
                <span className="text-xs text-gray-500 uppercase">Origen</span>
              </div>
              <p className="font-semibold text-gray-800">
                {tipo === 'entrada' 
                  ? derivadoInfo?.hospital_origen_nombre || 'Hospital origen'
                  : 'Este hospital'
                }
              </p>
              {derivadoInfo?.servicio_origen_nombre && (
                <p className="text-xs text-gray-500">{derivadoInfo.servicio_origen_nombre}</p>
              )}
              {derivadoInfo?.cama_origen_identificador && (
                <p className="text-xs text-gray-400">Cama: {derivadoInfo.cama_origen_identificador}</p>
              )}
            </div>
            
            {/* Flecha */}
            <div className="flex flex-col items-center">
              <ArrowRight className="w-8 h-8 text-purple-400" />
              <Badge variant={
                derivadoInfo?.estado_derivacion === 'aceptada' ? 'success' :
                derivadoInfo?.estado_derivacion === 'pendiente' ? 'warning' :
                'default'
              }>
                {derivadoInfo?.estado_derivacion || 'pendiente'}
              </Badge>
            </div>
            
            {/* Destino */}
            <div className="text-center">
              <div className="flex items-center justify-center gap-2 mb-1">
                <Building2 className="w-5 h-5 text-indigo-600" />
                <span className="text-xs text-gray-500 uppercase">Destino</span>
              </div>
              <p className="font-semibold text-gray-800">
                {tipo === 'salida' 
                  ? derivadoInfo?.hospital_destino_nombre || 'Hospital destino'
                  : 'Este hospital'
                }
              </p>
            </div>
          </div>
          
          {/* Motivo de derivación */}
          {derivadoInfo?.motivo_derivacion && (
            <div className="mt-3 pt-3 border-t border-purple-200">
              <span className="text-sm font-medium text-purple-700">Motivo de Derivación:</span>
              <p className="mt-1 text-sm text-purple-900 bg-white/50 p-2 rounded">
                {derivadoInfo.motivo_derivacion}
              </p>
            </div>
          )}
        </section>

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
              <p className="mt-1 text-gray-800 bg-gray-50 p-2 rounded">
                {paciente.diagnostico || 'Sin diagnóstico registrado'}
              </p>
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
        {/* SECCIÓN: REQUERIMIENTOS CLÍNICOS */}
        {/* ============================================ */}
        {todosRequerimientos.length > 0 && (
          <section>
            <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Requerimientos Clínicos
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
          </section>
        )}

        {/* ============================================ */}
        {/* SECCIÓN: REQUERIMIENTOS ESPECIALES */}
        {/* ============================================ */}
        {casosEspeciales.length > 0 && (
          <section>
            <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              Requerimientos Especiales
            </h4>
            <div className="flex flex-wrap gap-2">
              {casosEspeciales.map((caso: string, idx: number) => {
                const config = ICONOS_CASOS_ESPECIALES[caso];
                const IconoCaso = config?.icono;
                return (
                  <Badge key={idx} variant="warning" className="flex items-center gap-1">
                    {IconoCaso && <IconoCaso className={`w-3.5 h-3.5 ${config.color}`} />}
                    {caso}
                  </Badge>
                );
              })}
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
          <section className="bg-blue-50 p-4 rounded-lg border border-blue-200">
            <h4 className="text-sm font-semibold text-blue-800 mb-2 flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Documento Adjunto
            </h4>
            <div className="flex items-center justify-between">
              <span className="text-sm text-blue-700">{paciente.documento_adjunto}</span>
              <a
                href={getDocumentoUrl(paciente.documento_adjunto)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Eye className="w-4 h-4" />
                Ver documento
              </a>
            </div>
          </section>
        )}

        {/* ============================================ */}
        {/* BOTONES DE ACCIÓN */}
        {/* ============================================ */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          <Button variant="secondary" onClick={onClose}>
            Cerrar
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export default ModalDerivadoPaciente;