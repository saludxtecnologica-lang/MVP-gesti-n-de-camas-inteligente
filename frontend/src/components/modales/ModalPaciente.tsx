/**
 * MODAL DE PACIENTE ACTUALIZADO
 * REEMPLAZAR: src/components/modales/ModalPaciente.tsx
 * 
 * Incluye nueva sección: Información de Traslado con teléfonos
 * 
 * CORRECCIONES:
 * - Los teléfonos de urgencias y ambulatorio ahora están en el Hospital, no en ConfiguracionSistema
 * - Se obtienen los teléfonos desde el hospital del paciente usando la lista de hospitales del contexto
 */
import { useState, useEffect } from 'react';
import { 
  User, FileText, Stethoscope, AlertTriangle, RefreshCw, Send, 
  Heart, Gavel, Files, Clock, Phone, ArrowRight, Building2, BedDouble 
} from 'lucide-react';
import { Modal, Badge, Button, Spinner } from '../common';
import { useModal } from '../../context/ModalContext';
import { useApp } from '../../context/AppContext';
import type { Paciente } from '../../types';
import { 
  formatComplejidad, 
  formatTipoAislamiento, 
  formatTipoEnfermedad,
  formatSexo,
  safeJsonParse 
} from '../../utils';
import { getDocumentoUrl, getInfoTrasladoPaciente } from '../../services/api';
import { ModalDerivacionDirecta } from './ModalDerivacionDirecta';

// ============================================
// ICONOS DE CASOS ESPECIALES
// ============================================
const ICONOS_CASOS_ESPECIALES: Record<string, React.ElementType> = {
  'Espera cardiocirugía': Heart,
  'Socio-judicial': Gavel,
  'Socio-sanitario': Files,
};

// ============================================
// INTERFACE PARA INFO DE TRASLADO
// ============================================
interface InfoTraslado {
  origen_tipo: string | null;
  origen_hospital_nombre: string | null;
  origen_hospital_codigo: string | null;
  origen_servicio_nombre: string | null;
  origen_servicio_telefono: string | null;
  origen_cama_identificador: string | null;
  destino_servicio_nombre: string | null;
  destino_servicio_telefono: string | null;
  destino_cama_identificador: string | null;
  destino_hospital_nombre: string | null;
  tiene_cama_origen: boolean;
  tiene_cama_destino: boolean;
  en_traslado: boolean;
}

interface ModalPacienteProps {
  isOpen: boolean;
  onClose: () => void;
  paciente: Paciente | null;
}

