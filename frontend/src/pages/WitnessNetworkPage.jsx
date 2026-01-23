import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Progress } from '../components/ui/progress';
import { ScrollArea } from '../components/ui/scroll-area';
import { 
  Eye, MapPin, Radio, Users, Shield, Award, 
  Bell, Video, Clock, ChevronRight, Loader2,
  AlertTriangle, CheckCircle, Navigation, Zap
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../lib/api';
import { useWebSocket } from '../contexts/WebSocketContext';

const badgeStyles = {
  gold: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  purple: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  green: 'bg-green-500/20 text-green-400 border-green-500/30',
  gray: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
};

export default function WitnessNetworkPage() {
  const navigate = useNavigate();
  const { notifications } = useWebSocket();
  
  const [witnessMode, setWitnessMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [location, setLocation] = useState(null);
  const [locationError, setLocationError] = useState(null);
  const [stats, setStats] = useState(null);
  const [nearbyWitnesses, setNearbyWitnesses] = useState([]);
  const [activeAlerts, setActiveAlerts] = useState([]);
  const [updatingLocation, setUpdatingLocation] = useState(false);

  // Get current location
  const getCurrentLocation = useCallback(() => {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocation not supported'));
        return;
      }
      
      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            lat: position.coords.latitude,
            lng: position.coords.longitude
          });
        },
        (error) => reject(error),
        { enableHighAccuracy: true, timeout: 10000 }
      );
    });
  }, []);

  // Fetch initial data
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Get witness stats
        const statsRes = await api.get('/advanced/witness/stats');
        setStats(statsRes.data);

        // Get user's witness mode status
        const userRes = await api.get('/auth/me');
        setWitnessMode(userRes.data.witness_mode_enabled || false);

        // Get location
        const loc = await getCurrentLocation();
        setLocation(loc);

        // If witness mode is on, get nearby witnesses
        if (userRes.data.witness_mode_enabled) {
          const nearbyRes = await api.get(`/advanced/witness/nearby?lat=${loc.lat}&lng=${loc.lng}&radius=1`);
          setNearbyWitnesses(nearbyRes.data.witnesses || []);
        }
      } catch (error) {
        if (error.code === 1) {
          setLocationError('Location permission denied. Please enable location access.');
        } else {
          console.error('Failed to fetch data:', error);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [getCurrentLocation]);

  // Listen for witness alerts via WebSocket
  useEffect(() => {
    const witnessNotifications = notifications.filter(
      n => n.type === 'witness_alert' && !n.read
    );
    setActiveAlerts(witnessNotifications);
  }, [notifications]);

  // Toggle witness mode
  const toggleWitnessMode = async () => {
    if (!location) {
      toast.error('Location required to enable witness mode');
      return;
    }

    try {
      if (witnessMode) {
        await api.post('/advanced/witness/disable');
        setWitnessMode(false);
        setNearbyWitnesses([]);
        toast.success('Witness mode disabled');
      } else {
        await api.post('/advanced/witness/enable', location);
        setWitnessMode(true);
        toast.success('Witness mode enabled! You\'ll be alerted to nearby encounters.');
        
        // Fetch nearby witnesses
        const nearbyRes = await api.get(`/advanced/witness/nearby?lat=${location.lat}&lng=${location.lng}&radius=1`);
        setNearbyWitnesses(nearbyRes.data.witnesses || []);
      }
    } catch (error) {
      toast.error('Failed to toggle witness mode');
    }
  };

  // Update location
  const updateLocation = async () => {
    setUpdatingLocation(true);
    try {
      const loc = await getCurrentLocation();
      setLocation(loc);
      
      if (witnessMode) {
        await api.post('/advanced/witness/location', loc);
        
        // Refresh nearby witnesses
        const nearbyRes = await api.get(`/advanced/witness/nearby?lat=${loc.lat}&lng=${loc.lng}&radius=1`);
        setNearbyWitnesses(nearbyRes.data.witnesses || []);
      }
      
      toast.success('Location updated');
    } catch (error) {
      toast.error('Failed to update location');
    } finally {
      setUpdatingLocation(false);
    }
  };

  // Join an encounter as witness
  const joinAsWitness = async (encounterId) => {
    try {
      await api.post(`/advanced/witness/join/${encounterId}`);
      toast.success('You are now witnessing this encounter');
      navigate(`/encounter/watch/${encounterId}`);
    } catch (error) {
      toast.error('Failed to join as witness');
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-6" data-testid="witness-network-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Eye className="h-6 w-6 text-blue-500" />
              Witness Network
            </h1>
            <p className="text-muted-foreground mt-1">
              Be a community witness for nearby encounters
            </p>
          </div>
          
          {stats?.badge && (
            <Badge 
              variant="outline" 
              className={`text-lg px-4 py-2 ${badgeStyles[stats.badge.color]}`}
            >
              <Award className="h-5 w-5 mr-2" />
              {stats.badge.name}
            </Badge>
          )}
        </div>

        {/* Location Error */}
        {locationError && (
          <Alert className="border-red-500/50 bg-red-500/10">
            <AlertTriangle className="h-4 w-4 text-red-500" />
            <AlertDescription className="text-red-300">
              {locationError}
            </AlertDescription>
          </Alert>
        )}

        {/* Active Alerts */}
        {activeAlerts.length > 0 && (
          <Card className="border-red-500 bg-red-500/10 animate-pulse">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2 text-red-400">
                <AlertTriangle className="h-5 w-5" />
                Active Encounter Alerts ({activeAlerts.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {activeAlerts.map((alert, idx) => (
                <div 
                  key={idx}
                  className="flex items-center justify-between p-3 rounded-lg bg-red-500/20 border border-red-500/30"
                >
                  <div>
                    <p className="font-medium">{alert.title || 'Encounter Alert'}</p>
                    <p className="text-sm text-muted-foreground">{alert.message}</p>
                  </div>
                  <Button 
                    onClick={() => joinAsWitness(alert.metadata?.encounter_id)}
                    className="bg-red-600 hover:bg-red-700"
                  >
                    <Eye className="h-4 w-4 mr-2" />
                    Watch
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Witness Mode Toggle */}
        <Card className={`border-2 transition-all ${witnessMode ? 'border-blue-500/50 bg-blue-500/5' : 'border-border'}`}>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`p-4 rounded-full ${witnessMode ? 'bg-blue-500' : 'bg-muted'}`}>
                  <Eye className={`h-8 w-8 ${witnessMode ? 'text-white' : 'text-muted-foreground'}`} />
                </div>
                <div>
                  <h3 className="text-xl font-bold">Witness Mode</h3>
                  <p className="text-muted-foreground">
                    {witnessMode 
                      ? 'You\'ll receive alerts for encounters within 1 mile' 
                      : 'Enable to help protect your community'}
                  </p>
                </div>
              </div>
              <Switch
                checked={witnessMode}
                onCheckedChange={toggleWitnessMode}
                disabled={!location}
                className="scale-150"
                id="witness-mode-toggle"
                data-testid="witness-mode-toggle"
              />
            </div>

            {witnessMode && location && (
              <div className="mt-4 pt-4 border-t border-border/50 flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <MapPin className="h-4 w-4" />
                  <span>
                    {location.lat.toFixed(4)}, {location.lng.toFixed(4)}
                  </span>
                </div>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={updateLocation}
                  disabled={updatingLocation}
                >
                  {updatingLocation ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Navigation className="h-4 w-4 mr-2" />
                  )}
                  Update Location
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-3 gap-4">
            <Card>
              <CardContent className="p-4 text-center">
                <Eye className="h-6 w-6 mx-auto text-blue-400 mb-2" />
                <div className="text-2xl font-bold">{stats.total_witnessed}</div>
                <div className="text-xs text-muted-foreground">Encounters Witnessed</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <Video className="h-6 w-6 mx-auto text-green-400 mb-2" />
                <div className="text-2xl font-bold">{stats.recordings_submitted}</div>
                <div className="text-xs text-muted-foreground">Recordings Submitted</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <Award className="h-6 w-6 mx-auto text-yellow-400 mb-2" />
                <div className="text-2xl font-bold">{stats.reputation_score}</div>
                <div className="text-xs text-muted-foreground">Reputation Score</div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Reputation Progress */}
        {stats && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Reputation Progress</CardTitle>
            </CardHeader>
            <CardContent>
              <Progress value={stats.reputation_score} className="h-3" />
              <div className="flex justify-between text-xs text-muted-foreground mt-2">
                <span>New Witness</span>
                <span>Observer (10)</span>
                <span>Watcher (25)</span>
                <span>Protector (50)</span>
                <span>Guardian (80)</span>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Nearby Witnesses */}
        {witnessMode && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5 text-blue-400" />
                Nearby Witnesses
              </CardTitle>
              <CardDescription>
                Other community members watching this area
              </CardDescription>
            </CardHeader>
            <CardContent>
              {nearbyWitnesses.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Users className="h-12 w-12 mx-auto opacity-50 mb-2" />
                  <p>No other witnesses nearby</p>
                  <p className="text-sm">Be the first to protect your community!</p>
                </div>
              ) : (
                <ScrollArea className="h-48">
                  <div className="space-y-2">
                    {nearbyWitnesses.map((witness, idx) => (
                      <div 
                        key={idx}
                        className="flex items-center justify-between p-3 rounded-lg bg-muted/30"
                      >
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                            <Eye className="h-5 w-5 text-blue-400" />
                          </div>
                          <div>
                            <p className="font-medium">Witness #{idx + 1}</p>
                            <p className="text-xs text-muted-foreground">
                              {witness.distance_miles} miles away
                            </p>
                          </div>
                        </div>
                        <Badge variant="outline" className="bg-green-500/20 text-green-400">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Active
                        </Badge>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        )}

        {/* How It Works */}
        <Card className="bg-muted/30">
          <CardHeader>
            <CardTitle className="text-sm">How Witness Network Works</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-full bg-blue-500/20">
                <Radio className="h-4 w-4 text-blue-400" />
              </div>
              <div>
                <p className="font-medium text-foreground">Enable Witness Mode</p>
                <p>Toggle witness mode to receive alerts for encounters within 1 mile of your location.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-full bg-yellow-500/20">
                <Bell className="h-4 w-4 text-yellow-400" />
              </div>
              <div>
                <p className="font-medium text-foreground">Receive Alerts</p>
                <p>Get notified when someone nearby starts an encounter or triggers an emergency.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-full bg-green-500/20">
                <Eye className="h-4 w-4 text-green-400" />
              </div>
              <div>
                <p className="font-medium text-foreground">Watch & Record</p>
                <p>Join as a witness to watch the live stream and optionally record your own perspective.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-full bg-purple-500/20">
                <Award className="h-4 w-4 text-purple-400" />
              </div>
              <div>
                <p className="font-medium text-foreground">Build Reputation</p>
                <p>Earn reputation points and badges for witnessing encounters and submitting recordings.</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}
