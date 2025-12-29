import { useEffect, useRef, useState, useCallback } from 'react';
import type { WebSocketEvent } from '../types';
import { getWebSocketUrl } from '../services/api';

const NOTIFICATION_SOUND_URL = '/notification.mp3';

let notificationAudio: HTMLAudioElement | null = null;
let audioLoadFailed = false;

function playBeepSound(): void {
  try {
    const AudioContext = window.AudioContext || (window as unknown as { webkitAudioContext: typeof window.AudioContext }).webkitAudioContext;
    const audioContext = new AudioContext();
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

interface UseWebSocketOptions {
  onMessage?: (event: WebSocketEvent) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  enableSound?: boolean;
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
  
  // Refs para los callbacks para evitar re-conexiones
  const onMessageRef = useRef(onMessage);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);

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

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('[WS] Ya conectado, ignorando');
      return;
    }

    try {
      const wsUrl = getWebSocketUrl();
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
  }, [reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    console.log('[WS] Desconectando...');
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    reconnectAttemptsRef.current = maxReconnectAttempts; // Evitar reconexión
    wsRef.current?.close();
    wsRef.current = null;
  }, [maxReconnectAttempts]);

  const sendMessage = useCallback((message: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  const testSound = useCallback(() => {
    playNotificationSound();
  }, []);

  // Conectar al montar, desconectar al desmontar
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    isConnected,
    sendMessage,
    reconnect: connect,
    testSound
  };
}