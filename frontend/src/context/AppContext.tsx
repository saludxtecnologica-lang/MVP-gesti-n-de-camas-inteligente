import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode, useRef } from 'react';
import type { 
  Hospital, 
  Cama, 
  ConfiguracionSistema, 
  ListaEsperaItem, 
  DerivadoItem,
  AlertState,
  WebSocketEvent
} from '../types'
import * as api from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';
import { useTextToSpeech } from '../hooks/useTextToSpeech';

// ============================================
// TIPOS DEL CONTEXT
// ============================================

interface AppContextType {
  // Estado
  hospitales: Hospital[];
  hospitalSeleccionado: Hospital | null;
  camas: Cama[];
  listaEspera: ListaEsperaItem[];
  derivados: DerivadoItem[];
  configuracion: ConfiguracionSistema | null;
  loading: boolean;
  alert: AlertState | null;
  wsConnected: boolean;
  dataVersion: number;
  
  // ============================================
  // NUEVO: Estado TTS
  // ============================================
  servicioSeleccionadoId: string | null;
  ttsHabilitado: boolean;
  ttsDisponible: boolean;
  
  // Acciones
  setHospitalSeleccionado: (hospital: Hospital | null) => void;
  recargarCamas: () => Promise<void>;
  recargarListaEspera: () => Promise<void>;
  recargarDerivados: () => Promise<void>;
  recargarTodo: () => Promise<void>;
  setConfiguracion: (config: ConfiguracionSistema) => void;
  showAlert: (tipo: AlertState['tipo'], mensaje: string) => void;
  hideAlert: () => void;
  testSound: () => void;
  
  // ============================================
  // NUEVO: Acciones TTS
  // ============================================
  setServicioSeleccionadoId: (id: string | null) => void;
  setTtsHabilitado: (habilitado: boolean) => void;
  testTts: () => void;
}

const AppContext = createContext<AppContextType | null>(null);

// ============================================
// PROVIDER
// ============================================

