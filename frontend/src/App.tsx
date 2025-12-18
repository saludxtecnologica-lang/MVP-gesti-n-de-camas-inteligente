import React, { useState, useCallback } from 'react';
import {
  Building2,
  Bed,
  Users,
  ArrowRightLeft,
  Settings,
  Plus,
  RefreshCw,
  Wifi,
  WifiOff,
  BarChart3
} from 'lucide-react';
import { useApp } from './context/AppContext';
import { CamaCard } from './components/CamaCard';
import { Modal } from './components/Modal';
import { Alert } from './components/Alert';
import { PacienteForm } from './components/PacienteForm';
import { PacienteDetalle } from './components/PacienteDetalle';
import { ListaEspera } from './components/ListaEspera';
import { ListaDerivados } from './components/ListaDerivados';
import { Estadisticas } from './components/Estadisticas';
import { ModalAsignacionManual } from './components/Modalasignacionmanual';
import { ModalIntercambio } from './components/Modalintercambio';
import * as api from './services/api';
import type { Paciente, Cama, TipoServicioEnum } from './types/Index';

type Vista = 'dashboard' | 'listaEspera' | 'derivados' | 'estadisticas';
type ModalType = 'paciente' | 'reevaluar' | 'verPaciente' | 'configuracion' | null;

// CORRECCIÓN PROBLEMA 1: Interfaces para modales de modo manual
interface ModalAsignacionState {
  open: boolean;
  pacienteId: string | null;
  paciente: Paciente | null;
  fromLista?: boolean;
}

interface ModalIntercambioState {
  open: boolean;
  pacienteId: string | null;
  paciente: Paciente | null;
}

