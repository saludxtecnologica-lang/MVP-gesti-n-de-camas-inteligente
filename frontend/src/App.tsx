import { useState } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { ModalProvider, useModal } from './context/ModalContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Header } from './components/layout';
import { Alert, FullPageSpinner } from './components/common';
import { Dashboard, ListaEspera, Derivados, Estadisticas } from './pages';
import { LoginPage, UserBadge } from './components/auth/Login';
import { 
  ModalPaciente, 
  ModalConfiguracion, 
  ModalAsignacionManual, 
  ModalIntercambio,
  ModalRegistroPaciente,
  ModalReevaluarPaciente
} from './components/modales';

type Vista = 'dashboard' | 'listaEspera' | 'derivados' | 'estadisticas';

function AppContent() {
  const { loading, alert, hideAlert } = useApp();
  const { modalState, closeModal, isOpen } = useModal();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [vistaActual, setVistaActual] = useState<Vista>('dashboard');

  // Mostrar spinner mientras carga la autenticación
  if (authLoading) {
    return <FullPageSpinner />;
  }

  // Si no está autenticado, mostrar login
  if (!isAuthenticated) {
    return <LoginPage />;
  }

  // Usuario autenticado - mostrar la aplicación
  if (loading) {
    return <FullPageSpinner />;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header con UserBadge */}
      <Header vistaActual={vistaActual} onCambiarVista={setVistaActual}>
        {/* UserBadge se pasa como children al Header */}
        <UserBadge />
      </Header>

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

      {/* Modal de Registro de Paciente */}
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

      {/* Modal para Reevaluar Paciente */}
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
    <AuthProvider>
      <AppProvider>
        <ModalProvider>
          <AppContent />
        </ModalProvider>
      </AppProvider>
    </AuthProvider>
  );
}
