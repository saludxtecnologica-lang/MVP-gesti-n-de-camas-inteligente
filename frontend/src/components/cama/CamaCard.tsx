import React, { useState } from 'react';
import { 
  FileText, Check, X, Search, Clock, LogOut, 
  Lock, Unlock, UserPlus, ArrowRightLeft, AlertTriangle,
  Send, Truck, Wind, Loader2, RefreshCw,
  Heart, Gavel, Files, Cross
} from 'lucide-react';
import type { Cama, Paciente } from '../../types';
import { EstadoCamaEnum } from '../../types';
import { useCamaActions } from '../../hooks/useCamaActions';
import { useApp } from '../../context/AppContext';
import { Badge } from '../common/Badge';
import { 
  formatEstado, 
  formatComplejidad, 
  formatTipoAislamiento,
  COLORES_ESTADO,
  safeJsonParse
} from '../../utils';
import * as api from '../../services/api';
// ============================================
// IMPORTAR MODAL DE BÚSQUEDA EN RED
// ============================================
import { ModalBusquedaCamaRed } from '../modales/ModalBusquedaCamaRed';

// ============================================
// TIPOS DE CONFIGURACIÓN DE BOTONES
// ============================================

interface BotonConfig {
  key: string;
  tipo: 'primary' | 'secondary' | 'success' | 'danger' | 'warning';
  icono: React.ElementType;
  texto: string;
  accion: string;
  usaEntrante?: boolean;
  condicional?: string; // Condición especial para mostrar el botón
}

// ============================================
// CONFIGURACIÓN DECLARATIVA DE BOTONES
// MODIFICADO: Agregado estado FALLECIDO
// ============================================

const BOTONES_CONFIG: Record<string, BotonConfig[]> = {
  [EstadoCamaEnum.OCUPADA]: [],
  [EstadoCamaEnum.TRASLADO_ENTRANTE]: [
    { key: 'completar', tipo: 'success', icono: Check, texto: 'Completar', accion: 'completarTraslado', usaEntrante: true },
    { key: 'cancelar', tipo: 'danger', icono: X, texto: 'Cancelar', accion: 'cancelarTraslado', usaEntrante: true }
  ],
  [EstadoCamaEnum.CAMA_EN_ESPERA]: [
    { key: 'buscar', tipo: 'primary', icono: Search, texto: 'Nueva cama', accion: 'buscarCama', condicional: 'noEsperandoOxigeno' }
  ],
  [EstadoCamaEnum.TRASLADO_SALIENTE]: [
    { key: 'cancelar', tipo: 'danger', icono: X, texto: 'Cancelar', accion: 'cancelarDesdeOrigen' }
  ],
  [EstadoCamaEnum.TRASLADO_CONFIRMADO]: [
    { key: 'cancelar', tipo: 'danger', icono: X, texto: 'Cancelar', accion: 'cancelarTrasladoConfirmado' }
  ],
  [EstadoCamaEnum.ALTA_SUGERIDA]: [
    { key: 'alta', tipo: 'success', icono: LogOut, texto: 'Dar Alta', accion: 'iniciarAlta' }
  ],
  [EstadoCamaEnum.CAMA_ALTA]: [
    { key: 'ejecutar', tipo: 'success', icono: Check, texto: 'Confirmar', accion: 'darAlta' },
    { key: 'cancelar', tipo: 'danger', icono: X, texto: 'Cancelar', accion: 'cancelarAlta' }
  ],
  [EstadoCamaEnum.LIBRE]: [],
  [EstadoCamaEnum.EN_LIMPIEZA]: [],
  [EstadoCamaEnum.BLOQUEADA]: [
    { key: 'desbloquear', tipo: 'warning', icono: Unlock, texto: 'Desbloquear', accion: 'desbloquear' }
  ],
  // Estados de derivación
  [EstadoCamaEnum.ESPERA_DERIVACION]: [
    { key: 'cancelar', tipo: 'danger', icono: X, texto: 'Cancelar', accion: 'cancelarDerivacion' }
  ],
  [EstadoCamaEnum.DERIVACION_CONFIRMADA]: [
    { key: 'egreso', tipo: 'success', icono: Truck, texto: 'Confirmar Egreso', accion: 'confirmarEgreso' },
    { key: 'cancelar', tipo: 'danger', icono: X, texto: 'Cancelar', accion: 'cancelarDerivacion' }
  ],
  // ============================================
  // NUEVO: Estado FALLECIDO
  // ============================================
  [EstadoCamaEnum.FALLECIDO]: [
    { key: 'completarEgreso', tipo: 'success', icono: Check, texto: 'Completar Egreso', accion: 'completarEgresoFallecido' }
  ]
};