export function ModalPaciente({ isOpen, onClose, paciente }: ModalPacienteProps) {
  const { openModal } = useModal();
  const { camas, hospitales } = useApp();
  
  // Estado para modal de derivación
  const [modalDerivacionAbierto, setModalDerivacionAbierto] = useState(false);
  
  // Estado para información de traslado
  const [infoTraslado, setInfoTraslado] = useState<InfoTraslado | null>(null);
  const [cargandoInfoTraslado, setCargandoInfoTraslado] = useState(false);
  
  // Función para formatear tiempo restante
  const formatTiempoRestante = (segundos: number | null | undefined): string => {
    if (segundos === null || segundos === undefined) return '';
    if (segundos <= 0) return 'Completado';
    
    const horas = Math.floor(segundos / 3600);
    const minutos = Math.floor((segundos % 3600) / 60);
    
    if (horas > 0) {
      return `${horas}h ${minutos}m restantes`;
    }
    return `${minutos} minutos restantes`;
  };

  // Obtener el hospital del paciente (para acceder a sus teléfonos)
  const hospitalDelPaciente = paciente?.hospital_id 
    ? hospitales.find(h => h.id === paciente.hospital_id) 
    : null;

  // Cargar información de traslado cuando se abre el modal
  useEffect(() => {
    if (isOpen && paciente?.id) {
      cargarInfoTraslado();
    } else {
      setInfoTraslado(null);
    }
  }, [isOpen, paciente?.id]);

  const cargarInfoTraslado = async () => {
    if (!paciente?.id) return;
    
    try {
      setCargandoInfoTraslado(true);
      const info = await getInfoTrasladoPaciente(paciente.id);
      setInfoTraslado(info);
    } catch (error) {
      // Si falla, construir info localmente desde los datos del paciente
      construirInfoTrasladoLocal();
    } finally {
      setCargandoInfoTraslado(false);
    }
  };

  // Construir info de traslado desde datos locales si el endpoint falla
  const construirInfoTrasladoLocal = () => {
    if (!paciente) return;

    const info: InfoTraslado = {
      origen_tipo: null,
      origen_hospital_nombre: null,
      origen_hospital_codigo: null,
      origen_servicio_nombre: null,
      origen_servicio_telefono: null,
      origen_cama_identificador: null,
      destino_servicio_nombre: null,
      destino_servicio_telefono: null,
      destino_cama_identificador: null,
      destino_hospital_nombre: null,
      tiene_cama_origen: !!paciente.cama_id,
      tiene_cama_destino: !!paciente.cama_destino_id,
      en_traslado: !!paciente.cama_destino_id
    };

    // Determinar origen
    if (paciente.tipo_paciente === 'derivado' || paciente.derivacion_estado === 'aceptada') {
      info.origen_tipo = 'derivado';
      info.origen_hospital_nombre = paciente.origen_hospital_nombre || null;
      info.origen_servicio_nombre = paciente.origen_servicio_nombre || null;
    } else if (paciente.cama_id) {
      info.origen_tipo = 'hospitalizado';
      const camaOrigen = camas.find(c => c.id === paciente.cama_id);
      if (camaOrigen) {
        info.origen_servicio_nombre = camaOrigen.servicio_nombre || null;
        info.origen_cama_identificador = camaOrigen.identificador;
      }
    } else if (paciente.tipo_paciente === 'urgencia') {
      info.origen_tipo = 'urgencia';
      info.origen_servicio_nombre = 'Urgencias';
      // Teléfono de urgencias del hospital del paciente
      info.origen_servicio_telefono = hospitalDelPaciente?.telefono_urgencias || null;
    } else if (paciente.tipo_paciente === 'ambulatorio') {
      info.origen_tipo = 'ambulatorio';
      info.origen_servicio_nombre = 'Ambulatorio';
      // Teléfono de ambulatorio del hospital del paciente
      info.origen_servicio_telefono = hospitalDelPaciente?.telefono_ambulatorio || null;
    }

    // Determinar destino
    if (paciente.cama_destino_id) {
      const camaDestino = camas.find(c => c.id === paciente.cama_destino_id);
      if (camaDestino) {
        info.destino_servicio_nombre = camaDestino.servicio_nombre || null;
        info.destino_cama_identificador = camaDestino.identificador;
      }
    }

    setInfoTraslado(info);
  };

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

  // Verificar si mostrar sección de traslado
  const mostrarSeccionTraslado = infoTraslado && (
    infoTraslado.en_traslado || 
    infoTraslado.tiene_cama_destino ||
    infoTraslado.origen_tipo === 'urgencia' ||
    infoTraslado.origen_tipo === 'ambulatorio' ||
    infoTraslado.origen_tipo === 'derivado'
  );

  // Handlers
  const handleReevaluar = () => {
    onClose();
    openModal('reevaluar', { paciente });
  };

  const handleAbrirDerivacion = () => {
    setModalDerivacionAbierto(true);
  };

  const handleDerivacionCompletada = () => {
    setModalDerivacionAbierto(false);
    onClose();
  };

  // Función para formatear origen
  const formatOrigen = () => {
    if (!infoTraslado) return null;
    
    const partes: string[] = [];
    
    if (infoTraslado.origen_tipo === 'derivado' && infoTraslado.origen_hospital_nombre) {
      partes.push(infoTraslado.origen_hospital_nombre);
    } else if (infoTraslado.origen_tipo === 'urgencia') {
      partes.push('Urgencias');
      if (hospitalDelPaciente) {
        partes.push(hospitalDelPaciente.nombre);
      }
    } else if (infoTraslado.origen_tipo === 'ambulatorio') {
      partes.push('Ambulatorio');
      if (hospitalDelPaciente) {
        partes.push(hospitalDelPaciente.nombre);
      }
    } else if (infoTraslado.origen_servicio_nombre) {
      partes.push(infoTraslado.origen_servicio_nombre);
    }
    
    if (infoTraslado.origen_cama_identificador) {
      partes.push(`Cama ${infoTraslado.origen_cama_identificador}`);
    }
    
    return partes.length > 0 ? partes.join(', ') : 'No especificado';
  };

  // Función para formatear destino
  const formatDestino = () => {
    if (!infoTraslado || !infoTraslado.tiene_cama_destino) return null;
    
    const partes: string[] = [];
    
    if (infoTraslado.destino_servicio_nombre) {
      partes.push(infoTraslado.destino_servicio_nombre);
    }
    
    if (infoTraslado.destino_cama_identificador) {
      partes.push(`Cama ${infoTraslado.destino_cama_identificador}`);
    }
    
    return partes.length > 0 ? partes.join(', ') : 'No especificado';
  };

  return (
    <>
      <Modal isOpen={isOpen} onClose={onClose} title="Detalle del Paciente" size="lg">
        <div className="space-y-6">
          {/* ============================================ */}
          {/* SECCIÓN: INFORMACIÓN BÁSICA */}
          {/* ============================================ */}
          <section className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
              <User className="w-6 h-6 text-blue-600" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-800">{paciente.nombre}</h3>
              <div className="mt-1 text-sm text-gray-600 space-y-1">
                <p><span className="font-medium">RUT:</span> {paciente.rut || 'No registrado'}</p>
                <p><span className="font-medium">Edad:</span> {paciente.edad} años</p>
                <p><span className="font-medium">Sexo:</span> {formatSexo(paciente.sexo)}</p>
                {paciente.prevision && (
                  <p><span className="font-medium">Previsión:</span> {paciente.prevision}</p>
                )}
              </div>
            </div>
            <div className="text-right">
              <Badge variant={paciente.complejidad === 'alta_uci' || paciente.complejidad === 'alta_uti' ? 'danger' : 
                            paciente.complejidad === 'media' ? 'warning' : 'success'}>
                {formatComplejidad(paciente.complejidad)}
              </Badge>
              {paciente.tipo_paciente && (
                <p className="mt-2 text-xs text-gray-500 capitalize">
                  {paciente.tipo_paciente}
                </p>
              )}
            </div>
          </section>

          {/* ============================================ */}
          {/* SECCIÓN: INFORMACIÓN DE TRASLADO */}
          {/* ============================================ */}
          {mostrarSeccionTraslado && (
            <section className="bg-indigo-50 p-4 rounded-lg border border-indigo-200">
              <h4 className="text-sm font-semibold text-indigo-800 mb-3 flex items-center gap-2">
                <ArrowRight className="w-4 h-4" />
                Información de Traslado
              </h4>
              
              {cargandoInfoTraslado ? (
                <div className="flex justify-center py-2">
                  <Spinner size="sm" />
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  {/* Origen */}
                  <div className="bg-white p-3 rounded border border-indigo-100">
                    <div className="flex items-center gap-2 mb-2">
                      <Building2 className="w-4 h-4 text-indigo-600" />
                      <span className="text-xs font-semibold text-indigo-700 uppercase">Origen</span>
                    </div>
                    <p className="text-sm text-gray-700 font-medium">
                      {formatOrigen()}
                    </p>
                    {infoTraslado?.origen_servicio_telefono && (
                      <div className="flex items-center gap-1 mt-2 text-xs text-gray-600">
                        <Phone className="w-3 h-3" />
                        <span>Fono: {infoTraslado.origen_servicio_telefono}</span>
                      </div>
                    )}
                  </div>
                  
                  {/* Destino */}
                  <div className="bg-white p-3 rounded border border-indigo-100">
                    <div className="flex items-center gap-2 mb-2">
                      <BedDouble className="w-4 h-4 text-indigo-600" />
                      <span className="text-xs font-semibold text-indigo-700 uppercase">Destino</span>
                    </div>
                    {infoTraslado?.tiene_cama_destino ? (
                      <>
                        <p className="text-sm text-gray-700 font-medium">
                          {formatDestino()}
                        </p>
                        {infoTraslado?.destino_servicio_telefono && (
                          <div className="flex items-center gap-1 mt-2 text-xs text-gray-600">
                            <Phone className="w-3 h-3" />
                            <span>Fono: {infoTraslado.destino_servicio_telefono}</span>
                          </div>
                        )}
                      </>
                    ) : (
                      <p className="text-sm text-gray-500 italic">
                        Pendiente de asignación
                      </p>
                    )}
                  </div>
                </div>
              )}
            </section>
          )}

          {/* ============================================ */}
          {/* SECCIÓN: INFORMACIÓN CLÍNICA */}
          {/* ============================================ */}
          <section>
            <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <Stethoscope className="w-4 h-4 text-blue-600" />
              Información Clínica
            </h4>
            <div className="bg-gray-50 rounded-lg p-4 space-y-3">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium text-gray-600">Diagnóstico:</span>
                  <p className="text-gray-800">{paciente.diagnostico || 'No especificado'}</p>
                </div>
                <div>
                  <span className="font-medium text-gray-600">Tipo de Enfermedad:</span>
                  <p className="text-gray-800">{formatTipoEnfermedad(paciente.tipo_enfermedad)}</p>
                </div>
              </div>

              {/* Requerimientos Clínicos */}
              {todosRequerimientos.length > 0 && (
                <div>
                  <span className="font-medium text-gray-600 text-sm">Requerimientos Clínicos:</span>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {todosRequerimientos.map(({ req, nivel, color }, idx) => (
                      <Badge 
                        key={idx} 
                        variant={color === 'red' ? 'danger' : 
                                color === 'orange' ? 'warning' : 
                                color === 'yellow' ? 'warning' : 'secondary'}
                        className="text-xs"
                      >
                        {req} ({nivel})
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Aislamiento */}
              {paciente.requiere_aislamiento && (
                <div className="flex items-center gap-2 mt-2">
                  <Badge variant="danger">Requiere Aislamiento</Badge>
                  <span className="text-sm text-gray-600">
                    {formatTipoAislamiento(paciente.tipo_aislamiento)}
                  </span>
                </div>
              )}

              {/* Oxígeno */}
              {paciente.requiere_oxigeno && (
                <div className="mt-2">
                  <Badge variant="info">Requiere Oxígeno</Badge>
                </div>
              )}

              {/* Observación Continua */}
              {paciente.motivo_observacion && (
                <div className="mt-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-yellow-800">Observación Continua:</span>
                    {paciente.observacion_tiempo_horas && paciente.observacion_inicio && (
                      <div className="flex items-center gap-1 text-xs bg-yellow-100 px-2 py-1 rounded">
                        <Clock className="w-3 h-3 text-yellow-600" />
                        <span className="text-yellow-700 font-medium">
                          {paciente.observacion_tiempo_restante !== null && paciente.observacion_tiempo_restante !== undefined
                            ? formatTiempoRestante(paciente.observacion_tiempo_restante)
                            : `${paciente.observacion_tiempo_horas}h configuradas`
                          }
                        </span>
                      </div>
                    )}
                  </div>
                  <p className="text-yellow-700 mt-1">{paciente.motivo_observacion}</p>
                  {paciente.justificacion_observacion && (
                    <p className="text-yellow-600 text-xs mt-1">
                      <span className="font-medium">Justificación:</span> {paciente.justificacion_observacion}
                    </p>
                  )}
                </div>
              )}

              {/* Monitorización Continua */}
              {paciente.motivo_monitorizacion && (
                <div className="mt-3 p-3 bg-orange-50 rounded-lg border border-orange-200">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-orange-800">Monitorización Continua:</span>
                    {paciente.monitorizacion_tiempo_horas && paciente.monitorizacion_inicio && (
                      <div className="flex items-center gap-1 text-xs bg-orange-100 px-2 py-1 rounded">
                        <Clock className="w-3 h-3 text-orange-600" />
                        <span className="text-orange-700 font-medium">
                          {paciente.monitorizacion_tiempo_restante !== null && paciente.monitorizacion_tiempo_restante !== undefined
                            ? formatTiempoRestante(paciente.monitorizacion_tiempo_restante)
                            : `${paciente.monitorizacion_tiempo_horas}h configuradas`
                          }
                        </span>
                      </div>
                    )}
                  </div>
                  <p className="text-orange-700 mt-1">{paciente.motivo_monitorizacion}</p>
                  {paciente.justificacion_monitorizacion && (
                    <p className="text-orange-600 text-xs mt-1">
                      <span className="font-medium">Justificación:</span> {paciente.justificacion_monitorizacion}
                    </p>
                  )}
                </div>
              )}

              {/* Timers activos sin motivo */}
              {!paciente.motivo_observacion && paciente.observacion_tiempo_horas && paciente.observacion_inicio && (
                <div className="mt-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-yellow-600" />
                    <span className="font-medium text-yellow-800">Timer de Observación Activo:</span>
                    <span className="text-yellow-700 text-sm">
                      {paciente.observacion_tiempo_restante !== null && paciente.observacion_tiempo_restante !== undefined
                        ? formatTiempoRestante(paciente.observacion_tiempo_restante)
                        : `${paciente.observacion_tiempo_horas}h configuradas`
                      }
                    </span>
                  </div>
                </div>
              )}

              {!paciente.motivo_monitorizacion && paciente.monitorizacion_tiempo_horas && paciente.monitorizacion_inicio && (
                <div className="mt-3 p-3 bg-orange-50 rounded-lg border border-orange-200">
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-orange-600" />
                    <span className="font-medium text-orange-800">Timer de Monitorización Activo:</span>
                    <span className="text-orange-700 text-sm">
                      {paciente.monitorizacion_tiempo_restante !== null && paciente.monitorizacion_tiempo_restante !== undefined
                        ? formatTiempoRestante(paciente.monitorizacion_tiempo_restante)
                        : `${paciente.monitorizacion_tiempo_horas}h configuradas`
                      }
                    </span>
                  </div>
                </div>
              )}
            </div>
          </section>

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
                  const IconoCaso = ICONOS_CASOS_ESPECIALES[caso];
                  return (
                    <Badge key={idx} variant="warning" className="flex items-center gap-1">
                      {IconoCaso && <IconoCaso className="w-3.5 h-3.5" />}
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
          {/* SECCIÓN: ESTADO DE DERIVACIÓN */}
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
          {/* SECCIÓN: ALTA SOLICITADA */}
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
          {/* BOTONES DE ACCIÓN */}
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