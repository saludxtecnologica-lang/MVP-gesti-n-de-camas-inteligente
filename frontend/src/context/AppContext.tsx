import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode, useRef } from 'react';
import type {
  Hospital,
  Cama,
  ConfiguracionSistema,
  EstadisticasGlobales,
  ListaEsperaItem,
  DerivadoItem,
  WebSocketEvent
} from '../types/Index';
import * as api from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';

interface AppState {
  hospitales: Hospital[];
  hospitalActual: Hospital | null;
  camas: Cama[];
  configuracion: ConfiguracionSistema | null;
  estadisticas: EstadisticasGlobales | null;
  listaEspera: ListaEsperaItem[];
  derivados: DerivadoItem[];
  loading: boolean;
  error: string | null;
  wsConnected: boolean;
}

interface AppContextValue extends AppState {
  setHospitalActual: (hospital: Hospital | null) => void;
  cargarHospitales: () => Promise<void>;
  cargarCamas: (hospitalId: number) => Promise<void>;
  cargarListaEspera: (hospitalId: number) => Promise<void>;
  cargarDerivados: (hospitalId: number) => Promise<void>;
  cargarConfiguracion: () => Promise<void>;
  cargarEstadisticas: () => Promise<void>;
  refrescarDatos: () => Promise<void>;
  setError: (error: string | null) => void;
  clearError: () => void;
}

const AppContext = createContext<AppContextValue | undefined>(undefined);

interface AppProviderProps {
  children: ReactNode;
}

