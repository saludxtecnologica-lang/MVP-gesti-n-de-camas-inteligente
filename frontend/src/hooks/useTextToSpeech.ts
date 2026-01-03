/**
 * Hook useTextToSpeech para integrar TTS con React
 * 
 * Este hook maneja la lógica de Text-to-Speech para las notificaciones
 * del sistema de gestión de camas, incluyendo el filtrado por servicio.
 * 
 * Recibe servicioSeleccionadoId externamente (del AppContext)
 */

import { useCallback, useRef, useEffect, useState } from 'react';
import { 
  ttsService, 
  generarMensajeAsignacion,
  generarMensajeTrasladoCompletado,
  generarMensajeDerivacionAceptada
} from '../services/ttsService';
import type { WebSocketEvent } from '../types';

// ============================================
// TIPOS
// ============================================

export interface UseTextToSpeechOptions {
  /** ID del servicio que se está visualizando (null = vista global) */
  servicioSeleccionadoId: string | null;
  /** Si está habilitado el TTS */
  habilitado?: boolean;
}

export interface UseTextToSpeechReturn {
  /** Procesa un evento de WebSocket para determinar si debe reproducirse */
  procesarEvento: (evento: WebSocketEvent) => void;
  /** Reproduce un mensaje directamente */
  hablar: (mensaje: string) => void;
  /** Cancela cualquier mensaje en reproducción */
  cancelar: () => void;
  /** Habilita/deshabilita el TTS */
  setHabilitado: (habilitado: boolean) => void;
  /** Si el TTS está disponible */
  disponible: boolean;
  /** Si el TTS está habilitado */
  estaHabilitado: boolean;
  /** Prueba el sistema de TTS */
  probar: () => void;
}

// ============================================
// HOOK PRINCIPAL
// ============================================

export function useTextToSpeech(options: UseTextToSpeechOptions): UseTextToSpeechReturn {
  const { 
    servicioSeleccionadoId, 
    habilitado = true 
  } = options;

  // Refs para acceso sin re-renders
  const servicioRef = useRef<string | null>(servicioSeleccionadoId);
  const habilitadoRef = useRef<boolean>(habilitado);
  
  // Estados
  const [disponible, setDisponible] = useState(false);
  const [estaHabilitado, setEstaHabilitado] = useState(habilitado);

  // Mantener refs sincronizados
  useEffect(() => {
    servicioRef.current = servicioSeleccionadoId;
    console.log('[TTS] Servicio seleccionado actualizado:', servicioSeleccionadoId);
  }, [servicioSeleccionadoId]);

  useEffect(() => {
    habilitadoRef.current = habilitado;
    setEstaHabilitado(habilitado);
    ttsService.setHabilitado(habilitado);
  }, [habilitado]);

  // Verificar disponibilidad al montar
  useEffect(() => {
    const checkDisponibilidad = () => {
      const disp = ttsService.estaDisponible();
      setDisponible(disp);
      console.log('[TTS] Disponibilidad:', disp);
    };
    
    // Verificar inmediatamente y después de un delay (para voces)
    checkDisponibilidad();
    const timer = setTimeout(checkDisponibilidad, 1000);
    
    return () => clearTimeout(timer);
  }, []);

  /**
   * Determina si un evento debe reproducirse según el servicio actual
   */
  const debeReproducir = useCallback((evento: WebSocketEvent): boolean => {
    const servicioActual = servicioRef.current;

    // Si no hay servicio seleccionado (vista global), NO reproducir
    if (!servicioActual) {
      console.log('[TTS] Vista global - no se reproduce mensaje');
      return false;
    }

    // Verificar que el evento tenga tts_habilitado
    if (!evento.tts_habilitado) {
      return false;
    }

    switch (evento.tipo) {
      case 'asignacion_completada': {
        // Se reproduce en servicio de origen Y destino
        const esOrigenODestino = 
          evento.servicio_origen_id === servicioActual ||
          evento.servicio_destino_id === servicioActual;
        
        console.log('[TTS] Asignación - servicio actual:', servicioActual, 
          'origen:', evento.servicio_origen_id, 
          'destino:', evento.servicio_destino_id,
          'reproduce:', esOrigenODestino);
        
        return esOrigenODestino;
      }

      case 'traslado_completado': {
        // Solo se reproduce en el servicio de origen
        const esOrigen = evento.servicio_origen_id === servicioActual;
        
        console.log('[TTS] Traslado completado - servicio actual:', servicioActual,
          'origen:', evento.servicio_origen_id,
          'reproduce:', esOrigen);
        
        return esOrigen;
      }

      case 'derivacion_aceptada': {
        // Solo se reproduce en el servicio de origen
        const esOrigen = evento.servicio_origen_id === servicioActual;
        
        console.log('[TTS] Derivación aceptada - servicio actual:', servicioActual,
          'origen:', evento.servicio_origen_id,
          'reproduce:', esOrigen);
        
        return esOrigen;
      }

      default:
        return false;
    }
  }, []);

  /**
   * Genera el mensaje de texto según el tipo de evento
   */
  const generarMensaje = useCallback((evento: WebSocketEvent): string => {
    switch (evento.tipo) {
      case 'asignacion_completada':
        return generarMensajeAsignacion(
          evento.cama_identificador || 'desconocida',
          evento.paciente_nombre || 'paciente',
          evento.servicio_origen_nombre || null,
          evento.cama_origen_identificador || null
        );

      case 'traslado_completado':
        return generarMensajeTrasladoCompletado(
          evento.servicio_destino_nombre || 'destino',
          evento.paciente_nombre || 'paciente',
          evento.cama_origen_identificador || 'origen'
        );

      case 'derivacion_aceptada':
        return generarMensajeDerivacionAceptada(
          evento.paciente_nombre || 'paciente',
          evento.hospital_destino_nombre || 'hospital destino'
        );

      default:
        return '';
    }
  }, []);

  /**
   * Procesa un evento de WebSocket
   */
  const procesarEvento = useCallback((evento: WebSocketEvent) => {
    if (!habilitadoRef.current) {
      console.log('[TTS] No habilitado');
      return;
    }

    if (!debeReproducir(evento)) {
      return;
    }

    const mensaje = generarMensaje(evento);
    
    if (mensaje) {
      console.log('[TTS] Reproduciendo:', mensaje);
      ttsService.hablar(mensaje, 'alta').catch(error => {
        console.error('[TTS] Error al reproducir:', error);
      });
    }
  }, [debeReproducir, generarMensaje]);

  /**
   * Reproduce un mensaje directamente
   */
  const hablar = useCallback((mensaje: string) => {
    if (habilitadoRef.current) {
      ttsService.hablar(mensaje);
    }
  }, []);

  /**
   * Cancela cualquier mensaje
   */
  const cancelar = useCallback(() => {
    ttsService.cancelar();
  }, []);

  /**
   * Cambia el estado de habilitado
   */
  const setHabilitadoHandler = useCallback((valor: boolean) => {
    habilitadoRef.current = valor;
    ttsService.setHabilitado(valor);
    setEstaHabilitado(valor);
  }, []);

  /**
   * Prueba el sistema TTS
   */
  const probar = useCallback(() => {
    ttsService.probar();
  }, []);

  return {
    procesarEvento,
    hablar,
    cancelar,
    setHabilitado: setHabilitadoHandler,
    disponible,
    estaHabilitado,
    probar
  };
}

export default useTextToSpeech;