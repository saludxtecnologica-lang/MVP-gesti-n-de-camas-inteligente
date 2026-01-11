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
// ESTILOS DE BOTONES - DISEÑO APPLE STYLE
// ============================================

const estilosBotones: Record<string, string> = {
  primary: 'bg-blue-500 hover:bg-blue-600 text-white shadow-sm hover:shadow border-0',
  secondary: 'bg-gray-50 hover:bg-gray-100 text-gray-700 shadow-sm hover:shadow border border-gray-200',
  success: 'bg-green-500 hover:bg-green-600 text-white shadow-sm hover:shadow border-0',
  danger: 'bg-red-500 hover:bg-red-600 text-white shadow-sm hover:shadow border-0',
  warning: 'bg-yellow-400 hover:bg-yellow-500 text-gray-900 shadow-sm hover:shadow border-0'
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

  // ============================================
  // DETERMINAR SI DEBE TENER ANIMACIÓN DE PULSO
  // ============================================
  const estadosDinamicos = [
    EstadoCamaEnum.TRASLADO_ENTRANTE,
    EstadoCamaEnum.TRASLADO_SALIENTE,
    EstadoCamaEnum.TRASLADO_CONFIRMADO,
    EstadoCamaEnum.CAMA_EN_ESPERA,
    EstadoCamaEnum.ALTA_SUGERIDA,
    EstadoCamaEnum.CAMA_ALTA,
    EstadoCamaEnum.EN_LIMPIEZA,
    EstadoCamaEnum.ESPERA_DERIVACION,
    EstadoCamaEnum.DERIVACION_CONFIRMADA,
    EstadoCamaEnum.RESERVADA
  ];

  const debeAnimarPulso = estadosDinamicos.includes(cama.estado as EstadoCamaEnum) || esperandoOxigeno;

  return (
    <>
      <div
        className={`rounded-3xl border p-5 ${estadoColor}
          transition-all duration-500 ease-out
          hover:shadow-xl hover:scale-[1.01] hover:-translate-y-0.5
          relative backdrop-blur-sm
          min-h-[340px] max-h-[340px] flex flex-col
          ${pacienteMostrar ? 'cursor-pointer' : ''}
          animate-scaleEntrance
          ${debeAnimarPulso ? 'animate-borderPulse' : ''}`}
        onClick={handleClickTarjeta}
        style={{
          boxShadow: debeAnimarPulso
            ? '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)'
            : '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05)'
        }}
      >
        {/* ============================================ */}
        {/* LÍNEA 1: Identificador de Cama + Estado */}
        {/* ============================================ */}
        <div className="flex items-start justify-between mb-2 flex-shrink-0">
          <h3 className="font-semibold text-2xl tracking-tight leading-tight">
            {cama.identificador}
          </h3>
          <div className="flex items-center gap-2">
            {esFallecido && (
              <div className="p-1 bg-gray-700 rounded-full shadow-sm" title="Paciente fallecido">
                <Cross className="w-3.5 h-3.5 text-white" />
              </div>
            )}
            <Badge variant={cama.estado === 'libre' ? 'success' : esFallecido ? 'default' : 'default'}>
              {formatEstado(cama.estado)}
            </Badge>
            {mostrarBotonReevaluar && (
              <button
                onClick={handleClickReevaluar}
                className="p-1.5 rounded-full bg-blue-50 hover:bg-blue-100 text-blue-600
                  transition-all duration-300 border border-blue-100 hover:border-blue-200
                  hover:shadow-sm active:scale-95"
                title="Reevaluar paciente"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* ============================================ */}
        {/* LÍNEA 2: Servicio */}
        {/* ============================================ */}
        {cama.servicio_nombre && (
          <div className="mb-3 flex-shrink-0">
            <span className="text-xs font-medium opacity-60 tracking-wide uppercase">
              {cama.servicio_nombre}
            </span>
          </div>
        )}

        {/* ============================================ */}
        {/* LÍNEA 3 y 4: Logo de Persona + Nombre (2 líneas) + RUT */}
        {/* ============================================ */}
        {pacienteMostrar && (
          <div className={`mb-3 flex-shrink-0 ${esFallecido ? 'text-gray-200' : ''}`}>
            <div className="flex items-start gap-3 mb-2">
              {/* Logo de persona - tamaño de 2 líneas */}
              <div className={`flex-shrink-0 rounded-full p-2.5 shadow-sm ${
                pacienteMostrar.sexo === 'hombre'
                  ? 'bg-gradient-to-br from-blue-500 to-blue-600'
                  : 'bg-gradient-to-br from-pink-500 to-pink-600'
              }`}>
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="white"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="w-9 h-9"
                >
                  <circle cx="12" cy="8" r="4" />
                  <path d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2" />
                </svg>
              </div>
              {/* Nombre - máximo 2 líneas */}
              <div className="flex-grow min-w-0">
                <p className="font-semibold text-base leading-snug line-clamp-2">
                  {pacienteMostrar.nombre}
                </p>
              </div>
            </div>

            {/* RUT debajo del nombre */}
            <p className="text-xs opacity-70 font-mono mb-1.5 pl-[52px]">
              {pacienteMostrar.run}
            </p>
          </div>
        )}

        {/* ============================================ */}
        {/* LÍNEA 5: Solo Edad (sin complejidad) */}
        {/* ============================================ */}
        {pacienteMostrar && (
          <div className="mb-3 flex-shrink-0 pl-[52px]">
            <span className="inline-flex items-center text-xs font-medium px-2.5 py-1 bg-white bg-opacity-20 rounded-full">
              {pacienteMostrar.edad} años
            </span>
          </div>
        )}

        {/* ============================================ */}
        {/* LÍNEA 6: Logos Especiales (Badges) */}
        {/* ============================================ */}
        {(tieneCasosEspeciales || esDerivado || esperandoOxigeno || esFallecido ||
          (pacienteMostrar?.tipo_aislamiento && pacienteMostrar.tipo_aislamiento !== 'ninguno')) && (
          <div className="flex flex-wrap gap-1.5 mb-3 flex-shrink-0">
            {esFallecido && (
              <Badge variant="default" className="bg-gray-700 text-white shadow-sm text-xs">
                <Cross className="w-3 h-3 mr-1" />
                Fallecido
              </Badge>
            )}
            {iconosCasosEspeciales.length > 0 && !esFallecido && (
              <div className="flex items-center gap-1 px-2.5 py-1 bg-amber-50 rounded-full border border-amber-200 shadow-sm">
                {iconosCasosEspeciales.map((config: { icono: React.ElementType; color: string }, idx: number) => {
                  const IconComponent = config.icono;
                  return (
                    <IconComponent
                      key={idx}
                      className={`w-3.5 h-3.5 ${config.color}`}
                      title={casosEspeciales[idx]}
                    />
                  );
                })}
              </div>
            )}
            {tieneCasosEspeciales && iconosCasosEspeciales.length === 0 && !esFallecido && (
              <Badge variant="warning" className="shadow-sm text-xs">
                <AlertTriangle className="w-3 h-3 mr-1" />
                Caso Especial
              </Badge>
            )}
            {esDerivado && !esFallecido && (
              <Badge variant="purple" className="shadow-sm text-xs">
                <Send className="w-3 h-3 mr-1" />
                Derivado
              </Badge>
            )}
            {esperandoOxigeno && !esFallecido && (
              <Badge variant="info" className="shadow-sm text-xs">
                <Wind className="w-3 h-3 mr-1" />
                Evaluando O₂
              </Badge>
            )}
            {pacienteMostrar?.tipo_aislamiento && pacienteMostrar.tipo_aislamiento !== 'ninguno' && !esFallecido && (
              <span className="inline-flex items-center text-xs font-medium px-2.5 py-1 bg-red-50 text-red-700 rounded-full border border-red-200 shadow-sm">
                {formatTipoAislamiento(pacienteMostrar.tipo_aislamiento)}
              </span>
            )}
          </div>
        )}

        {/* ============================================ */}
        {/* LÍNEA 7: Espacio para Mensajes (hasta 3) */}
        {/* ============================================ */}
        <div className="mb-3 flex-shrink-0 space-y-1.5" style={{ minHeight: '60px' }}>
          {/* Mensaje 1: Evaluación de oxígeno */}
          {esperandoOxigeno && !esFallecido && (
            <div className="text-xs p-2.5 bg-cyan-50 rounded-xl border border-cyan-200 text-cyan-800 shadow-sm">
              <div className="flex items-center gap-1.5">
                <Wind className="w-3.5 h-3.5 flex-shrink-0" />
                <span className="font-medium text-xs leading-tight">Evaluando descalaje de oxígeno</span>
              </div>
            </div>
          )}

          {/* Mensaje 2: Fallecido */}
          {esFallecido && (
            <div className="text-xs p-2.5 bg-gray-700 bg-opacity-50 rounded-xl border border-gray-600 text-gray-200 shadow-sm">
              <div className="flex items-center gap-1.5">
                <Cross className="w-3.5 h-3.5 flex-shrink-0" />
                <span className="font-medium text-xs leading-tight">Cuidados postmortem en curso</span>
              </div>
            </div>
          )}

          {/* Mensaje 3: Causa de fallecimiento */}
          {esFallecido && pacienteMostrar?.causa_fallecimiento && (
            <div className="text-xs p-2.5 bg-gray-700 bg-opacity-50 rounded-xl border border-gray-600 text-gray-300 italic">
              <span className="text-xs leading-tight">Causa: {pacienteMostrar.causa_fallecimiento}</span>
            </div>
          )}

          {/* Mensaje alternativo: Estado de la cama */}
          {!esperandoOxigeno && !esFallecido && cama.mensaje_estado && (
            <div className="text-xs p-2.5 bg-white bg-opacity-10 rounded-xl italic opacity-75">
              <span className="text-xs leading-tight">{cama.mensaje_estado}</span>
            </div>
          )}

          {/* Mensaje alternativo: Motivo de bloqueo */}
          {cama.estado === 'bloqueada' && cama.bloqueada_motivo && (
            <div className="text-xs p-2.5 bg-red-50 rounded-xl border border-red-200 text-red-700">
              <span className="font-semibold">Motivo:</span> {cama.bloqueada_motivo}
            </div>
          )}
        </div>

        {/* ============================================ */}
        {/* LÍNEA 8: Botones de Acción */}
        {/* ============================================ */}
        <div className="mt-auto flex-shrink-0 space-y-2">
          {/* Botones principales */}
          {botones.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {botones.map((config) => {
                const Icon = config.icono;
                const isLoading = config.accion === 'buscarCama' && verificandoDisponibilidad;

                return (
                  <button
                    key={config.key}
                    onClick={(e) => {
                      e.stopPropagation();
                      ejecutarAccion(config);
                    }}
                    disabled={isLoading}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl
                      transition-all duration-300 shadow-sm hover:shadow-md
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
              className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium
                rounded-xl bg-teal-600 hover:bg-teal-700 text-white
                transition-all duration-300 shadow-sm hover:shadow-md active:scale-95"
            >
              <Clock className="w-4 h-4" />
              Omitir espera O₂ y buscar cama
            </button>
          )}
        </div>
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