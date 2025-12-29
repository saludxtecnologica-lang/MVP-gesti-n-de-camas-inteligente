import { useState } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { ModalProvider, useModal } from './context/ModalContext';
import { Header } from './components/layout';
import { Alert, FullPageSpinner } from './components/common';
import { Dashboard, ListaEspera, Derivados, Estadisticas } from './pages';
import { 
  ModalPaciente, 
  ModalConfiguracion, 
  ModalAsignacionManual, 
  ModalIntercambio,
  ModalRegistroPaciente,
  ModalReevaluarPaciente  // NUEVO: Importar el modal de reevaluación
} from './components/modales';

type Vista = 'dashboard' | 'listaEspera' | 'derivados' | 'estadisticas';

function AppContent() {
  const { loading, alert, hideAlert } = useApp();
  const { modalState, closeModal, isOpen } = useModal();
  const [vistaActual, setVistaActual] = useState<Vista>('dashboard');

  if (loading) {
    return <FullPageSpinner />;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <Header vistaActual={vistaActual} onCambiarVista={setVistaActual} />

      {/* Contenido principal */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {vistaActual === 'dashboard' && <Dashboard />}
        {vistaActual === 'listaEspera' && <ListaEspera />}
        {vistaActual === 'derivados' && <Derivados />}
        {vistaActual === 'estadisticas' && <Estadisticas />}
      </main>

      {/* Alertas globales */}
      {alert && (
        <Alert tipo={alert.tipo} mensaje={alert.mensaje} onClose={hideAlert} />
      )}

      {/* Modal de Registro de Paciente (NUEVO) */}
      <ModalRegistroPaciente
        isOpen={isOpen('paciente')}
        onClose={closeModal}
      />

      {/* Modal para Ver Paciente */}
      <ModalPaciente
        isOpen={isOpen('verPaciente')}
        onClose={closeModal}
        paciente={modalState.data.paciente || null}
      />

      {/* NUEVO: Modal para Reevaluar Paciente */}
      <ModalReevaluarPaciente
        isOpen={isOpen('reevaluar')}
        onClose={closeModal}
        paciente={modalState.data.paciente || null}
      />

      <ModalConfiguracion
        isOpen={isOpen('configuracion')}
        onClose={closeModal}
      />

      <ModalAsignacionManual
        isOpen={isOpen('asignacionManual')}
        onClose={closeModal}
        cama={modalState.data.cama || null}
      />

      <ModalIntercambio
        isOpen={isOpen('intercambio')}
        onClose={closeModal}
        cama={modalState.data.cama || null}
      />
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <ModalProvider>
        <AppContent />
      </ModalProvider>
    </AppProvider>
  );
}