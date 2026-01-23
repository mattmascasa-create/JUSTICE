import React, { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { toast } from 'sonner';

const WebSocketContext = createContext();

// Exponential backoff configuration
const INITIAL_RECONNECT_DELAY = 1000;
const MAX_RECONNECT_DELAY = 30000;
const MAX_RECONNECT_ATTEMPTS = 10;

export function WebSocketProvider({ children }) {
  const { token, user } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [lastMessage, setLastMessage] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY);

  const resetReconnectState = useCallback(() => {
    reconnectAttemptRef.current = 0;
    reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;
  }, []);

  const connect = useCallback(() => {
    if (!token || !user) return;

    // Prevent multiple connections
    if (wsRef.current && wsRef.current.readyState === WebSocket.CONNECTING) {
      return;
    }

    const wsUrl = process.env.REACT_APP_BACKEND_URL
      .replace('https://', 'wss://')
      .replace('http://', 'ws://');
    
    try {
      wsRef.current = new WebSocket(`${wsUrl}/api/ws/${token}`);

      wsRef.current.onopen = () => {
        setIsConnected(true);
        resetReconnectState();
        console.log('WebSocket connected');
      };

      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
      };

      wsRef.current.onclose = (event) => {
        setIsConnected(false);
        console.log('WebSocket disconnected', event.code, event.reason);
        
        // Don't reconnect if explicitly closed or max attempts reached
        if (event.code === 1000 || reconnectAttemptRef.current >= MAX_RECONNECT_ATTEMPTS) {
          if (reconnectAttemptRef.current >= MAX_RECONNECT_ATTEMPTS) {
            console.warn('Max WebSocket reconnect attempts reached');
            toast.error('Connection lost. Please refresh the page.');
          }
          return;
        }

        // Exponential backoff reconnection
        reconnectAttemptRef.current += 1;
        const delay = Math.min(
          reconnectDelayRef.current * Math.pow(2, reconnectAttemptRef.current - 1),
          MAX_RECONNECT_DELAY
        );
        
        console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptRef.current}/${MAX_RECONNECT_ATTEMPTS})`);
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('WebSocket connection error:', error);
    }
  }, [token, user, resetReconnectState]);

  const handleMessage = (data) => {
    // Store last message for components to react to
    setLastMessage(data);
    
    switch (data.type) {
      case 'connected':
        console.log('WebSocket authenticated');
        break;
      case 'notification':
        // Real-time notification from server
        toast.info(data.data?.title || 'New notification', {
          description: data.data?.message
        });
        setNotifications(prev => [...prev, data]);
        break;
      case 'new_message':
        toast.info(`New message from ${data.sender_name}`, {
          description: data.content_preview
        });
        setNotifications(prev => [...prev, data]);
        break;
      case 'case_status_changed':
        toast.info('Case status updated', {
          description: `Status changed to ${data.new_status}`
        });
        break;
      case 'evidence_added':
        toast.success('Evidence uploaded', {
          description: `${data.file_name} added to case`
        });
        break;
      case 'sos_alert':
        toast.error('SOS Alert!', {
          description: `Emergency alert from ${data.user_name}`,
          duration: 10000
        });
        break;
      case 'guidance_message':
        // Real-time guidance from viewers
        toast.info(`💬 Guidance from ${data.sender_name}`, {
          description: data.message,
          duration: 15000
        });
        setNotifications(prev => [...prev, { ...data, type: 'guidance_message' }]);
        break;
      case 'viewer_joined':
        toast.success(`👁️ Someone is watching your encounter`, {
          description: `${data.viewer_count} viewer(s) connected`
        });
        setNotifications(prev => [...prev, { ...data, type: 'viewer_joined' }]);
        break;
      case 'viewer_left':
        setNotifications(prev => [...prev, { ...data, type: 'viewer_left' }]);
        break;
      case 'encounter_share':
        toast.warning(`🚨 ${data.user_name} is in a police encounter!`, {
          description: data.message,
          duration: 30000,
          action: {
            label: 'Watch',
            onClick: () => window.open(data.share_url, '_blank')
          }
        });
        break;
      case 'typing':
        // Handle typing indicator
        break;
      default:
        console.log('Unknown message type:', data.type);
    }
  };

  const sendMessage = useCallback((data) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const sendTyping = useCallback((recipientId, conversationId) => {
    sendMessage({
      type: 'typing',
      recipient_id: recipientId,
      conversation_id: conversationId
    });
  }, [sendMessage]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  const value = {
    isConnected,
    notifications,
    lastMessage,
    sendMessage,
    sendTyping,
    clearNotifications: () => setNotifications([])
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
}
