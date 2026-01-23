import React, { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { toast } from 'sonner';
import { playSound, DEFAULT_NOTIFICATION_SOUNDS } from '../services/notificationSounds';
import api from '../lib/api';

const WebSocketContext = createContext();

// Connection state enum for better UI feedback
export const ConnectionState = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
  FAILED: 'failed'
};

// Exponential backoff configuration
const INITIAL_RECONNECT_DELAY = 1000;
const MAX_RECONNECT_DELAY = 30000;
const MAX_RECONNECT_ATTEMPTS = 10;

// Heartbeat configuration
const HEARTBEAT_INTERVAL = 25000; // Send ping every 25 seconds
const HEARTBEAT_TIMEOUT = 10000;  // Wait 10 seconds for pong response

// Cache for notification preferences
let cachedPreferences = null;
let preferencesLastFetched = 0;
const PREFERENCES_CACHE_TTL = 60000; // 1 minute

async function getNotificationPreferences() {
  const now = Date.now();
  if (cachedPreferences && (now - preferencesLastFetched) < PREFERENCES_CACHE_TTL) {
    return cachedPreferences;
  }
  try {
    const res = await api.get('/notification-preferences');
    cachedPreferences = res.data;
    preferencesLastFetched = now;
    return cachedPreferences;
  } catch {
    return null;
  }
}

async function playNotificationSound(notificationType) {
  try {
    const prefs = await getNotificationPreferences();
    if (!prefs?.sounds_enabled) return;
    
    const typeToKey = {
      message: 'sound_message',
      new_message: 'sound_message',
      case_update: 'sound_case_update',
      case_status_changed: 'sound_case_update',
      attorney_response: 'sound_attorney_response',
      sos_alert: 'sound_sos_alert',
      warning: 'sound_warning',
      system: 'sound_system',
      notification: 'sound_message'
    };
    
    const soundKey = typeToKey[notificationType] || 'sound_message';
    const soundId = prefs[soundKey] || DEFAULT_NOTIFICATION_SOUNDS[notificationType] || 'default_ping';
    
    if (soundId && soundId !== 'none') {
      const volume = (prefs.sound_volume || 70) / 100;
      playSound(soundId, volume);
    }
  } catch (error) {
    console.error('Error playing notification sound:', error);
  }
}