const BOTONES_MANUAL: Record<string, BotonConfig[]> = {
  [EstadoCamaEnum.LIBRE]: [
    { key: 'bloquear', tipo: 'secondary', icono: Lock, texto: 'Bloquear', accion: 'bloquear' }
  ],
  [EstadoCamaEnum.OCUPADA]: [
    { key: 'asignar', tipo: 'primary', icono: UserPlus, texto: 'Nueva cama', accion: 'asignarManual' },
    { key: 'intercambiar', tipo: 'warning', icono: ArrowRightLeft, texto: 'Intercambiar', accion: 'intercambiar' },
    { key: 'egresar', tipo: 'danger', icono: LogOut, texto: 'Egresar', accion: 'egresarManual' }
  ],
  // ============================================
  // NUEVO: Botón cancelar fallecimiento (SOLO MODO MANUAL)
  // ============================================
  [EstadoCamaEnum.FALLECIDO]: [
    { key: 'cancelarFallecimiento', tipo: 'danger', icono: X, texto: 'Cancelar', accion: 'cancelarFallecimiento' }
  ]
};

// ============================================
// ESTILOS DE BOTONES - DISEÑO MODERNO
// ============================================

const estilosBotones: Record<string, string> = {
  primary: 'bg-blue-600 hover:bg-blue-700 text-white border border-blue-700',
  secondary: 'bg-gray-100 hover:bg-gray-200 text-gray-700 border border-gray-300',
  success: 'bg-green-600 hover:bg-green-700 text-white border border-green-700',
  danger: 'bg-red-600 hover:bg-red-700 text-white border border-red-700',
  warning: 'bg-yellow-500 hover:bg-yellow-600 text-gray-900 border border-yellow-600'
};

// ============================================
// ESTADOS QUE PERMITEN REEVALUACIÓN
// MODIFICADO: No permitir reevaluación en estado FALLECIDO
// ============================================

const ESTADOS_CON_REEVALUACION = [
  EstadoCamaEnum.OCUPADA,
  EstadoCamaEnum.CAMA_EN_ESPERA,
  EstadoCamaEnum.ALTA_SUGERIDA
];

// ============================================
// ICONOS DE CASOS ESPECIALES
// ============================================

const ICONOS_CASOS_ESPECIALES: Record<string, { icono: React.ElementType; color: string }> = {
  'Espera cardiocirugía': { icono: Heart, color: 'text-red-500' },
  'Socio-judicial': { icono: Gavel, color: 'text-amber-600' },
  'Socio-sanitario': { icono: Files, color: 'text-blue-500' },
};

// ============================================
// COMPONENTE PRINCIPAL
// ============================================

interface CamaCardProps {
  cama: Cama;
}

