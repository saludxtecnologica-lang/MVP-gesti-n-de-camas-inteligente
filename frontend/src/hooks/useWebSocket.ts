/**
 * Hook de WebSocket para actualizaciones en tiempo real
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { tokenStorage } from '../services/authApi';

// ============================================
// TIPOS
// ============================================

export interface WebSocketEvent {
  tipo: string;
  datos?: Record<string, unknown>;
  timestamp?: string;
  hospital_id?: string;
  play_sound?: boolean;
  [key: string]: unknown;
}

export interface UseWebSocketOptions {
  onMessage?: (event: WebSocketEvent) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  enableSound?: boolean;
  hospitalId?: string;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  lastMessage: WebSocketEvent | null;
  sendMessage: (message: unknown) => void;
  reconnect: () => void;
  disconnect: () => void;
  testSound: () => void;
}

// ============================================
// SONIDO DE NOTIFICACIÓN
// ============================================

const NOTIFICATION_SOUND_URL = '/notification.mp3';
let notificationAudio: HTMLAudioElement | null = null;
let audioLoadFailed = false;

function playBeepSound(): void {
  try {
    const AudioContextClass = window.AudioContext || 
      (window as unknown as { webkitAudioContext: typeof window.AudioContext }).webkitAudioContext;
    const audioContext = new AudioContextClass();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    oscillator.frequency.value = 880;
    oscillator.type = 'sine';
    gainNode.gain.setValueAtTime(0.4, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.4);
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.4);
    
    setTimeout(() => {
      try {
        const osc2 = audioContext.createOscillator();
        const gain2 = audioContext.createGain();
        osc2.connect(gain2);
        gain2.connect(audioContext.destination);
        osc2.frequency.value = 1320;
        osc2.type = 'sine';
        gain2.gain.setValueAtTime(0.3, audioContext.currentTime);
        gain2.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
        osc2.start(audioContext.currentTime);
        osc2.stop(audioContext.currentTime + 0.3);
      } catch {
        // Ignorar error del segundo tono
      }
    }, 150);
  } catch (error) {
    console.warn('No se pudo reproducir el sonido beep:', error);
  }
}

function playNotificationSound(): void {
  if (audioLoadFailed) {
    playBeepSound();
    return;
  }
  
  try {
    if (!notificationAudio) {
      notificationAudio = new Audio(NOTIFICATION_SOUND_URL);
      notificationAudio.volume = 0.5;
      notificationAudio.onerror = () => {
        audioLoadFailed = true;
        playBeepSound();
      };
    }
    
    notificationAudio.currentTime = 0;
    notificationAudio.play().catch(() => playBeepSound());
  } catch {
    playBeepSound();
  }
}

// ============================================
// HELPER PARA URL
// ============================================

function getWebSocketUrl(hospitalId?: string): string {
  const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const wsProtocol = baseUrl.startsWith('https') ? 'wss' : 'ws';
  const wsBaseUrl = baseUrl.replace(/^https?/, wsProtocol);
  
  let url = `${wsBaseUrl}/api/ws`;
  
  // Añadir token como query param si existe
  const token = tokenStorage.getAccessToken();
  const params = new URLSearchParams();
  
  if (token) {
    params.append('token', token);
  }
  
  if (hospitalId) {
    params.append('hospital_id', hospitalId);
  }
  
  const queryString = params.toString();
  if (queryString) {
    url += `?${queryString}`;
  }
  
  return url;
}

// ============================================
// HOOK PRINCIPAL
// ============================================

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    onMessage,
    onConnect,
    onDisconnect,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
    enableSound = true,
    hospitalId,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketEvent | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  // Refs para callbacks para evitar re-conexiones innecesarias
  const onMessageRef = useRef(onMessage);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);
  const enableSoundRef = useRef(enableSound);

  // Actualizar refs cuando cambien los callbacks
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);
  
  useEffect(() => {
    onConnectRef.current = onConnect;
  }, [onConnect]);
  
  useEffect(() => {
    onDisconnectRef.current = onDisconnect;
  }, [onDisconnect]);

  useEffect(() => {
    enableSoundRef.current = enableSound;
  }, [enableSound]);

  // Función de conexión
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('[WS] Ya conectado, ignorando');
      return;
    }

    try {
      const wsUrl = getWebSocketUrl(hospitalId);
      console.log('[WS] Conectando a:', wsUrl);
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WS] Conexión establecida');
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        onConnectRef.current?.();
      };

      ws.onclose = (event) => {
        console.log('[WS] Conexión cerrada:', event.code, event.reason);
        setIsConnected(false);
        onDisconnectRef.current?.();

        // Reintentar conexión
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(`[WS] Reintentando conexión (${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
          reconnectTimeoutRef.current = setTimeout(connect, reconnectInterval);
        } else {
          console.log('[WS] Máximo de reintentos alcanzado');
        }
      };

      ws.onerror = (error) => {
        console.error('[WS] Error:', error);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketEvent;
          console.log('[WS] Mensaje recibido:', data.tipo);
          
          setLastMessage(data);
          
          // Reproducir sonido si está habilitado y el mensaje lo requiere
          if (enableSoundRef.current && data.play_sound === true) {
            playNotificationSound();
          }
          
          onMessageRef.current?.(data);
        } catch (err) {
          console.error('[WS] Error parsing mensaje:', err);
        }
      };
    } catch (err) {
      console.error('[WS] Error conectando:', err);
    }
  }, [hospitalId, reconnectInterval, maxReconnectAttempts]);

  // Función de desconexión
  const disconnect = useCallback(() => {
    console.log('[WS] Desconectando...');
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    // Evitar reconexión automática
    reconnectAttemptsRef.current = maxReconnectAttempts;
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
  }, [maxReconnectAttempts]);

  // Función de reconexión manual
  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    disconnect();
    setTimeout(connect, 100);
  }, [connect, disconnect]);

  // Función para enviar mensajes
  const sendMessage = useCallback((message: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('[WS] No conectado, mensaje no enviado');
    }
  }, []);

  // Función para probar sonido
  const testSound = useCallback(() => {
    playNotificationSound();
  }, []);

  // Conectar al montar, desconectar al desmontar
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  // Escuchar evento de logout para desconectar
  useEffect(() => {
    const handleLogout = () => {
      disconnect();
    };

    window.addEventListener('auth:logout', handleLogout);
    return () => window.removeEventListener('auth:logout', handleLogout);
  }, [disconnect]);

  return {
    isConnected,
    lastMessage,
    sendMessage,
    reconnect,
    disconnect,
    testSound,
  };
}

// ============================================
// EXPORT
// ============================================

export default useWebSocket;