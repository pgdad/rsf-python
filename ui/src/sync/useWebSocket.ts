/**
 * WebSocket connection hook for the RSF graph editor.
 *
 * Manages the WebSocket connection to the FastAPI backend,
 * handles reconnection, and dispatches incoming messages.
 */

import { useEffect, useRef, useCallback } from 'react';
import type { WSMessage, WSResponse } from '../types';

interface UseWebSocketOptions {
  url?: string;
  onMessage: (response: WSResponse) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
}

interface UseWebSocketReturn {
  send: (message: WSMessage) => void;
  isConnected: boolean;
}

export function useWebSocket({
  url,
  onMessage,
  onOpen,
  onClose,
  onError,
}: UseWebSocketOptions): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const isConnectedRef = useRef(false);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const callbacksRef = useRef({ onMessage, onOpen, onClose, onError });

  // Keep callbacks fresh
  callbacksRef.current = { onMessage, onOpen, onClose, onError };

  const wsUrl = url ?? `ws://${window.location.host}/ws`;

  const send = useCallback((message: WSMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  useEffect(() => {
    function connect() {
      if (wsRef.current?.readyState === WebSocket.OPEN) return;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        isConnectedRef.current = true;
        callbacksRef.current.onOpen?.();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WSResponse;
          callbacksRef.current.onMessage(data);
        } catch {
          console.error('Failed to parse WebSocket message:', event.data);
        }
      };

      ws.onclose = () => {
        isConnectedRef.current = false;
        callbacksRef.current.onClose?.();
        reconnectTimeoutRef.current = setTimeout(connect, 2000);
      };

      ws.onerror = (error) => {
        callbacksRef.current.onError?.(error);
      };
    }

    connect();
    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [wsUrl]);

  return {
    send,
    get isConnected() {
      return isConnectedRef.current;
    },
  };
}