export function CamaCard({ cama }: CamaCardProps) {
  const { configuracion, showAlert, recargarTodo } = useApp();
  const actions = useCamaActions();
  const modoManual = configuracion?.modo_manual ?? false;

  // Estados para búsqueda de cama en red
  const [verificandoDisponibilidad, setVerificandoDisponibilidad] = useState(false);
  const [modalBusquedaRedAbierto, setModalBusquedaRedAbierto] = useState(false);
  const [pacienteParaBusquedaRed, setPacienteParaBusquedaRed] = useState<Paciente | null>(null);

  const paciente = cama.paciente;
  const pacienteEntrante = cama.paciente_entrante;
  
  // ============================================
  // COLORES DE ESTADO - INCLUYENDO FALLECIDO
  // ============================================
  const getEstadoColor = () => {
    if (cama.estado === EstadoCamaEnum.FALLECIDO) {
      return 'bg-gray-800 text-gray-100 border-gray-900';
    }
    return COLORES_ESTADO[cama.estado] || COLORES_ESTADO.libre;
  };

  const estadoColor = getEstadoColor();

  // Obtener paciente a mostrar
  const pacienteMostrar = pacienteEntrante || paciente;

  // Verificar casos especiales
  const casosEspeciales = pacienteMostrar ? safeJsonParse(pacienteMostrar.casos_especiales) : [];
  const tieneCasosEspeciales = casosEspeciales.length > 0;
  const esDerivado = pacienteMostrar?.tipo_paciente === 'derivado' || 
                     pacienteMostrar?.derivacion_estado === 'aceptado' ||
                     pacienteMostrar?.derivacion_estado === 'aceptada' ||
                     pacienteMostrar?.derivacion_estado === 'pendiente';
  const esperandoOxigeno = pacienteMostrar?.esperando_evaluacion_oxigeno === true;
  
  // ============================================
  // VERIFICAR SI ES ESTADO FALLECIDO
  // ============================================
  const esFallecido = cama.estado === EstadoCamaEnum.FALLECIDO;

  // ============================================
  // Verificar si se muestra el botón de reevaluar
  // No mostrar en estado FALLECIDO
  // ============================================
  const mostrarBotonReevaluar = pacienteMostrar && 
    ESTADOS_CON_REEVALUACION.includes(cama.estado as EstadoCamaEnum) &&
    !esFallecido;

  // ============================================
  // Obtener íconos de casos especiales para mostrar
  // ============================================
  const iconosCasosEspeciales = casosEspeciales
    .map((caso: string) => ICONOS_CASOS_ESPECIALES[caso])
    .filter(Boolean);

  // ============================================
  // FUNCIÓN PARA INICIAR BÚSQUEDA DE CAMA CON VERIFICACIÓN
  // ============================================
  const handleBuscarCamaConVerificacion = async (pac: Paciente) => {
    if (!pac.id) {
      showAlert('error', 'Error: Paciente no válido');
      return;
    }

    setVerificandoDisponibilidad(true);

    try {
      const verificacion = await api.verificarDisponibilidadTipoCama(pac.id);

      // CASO 1: Hospital NO tiene el tipo de servicio → Buscar en red
      if (!verificacion.tiene_tipo_servicio) {
        setPacienteParaBusquedaRed(pac);
        setModalBusquedaRedAbierto(true);
        showAlert('info', verificacion.mensaje || 'El hospital no cuenta con el tipo de cama requerido. Buscando en la red hospitalaria...');
      }
      // CASO 2 y 3: Hospital SÍ tiene el tipo de servicio → Ir a lista de espera
      // (sin importar si hay camas libres o no)
      else {
        try {
          const resultado = await api.buscarCamaPaciente(pac.id);
          showAlert('success', resultado.message || 'Paciente agregado a lista de espera');
          await recargarTodo();
        } catch (error) {
          showAlert('error', error instanceof Error ? error.message : 'Error al agregar a lista de espera');
        }
      }
    } catch (error) {
      console.error('Error verificando disponibilidad:', error);
      try {
        const resultado = await api.buscarCamaPaciente(pac.id);
        showAlert('success', resultado.message || 'Búsqueda de cama iniciada');
        await recargarTodo();
      } catch (fallbackError) {
        showAlert('error', 'Error al verificar disponibilidad de camas');
      }
    } finally {
      setVerificandoDisponibilidad(false);
    }
  };

  // ============================================
  // Cerrar modal de búsqueda en red
  // ============================================
  const cerrarModalBusquedaRed = () => {
    setModalBusquedaRedAbierto(false);
    setPacienteParaBusquedaRed(null);
  };

  // ============================================
  // Callback cuando se completa derivación
  // ============================================
  const onDerivacionCompletada = async () => {
    cerrarModalBusquedaRed();
    await recargarTodo();
  };

  // ============================================
  // CLICK EN TARJETA - Abre modal de paciente
  // ============================================
  const handleClickTarjeta = (e: React.MouseEvent) => {
    // Evitar que se abra el modal si se hizo clic en un botón
    if ((e.target as HTMLElement).closest('button')) {
      return;
    }
    
    if (pacienteMostrar) {
      // Usar el paciente entrante si existe (para traslados entrantes)
      const pacienteParaVer = pacienteEntrante || paciente;
      if (pacienteParaVer) {
        actions.handleVerPaciente(pacienteParaVer);
      }
    }
  };

  // ============================================
  // CLICK EN BOTÓN REEVALUAR
  // ============================================
  const handleClickReevaluar = (e: React.MouseEvent) => {
    e.stopPropagation(); // Evitar que se abra el modal de ver paciente
    
    const pacienteParaReevaluar = pacienteEntrante || paciente;
    if (pacienteParaReevaluar) {
      actions.handleReevaluar(pacienteParaReevaluar);
    }
  };

  // ============================================
  // HANDLER PARA COMPLETAR EGRESO FALLECIDO
  // ============================================
  const handleCompletarEgresoFallecido = async () => {
    if (!paciente?.id) return;
    
    try {
      const resultado = await api.completarEgresoFallecido(paciente.id);
      showAlert('success', resultado.message || 'Egreso completado');
      await recargarTodo();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al completar egreso');
    }
  };

  // ============================================
  // HANDLER PARA CANCELAR FALLECIMIENTO (SOLO MODO MANUAL)
  // ============================================
  const handleCancelarFallecimiento = async () => {
    if (!paciente?.id) return;
    
    if (!window.confirm('¿Está seguro de cancelar el registro de fallecimiento? Esta acción restaurará al paciente a su estado anterior.')) {
      return;
    }
    
    try {
      const resultado = await api.cancelarFallecimiento(paciente.id);
      showAlert('success', resultado.message || 'Fallecimiento cancelado');
      await recargarTodo();
    } catch (error) {
      showAlert('error', error instanceof Error ? error.message : 'Error al cancelar fallecimiento');
    }
  };

  // Ejecutar acción según configuración
  const ejecutarAccion = (config: BotonConfig) => {
    const pac = config.usaEntrante ? pacienteEntrante : paciente;
    if (!pac && config.accion !== 'bloquear' && config.accion !== 'desbloquear' && 
        config.accion !== 'asignarManual') return;

    switch (config.accion) {
      case 'completarTraslado':
        if (pac) actions.handleCompletarTraslado(pac.id);
        break;
      case 'cancelarTraslado':
        if (pac) actions.handleCancelarTraslado(pac.id);
        break;
      case 'cancelarDesdeOrigen':
        if (pac) actions.handleCancelarDesdeOrigen(pac.id);
        break;
      case 'cancelarTrasladoConfirmado':
        if (pac) actions.handleCancelarTrasladoConfirmado(pac.id);
        break;
      case 'buscarCama':
        if (pac) handleBuscarCamaConVerificacion(pac);
        break;
      case 'iniciarAlta':
        if (pac) actions.handleIniciarAlta(pac.id);
        break;
      case 'darAlta':
        if (pac) actions.handleDarAlta(pac.id);
        break;
      case 'cancelarAlta':
        if (pac) actions.handleCancelarAlta(pac.id);
        break;
      case 'confirmarEgreso':
        if (pac) actions.handleConfirmarEgreso(pac.id);
        break;
      case 'cancelarDerivacion':
        if (pac) actions.handleCancelarDerivacion(pac.id);
        break;
      case 'bloquear':
        actions.handleBloquear(cama.id, true);
        break;
      case 'desbloquear':
        actions.handleBloquear(cama.id, false);
        break;
      case 'asignarManual':
        actions.handleAsignarManual(cama);
        break;
      case 'intercambiar':
        actions.handleIntercambio(cama);
        break;
      case 'egresarManual':
        if (pac) actions.handleEgresarManual(pac.id);
        break;
      // ============================================
      // NUEVAS ACCIONES PARA FALLECIMIENTO
      // ============================================
      case 'completarEgresoFallecido':
        handleCompletarEgresoFallecido();
        break;
      case 'cancelarFallecimiento':
        handleCancelarFallecimiento();
        break;
    }
  };

  // Verificar condiciones especiales para botones
  const cumpleCondicion = (condicion: string | undefined): boolean => {
    if (!condicion) return true;
    
    switch (condicion) {
      case 'noEsperandoOxigeno':
        return !esperandoOxigeno;
      default:
        return true;
    }
  };

  // Obtener botones según estado y modo
  const botonesEstado = (BOTONES_CONFIG[cama.estado] || []).filter(
    config => cumpleCondicion(config.condicional)
  );
  const botonesManual = modoManual ? (BOTONES_MANUAL[cama.estado] || []) : [];
  const botones = [...botonesEstado, ...botonesManual];

  return (
    <>
      <div
        className={`rounded-2xl border-2 p-4 ${estadoColor}
          transition-all duration-300 ease-in-out
          hover:shadow-2xl hover:scale-[1.02] hover:-translate-y-1
          relative backdrop-blur-sm
          min-h-[280px] max-h-[280px] flex flex-col
          ${pacienteMostrar ? 'cursor-pointer' : ''}
          animate-fadeIn`}
        onClick={handleClickTarjeta}
        style={{
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
          animation: 'cardEntrance 0.3s ease-out'
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-3 flex-shrink-0">
          <div className="flex items-center gap-3">
            <span className="font-bold text-xl tracking-tight">{cama.identificador}</span>
            {cama.servicio_nombre && (
              <span className="text-xs opacity-60 font-medium">{cama.servicio_nombre}</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* ============================================ */}
            {/* ÍCONO DE CRUZ PARA ESTADO FALLECIDO */}
            {/* ============================================ */}
            {esFallecido && (
              <div className="p-1.5 bg-gray-700 rounded-full shadow-md transition-all duration-200 hover:scale-110" title="Paciente fallecido">
                <Cross className="w-4 h-4 text-white" />
              </div>
            )}

            <Badge variant={cama.estado === 'libre' ? 'success' : esFallecido ? 'default' : 'default'}>
              {formatEstado(cama.estado)}
            </Badge>

            {/* ============================================ */}
            {/* BOTÓN DE REEVALUAR - No mostrar en fallecido */}
            {/* ============================================ */}
            {mostrarBotonReevaluar && (
              <button
                onClick={handleClickReevaluar}
                className="p-2 rounded-full bg-blue-50 hover:bg-blue-100 text-blue-600
                  transition-all duration-200 border border-blue-200 shadow-sm
                  hover:shadow-md hover:scale-110 active:scale-95"
                title="Reevaluar paciente"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Badges especiales */}
        {(tieneCasosEspeciales || esDerivado || esperandoOxigeno || esFallecido) && (
          <div className="flex flex-wrap gap-2 mb-3 flex-shrink-0">
            {/* ============================================ */}
            {/* BADGE DE FALLECIDO */}
            {/* ============================================ */}
            {esFallecido && (
              <Badge variant="default" className="bg-gray-700 text-white shadow-sm">
                <Cross className="w-3 h-3 mr-1" />
                Fallecido
              </Badge>
            )}

            {/* Íconos de casos especiales */}
            {iconosCasosEspeciales.length > 0 && !esFallecido && (
              <div className="flex items-center gap-1.5 px-3 py-1 bg-amber-50 rounded-full border border-amber-200 shadow-sm">
                {iconosCasosEspeciales.map((config: { icono: React.ElementType; color: string }, idx: number) => {
                  const IconComponent = config.icono;
                  return (
                    <IconComponent
                      key={idx}
                      className={`w-4 h-4 ${config.color}`}
                      title={casosEspeciales[idx]}
                    />
                  );
                })}
              </div>
            )}
            {tieneCasosEspeciales && iconosCasosEspeciales.length === 0 && !esFallecido && (
              <Badge variant="warning" className="shadow-sm">
                <AlertTriangle className="w-3 h-3 mr-1" />
                Caso Especial
              </Badge>
            )}
            {esDerivado && !esFallecido && (
              <Badge variant="purple" className="shadow-sm">
                <Send className="w-3 h-3 mr-1" />
                Derivado
              </Badge>
            )}
            {esperandoOxigeno && !esFallecido && (
              <Badge variant="info" className="shadow-sm">
                <Wind className="w-3 h-3 mr-1" />
                Evaluando O₂
              </Badge>
            )}
          </div>
        )}

        {/* Info paciente - Clickeable para abrir modal */}
        {pacienteMostrar && (
          <div className={`text-sm space-y-2 mb-3 flex-grow overflow-hidden ${esFallecido ? 'text-gray-200' : ''}`}>
            <p className="font-semibold text-base truncate tracking-tight">{pacienteMostrar.nombre}</p>
            <p className="text-xs opacity-75 font-mono">RUN: {pacienteMostrar.run}</p>
            <div className="flex flex-wrap gap-2 text-xs font-medium">
              <span className="px-2 py-0.5 bg-white bg-opacity-20 rounded-full">
                {pacienteMostrar.edad} años
              </span>
              <span className="px-2 py-0.5 bg-white bg-opacity-20 rounded-full">
                {formatComplejidad(pacienteMostrar.complejidad_requerida || pacienteMostrar.complejidad || 'ninguna')}
              </span>
              {pacienteMostrar.tipo_aislamiento && pacienteMostrar.tipo_aislamiento !== 'ninguno' && !esFallecido && (
                <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full border border-red-300">
                  {formatTipoAislamiento(pacienteMostrar.tipo_aislamiento)}
                </span>
              )}
            </div>
            {/* Mostrar causa de fallecimiento si está disponible */}
            {esFallecido && pacienteMostrar.causa_fallecimiento && (
              <p className="text-xs text-gray-300 mt-2 italic px-2 py-1 bg-gray-700 bg-opacity-50 rounded">
                Causa: {pacienteMostrar.causa_fallecimiento}
              </p>
            )}
          </div>
        )}

        {/* Mensaje estado - Especial para evaluación de oxígeno */}
        {esperandoOxigeno && !esFallecido ? (
          <div className="text-xs mb-2 p-3 bg-cyan-50 rounded-xl border border-cyan-200 text-cyan-800 shadow-sm flex-shrink-0">
            <div className="flex items-center gap-2">
              <Wind className="w-4 h-4" />
              <span className="font-semibold">Evaluando descalaje de oxígeno</span>
            </div>
            <p className="mt-1.5 text-cyan-700 text-xs">
              Esperando confirmación antes de buscar nueva cama
            </p>
          </div>
        ) : esFallecido ? (
          <div className="text-xs mb-2 p-3 bg-gray-700 bg-opacity-50 rounded-xl border border-gray-600 text-gray-200 shadow-sm flex-shrink-0">
            <div className="flex items-center gap-2">
              <Cross className="w-4 h-4" />
              <span className="font-semibold">Cuidados postmortem en curso</span>
            </div>
          </div>
        ) : cama.mensaje_estado ? (
          <p className="text-xs italic mb-2 opacity-75 px-2 py-1 bg-white bg-opacity-10 rounded flex-shrink-0">
            {cama.mensaje_estado}
          </p>
        ) : null}

        {/* Motivo bloqueo */}
        {cama.estado === 'bloqueada' && cama.bloqueada_motivo && (
          <p className="text-xs text-red-700 mb-2 px-2 py-1 bg-red-50 rounded border border-red-200 flex-shrink-0">
            <span className="font-semibold">Motivo:</span> {cama.bloqueada_motivo}
          </p>
        )}

        {/* Botones */}
        {botones.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-auto flex-shrink-0">
            {botones.map((config) => {
              const Icon = config.icono;
              const isLoading = config.accion === 'buscarCama' && verificandoDisponibilidad;

              return (
                <button
                  key={config.key}
                  onClick={(e) => {
                    e.stopPropagation(); // Evitar que se abra el modal de paciente
                    ejecutarAccion(config);
                  }}
                  disabled={isLoading}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg
                    transition-all duration-200 shadow-sm hover:shadow-md
                    active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed
                    ${estilosBotones[config.tipo]}`}
                >
                  {isLoading ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Icon className="w-3.5 h-3.5" />
                  )}
                  {isLoading ? 'Verificando...' : config.texto}
                </button>
              );
            })}
          </div>
        )}

        {/* Botón omitir pausa de oxígeno */}
        {esperandoOxigeno && paciente && !esFallecido && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              actions.handleOmitirPausaOxigeno(paciente.id);
            }}
            className="mt-2 w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium
              rounded-lg bg-teal-600 hover:bg-teal-700 text-white
              transition-all duration-200 shadow-sm hover:shadow-md active:scale-95 flex-shrink-0"
          >
            <Clock className="w-4 h-4" />
            Omitir espera O₂ y buscar cama
          </button>
        )}
      </div>

      {/* Modal de búsqueda de cama en red */}
      <ModalBusquedaCamaRed
        isOpen={modalBusquedaRedAbierto}
        onClose={cerrarModalBusquedaRed}
        paciente={pacienteParaBusquedaRed}
        onDerivacionCompletada={onDerivacionCompletada}
      />
    </>
  );
}