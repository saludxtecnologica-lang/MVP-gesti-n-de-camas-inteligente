import { useEffect, useRef, useState, useCallback } from 'react';
import type { WebSocketEvent } from '../types/Index';
import { getWebSocketUrl } from '../services/api';

// URL del archivo de sonido de notificación
// Puedes usar un sonido desde la carpeta public o una URL externa
const NOTIFICATION_SOUND_URL = '/notification.mp3';

interface UseWebSocketOptions {
  onMessage?: (event: WebSocketEvent) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  enableSound?: boolean; // Opción para habilitar/deshabilitar sonidos
}

// Cache del audio para evitar recrearlo en cada notificación
let notificationAudio: HTMLAudioElement | null = null;
let audioLoadFailed = false;

/**
 * Reproduce un sonido usando la Web Audio API como fallback
 * Esto funciona incluso sin un archivo de audio externo
 */
function playBeepSound(): void {
  try {
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    // Configurar el tono - sonido más agradable para notificación
    oscillator.frequency.value = 880; // La nota A5
    oscillator.type = 'sine';
    
    // Configurar el volumen y fade out
    gainNode.gain.setValueAtTime(0.4, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.4);
    
    // Reproducir
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.4);
    
    // Segundo tono (armonía)
    setTimeout(() => {
      try {
        const osc2 = audioContext.createOscillator();
        const gain2 = audioContext.createGain();
        osc2.connect(gain2);
        gain2.connect(audioContext.destination);
        osc2.frequency.value = 1320; // E6
        osc2.type = 'sine';
        gain2.gain.setValueAtTime(0.3, audioContext.currentTime);
        gain2.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
        osc2.start(audioContext.currentTime);
        osc2.stop(audioContext.currentTime + 0.3);
      } catch (e) {
        // Ignorar error del segundo tono
      }
    }, 150);
    
    // Limpiar después de reproducir
    setTimeout(() => {
      try {
        oscillator.disconnect();
        gainNode.disconnect();
      } catch (e) {
        // Ignorar errores de limpieza
      }
    }, 600);
  } catch (error) {
    console.warn('No se pudo reproducir el sonido beep:', error);
  }
}

/**
 * Reproduce un sonido de notificación
 * CORRECCIÓN Problema 11: Soporte para notificaciones con audio con fallback mejorado
 */
function playNotificationSound(): void {
  // Si ya sabemos que el archivo de audio falló, usar beep directamente
  if (audioLoadFailed) {
    playBeepSound();
    return;
  }
  
  try {
    // Crear el audio solo una vez
    if (!notificationAudio) {
      notificationAudio = new Audio(NOTIFICATION_SOUND_URL);
      notificationAudio.volume = 0.5; // Volumen al 50%
      
      // Manejar errores de carga
      notificationAudio.onerror = () => {
        console.warn('No se pudo cargar el archivo de sonido, usando beep');
        audioLoadFailed = true;
        playBeepSound();
      };
    }
    
    // Reiniciar y reproducir
    notificationAudio.currentTime = 0;
    notificationAudio.play()
      .then(() => {
        console.log('🔊 Sonido de notificación reproducido');
      })
      .catch(err => {
        // El navegador puede bloquear la reproducción automática
        // hasta que el usuario interactúe con la página
        console.warn('No se pudo reproducir el sonido de notificación, intentando beep:', err);
        playBeepSound();
      });
  } catch (error) {
    console.error('Error al reproducir sonido de notificación, usando beep:', error);
    playBeepSound();
  }
}

export function useWebSocket({
  onMessage,
  onConnect,
  onDisconnect,
  reconnectInterval = 3000,
  maxReconnectAttempts = 10,
  enableSound = true
}: UseWebSocketOptions = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const enableSoundRef = useRef(enableSound);

  // Mantener la referencia actualizada
  useEffect(() => {
    enableSoundRef.current = enableSound;
  }, [enableSound]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const ws = new WebSocket(getWebSocketUrl());
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket conectado');
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        onConnect?.();
      };

      ws.onclose = () => {
        console.log('WebSocket desconectado');
        setIsConnected(false);
        onDisconnect?.();

        // Intentar reconectar
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(`Intentando reconectar (${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`);
          reconnectTimeoutRef.current = setTimeout(connect, reconnectInterval);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketEvent;
          
          // CORRECCIÓN Problema 11: Reproducir sonido si play_sound es true
          if (enableSoundRef.current && data.play_sound === true) {
            console.log('🔔 Evento de notificación con sonido recibido:', data.tipo);
            playNotificationSound();
          }
          
          onMessage?.(data);
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };
    } catch (err) {
      console.error('Error connecting WebSocket:', err);
    }
  }, [onConnect, onDisconnect, onMessage, reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    reconnectAttemptsRef.current = maxReconnectAttempts; // Prevent reconnection
    wsRef.current?.close();
    wsRef.current = null;
  }, [maxReconnectAttempts]);

  const sendMessage = useCallback((message: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  // Función para probar el sonido manualmente
  const testSound = useCallback(() => {
    playNotificationSound();
  }, []);

  // Función para reproducir beep (útil como fallback)
  const playBeep = useCallback(() => {
    playBeepSound();
  }, []);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    sendMessage,
    reconnect: connect,
    testSound,
    playBeep
  };
}
