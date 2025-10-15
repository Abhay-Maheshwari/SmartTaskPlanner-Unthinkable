/**
 * useWebSocket.ts - Custom React Hook for WebSocket Connection
 * 
 * This hook manages WebSocket connections and provides real-time progress updates
 * during task plan generation. It handles connection lifecycle, message parsing,
 * and provides a clean interface for components to use.
 * 
 * FEATURES:
 * - Automatic connection management
 * - Real-time progress updates
 * - Error handling and reconnection
 * - Session-based communication
 * - TypeScript support
 * 
 * USAGE:
 * const { connect, disconnect, progress, message, isConnected } = useWebSocket();
 * 
 * Author: Junior Developer Learning Squad
 * Date: 2025-10-11
 */

import { useState, useEffect, useCallback, useRef } from 'react';

// WebSocket message types from backend
export interface WebSocketMessage {
  type: 'connection_established' | 'generation_progress' | 'generation_complete' | 'error' | 'pong';
  session_id?: string;
  progress?: number;
  message?: string;
  status?: 'processing' | 'completed' | 'error';
  success?: boolean;
  plan_id?: string;
  error?: string;
  timestamp: string;
}

export interface WebSocketProgress {
  progress: number;
  message: string;
  status: 'processing' | 'completed' | 'error';
}

export interface UseWebSocketReturn {
  // Connection state
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  
  // Progress data
  progress: WebSocketProgress | null;
  
  // Connection methods
  connect: (sessionId: string) => void;
  disconnect: () => void;
  sendMessage: (message: any) => void;
  
  // Current session info
  sessionId: string | null;
}

export const useWebSocket = (): UseWebSocketReturn => {
  // WebSocket connection state
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  
  // Progress state
  const [progress, setProgress] = useState<WebSocketProgress | null>(null);
  
  // WebSocket reference
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Generate a unique session ID
   */
  const generateSessionId = useCallback((): string => {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  /**
   * Handle incoming WebSocket messages
   */
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data: WebSocketMessage = JSON.parse(event.data);
      
      switch (data.type) {
        case 'connection_established':
          console.log('🔗 WebSocket connected:', data.message);
          setError(null);
          break;
          
        case 'generation_progress':
          console.log(`📊 Progress: ${data.progress}% - ${data.message}`);
          setProgress({
            progress: data.progress || 0,
            message: data.message || 'Processing...',
            status: data.status || 'processing'
          });
          break;
          
        case 'generation_complete':
          console.log('✅ Generation complete:', data.success ? 'Success' : 'Failed');
          if (data.success) {
            setProgress({
              progress: 100,
              message: data.message || 'Task plan generated successfully!',
              status: 'completed'
            });
          } else {
            setProgress({
              progress: 0,
              message: data.error || 'Generation failed',
              status: 'error'
            });
          }
          break;
          
        case 'error':
          console.error('❌ WebSocket error:', data.message);
          setError(data.message || 'WebSocket error occurred');
          break;
          
        case 'pong':
          // Server responded to ping - connection is alive
          break;
          
        default:
          console.log('📨 Unknown message type:', data.type);
      }
    } catch (err) {
      console.error('❌ Failed to parse WebSocket message:', err);
      setError('Failed to parse server message');
    }
  }, []);

  /**
   * Handle WebSocket connection open
   */
  const handleOpen = useCallback(() => {
    console.log('🔌 WebSocket connection opened');
    setIsConnected(true);
    setIsConnecting(false);
    setError(null);
    
    // Start ping interval to keep connection alive
    pingIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // Ping every 30 seconds
  }, []);

  /**
   * Handle WebSocket connection close
   */
  const handleClose = useCallback((event: CloseEvent) => {
    console.log('🔌 WebSocket connection closed:', event.code, event.reason);
    setIsConnected(false);
    setIsConnecting(false);
    
    // Clear ping interval
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    
    // Clear reconnect timeout if it exists
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    // Don't attempt reconnection for normal closures or if we're disconnecting intentionally
    if (event.code !== 1000 && event.code !== 1001) {
      console.log('🔄 Attempting to reconnect in 3 seconds...');
      reconnectTimeoutRef.current = setTimeout(() => {
        if (sessionId && !isConnected) {
          connect(sessionId);
        }
      }, 3000);
    }
  }, [sessionId, isConnected]);

  /**
   * Handle WebSocket errors
   */
  const handleError = useCallback((event: Event) => {
    console.error('❌ WebSocket error:', event);
    setError('WebSocket connection error');
    setIsConnecting(false);
  }, []);

  /**
   * Connect to WebSocket server
   */
  const connect = useCallback((newSessionId?: string) => {
    // Don't connect if already connected or connecting
    if (isConnected || isConnecting) {
      return;
    }
    
    // Use provided session ID or generate new one
    const currentSessionId = newSessionId || generateSessionId();
    setSessionId(currentSessionId);
    setIsConnecting(true);
    setError(null);
    
    try {
      // Create WebSocket connection
      const wsUrl = `ws://localhost:8000/ws/${currentSessionId}`;
      console.log('🔌 Connecting to WebSocket:', wsUrl);
      
      wsRef.current = new WebSocket(wsUrl);
      
      // Set up event handlers
      wsRef.current.onopen = handleOpen;
      wsRef.current.onmessage = handleMessage;
      wsRef.current.onclose = handleClose;
      wsRef.current.onerror = handleError;
      
    } catch (err) {
      console.error('❌ Failed to create WebSocket:', err);
      setError('Failed to create WebSocket connection');
      setIsConnecting(false);
    }
  }, [isConnected, isConnecting, generateSessionId, handleOpen, handleMessage, handleClose, handleError]);

  /**
   * Disconnect from WebSocket server
   */
  const disconnect = useCallback(() => {
    console.log('🔌 Disconnecting WebSocket...');
    
    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    // Clear ping interval
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    
    // Close WebSocket connection
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnecting'); // Normal closure
      wsRef.current = null;
    }
    
    setIsConnected(false);
    setIsConnecting(false);
    setSessionId(null);
    setProgress(null);
    setError(null);
  }, []);

  /**
   * Send message through WebSocket
   */
  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('⚠️ Cannot send message: WebSocket not connected');
    }
  }, []);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    // Connection state
    isConnected,
    isConnecting,
    error,
    
    // Progress data
    progress,
    
    // Connection methods
    connect,
    disconnect,
    sendMessage,
    
    // Current session info
    sessionId,
  };
};

