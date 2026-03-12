import { useEffect, useRef, useCallback, useState } from 'react';

/** Shape of a WebSocket event message from the backend. */
export interface WSMessage {
  type: string;
  payload: Record<string, unknown>;
}

interface UseWebSocketOptions {
  /** Whether to automatically connect. Defaults to true. */
  autoConnect?: boolean;
  /** Reconnection delay in milliseconds. Defaults to 3000. */
  reconnectDelay?: number;
  /** Maximum reconnection attempts. Defaults to 10. */
  maxRetries?: number;
}

interface UseWebSocketReturn {
  connected: boolean;
  lastMessage: WSMessage | null;
  send: (message: WSMessage) => void;
  connect: () => void;
  disconnect: () => void;
}

/**
 * Hook that manages a WebSocket connection to the backend.
 * Automatically reconnects on disconnect with exponential backoff.
 */
export function useWebSocket(
  url = '/ws',
  options: UseWebSocketOptions = {},
): UseWebSocketReturn {
  const { autoConnect = true, reconnectDelay = 3000, maxRetries = 10 } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const disconnect = useCallback(() => {
    clearReconnectTimer();
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }
    setConnected(false);
  }, [clearReconnectTimer]);

  const connect = useCallback(() => {
    disconnect();

    const envWsUrl = import.meta.env.VITE_WS_URL as string | undefined;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = envWsUrl
      ? envWsUrl
      : url.startsWith('ws')
        ? url
        : `${protocol}//${window.location.host}${url}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      retriesRef.current = 0;
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const parsed = JSON.parse(String(event.data)) as WSMessage;
        setLastMessage(parsed);
      } catch {
        // Ignore non-JSON messages
      }
    };

    ws.onclose = (event) => {
      setConnected(false);
      if (event.code !== 1000 && retriesRef.current < maxRetries) {
        const delay = reconnectDelay * Math.pow(2, retriesRef.current);
        retriesRef.current += 1;
        reconnectTimerRef.current = setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [url, reconnectDelay, maxRetries, disconnect]);

  const send = useCallback((message: WSMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return { connected, lastMessage, send, connect, disconnect };
}
