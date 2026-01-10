import React, { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { toast } from 'sonner';

const WebSocketContext = createContext();

export function WebSocketProvider({ children }) {
  const { token, user } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    if (!token || !user) return;

    const wsUrl = process.env.REACT_APP_BACKEND_URL
      .replace('https://', 'wss://')
      .replace('http://', 'ws://');
    
    try {
      wsRef.current = new WebSocket(`${wsUrl}/api/ws/${token}`);

      wsRef.current.onopen = () => {
        setIsConnected(true);
        console.log('WebSocket connected');
      };

      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
      };

      wsRef.current.onclose = () => {
        setIsConnected(false);
        console.log('WebSocket disconnected');
        // Reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('WebSocket connection error:', error);
    }
  }, [token, user]);

  const handleMessage = (data) => {
    switch (data.type) {
      case 'connected':
        console.log('WebSocket authenticated');
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
