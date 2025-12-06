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
import * as api from './services/api';
import type { Paciente, Cama, TipoServicioEnum } from './types/Index';

type Vista = 'dashboard' | 'listaEspera' | 'derivados' | 'estadisticas';
type ModalType = 'paciente' | 'reevaluar' | 'verPaciente' | 'configuracion' | null;

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
    setError,
    clearError
  } = useApp();

  const [vistaActual, setVistaActual] = useState<Vista>('dashboard');
  const [modalActual, setModalActual] = useState<ModalType>(null);
  const [pacienteSeleccionado, setPacienteSeleccionado] = useState<Paciente | null>(null);
  const [filtroServicio, setFiltroServicio] = useState<TipoServicioEnum | 'todos'>('todos');
  const [alertMessage, setAlertMessage] = useState<{ tipo: 'success' | 'error' | 'info'; mensaje: string } | null>(null);

  // Agrupar camas por servicio y sala
  const camasAgrupadas = React.useMemo(() => {
    const grupos: Record<string, { servicio: string; tipo: TipoServicioEnum; salas: Record<string, Cama[]> }> = {};
    
    camas.forEach(cama => {
      const servicio = cama.sala?.servicio;
      if (!servicio) return;
      
      if (filtroServicio !== 'todos' && servicio.tipo !== filtroServicio) return;
      
      if (!grupos[servicio.nombre]) {
        grupos[servicio.nombre] = {
          servicio: servicio.nombre,
          tipo: servicio.tipo as TipoServicioEnum,
          salas: {}
        };
      }
      
      const salaNombre = cama.sala?.nombre || 'Sin sala';
      if (!grupos[servicio.nombre].salas[salaNombre]) {
        grupos[servicio.nombre].salas[salaNombre] = [];
      }
      grupos[servicio.nombre].salas[salaNombre].push(cama);
    });
    
    return grupos;
  }, [camas, filtroServicio]);

  // Obtener tipos de servicio únicos para el filtro
  const tiposServicio = React.useMemo(() => {
    const tipos = new Set<TipoServicioEnum>();
    camas.forEach(cama => {
      if (cama.sala?.servicio?.tipo) {
        tipos.add(cama.sala.servicio.tipo as TipoServicioEnum);
      }
    });
    return Array.from(tipos);
  }, [camas]);

  const showAlert = useCallback((tipo: 'success' | 'error' | 'info', mensaje: string) => {
    setAlertMessage({ tipo, mensaje });
    setTimeout(() => setAlertMessage(null), 5000);
  }, []);

  // Handlers para acciones de cama
  const handleVerPaciente = useCallback((paciente: Paciente) => {
    setPacienteSeleccionado(paciente);
    setModalActual('verPaciente');
  }, []);

  const handleReevaluar = useCallback((paciente: Paciente) => {
    setPacienteSeleccionado(paciente);
    setModalActual('reevaluar');
  }, []);

  const handleCompletarTraslado = useCallback(async (pacienteId: number) => {
    try {
      await api.completarTraslado(pacienteId);
      showAlert('success', 'Traslado completado exitosamente');
      if (hospitalActual) cargarCamas(hospitalActual.id);
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al completar traslado');
    }
  }, [hospitalActual, cargarCamas, showAlert]);

  const handleCancelarTraslado = useCallback(async (pacienteId: number) => {
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

  const handleBuscarNuevaCama = useCallback(async (pacienteId: number) => {
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

  const handleIniciarAlta = useCallback(async (pacienteId: number) => {
    try {
      await api.iniciarAlta(pacienteId);
      showAlert('success', 'Alta iniciada');
      if (hospitalActual) cargarCamas(hospitalActual.id);
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al iniciar alta');
    }
  }, [hospitalActual, cargarCamas, showAlert]);

  const handleDarAlta = useCallback(async (pacienteId: number) => {
    if (!confirm('¿Confirma dar de alta al paciente?')) return;
    try {
      await api.ejecutarAlta(pacienteId);
      showAlert('success', 'Paciente dado de alta exitosamente');
      if (hospitalActual) cargarCamas(hospitalActual.id);
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al dar alta');
    }
  }, [hospitalActual, cargarCamas, showAlert]);

  const handleCancelarAlta = useCallback(async (pacienteId: number) => {
    try {
      await api.cancelarAlta(pacienteId);
      showAlert('info', 'Alta cancelada');
      if (hospitalActual) cargarCamas(hospitalActual.id);
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al cancelar alta');
    }
  }, [hospitalActual, cargarCamas, showAlert]);

  const handleConfirmarEgreso = useCallback(async (pacienteId: number) => {
    if (!confirm('¿Confirma el egreso del paciente por derivación?')) return;
    try {
      await api.confirmarEgresoDerivacion(pacienteId);
      showAlert('success', 'Egreso confirmado');
      if (hospitalActual) cargarCamas(hospitalActual.id);
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al confirmar egreso');
    }
  }, [hospitalActual, cargarCamas, showAlert]);

  const handleBloquear = useCallback(async (camaId: number, bloquear: boolean) => {
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
      if (hospitalActual) cargarCamas(hospitalActual.id);
    } catch (err) {
      showAlert('error', err instanceof Error ? err.message : 'Error al cambiar modo');
    }
  }, [configuracion, cargarConfiguracion, hospitalActual, cargarCamas, showAlert]);

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
  value={hospitalActual ? String(hospitalActual.id) : ''}
  onChange={(e) => {
    const selectedId = e.target.value;
    if (selectedId === '') {
      setHospitalActual(null);
    } else {
      const hospital = hospitales.find(h => h.id === Number(selectedId));
      if (hospital) {
        setHospitalActual(hospital);
      }
    }
  }}
>
  <option value="">Seleccionar hospital</option>
  {hospitales.map(h => (
    <option key={h.id} value={String(h.id)}>{h.nombre}</option>
  ))}
</select>
        <button
          className={`btn btn-secondary ${configuracion?.modo_manual ? 'active' : ''}`}
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
          hospitalId={hospitalActual?.id || 0}
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
            hospitalId={hospitalActual?.id || 0}
            hospitales={hospitales}
            isReevaluacion
            onSubmit={handleFormSubmit}
            onError={handleFormError}
            onCancel={() => { setModalActual(null); setPacienteSeleccionado(null); }}
          />
        )}
      </Modal>

      {/* Modal para ver paciente */}
      <Modal
        isOpen={modalActual === 'verPaciente'}
        onClose={() => { setModalActual(null); setPacienteSeleccionado(null); }}
        title="Detalle del Paciente"
        size="medium"
      >
        {pacienteSeleccionado && (
          <PacienteDetalle
            paciente={pacienteSeleccionado}
            onReevaluar={() => setModalActual('reevaluar')}
            onClose={() => { setModalActual(null); setPacienteSeleccionado(null); }}
          />
        )}
      </Modal>
    </div>
  );
}

export default App;