export function WebSocketProvider({ children }) {
  const { token, user } = useAuth();
  const [connectionState, setConnectionState] = useState(ConnectionState.DISCONNECTED);
  const [notifications, setNotifications] = useState([]);
  const [lastMessage, setLastMessage] = useState(null);
  const [connectionQuality, setConnectionQuality] = useState('good'); // good, degraded, poor
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY);
  const connectRef = useRef(null);
  const heartbeatIntervalRef = useRef(null);
  const heartbeatTimeoutRef = useRef(null);
  const lastPongRef = useRef(Date.now());
  const missedPongsRef = useRef(0);

  // Derived state for backward compatibility
  const isConnected = connectionState === ConnectionState.CONNECTED;

  const resetReconnectState = useCallback(() => {
    reconnectAttemptRef.current = 0;
    reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;
    missedPongsRef.current = 0;
    setConnectionQuality('good');
  }, []);

  // Clear all timeouts and intervals
  const clearTimers = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }
  }, []);

  // Start heartbeat mechanism
  const startHeartbeat = useCallback(() => {
    // Clear existing heartbeat
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
    }
    
    heartbeatIntervalRef.current = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        // Send ping
        try {
          wsRef.current.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
          
          // Set timeout for pong response
          heartbeatTimeoutRef.current = setTimeout(() => {
            missedPongsRef.current += 1;
            
            // Update connection quality based on missed pongs
            if (missedPongsRef.current >= 3) {
              setConnectionQuality('poor');
              // Force reconnect if too many missed pongs
              console.warn('Too many missed heartbeats, forcing reconnect...');
              if (wsRef.current) {
                wsRef.current.close(4000, 'Heartbeat timeout');
              }
            } else if (missedPongsRef.current >= 1) {
              setConnectionQuality('degraded');
            }
          }, HEARTBEAT_TIMEOUT);
        } catch (error) {
          console.error('Error sending heartbeat:', error);
        }
      }
    }, HEARTBEAT_INTERVAL);
  }, []);

  // Handle pong response
  const handlePong = useCallback(() => {
    lastPongRef.current = Date.now();
    missedPongsRef.current = 0;
    setConnectionQuality('good');
    
    // Clear the timeout waiting for pong
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }
  }, []);

  // Handle incoming WebSocket messages
  const handleMessage = useCallback((data) => {
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
        playNotificationSound('notification');
        setNotifications(prev => [...prev, data]);
        break;
      case 'new_message':
        toast.info(`New message from ${data.sender_name}`, {
          description: data.content_preview
        });
        playNotificationSound('new_message');
        setNotifications(prev => [...prev, data]);
        break;
      case 'case_status_changed':
        toast.info('Case status updated', {
          description: `Status changed to ${data.new_status}`
        });
        playNotificationSound('case_status_changed');
        break;
      case 'evidence_added':
        toast.success('Evidence uploaded', {
          description: `${data.file_name} added to case`
        });
        playNotificationSound('case_update');
        break;
      case 'sos_alert':
        toast.error('SOS Alert!', {
          description: `Emergency alert from ${data.user_name}`,
          duration: 10000
        });
        playNotificationSound('sos_alert');
        break;
      case 'guidance_message':
        toast.info(`💬 Guidance from ${data.sender_name}`, {
          description: data.message,
          duration: 15000
        });
        playNotificationSound('message');
        setNotifications(prev => [...prev, { ...data, type: 'guidance_message' }]);
        break;
      case 'viewer_joined':
        toast.success(`👁️ Someone is watching your encounter`, {
          description: `${data.viewer_count} viewer(s) connected`
        });
        playNotificationSound('system');
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
        playNotificationSound('sos_alert');
        break;
      case 'typing':
        break;
      case 'pong':
        handlePong();
        break;
      default:
        console.log('Unknown message type:', data.type);
    }
  }, [handlePong]);

  const connect = useCallback(() => {
    if (!token || !user) return;

    // Prevent multiple connections
    if (wsRef.current && (wsRef.current.readyState === WebSocket.CONNECTING || wsRef.current.readyState === WebSocket.OPEN)) {
      return;
    }

    setConnectionState(reconnectAttemptRef.current > 0 ? ConnectionState.RECONNECTING : ConnectionState.CONNECTING);

    const wsUrl = process.env.REACT_APP_BACKEND_URL
      .replace('https://', 'wss://')
      .replace('http://', 'ws://');
    
    try {
      wsRef.current = new WebSocket(`${wsUrl}/api/ws/${token}`);

      wsRef.current.onopen = () => {
        setConnectionState(ConnectionState.CONNECTED);
        resetReconnectState();
        startHeartbeat();
        console.log('WebSocket connected');
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      wsRef.current.onclose = (event) => {
        setConnectionState(ConnectionState.DISCONNECTED);
        clearTimers();
        console.log('WebSocket disconnected', event.code, event.reason);
        
        // Don't reconnect if explicitly closed (1000) or auth failed (4001)
        if (event.code === 1000 || event.code === 4001) {
          return;
        }
        
        // Check if max attempts reached
        if (reconnectAttemptRef.current >= MAX_RECONNECT_ATTEMPTS) {
          console.warn('Max WebSocket reconnect attempts reached');
          setConnectionState(ConnectionState.FAILED);
          toast.error('Connection lost. Please refresh the page.', {
            duration: 10000,
            action: {
              label: 'Refresh',
              onClick: () => window.location.reload()
            }
          });
          return;
        }

        // Exponential backoff reconnection
        reconnectAttemptRef.current += 1;
        const delay = Math.min(
          reconnectDelayRef.current * Math.pow(2, reconnectAttemptRef.current - 1),
          MAX_RECONNECT_DELAY
        );
        
        setConnectionState(ConnectionState.RECONNECTING);
        console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptRef.current}/${MAX_RECONNECT_ATTEMPTS})`);
        reconnectTimeoutRef.current = setTimeout(connectRef.current, delay);
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('WebSocket connection error:', error);
      setConnectionState(ConnectionState.FAILED);
    }
  }, [token, user, resetReconnectState, handleMessage, startHeartbeat, clearTimers]);

  // Keep connect ref updated in effect
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const sendMessage = useCallback((data) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
      return true;
    }
    return false;
  }, []);

  const sendTyping = useCallback((recipientId, conversationId) => {
    sendMessage({
      type: 'typing',
      recipient_id: recipientId,
      conversation_id: conversationId
    });
  }, [sendMessage]);

  // Manual reconnect function for UI
  const reconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    clearTimers();
    resetReconnectState();
    setTimeout(() => connect(), 100);
  }, [connect, clearTimers, resetReconnectState]);

  // Handle visibility change - reconnect when tab becomes visible
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && connectionState !== ConnectionState.CONNECTED) {
        console.log('Tab became visible, checking connection...');
        // Check if we should reconnect
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          reconnectAttemptRef.current = 0; // Reset attempts on visibility change
          connect();
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [connect, connectionState]);

  // Handle online/offline events
  useEffect(() => {
    const handleOnline = () => {
      console.log('Network online, reconnecting...');
      if (connectionState !== ConnectionState.CONNECTED) {
        reconnectAttemptRef.current = 0;
        connect();
      }
    };

    const handleOffline = () => {
      console.log('Network offline');
      setConnectionState(ConnectionState.DISCONNECTED);
      setConnectionQuality('poor');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [connect, connectionState]);

  useEffect(() => {
    connect();
    return () => {
      clearTimers();
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting');
      }
    };
  }, [connect, clearTimers]);

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
