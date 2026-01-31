/**
 * SOSPanel Component
 * 
 * Emergency SOS functionality for encounter mode.
 * Sends alerts to emergency contacts and attorneys.
 */

import React, { useState, useCallback } from 'react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Siren, Phone, Loader2, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';
import { sosAPI } from '../lib/api';

export function SOSPanel({ 
  encounter, 
  location, 
  isRecording,
  onSOSTriggered,
  className = '' 
}) {
  const [sosActive, setSosActive] = useState(false);
  const [sosSending, setSosSending] = useState(false);
  const [sosAlertId, setSosAlertId] = useState(null);

  const triggerQuickSOS = useCallback(async () => {
    if (!encounter || sosSending) return;
    setSosSending(true);
    
    try {
      const response = await sosAPI.trigger({
        encounter_id: encounter.encounter_id,
        latitude: location?.latitude,
        longitude: location?.longitude,
        alert_type: 'encounter_distress',
        message: 'Emergency alert triggered during police encounter'
      });
      
      setSosActive(true);
      setSosAlertId(response.data.alert_id);
      toast.success('🚨 Emergency Alert Sent!', {
        description: 'Your emergency contacts have been notified.'
      });
      onSOSTriggered?.(response.data);
    } catch (error) {
      toast.error('SOS failed. Trying again...');
      // Retry logic
      try {
        const retryResponse = await sosAPI.trigger({
          encounter_id: encounter.encounter_id,
          latitude: location?.latitude,
          longitude: location?.longitude,
          alert_type: 'encounter_distress',
          message: 'RETRY: Emergency alert during police encounter'
        });
        setSosActive(true);
        setSosAlertId(retryResponse.data.alert_id);
        toast.success('🚨 Emergency Alert Sent!');
        onSOSTriggered?.(retryResponse.data);
      } catch {
        toast.error('Unable to send SOS. Call 911 directly.');
      }
    } finally {
      setSosSending(false);
    }
  }, [encounter, location, sosSending, onSOSTriggered]);

  const cancelSOS = useCallback(async () => {
    if (!sosAlertId) return;
    
    try {
      await sosAPI.cancel(sosAlertId);
      setSosActive(false);
      setSosAlertId(null);
      toast.info('SOS Alert cancelled');
    } catch (error) {
      toast.error('Could not cancel SOS');
    }
  }, [sosAlertId]);

  if (!isRecording) return null;

  return (
    <Card className={`border-2 ${sosActive ? 'border-red-500 bg-red-500/10 animate-pulse' : 'border-red-500/30'} ${className}`}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-3 rounded-full ${sosActive ? 'bg-red-500 animate-bounce' : 'bg-red-500/20'}`}>
              <Siren className={`h-6 w-6 ${sosActive ? 'text-white' : 'text-red-500'}`} />
            </div>
            <div>
              <p className="font-bold text-red-500 flex items-center gap-2">
                Emergency SOS
                {sosActive && (
                  <Badge variant="destructive" className="animate-pulse">
                    <CheckCircle className="h-3 w-3 mr-1" />
                    SENT
                  </Badge>
                )}
              </p>
              <p className="text-sm text-muted-foreground">
                {sosActive 
                  ? 'Emergency contacts notified' 
                  : 'Alert contacts & share location'}
              </p>
            </div>
          </div>
          
          {sosActive ? (
            <Button 
              variant="outline" 
              size="sm" 
              onClick={cancelSOS}
              className="border-red-500 text-red-500 hover:bg-red-500/10"
            >
              Cancel Alert
            </Button>
          ) : (
            <Button 
              variant="destructive" 
              size="lg"
              onClick={triggerQuickSOS}
              disabled={sosSending}
              className="h-12 px-6"
              data-testid="sos-button"
            >
              {sosSending ? (
                <>
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Phone className="h-5 w-5 mr-2" />
                  SOS
                </>
              )}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default SOSPanel;
