import { useEffect, useRef, useState, useCallback } from 'react';
import type { WebSocketEvent } from '../types/Index';
import { getWebSocketUrl } from '../services/api';

interface UseWebSocketOptions {
  onMessage?: (event: WebSocketEvent) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export function useWebSocket({
  onMessage,
  onConnect,
  onDisconnect,
  reconnectInterval = 3000,
  maxReconnectAttempts = 10
}: UseWebSocketOptions = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    sendMessage,
    reconnect: connect
  };
}
