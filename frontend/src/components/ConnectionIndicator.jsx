import React, { useContext } from 'react';
import { ConnectionState } from '../contexts/WebSocketContext';
import { Wifi, WifiOff, Loader2, AlertCircle } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';

// Import context directly to check if available
const WebSocketContext = React.createContext(null);

export default function ConnectionIndicator() {
  // Try to use WebSocket context, but don't crash if not available
  let wsContext = null;
  try {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    wsContext = require('../contexts/WebSocketContext').useWebSocket?.();
  } catch {
    // Context not available, will render as disconnected
  }
  
  const connectionState = wsContext?.connectionState || ConnectionState.DISCONNECTED;
  const connectionQuality = wsContext?.connectionQuality || 'unknown';
  const reconnect = wsContext?.reconnect || (() => {});

  const getIndicator = () => {
    switch (connectionState) {
      case ConnectionState.CONNECTED:
        return {
          icon: Wifi,
          color: connectionQuality === 'good' 
            ? 'text-green-500' 
            : connectionQuality === 'degraded' 
              ? 'text-yellow-500' 
              : 'text-orange-500',
          label: connectionQuality === 'good' 
            ? 'Connected' 
            : connectionQuality === 'degraded' 
              ? 'Connection Unstable' 
              : 'Poor Connection',
          pulse: connectionQuality !== 'good'
        };
      case ConnectionState.CONNECTING:
        return {
          icon: Loader2,
          color: 'text-blue-500',
          label: 'Connecting...',
          spin: true
        };
      case ConnectionState.RECONNECTING:
        return {
          icon: Loader2,
          color: 'text-yellow-500',
          label: 'Reconnecting...',
          spin: true
        };
      case ConnectionState.FAILED:
        return {
          icon: AlertCircle,
          color: 'text-red-500',
          label: 'Connection Failed',
          clickable: true
        };
      case ConnectionState.DISCONNECTED:
      default:
        return {
          icon: WifiOff,
          color: 'text-gray-400',
          label: 'Disconnected',
          clickable: true
        };
    }
  };

  const indicator = getIndicator();
  const Icon = indicator.icon;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={indicator.clickable ? reconnect : undefined}
            className={`
              relative p-2 rounded-full transition-all duration-200
              ${indicator.clickable ? 'hover:bg-muted cursor-pointer' : 'cursor-default'}
              ${indicator.pulse ? 'animate-pulse' : ''}
            `}
            data-testid="connection-indicator"
            aria-label={indicator.label}
          >
            <Icon 
              className={`h-4 w-4 ${indicator.color} ${indicator.spin ? 'animate-spin' : ''}`} 
            />
            {connectionState === ConnectionState.CONNECTED && connectionQuality === 'good' && (
              <span className="absolute top-1 right-1 h-2 w-2 bg-green-500 rounded-full" />
            )}
          </button>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="text-xs">
          <p>{indicator.label}</p>
          {indicator.clickable && (
            <p className="text-muted-foreground">Click to reconnect</p>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