export function AppProvider({ children }: AppProviderProps) {
  const [state, setState] = useState<AppState>({
    hospitales: [],
    hospitalActual: null,
    camas: [],
    configuracion: null,
    estadisticas: null,
    listaEspera: [],
    derivados: [],
    loading: false,
    error: null,
    wsConnected: false
  });

  // Ref para acceder al hospital actual sin causar re-renders en callbacks
  const hospitalActualRef = useRef<Hospital | null>(null);

  // Mantener ref sincronizada
  useEffect(() => {
    hospitalActualRef.current = state.hospitalActual;
  }, [state.hospitalActual]);

  // Handler de WebSocket - usa ref para evitar recreación del callback
  const handleWsMessage = useCallback((event: WebSocketEvent) => {
    console.log('WebSocket event:', event);
    const currentHospital = hospitalActualRef.current;
    if (currentHospital) {
      api.getCamasHospital(currentHospital.id).then(camas => {
        setState(prev => ({ ...prev, camas }));
      }).catch(console.error);
      api.getListaEspera(currentHospital.id).then(listaEspera => {
        setState(prev => ({ ...prev, listaEspera }));
      }).catch(console.error);
      api.getDerivados(currentHospital.id).then(derivados => {
        setState(prev => ({ ...prev, derivados }));
      }).catch(console.error);
    }
    api.getEstadisticas().then(estadisticas => {
      setState(prev => ({ ...prev, estadisticas }));
    }).catch(console.error);
  }, []); // Sin dependencias - usa ref

  const handleWsConnect = useCallback(() => {
    setState(prev => ({ ...prev, wsConnected: true }));
  }, []);

  const handleWsDisconnect = useCallback(() => {
    setState(prev => ({ ...prev, wsConnected: false }));
  }, []);

  const { isConnected } = useWebSocket({
    onMessage: handleWsMessage,
    onConnect: handleWsConnect,
    onDisconnect: handleWsDisconnect
  });

  useEffect(() => {
    setState(prev => ({ ...prev, wsConnected: isConnected }));
  }, [isConnected]);

  // Cargar hospitales
  const cargarHospitales = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      const hospitales = await api.getHospitales();
      setState(prev => ({ ...prev, hospitales, loading: false }));
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Error cargando hospitales'
      }));
    }
  }, []);

  // Cargar camas - NO modifica loading para evitar race conditions
  const cargarCamas = useCallback(async (hospitalId: number) => {
    try {
      const camas = await api.getCamasHospital(hospitalId);
      setState(prev => ({ ...prev, camas }));
    } catch (error) {
      console.error('Error cargando camas:', error);
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Error cargando camas'
      }));
    }
  }, []);

  // Cargar lista de espera
  const cargarListaEspera = useCallback(async (hospitalId: number) => {
    try {
      const listaEspera = await api.getListaEspera(hospitalId);
      setState(prev => ({ ...prev, listaEspera }));
    } catch (error) {
      console.error('Error cargando lista de espera:', error);
    }
  }, []);

  // Cargar derivados
  const cargarDerivados = useCallback(async (hospitalId: number) => {
    try {
      const derivados = await api.getDerivados(hospitalId);
      setState(prev => ({ ...prev, derivados }));
    } catch (error) {
      console.error('Error cargando derivados:', error);
    }
  }, []);

  // Cargar configuración
  const cargarConfiguracion = useCallback(async () => {
    try {
      const configuracion = await api.getConfiguracion();
      setState(prev => ({ ...prev, configuracion }));
    } catch (error) {
      console.error('Error cargando configuración:', error);
    }
  }, []);

  // Cargar estadísticas
  const cargarEstadisticas = useCallback(async () => {
    try {
      const estadisticas = await api.getEstadisticas();
      setState(prev => ({ ...prev, estadisticas }));
    } catch (error) {
      console.error('Error cargando estadísticas:', error);
    }
  }, []);

  // Establecer hospital actual - SOLUCIÓN PRINCIPAL
  const setHospitalActual = useCallback((hospital: Hospital | null) => {
    // Actualizar ref inmediatamente
    hospitalActualRef.current = hospital;
    
    if (hospital) {
      // Actualizar estado con hospital, loading y limpiar datos anteriores en UNA SOLA operación
      setState(prev => ({ 
        ...prev, 
        hospitalActual: hospital,
        loading: true,
        camas: [],
        listaEspera: [],
        derivados: []
      }));
      
      // Cargar todos los datos del hospital en paralelo
      Promise.all([
        api.getCamasHospital(hospital.id),
        api.getListaEspera(hospital.id),
        api.getDerivados(hospital.id)
      ]).then(([camas, listaEspera, derivados]) => {
        setState(prev => ({
          ...prev,
          camas,
          listaEspera,
          derivados,
          loading: false
        }));
      }).catch(error => {
        console.error('Error cargando datos del hospital:', error);
        setState(prev => ({
          ...prev,
          loading: false,
          error: error instanceof Error ? error.message : 'Error cargando datos del hospital'
        }));
      });
    } else {
      // Limpiar todo cuando no hay hospital
      setState(prev => ({ 
        ...prev, 
        hospitalActual: null,
        camas: [],
        listaEspera: [],
        derivados: [],
        loading: false
      }));
    }
  }, []);

  // Refrescar todos los datos
  const refrescarDatos = useCallback(async () => {
    await cargarHospitales();
    await cargarConfiguracion();
    await cargarEstadisticas();
    const currentHospital = hospitalActualRef.current;
    if (currentHospital) {
      await Promise.all([
        cargarCamas(currentHospital.id),
        cargarListaEspera(currentHospital.id),
        cargarDerivados(currentHospital.id)
      ]);
    }
  }, [cargarHospitales, cargarConfiguracion, cargarEstadisticas, cargarCamas, cargarListaEspera, cargarDerivados]);

  // Manejo de errores
  const setError = useCallback((error: string | null) => {
    setState(prev => ({ ...prev, error }));
  }, []);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  // Cargar datos iniciales
  useEffect(() => {
    cargarHospitales();
    cargarConfiguracion();
    cargarEstadisticas();
  }, [cargarHospitales, cargarConfiguracion, cargarEstadisticas]);

  const value: AppContextValue = {
    ...state,
    setHospitalActual,
    cargarHospitales,
    cargarCamas,
    cargarListaEspera,
    cargarDerivados,
    cargarConfiguracion,
    cargarEstadisticas,
    refrescarDatos,
    setError,
    clearError
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppContextValue {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp debe usarse dentro de AppProvider');
  }
  return context;
}