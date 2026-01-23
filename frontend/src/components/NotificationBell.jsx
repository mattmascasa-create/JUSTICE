import React, { useState, useEffect, useRef } from 'react';
import { Bell, X, Check, CheckCheck, AlertTriangle, MessageCircle, FileText, Gavel, Siren, BellRing, BellOff, Settings } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { Switch } from './ui/switch';
import { useWebSocket } from '../contexts/WebSocketContext';
import { useAuth } from '../contexts/AuthContext';
import { usePushNotifications } from '../hooks/usePushNotifications';
import api from '../lib/api';
import { cn } from '../lib/utils';

const notificationIcons = {
  message: MessageCircle,
  case_update: FileText,
  attorney_response: Gavel,
  sos_alert: Siren,
  system: Bell,
  warning: AlertTriangle,
};

const notificationColors = {
  message: 'text-blue-400',
  case_update: 'text-green-400',
  attorney_response: 'text-purple-400',
  sos_alert: 'text-red-500',
  system: 'text-gray-400',
  warning: 'text-yellow-400',
};

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef(null);
  const { lastMessage } = useWebSocket();
  const { token } = useAuth();
  const { 
    isSupported: pushSupported, 
    isSubscribed: pushEnabled, 
    loading: pushLoading,
    subscribe: enablePush,
    unsubscribe: disablePush 
  } = usePushNotifications();

  // Fetch notifications on mount
  useEffect(() => {
    if (token) {
      fetchNotifications();
    }
  }, [token]);

  // Listen for real-time notifications via WebSocket
  useEffect(() => {
    if (lastMessage?.type === 'notification') {
      const newNotification = lastMessage.data;
      setNotifications(prev => [newNotification, ...prev.slice(0, 49)]);
      setUnreadCount(prev => prev + 1);
    }
  }, [lastMessage]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const res = await api.get('/notifications');
      setNotifications(res.data.notifications || []);
      setUnreadCount(res.data.unread_count || 0);
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
    } finally {
      setLoading(false);
    }
  };

  const markAsRead = async (notificationId) => {
    try {
      await api.post(`/notifications/${notificationId}/read`);
      setNotifications(prev =>
        prev.map(n => n.notification_id === notificationId ? { ...n, read: true } : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  };

  const markAllAsRead = async () => {
    try {
      await api.post('/notifications/mark-all-read');
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <Button
        variant="ghost"
        size="icon"
        className="relative"
        onClick={() => setIsOpen(!isOpen)}
        data-testid="notification-bell"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <Badge 
            className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 bg-red-500 text-white text-xs"
            data-testid="notification-count"
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </Badge>
        )}
      </Button>

      {isOpen && (
        <div 
          className="absolute right-0 mt-2 w-80 sm:w-96 bg-card border border-border rounded-lg shadow-xl z-50"
          data-testid="notification-dropdown"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-3 border-b border-border">
            <h3 className="font-semibold text-foreground">Notifications</h3>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={markAllAsRead}
                  className="text-xs text-muted-foreground hover:text-foreground"
                >
                  <CheckCheck className="h-4 w-4 mr-1" />
                  Mark all read
                </Button>
              )}
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => setIsOpen(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Push Notification Toggle */}
          {pushSupported && (
            <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-muted/30">
              <div className="flex items-center gap-2 text-sm">
                {pushEnabled ? (
                  <BellRing className="h-4 w-4 text-green-500" />
                ) : (
                  <BellOff className="h-4 w-4 text-muted-foreground" />
                )}
                <span className="text-muted-foreground">
                  Push alerts {pushEnabled ? 'on' : 'off'}
                </span>
              </div>
              <Switch
                checked={pushEnabled}
                onCheckedChange={(checked) => checked ? enablePush() : disablePush()}
                disabled={pushLoading}
                data-testid="push-notification-toggle"
              />
            </div>
          )}

          {/* Notifications List */}
          <ScrollArea className="h-[400px]">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Bell className="h-10 w-10 mb-3 opacity-50" />
                <p>No notifications yet</p>
                <p className="text-sm">You&apos;re all caught up!</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {notifications.map((notification) => {
                  const Icon = notificationIcons[notification.type] || Bell;
                  const colorClass = notificationColors[notification.type] || 'text-gray-400';
                  
                  return (
                    <div
                      key={notification.notification_id}
                      className={cn(
                        "p-3 hover:bg-accent/50 cursor-pointer transition-colors",
                        !notification.read && "bg-primary/5"
                      )}
                      onClick={() => !notification.read && markAsRead(notification.notification_id)}
                      data-testid={`notification-item-${notification.notification_id}`}
                    >
                      <div className="flex gap-3">
                        <div className={cn("mt-1", colorClass)}>
                          <Icon className="h-5 w-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <p className={cn(
                              "text-sm",
                              !notification.read ? "font-medium text-foreground" : "text-muted-foreground"
                            )}>
                              {notification.title}
                            </p>
                            {!notification.read && (
                              <div className="h-2 w-2 rounded-full bg-primary flex-shrink-0 mt-1.5" />
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                            {notification.message}
                          </p>
                          <p className="text-xs text-muted-foreground/70 mt-1">
                            {formatTime(notification.created_at)}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </ScrollArea>

          {/* Footer */}
          <div className="p-2 border-t border-border flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="flex-1 text-sm text-muted-foreground hover:text-foreground"
              onClick={() => {
                setIsOpen(false);
                window.location.href = '/notification-preferences';
              }}
            >
              <Settings className="h-4 w-4 mr-1" />
              Preferences
            </Button>
            {notifications.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className="flex-1 text-sm text-muted-foreground hover:text-foreground"
                onClick={() => {
                  setIsOpen(false);
                  window.location.href = '/notifications';
                }}
              >
                View all
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