export function AppProvider({ children }: { children: ReactNode }) {
  // Estado principal
  const [hospitales, setHospitales] = useState<Hospital[]>([]);
  const [hospitalSeleccionado, setHospitalSeleccionado] = useState<Hospital | null>(null);
  const [camas, setCamas] = useState<Cama[]>([]);
  const [listaEspera, setListaEspera] = useState<ListaEsperaItem[]>([]);
  const [derivados, setDerivados] = useState<DerivadoItem[]>([]);
  const [configuracion, setConfiguracion] = useState<ConfiguracionSistema | null>(null);
  const [loading, setLoading] = useState(true);
  const [alert, setAlert] = useState<AlertState | null>(null);
  const [dataVersion, setDataVersion] = useState(0);

  // ============================================
  // NUEVO: Estado TTS
  // ============================================
  const [servicioSeleccionadoId, setServicioSeleccionadoId] = useState<string | null>(null);
  const [ttsHabilitado, setTtsHabilitado] = useState(true);

  // Ref para acceder al hospital actual sin causar re-renders del callback
  const hospitalRef = useRef<Hospital | null>(null);
  
  // Flag para evitar múltiples recargas simultáneas
  const isReloadingRef = useRef(false);
  
  // Mantener ref sincronizado con el estado
  useEffect(() => {
    hospitalRef.current = hospitalSeleccionado;
  }, [hospitalSeleccionado]);

  // ============================================
  // HOOK TTS
  // ============================================
  const { 
    procesarEvento: procesarEventoTTS, 
    probar: testTts,
    disponible: ttsDisponible 
  } = useTextToSpeech({
    servicioSeleccionadoId,
    habilitado: ttsHabilitado
  });

  // Ref para TTS
  const procesarEventoTTSRef = useRef(procesarEventoTTS);
  useEffect(() => {
    procesarEventoTTSRef.current = procesarEventoTTS;
  }, [procesarEventoTTS]);

  // ============================================
  // FUNCIÓN DE RECARGA DIRECTA (para WebSocket)
  // ============================================
  const recargarDatosDirecto = useCallback(async () => {
    const hospital = hospitalRef.current;
    if (!hospital?.id) {
      console.log('[WS] No hay hospital seleccionado, ignorando recarga');
      return;
    }
    
    if (isReloadingRef.current) {
      console.log('[WS] Ya hay una recarga en progreso, ignorando');
      return;
    }
    
    isReloadingRef.current = true;
    console.log('[WS] Recargando datos para hospital:', hospital.nombre);
    
    // ============================================
    // PRESERVAR POSICIÓN DEL SCROLL
    // ============================================
    const scrollPosition = window.scrollY;
    const scrollElement = document.scrollingElement || document.documentElement;
    
    try {
      const [camasData, listaData, derivadosData] = await Promise.all([
        api.getCamasHospital(hospital.id),
        api.getListaEspera(hospital.id),
        api.getDerivados(hospital.id)
      ]);
      
      setCamas([...camasData]);
      setListaEspera([...listaData]);
      setDerivados([...derivadosData]);
      setDataVersion(v => v + 1);
      
      // ============================================
      // RESTAURAR POSICIÓN DEL SCROLL
      // ============================================
      // Usar requestAnimationFrame para asegurar que el DOM se haya actualizado
      requestAnimationFrame(() => {
        // Doble requestAnimationFrame para mayor seguridad en la sincronización
        requestAnimationFrame(() => {
          window.scrollTo({
            top: scrollPosition,
            behavior: 'instant'
          });
        });
      });
      
      console.log('[WS] Datos recargados exitosamente');
    } catch (error) {
      console.error('[WS] Error recargando datos:', error);
    } finally {
      isReloadingRef.current = false;
    }
  }, []);

  // ============================================
  // HANDLER DE WEBSOCKET (MODIFICADO PARA TTS)
  // ============================================
  const handleWebSocketMessage = useCallback((event: WebSocketEvent) => {
    console.log('[WS] Mensaje recibido:', event.tipo, 'reload:', event.reload);
    
    // ============================================
    // NUEVO: Procesar evento TTS si corresponde
    // ============================================
    if (event.tts_habilitado) {
      procesarEventoTTSRef.current(event);
    }
    
    if (event.reload === true) {
      const eventosRecarga = [
        'paciente_creado',
        'paciente_actualizado',
        'asignacion_completada',
        'asignacion_automatica',
        'busqueda_iniciada',
        'busqueda_cancelada',
        'pausa_oxigeno_omitida',
        'traslado_completado',
        'traslado_iniciado',
        'alta_ejecutada',
        'alta_iniciada',
        'limpieza_completada',
        'estado_actualizado',
        'configuracion_actualizada',
        'cama_bloqueada',
        'cama_desbloqueada',
        'evaluacion_oxigeno_completada',
        'camas_liberadas',
        // NUEVO: Agregar derivación aceptada
        'derivacion_aceptada'
      ];
      
      if (eventosRecarga.includes(event.tipo)) {
        console.log('[WS] Ejecutando recarga por evento:', event.tipo);
        recargarDatosDirecto();
      } else {
        const currentHospital = hospitalRef.current;
        if (event.hospital_id && currentHospital && event.hospital_id === currentHospital.id) {
          console.log('[WS] Ejecutando recarga por hospital_id match');
          recargarDatosDirecto();
        }
      }
    }
  }, [recargarDatosDirecto]);

  // ============================================
  // WEBSOCKET HOOK
  // ============================================
  const { isConnected: wsConnected, testSound } = useWebSocket({
    onMessage: handleWebSocketMessage,
    onConnect: () => console.log('[WS] Conectado al servidor'),
    onDisconnect: () => console.log('[WS] Desconectado del servidor'),
    enableSound: true
  });

  // ============================================
  // FUNCIONES DE CARGA PÚBLICAS
  // ============================================
  const recargarCamas = useCallback(async () => {
    if (!hospitalSeleccionado) return;
    
    const scrollPosition = window.scrollY;
    
    try {
      const data = await api.getCamasHospital(hospitalSeleccionado.id);
      setCamas([...data]);
      setDataVersion(v => v + 1);
      
      // Restaurar scroll
      requestAnimationFrame(() => {
        window.scrollTo({ top: scrollPosition, behavior: 'instant' });
      });
    } catch (error) {
      console.error('Error al cargar camas:', error);
    }
  }, [hospitalSeleccionado]);

  const recargarListaEspera = useCallback(async () => {
    if (!hospitalSeleccionado) return;
    
    const scrollPosition = window.scrollY;
    
    try {
      const data = await api.getListaEspera(hospitalSeleccionado.id);
      setListaEspera([...data]);
      setDataVersion(v => v + 1);
      
      // Restaurar scroll
      requestAnimationFrame(() => {
        window.scrollTo({ top: scrollPosition, behavior: 'instant' });
      });
    } catch (error) {
      console.error('Error al cargar lista de espera:', error);
    }
  }, [hospitalSeleccionado]);

  const recargarDerivados = useCallback(async () => {
    if (!hospitalSeleccionado) return;
    
    const scrollPosition = window.scrollY;
    
    try {
      const data = await api.getDerivados(hospitalSeleccionado.id);
      setDerivados([...data]);
      setDataVersion(v => v + 1);
      
      // Restaurar scroll
      requestAnimationFrame(() => {
        window.scrollTo({ top: scrollPosition, behavior: 'instant' });
      });
    } catch (error) {
      console.error('Error al cargar derivados:', error);
    }
  }, [hospitalSeleccionado]);

  const recargarTodo = useCallback(async () => {
    if (!hospitalSeleccionado) return;
    
    // ============================================
    // PRESERVAR POSICIÓN DEL SCROLL
    // ============================================
    const scrollPosition = window.scrollY;
    
    try {
      const [camasData, listaData, derivadosData] = await Promise.all([
        api.getCamasHospital(hospitalSeleccionado.id),
        api.getListaEspera(hospitalSeleccionado.id),
        api.getDerivados(hospitalSeleccionado.id)
      ]);
      
      setCamas([...camasData]);
      setListaEspera([...listaData]);
      setDerivados([...derivadosData]);
      setDataVersion(v => v + 1);
      
      // ============================================
      // RESTAURAR POSICIÓN DEL SCROLL
      // ============================================
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          window.scrollTo({
            top: scrollPosition,
            behavior: 'instant'
          });
        });
      });
    } catch (error) {
      console.error('Error al recargar todo:', error);
    }
  }, [hospitalSeleccionado]);

  // ============================================
  // ALERTAS
  // ============================================
  const showAlert = useCallback((tipo: AlertState['tipo'], mensaje: string) => {
    setAlert({ tipo, mensaje });
    setTimeout(() => setAlert(null), 5000);
  }, []);

  const hideAlert = useCallback(() => {
    setAlert(null);
  }, []);

  // ============================================
  // CARGA INICIAL
  // ============================================
  useEffect(() => {
    async function cargarDatosIniciales() {
      try {
        setLoading(true);
        const [hospitalesData, configData] = await Promise.all([
          api.getHospitales(),
          api.getConfiguracion()
        ]);
        
        setHospitales(hospitalesData);
        setConfiguracion(configData);
        
        if (hospitalesData.length > 0) {
          setHospitalSeleccionado(hospitalesData[0]);
        }
      } catch (error) {
        console.error('Error al cargar datos iniciales:', error);
        showAlert('error', 'Error al conectar con el servidor');
      } finally {
        setLoading(false);
      }
    }
    
    cargarDatosIniciales();
  }, [showAlert]);

  // ============================================
  // RECARGAR AL CAMBIAR HOSPITAL
  // ============================================
  useEffect(() => {
    if (hospitalSeleccionado) {
      recargarTodo();
    }
  }, [hospitalSeleccionado, recargarTodo]);

  // ============================================
  // VALOR DEL CONTEXTO
  // ============================================
  const value: AppContextType = {
    hospitales,
    hospitalSeleccionado,
    camas,
    listaEspera,
    derivados,
    configuracion,
    loading,
    alert,
    wsConnected,
    dataVersion,
    // NUEVO: TTS
    servicioSeleccionadoId,
    ttsHabilitado,
    ttsDisponible,
    // Acciones
    setHospitalSeleccionado,
    recargarCamas,
    recargarListaEspera,
    recargarDerivados,
    recargarTodo,
    setConfiguracion,
    showAlert,
    hideAlert,
    testSound,
    // NUEVO: Acciones TTS
    setServicioSeleccionadoId,
    setTtsHabilitado,
    testTts
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}

// ============================================
// HOOK
// ============================================

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp debe usarse dentro de AppProvider');
  }
  return context;
}