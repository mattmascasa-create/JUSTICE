import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Alert, AlertDescription } from './ui/alert';
import { ScrollArea } from './ui/scroll-area';
import { Switch } from './ui/switch';
import { Label } from './ui/label';
import { locationAlertsAPI } from '../lib/api';
import { 
  MapPin, AlertTriangle, Shield, Bell, BellOff, 
  RefreshCw, ChevronRight, Loader2, X
} from 'lucide-react';
import { toast } from 'sonner';

const warningColors = {
  critical: 'bg-red-500 text-white border-red-600',
  high: 'bg-orange-500 text-white border-orange-600',
  elevated: 'bg-yellow-500 text-black border-yellow-600',
  normal: 'bg-green-500 text-white border-green-600'
};

const warningIcons = {
  critical: '🚨',
  high: '🔴',
  elevated: '🟡',
  normal: '🟢'
};

export function LocationAlertPanel({ onAlertReceived, className = '' }) {
  const [enabled, setEnabled] = useState(true);
  const [loading, setLoading] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [location, setLocation] = useState(null);
  const [locationError, setLocationError] = useState(null);
  const [lastCheck, setLastCheck] = useState(null);
  const [dismissed, setDismissed] = useState([]);

  // Get current location
  const getLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setLocationError('Geolocation not supported');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          lat: position.coords.latitude,
          lon: position.coords.longitude
        });
        setLocationError(null);
      },
      (error) => {
        setLocationError(error.message);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }, []);

  // Check for alerts at current location
  const checkAlerts = useCallback(async () => {
    if (!enabled || !location) return;

    setLoading(true);
    try {
      const response = await locationAlertsAPI.check(location.lat, location.lon);
      const newAlerts = response.data.alerts.filter(
        a => !dismissed.includes(a.alert_id)
      );
      
      setAlerts(newAlerts);
      setLastCheck(new Date());

      // Notify parent component if there are critical/high alerts
      if (onAlertReceived && (response.data.has_critical || response.data.has_high)) {
        onAlertReceived(newAlerts);
      }

      // Show toast for critical alerts
      const criticalAlert = newAlerts.find(a => a.warning_level === 'critical');
      if (criticalAlert) {
        toast.warning(criticalAlert.message, { duration: 10000 });
      }
    } catch (error) {
      console.error('Location alert check failed:', error);
    } finally {
      setLoading(false);
    }
  }, [enabled, location, dismissed, onAlertReceived]);

  // Initial location fetch
  useEffect(() => {
    getLocation();
  }, [getLocation]);

  // Check alerts when location changes
  useEffect(() => {
    if (location && enabled) {
      checkAlerts();
    }
  }, [location, enabled, checkAlerts]);

  // Periodic location checks (every 5 minutes when enabled)
  useEffect(() => {
    if (!enabled) return;

    const interval = setInterval(() => {
      getLocation();
    }, 5 * 60 * 1000);

    return () => clearInterval(interval);
  }, [enabled, getLocation]);

  const dismissAlert = (alertId) => {
    setDismissed(prev => [...prev, alertId]);
    setAlerts(prev => prev.filter(a => a.alert_id !== alertId));
  };

  const activeAlerts = alerts.filter(a => a.warning_level !== 'normal');

  return (
    <Card className={className} data-testid="location-alert-panel">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <MapPin className="h-5 w-5 text-primary" />
            Location Alerts
          </CardTitle>
          <div className="flex items-center gap-2">
            <Switch
              id="location-alerts"
              checked={enabled}
              onCheckedChange={setEnabled}
              data-testid="location-alerts-toggle"
            />
            <Label htmlFor="location-alerts" className="text-xs">
              {enabled ? <Bell className="h-4 w-4" /> : <BellOff className="h-4 w-4 text-muted-foreground" />}
            </Label>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {!enabled ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            Location alerts are disabled
          </p>
        ) : locationError ? (
          <Alert variant="destructive" className="mb-3">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription className="text-sm">
              {locationError}
              <Button 
                variant="link" 
                size="sm" 
                className="p-0 h-auto ml-2"
                onClick={getLocation}
              >
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        ) : loading ? (
          <div className="flex items-center justify-center py-6">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : activeAlerts.length === 0 ? (
          <div className="text-center py-4">
            <Shield className="h-8 w-8 mx-auto text-green-500 mb-2" />
            <p className="text-sm text-muted-foreground">
              No alerts in your area
            </p>
            {lastCheck && (
              <p className="text-xs text-muted-foreground mt-1">
                Last checked: {lastCheck.toLocaleTimeString()}
              </p>
            )}
          </div>
        ) : (
          <ScrollArea className="h-[300px]">
            <div className="space-y-3">
              {activeAlerts.map((alert) => (
                <div
                  key={alert.alert_id}
                  className={`p-3 rounded-lg border-2 ${warningColors[alert.warning_level]}`}
                  data-testid={`alert-${alert.alert_id}`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{warningIcons[alert.warning_level]}</span>
                      <div>
                        <p className="font-semibold text-sm">{alert.department_name}</p>
                        <p className="text-xs opacity-80">
                          {alert.distance_km}km away • Score: {alert.accountability_score}/100
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 opacity-70 hover:opacity-100"
                      onClick={() => dismissAlert(alert.alert_id)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                  
                  <p className="text-sm mb-3">{alert.message}</p>
                  
                  {alert.coaching_tips?.length > 0 && (
                    <div className="bg-black/10 rounded p-2">
                      <p className="text-xs font-semibold mb-1">Quick Tips:</p>
                      <ul className="space-y-1">
                        {alert.coaching_tips.slice(0, 3).map((tip, idx) => (
                          <li key={idx} className="text-xs flex items-start gap-1">
                            <ChevronRight className="h-3 w-3 mt-0.5 flex-shrink-0" />
                            {tip}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
        )}

        {enabled && !loading && (
          <Button
            variant="outline"
            size="sm"
            className="w-full mt-3"
            onClick={() => {
              getLocation();
              setTimeout(checkAlerts, 500);
            }}
            data-testid="refresh-alerts-btn"
          >
            <RefreshCw className="h-3 w-3 mr-2" />
            Refresh Location
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

// Compact badge version for header/navbar
export function LocationAlertBadge({ onClick }) {
  const [hasAlerts, setHasAlerts] = useState(false);
  const [alertLevel, setAlertLevel] = useState('normal');
  const [checking, setChecking] = useState(false);

  const checkLocation = useCallback(async () => {
    if (!navigator.geolocation) return;

    setChecking(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const response = await locationAlertsAPI.check(
            position.coords.latitude,
            position.coords.longitude
          );
          
          if (response.data.has_critical) {
            setAlertLevel('critical');
            setHasAlerts(true);
          } else if (response.data.has_high) {
            setAlertLevel('high');
            setHasAlerts(true);
          } else if (response.data.alert_count > 0) {
            setAlertLevel('elevated');
            setHasAlerts(true);
          } else {
            setHasAlerts(false);
            setAlertLevel('normal');
          }
        } catch (error) {
          console.error('Location check error:', error);
        } finally {
          setChecking(false);
        }
      },
      () => setChecking(false),
      { enableHighAccuracy: false, timeout: 5000 }
    );
  }, []);

  useEffect(() => {
    checkLocation();
    const interval = setInterval(checkLocation, 10 * 60 * 1000); // Every 10 min
    return () => clearInterval(interval);
  }, [checkLocation]);

  if (!hasAlerts && !checking) return null;

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={onClick}
      className="relative"
      data-testid="location-alert-badge"
    >
      <MapPin className={`h-5 w-5 ${
        alertLevel === 'critical' ? 'text-red-500 animate-pulse' :
        alertLevel === 'high' ? 'text-orange-500' :
        alertLevel === 'elevated' ? 'text-yellow-500' : 'text-muted-foreground'
      }`} />
      {hasAlerts && (
        <span className={`absolute -top-1 -right-1 w-3 h-3 rounded-full ${
          alertLevel === 'critical' ? 'bg-red-500 animate-ping' :
          alertLevel === 'high' ? 'bg-orange-500' : 'bg-yellow-500'
        }`} />
      )}
    </Button>
  );
}

export default LocationAlertPanel;
