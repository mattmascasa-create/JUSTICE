import React, { useState, useEffect } from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { sosAPI } from '../lib/api';
import { cn } from '../lib/utils';
import { Siren, MapPin, Phone, Shield, CheckCircle, X, AlertTriangle, Users } from 'lucide-react';
import { toast } from 'sonner';

export default function SOSPage() {
  const [activeAlert, setActiveAlert] = useState(null);
  const [loading, setLoading] = useState(false);
  const [location, setLocation] = useState(null);
  const [gettingLocation, setGettingLocation] = useState(false);

  useEffect(() => {
    checkActiveAlert();
    getLocation();
  }, []);

  const checkActiveAlert = async () => {
    try {
      const response = await sosAPI.getActive();
      if (response.data) {
        setActiveAlert(response.data);
      }
    } catch (error) {
      console.error('Error checking active alert:', error);
    }
  };

  const getLocation = () => {
    setGettingLocation(true);
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocation({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude
          });
          setGettingLocation(false);
        },
        (error) => {
          console.error('Location error:', error);
          setGettingLocation(false);
          toast.error('Unable to get location. Please enable location services.');
        },
        { enableHighAccuracy: true }
      );
    } else {
      setGettingLocation(false);
      toast.error('Geolocation is not supported by your browser.');
    }
  };

  const activateSOS = async () => {
    if (!location) {
      toast.error('Location required for SOS. Please enable location services.');
      getLocation();
      return;
    }

    setLoading(true);
    try {
      const response = await sosAPI.create({
        latitude: location.latitude,
        longitude: location.longitude,
        address: null // Could be reverse geocoded
      });
      setActiveAlert(response.data);
      toast.success('SOS Alert Activated! Help is on the way.');
    } catch (error) {
      toast.error('Failed to activate SOS. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const resolveAlert = async () => {
    if (!activeAlert) return;

    try {
      await sosAPI.resolve(activeAlert.alert_id);
      setActiveAlert(null);
      toast.success('SOS Alert resolved. Stay safe.');
    } catch (error) {
      toast.error('Failed to resolve alert.');
    }
  };

  return (
    <AppLayout>
      <div className="min-h-[80vh] flex flex-col items-center justify-center p-4" data-testid="sos-page">
        {activeAlert ? (
          // Active Alert State
          <div className="w-full max-w-lg text-center space-y-6">
            <div className="animate-pulse">
              <div className="w-32 h-32 mx-auto rounded-full bg-red-500 flex items-center justify-center">
                <Siren className="h-16 w-16 text-white" />
              </div>
            </div>

            <div>
              <h1 className="font-serif text-3xl font-bold text-red-500 mb-2">SOS ACTIVE</h1>
              <p className="text-muted-foreground">
                Your emergency alert has been sent. Help is being notified.
              </p>
            </div>

            <Card className="border-red-500/20 bg-red-500/5">
              <CardContent className="p-6 space-y-4">
                <div className="flex items-center justify-center gap-2 text-green-500">
                  <CheckCircle className="h-5 w-5" />
                  <span>Location shared</span>
                </div>
                <div className="flex items-center justify-center gap-2 text-green-500">
                  <CheckCircle className="h-5 w-5" />
                  <span>Emergency contacts notified (MOCKED)</span>
                </div>
                <div className="flex items-center justify-center gap-2 text-green-500">
                  <CheckCircle className="h-5 w-5" />
                  <span>Nearby attorneys alerted (MOCKED)</span>
                </div>
                <div className="text-sm text-muted-foreground font-mono">
                  Alert ID: {activeAlert.alert_id}
                </div>
              </CardContent>
            </Card>

            <div className="space-y-3">
              <Button
                size="lg"
                variant="outline"
                className="w-full h-14 border-green-500 text-green-500 hover:bg-green-500 hover:text-white"
                onClick={resolveAlert}
                data-testid="resolve-sos-btn"
              >
                <Shield className="h-5 w-5 mr-2" />
                I Am Safe - Resolve Alert
              </Button>
              
              <p className="text-xs text-muted-foreground">
                Only resolve if you are safe. False alarms may affect response times.
              </p>
            </div>
          </div>
        ) : (
          // Ready State
          <div className="w-full max-w-lg text-center space-y-8">
            {/* SOS Button */}
            <div className="relative">
              <div className={cn(
                "w-48 h-48 mx-auto rounded-full bg-gradient-to-br from-red-500 to-red-700 flex items-center justify-center cursor-pointer transition-all duration-300",
                "hover:scale-105 hover:shadow-2xl hover:shadow-red-500/50",
                "animate-pulse-emergency",
                loading && "opacity-50 cursor-not-allowed"
              )}>
                <button
                  onClick={activateSOS}
                  disabled={loading || gettingLocation}
                  className="w-full h-full rounded-full flex flex-col items-center justify-center text-white focus:outline-none"
                  data-testid="sos-btn"
                >
                  <Siren className="h-16 w-16 mb-2" />
                  <span className="text-2xl font-bold">SOS</span>
                </button>
              </div>
              
              {/* Pulsing rings */}
              <div className="absolute inset-0 -z-10">
                <div className="w-48 h-48 mx-auto rounded-full border-2 border-red-500/30 animate-ping" style={{ animationDuration: '2s' }} />
              </div>
            </div>

            <div>
              <h1 className="font-serif text-3xl font-bold mb-2">Emergency SOS</h1>
              <p className="text-muted-foreground">
                {gettingLocation 
                  ? 'Getting your location...'
                  : 'Tap the button to activate emergency protocol'}
              </p>
            </div>

            {/* Location Status */}
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-center gap-2">
                  <MapPin className={cn(
                    "h-5 w-5",
                    location ? "text-green-500" : "text-yellow-500"
                  )} />
                  <span className={cn(
                    location ? "text-green-500" : "text-yellow-500"
                  )}>
                    {location 
                      ? `Location ready: ${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)}`
                      : 'Location required for SOS'}
                  </span>
                </div>
                {!location && (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="mt-2"
                    onClick={getLocation}
                  >
                    Enable Location
                  </Button>
                )}
              </CardContent>
            </Card>

            {/* What happens */}
            <Card className="text-left">
              <CardContent className="p-6 space-y-4">
                <h3 className="font-serif font-bold">When you activate SOS:</h3>
                <div className="space-y-3">
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded bg-red-500/10">
                      <MapPin className="h-4 w-4 text-red-500" />
                    </div>
                    <div>
                      <p className="font-medium">Location Shared</p>
                      <p className="text-sm text-muted-foreground">Your GPS coordinates are recorded and shared</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded bg-blue-500/10">
                      <Phone className="h-4 w-4 text-blue-500" />
                    </div>
                    <div>
                      <p className="font-medium">Contacts Notified (MOCKED)</p>
                      <p className="text-sm text-muted-foreground">SMS/Email sent to your emergency contacts</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded bg-green-500/10">
                      <Users className="h-4 w-4 text-green-500" />
                    </div>
                    <div>
                      <p className="font-medium">Attorneys Alerted (MOCKED)</p>
                      <p className="text-sm text-muted-foreground">Emergency-available attorneys are notified</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="flex items-center justify-center gap-2 text-yellow-500">
              <AlertTriangle className="h-4 w-4" />
              <span className="text-sm">Use only in genuine emergencies</span>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