function App() {
  const {
    hospitales,
    hospitalActual,
    camas,
    configuracion,
    listaEspera,
    derivados,
    estadisticas,
    loading,
    error,
    wsConnected,
    setHospitalActual,
    cargarCamas,
    cargarListaEspera,
    cargarDerivados,
    cargarConfiguracion,
    refrescarDatos,
    clearError
  } = useApp();

  const [vistaActual, setVistaActual] = useState<Vista>('dashboard');
  const [modalActual, setModalActual] = useState<ModalType>(null);
  const [pacienteSeleccionado, setPacienteSeleccionado] = useState<Paciente | null>(null);
  const [filtroServicio, setFiltroServicio] = useState<TipoServicioEnum | 'todos'>('todos');
  const [alertMessage, setAlertMessage] = useState<{ tipo: 'success' | 'error' | 'info'; mensaje: string } | null>(null);

  // CORRECCIÓN PROBLEMA 1: Estados para modales de modo manual
  const [modalAsignacion, setModalAsignacion] = useState<ModalAsignacionState>({
    open: false,
    pacienteId: null,
    paciente: null,
    fromLista: false
  });

  const [modalIntercambio, setModalIntercambio] = useState<ModalIntercambioState>({
    open: false,
    pacienteId: null,
    paciente: null
  });

  // Agrupar camas por servicio y sala
  const camasAgrupadas = React.useMemo(() => {
    const grupos: Record<string, { servicio: string; tipo: TipoServicioEnum; salas: Record<string, Cama[]> }> = {};
    
    camas.forEach(cama => {
      const servicioNombre = cama.servicio_nombre || cama.sala?.servicio?.nombre;
      const servicioTipo = cama.servicio_tipo || cama.sala?.servicio?.tipo;
      
      if (!servicioNombre || !servicioTipo) return;
      
      if (filtroServicio !== 'todos' && servicioTipo !== filtroServicio) return;
      
      if (!grupos[servicioNombre]) {
        grupos[servicioNombre] = {
          servicio: servicioNombre,
          tipo: servicioTipo as TipoServicioEnum,
          salas: {}
        };
      }
      
      const salaNombre = cama.sala?.nombre || `Sala ${cama.sala_id?.slice(0, 8) || 'Sin sala'}`;
      if (!grupos[servicioNombre].salas[salaNombre]) {
        grupos[servicioNombre].salas[salaNombre] = [];
      }
      grupos[servicioNombre].salas[salaNombre].push(cama);
    });
    
    return grupos;
  }, [camas, filtroServicio]);

  // Obtener tipos de servicio únicos para el filtro
  const tiposServicio = React.useMemo(() => {
    const tipos = new Set<TipoServicioEnum>();
    camas.forEach(cama => {
      const tipo = cama.servicio_tipo || cama.sala?.servicio?.tipo;
      if (tipo) {
        tipos.add(tipo as TipoServicioEnum);
      }
    });
    return Array.from(tipos);
  }, [camas]);

  const showAlert = useCallback((tipo: 'success' | 'error' | 'info', mensaje: string) => {
    setAlertMessage({ tipo, mensaje });
    setTimeout(() => setAlertMessage(null), 5000);
  }, []);

  //  Función segura para obtener paciente completo
  const obtenerPacienteSeguro = useCallback(async (paciente: Paciente): Promise<Paciente | null> => {
    try {
      // Si el paciente ya tiene todos los datos necesarios, usarlo directamente
      if (paciente && paciente.id && paciente.nombre && paciente.run) {
        return paciente;
      }
      // Si falta información, obtenerla del servidor
      if (paciente?.id) {
        const pacienteCompleto = await api.getPaciente(paciente.id);
        return pacienteCompleto;
      }
      return null;
    } catch (err) {
      console.error('Error obteniendo paciente:', err);
      return null;
    }
  }, []);

  //  Handler mejorado para ver paciente
  const handleVerPaciente = useCallback(async (paciente: Paciente) => {
    if (!paciente || !paciente.id) {
      showAlert('error', 'No se puede mostrar el detalle: datos de paciente incompletos');
      return;
    }
    
    try {
      // Obtener datos completos del paciente
      const pacienteCompleto = await obtenerPacienteSeguro(paciente);
    if (pacienteCompleto) {
      setPacienteSeleccionado(pacienteCompleto);
      setModalActual('verPaciente');
    }
  } catch (err) {
    showAlert('error', 'Error al cargar los datos del paciente');
  }
}, []);


  const handleReevaluar = useCallback(async (paciente: Paciente) => {
    if (!paciente || !paciente.id) {
      showAlert('error', 'No se puede reevaluar: datos de paciente incompletos');
      return;
    }
    
    try {
      const pacienteCompleto = await obtenerPacienteSeguro(paciente);
      if (pacienteCompleto) {
        setPacienteSeleccionado(pacienteCompleto);
        setModalActual('reevaluar');
      } else {
        showAlert('error', 'No se pudo obtener la información del paciente');
      }
    } catch (err) {
      console.error('Error al abrir reevaluación:', err);
      showAlert('error', 'Error al cargar los datos del paciente');
    }
  }, [obtenerPacienteSeguro, showAlert]);

  const handleCompletarTraslado = useCallback(async (pacienteId: string) => {
    try {
      await api.completarTraslado(pacienteId);
      showAlert('success', 'Traslado completado exitosamente');
      if (hospitalActual) cargarCamas(hospitalActual.id);
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al completar traslado');
    }
  }, [hospitalActual, cargarCamas, showAlert]);

  const handleCancelarTraslado = useCallback(async (pacienteId: string) => {
    if (!confirm('¿Está seguro de cancelar este traslado?')) return;
    try {
      await api.cancelarTraslado(pacienteId);
      showAlert('success', 'Traslado cancelado');
      if (hospitalActual) {
        cargarCamas(hospitalActual.id);
        cargarListaEspera(hospitalActual.id);
      }
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al cancelar traslado');
    }
  }, [hospitalActual, cargarCamas, cargarListaEspera, showAlert]);

  const handleBuscarNuevaCama = useCallback(async (pacienteId: string) => {
    try {
      await api.buscarCamaPaciente(pacienteId);
      showAlert('info', 'Paciente agregado a la lista de búsqueda de cama');
      if (hospitalActual) {
        cargarCamas(hospitalActual.id);
        cargarListaEspera(hospitalActual.id);
      }
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al buscar cama');
    }
  }, [hospitalActual, cargarCamas, cargarListaEspera, showAlert]);

  const handleIniciarAlta = useCallback(async (pacienteId: string) => {
    try {
      await api.iniciarAlta(pacienteId);
      showAlert('success', 'Alta iniciada');
      if (hospitalActual) cargarCamas(hospitalActual.id);
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al iniciar alta');
    }
  }, [hospitalActual, cargarCamas, showAlert]);

  const handleDarAlta = useCallback(async (pacienteId: string) => {
    if (!confirm('¿Confirma dar de alta al paciente?')) return;
    try {
      await api.ejecutarAlta(pacienteId);
      showAlert('success', 'Paciente dado de alta exitosamente');
      if (hospitalActual) cargarCamas(hospitalActual.id);
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al dar alta');
    }
  }, [hospitalActual, cargarCamas, showAlert]);

  const handleCancelarAlta = useCallback(async (pacienteId: string) => {
    try {
      await api.cancelarAlta(pacienteId);
      showAlert('info', 'Alta cancelada');
      if (hospitalActual) cargarCamas(hospitalActual.id);
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al cancelar alta');
    }
  }, [hospitalActual, cargarCamas, showAlert]);

  const handleOmitirPausaOxigeno = async (pacienteId: string) => {
  try {
    const resultado = await api.omitirPausaOxigeno(pacienteId);
    if (resultado.success) {
      // Mostrar notificación de éxito
      console.log('Pausa omitida:', resultado.message);
      // Refrescar datos
      await refrescarDatos();
    }
  } catch (error) {
    console.error('Error al omitir pausa:', error);
    // Mostrar error al usuario
  }
};

  const handleConfirmarEgreso = useCallback(async (pacienteId: string) => {
    if (!confirm('¿Confirma el egreso del paciente por derivación?')) return;
    try {
      await api.confirmarEgresoDerivacion(pacienteId);
      showAlert('success', 'Egreso confirmado');
      if (hospitalActual) cargarCamas(hospitalActual.id);
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al confirmar egreso');
    }
  }, [hospitalActual, cargarCamas, showAlert]);

  const handleBloquear = useCallback(async (camaId: string, bloquear: boolean) => {
    const motivo = bloquear ? prompt('Motivo del bloqueo (opcional):') : undefined;
    try {
      await api.bloquearCama(camaId, { bloquear, motivo: motivo || undefined });
      showAlert('success', bloquear ? 'Cama bloqueada' : 'Cama desbloqueada');
      if (hospitalActual) cargarCamas(hospitalActual.id);
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al bloquear/desbloquear cama');
    }
  }, [hospitalActual, cargarCamas, showAlert]);

  const handleToggleModoManual = useCallback(async () => {
    if (!configuracion) return;
    const nuevoModo = !configuracion.modo_manual;
    const mensaje = nuevoModo
      ? '¿Activar modo manual? Se cancelarán los traslados pendientes automatizados.'
      : '¿Desactivar modo manual? Se reactivará la asignación automática.';
    
    if (!confirm(mensaje)) return;
    
    try {
      await api.actualizarConfiguracion({ modo_manual: nuevoModo });
      showAlert('success', `Modo ${nuevoModo ? 'manual' : 'automático'} activado`);
      await cargarConfiguracion();
      if (hospitalActual) {
        cargarCamas(hospitalActual.id);
        cargarListaEspera(hospitalActual.id);
      }
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al cambiar modo');
    }
  }, [configuracion, cargarConfiguracion, hospitalActual, cargarCamas, cargarListaEspera, showAlert]);

  // CORRECCIÓN PROBLEMA 1: Handlers para modo manual desde CamaCard

  /**
   * Abre el modal de asignación manual desde una cama ocupada
   */
  const handleAsignarManual = useCallback(async (pacienteId: string) => {
    try {
      const paciente = await api.getPaciente(pacienteId);
      setModalAsignacion({
        open: true,
        pacienteId,
        paciente,
        fromLista: false
      });
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al cargar paciente');
    }
  }, [showAlert]);

  /**
   * Abre el modal de intercambio de pacientes
   */
  const handleIntercambiar = useCallback(async (pacienteId: string) => {
    try {
      const paciente = await api.getPaciente(pacienteId);
      setModalIntercambio({
        open: true,
        pacienteId,
        paciente
      });
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al cargar paciente');
    }
  }, [showAlert]);

  /**
   * Egresa manualmente a un paciente del sistema (con confirmación)
   */
  const handleEgresarManual = useCallback(async (pacienteId: string) => {
    if (!confirm('¿Está seguro de egresar a este paciente del sistema? Esta acción no se puede deshacer.')) {
      return;
    }
    try {
      await api.egresarManual(pacienteId);
      showAlert('success', 'Paciente egresado correctamente');
      if (hospitalActual) {
        cargarCamas(hospitalActual.id);
        cargarListaEspera(hospitalActual.id);
      }
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al egresar paciente');
    }
  }, [hospitalActual, cargarCamas, cargarListaEspera, showAlert]);

  // CORRECCIÓN PROBLEMA 1: Handlers para modo manual desde ListaEspera

  /**
   * Abre el modal de asignación manual desde la lista de espera
   */
  const handleAsignarManualLista = useCallback(async (pacienteId: string) => {
    try {
      const paciente = await api.getPaciente(pacienteId);
      setModalAsignacion({
        open: true,
        pacienteId,
        paciente,
        fromLista: true
      });
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al cargar paciente');
    }
  }, [showAlert]);

  /**
   * Egresa a un paciente de la lista de espera (con confirmación)
   */
  const handleEgresarDeLista = useCallback(async (pacienteId: string) => {
    if (!confirm('¿Está seguro de sacar a este paciente de la lista de espera?')) {
      return;
    }
    try {
      await api.egresarDeLista(pacienteId);
      showAlert('success', 'Paciente removido de la lista');
      if (hospitalActual) {
        cargarCamas(hospitalActual.id);
        cargarListaEspera(hospitalActual.id);
      }
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al remover paciente');
    }
  }, [hospitalActual, cargarCamas, cargarListaEspera, showAlert]);

  // CORRECCIÓN PROBLEMA 1: Handler para asignación desde modal

  /**
   * Ejecuta la asignación manual de cama
   */
  const handleConfirmarAsignacion = useCallback(async (pacienteId: string, camaId: string) => {
    try {
      if (modalAsignacion.fromLista) {
        await api.asignarManualDesdeLista(pacienteId, camaId);
      } else {
        await api.asignarManualDesdeCama(pacienteId, camaId);
      }
      showAlert('success', 'Cama asignada correctamente');
      setModalAsignacion({ open: false, pacienteId: null, paciente: null, fromLista: false });
      if (hospitalActual) {
        cargarCamas(hospitalActual.id);
        cargarListaEspera(hospitalActual.id);
      }
    } catch (err) {
      throw err; // Propagar para que el modal muestre el error
    }
  }, [modalAsignacion.fromLista, hospitalActual, cargarCamas, cargarListaEspera, showAlert]);

  /**
   * Ejecuta el intercambio de pacientes
   */
  const handleConfirmarIntercambio = useCallback(async (pacienteAId: string, pacienteBId: string) => {
    try {
      await api.intercambiarPacientes(pacienteAId, pacienteBId);
      showAlert('success', 'Pacientes intercambiados correctamente');
      setModalIntercambio({ open: false, pacienteId: null, paciente: null });
      if (hospitalActual) {
        cargarCamas(hospitalActual.id);
      }
    } catch (err) {
      throw err; // Propagar para que el modal muestre el error
    }
  }, [hospitalActual, cargarCamas, showAlert]);

  const handleFormSubmit = useCallback(async () => {
    setModalActual(null);
    setPacienteSeleccionado(null);
    showAlert('success', 'Operación completada exitosamente');
    if (hospitalActual) {
      await cargarCamas(hospitalActual.id);
      await cargarListaEspera(hospitalActual.id);
      await cargarDerivados(hospitalActual.id);
    }
  }, [hospitalActual, cargarCamas, cargarListaEspera, cargarDerivados, showAlert]);

  const handleFormError = useCallback((mensaje: string) => {
    showAlert('error', mensaje);
  }, [showAlert]);

  // Handler para selección de hospital
  const handleHospitalChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedId = e.target.value;
    if (selectedId === '') {
      setHospitalActual(null);
    } else {
      const hospital = hospitales.find(h => h.id === selectedId);
      if (hospital) {
        setHospitalActual(hospital);
      }
    }
  }, [hospitales, setHospitalActual]);

  // Render header
  const renderHeader = () => (
    <header className="header">
      <div className="header-left">
        <Building2 className="header-icon" />
        <h1>Sistema de Gestión de Camas</h1>
        <span className={`ws-status ${wsConnected ? 'connected' : 'disconnected'}`}>
          {wsConnected ? <Wifi size={16} /> : <WifiOff size={16} />}
          {wsConnected ? 'Conectado' : 'Desconectado'}
        </span>
      </div>
      <div className="header-right">
        <select
          className="hospital-select"
          value={hospitalActual?.id || ''}
          onChange={handleHospitalChange}
        >
          <option value="">Seleccionar hospital</option>
          {hospitales.map(h => (
            <option key={h.id} value={h.id}>{h.nombre}</option>
          ))}
        </select>
        <button
          className={`btn btn-secondary ${configuracion?.modo_manual ? 'active modo-manual-btn' : ''}`}
          onClick={handleToggleModoManual}
          title={configuracion?.modo_manual ? 'Modo manual activo' : 'Modo automático activo'}
        >
          <Settings size={18} />
          {configuracion?.modo_manual ? 'Manual' : 'Auto'}
        </button>
        <button className="btn btn-secondary" onClick={refrescarDatos} title="Refrescar datos">
          <RefreshCw size={18} />
        </button>
      </div>
    </header>
  );

  // Render navegación
  const renderNav = () => (
    <nav className="nav-tabs">
      <button
        className={`nav-tab ${vistaActual === 'dashboard' ? 'active' : ''}`}
        onClick={() => setVistaActual('dashboard')}
      >
        <Bed size={18} /> Dashboard
      </button>
      <button
        className={`nav-tab ${vistaActual === 'listaEspera' ? 'active' : ''}`}
        onClick={() => setVistaActual('listaEspera')}
      >
        <Users size={18} /> Lista de Espera
        {listaEspera.length > 0 && <span className="badge">{listaEspera.length}</span>}
      </button>
      <button
        className={`nav-tab ${vistaActual === 'derivados' ? 'active' : ''}`}
        onClick={() => setVistaActual('derivados')}
      >
        <ArrowRightLeft size={18} /> Derivados
        {derivados.length > 0 && <span className="badge">{derivados.length}</span>}
      </button>
      <button
        className={`nav-tab ${vistaActual === 'estadisticas' ? 'active' : ''}`}
        onClick={() => setVistaActual('estadisticas')}
      >
        <BarChart3 size={18} /> Estadísticas
      </button>
      <div className="nav-spacer" />
      <button
        className="btn btn-primary"
        onClick={() => setModalActual('paciente')}
        disabled={!hospitalActual}
      >
        <Plus size={18} /> Nuevo Paciente
      </button>
    </nav>
  );

  // Render dashboard de camas
  const renderDashboard = () => {
    if (!hospitalActual) {
      return (
        <div className="empty-state">
          <Building2 size={48} />
          <h2>Seleccione un hospital</h2>
          <p>Elija un hospital del menú superior para ver sus camas</p>
        </div>
      );
    }

    if (loading) {
      return (
        <div className="loading">
          <RefreshCw className="spin" size={32} />
          <p>Cargando...</p>
        </div>
      );
    }

    return (
      <div className="dashboard">
        <div className="dashboard-header">
          <h2>{hospitalActual.nombre}</h2>
          {configuracion?.modo_manual && (
            <span className="modo-manual-badge">MODO MANUAL ACTIVO</span>
          )}
          <div className="filtro-servicio">
            <label>Filtrar por servicio:</label>
            <select
              value={filtroServicio}
              onChange={(e) => setFiltroServicio(e.target.value as TipoServicioEnum | 'todos')}
            >
              <option value="todos">Todos los servicios</option>
              {tiposServicio.map(tipo => (
                <option key={tipo} value={tipo}>
                  {tipo.charAt(0).toUpperCase() + tipo.slice(1).replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>
        </div>

        {Object.keys(camasAgrupadas).length === 0 ? (
          <div className="empty-state">
            <Bed size={48} />
            <h3>No hay camas disponibles</h3>
            <p>No se encontraron camas con los filtros seleccionados</p>
          </div>
        ) : (
          <div className="servicios-grid">
            {Object.entries(camasAgrupadas).map(([servicioNombre, grupo]) => (
              <div key={servicioNombre} className={`servicio-section servicio-${grupo.tipo}`}>
                <h3 className="servicio-titulo">{servicioNombre}</h3>
                {Object.entries(grupo.salas).map(([salaNombre, camasSala]) => (
                  <div key={salaNombre} className="sala-section">
                    <h4 className="sala-titulo">{salaNombre}</h4>
                    <div className="camas-grid">
                      {camasSala.map(cama => (
                        <CamaCard
                          key={cama.id}
                          cama={cama}
                          modoManual={configuracion?.modo_manual || false}
                          onVerPaciente={handleVerPaciente}
                          onReevaluar={handleReevaluar}
                          onCompletarTraslado={handleCompletarTraslado}
                          onCancelarTraslado={handleCancelarTraslado}
                          onBuscarNuevaCama={handleBuscarNuevaCama}
                          onIniciarAlta={handleIniciarAlta}
                          onDarAlta={handleDarAlta}
                          onCancelarAlta={handleCancelarAlta}
                          onConfirmarEgreso={handleConfirmarEgreso}
                          onBloquear={handleBloquear}
                          onAsignarManual={handleAsignarManual}
                          onIntercambiar={handleIntercambiar}
                          onEgresarManual={handleEgresarManual}
                          onOmitirPausaOxigeno={handleOmitirPausaOxigeno}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  // Render contenido principal según vista
  const renderContenido = () => {
    switch (vistaActual) {
      case 'dashboard':
        return renderDashboard();
      case 'listaEspera':
        return (
          <ListaEspera
            items={listaEspera}
            hospitalActual={hospitalActual}
            modoManual={configuracion?.modo_manual || false}
            onVerPaciente={handleVerPaciente}
            onCancelarBusqueda={async (pacienteId) => {
              if (!confirm('¿Cancelar la búsqueda de cama para este paciente?')) return;
              try {
                await api.cancelarBusquedaCama(pacienteId);
                showAlert('info', 'Búsqueda cancelada');
                if (hospitalActual) {
                  cargarCamas(hospitalActual.id);
                  cargarListaEspera(hospitalActual.id);
                }
              } catch (err) {
                showAlert('error', err instanceof Error ? err.message : 'Error al cancelar');
              }
            }}
            onRefresh={() => hospitalActual && cargarListaEspera(hospitalActual.id)}
            onAsignarManual={handleAsignarManualLista}
            onEgresarDeLista={handleEgresarDeLista}
          />
        );
      case 'derivados':
        return (
          <ListaDerivados
            items={derivados}
            hospitalActual={hospitalActual}
            onVerPaciente={handleVerPaciente}
            onAceptar={async (pacienteId) => {
              try {
                await api.accionDerivacion(pacienteId, { accion: 'aceptar' });
                showAlert('success', 'Derivación aceptada');
                if (hospitalActual) {
                  cargarDerivados(hospitalActual.id);
                  cargarListaEspera(hospitalActual.id);
                }
              } catch (err) {
                showAlert('error', err instanceof Error ? err.message : 'Error al aceptar');
              }
            }}
            onRechazar={async (pacienteId) => {
              const motivo = prompt('Motivo del rechazo:');
              if (!motivo) return;
              try {
                await api.accionDerivacion(pacienteId, { accion: 'rechazar', motivo_rechazo: motivo });
                showAlert('info', 'Derivación rechazada');
                if (hospitalActual) cargarDerivados(hospitalActual.id);
              } catch (err) {
                showAlert('error', err instanceof Error ? err.message : 'Error al rechazar');
              }
            }}
            onRefresh={() => hospitalActual && cargarDerivados(hospitalActual.id)}
          />
        );
      case 'estadisticas':
        return <Estadisticas estadisticas={estadisticas} />;
      default:
        return null;
    }
  };

  return (
    <div className="app">
      {renderHeader()}
      {renderNav()}
      
      <main className="main-content">
        {error && (
          <Alert tipo="error" mensaje={error} onClose={clearError} />
        )}
        {alertMessage && (
          <Alert
            tipo={alertMessage.tipo}
            mensaje={alertMessage.mensaje}
            onClose={() => setAlertMessage(null)}
          />
        )}
        {renderContenido()}
      </main>

      {/* Modal para nuevo paciente */}
      <Modal
        isOpen={modalActual === 'paciente'}
        onClose={() => setModalActual(null)}
        title="Registrar Nuevo Paciente"
        size="large"
      >
        <PacienteForm
          hospitalId={hospitalActual?.id || ''}
          hospitales={hospitales}
          onSubmit={handleFormSubmit}
          onError={handleFormError}
          onCancel={() => setModalActual(null)}
        />
      </Modal>

      {/* Modal para reevaluar paciente */}
      <Modal
        isOpen={modalActual === 'reevaluar'}
        onClose={() => { setModalActual(null); setPacienteSeleccionado(null); }}
        title="Reevaluar Paciente"
        size="large"
      >
        {pacienteSeleccionado && (
          <PacienteForm
            paciente={pacienteSeleccionado}
            hospitalId={hospitalActual?.id || ''}
            hospitales={hospitales}
            isReevaluacion
            onSubmit={handleFormSubmit}
            onError={handleFormError}
            onCancel={() => { setModalActual(null); setPacienteSeleccionado(null); }}
          />
        )}
      </Modal>

      {/* CORRECCIÓN PROBLEMA 2: Modal para ver paciente con manejo de errores */}
      <Modal
        isOpen={modalActual === 'verPaciente'}
        onClose={() => { setModalActual(null); setPacienteSeleccionado(null); }}
        title="Detalle del Paciente"
        size="medium"
      >
        {pacienteSeleccionado ? (
          <PacienteDetalle
            paciente={pacienteSeleccionado}
            onReevaluar={() => setModalActual('reevaluar')}
            onClose={() => { setModalActual(null); setPacienteSeleccionado(null); }}
          />
        ) : (
          <div className="loading">
            <RefreshCw className="spin" size={24} />
            <p>Cargando datos del paciente...</p>
          </div>
        )}
      </Modal>

      {/* CORRECCIÓN PROBLEMA 1: Modal de asignación manual */}
      <ModalAsignacionManual
        isOpen={modalAsignacion.open}
        paciente={modalAsignacion.paciente}
        hospitalId={hospitalActual?.id || ''}
        onClose={() => setModalAsignacion({ open: false, pacienteId: null, paciente: null, fromLista: false })}
        onAsignar={handleConfirmarAsignacion}
        titulo={modalAsignacion.fromLista ? "Asignar Cama desde Lista de Espera" : "Asignar Nueva Cama"}
      />

      {/* CORRECCIÓN PROBLEMA 1: Modal de intercambio */}
      <ModalIntercambio
        isOpen={modalIntercambio.open}
        pacienteOrigen={modalIntercambio.paciente}
        hospitalId={hospitalActual?.id || ''}
        onClose={() => setModalIntercambio({ open: false, pacienteId: null, paciente: null })}
        onIntercambiar={handleConfirmarIntercambio}
      />
    </div>
  );
}

export default App;