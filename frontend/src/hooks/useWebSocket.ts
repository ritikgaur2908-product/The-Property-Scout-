import { useState, useEffect, useCallback, useRef } from 'react';

type WebSocketStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

interface UseWebSocketOptions {
  url: string;
  onMessage?: (data: any) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnect?: boolean;
}

export const useWebSocket = ({
  url,
  onMessage,
  onOpen,
  onClose,
  onError,
  reconnect = true,
}: UseWebSocketOptions) => {
  const [status, setStatus] = useState<WebSocketStatus>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Store callbacks in refs to avoid reconnecting on inline function reference changes
  const callbacksRef = useRef({ onMessage, onOpen, onClose, onError });
  useEffect(() => {
    callbacksRef.current = { onMessage, onOpen, onClose, onError };
  });

  const connect = useCallback(() => {
    if (!url) {
      return;
    }
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    setStatus('connecting');
    const ws = new WebSocket(url);
    ws.binaryType = 'blob'; // explicitly ensure we get Blobs for audio
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('connected');
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      callbacksRef.current.onOpen?.();
    };

    ws.onmessage = (event) => {
      try {
        if (event.data instanceof Blob) {
          callbacksRef.current.onMessage?.(event.data);
        } else if (event.data instanceof ArrayBuffer) {
          // If browser somehow gives ArrayBuffer, convert to Blob
          callbacksRef.current.onMessage?.(new Blob([event.data]));
        } else {
          const data = JSON.parse(event.data);
          callbacksRef.current.onMessage?.(data);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message', e);
        callbacksRef.current.onMessage?.(event.data);
      }
    };

    ws.onerror = (error) => {
      setStatus('error');
      callbacksRef.current.onError?.(error);
    };

    ws.onclose = () => {
      setStatus('disconnected');
      callbacksRef.current.onClose?.();
      
      if (reconnect) {
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 5000); // 5s delay prevents aggressive reconnect during LLM processing
      }
    };
  }, [url, reconnect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const data = typeof message === 'string' || message instanceof Blob || message instanceof ArrayBuffer
        ? message
        : JSON.stringify(message);
      wsRef.current.send(data);
    } else {
      console.warn('WebSocket is not connected. Message not sent.');
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    status,
    sendMessage,
    disconnect,
    connect,
  };
};
