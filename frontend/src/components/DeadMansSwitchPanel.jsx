import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Alert, AlertDescription } from './ui/alert';
import { Switch } from './ui/switch';
import { Label } from './ui/label';
import { 
  Shield, AlertTriangle, Clock, CheckCircle, 
  Loader2, Hand, Timer, Bell
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../lib/api';

export default function DeadMansSwitchPanel({ 
  encounterId,
  isRecording = false,
  onTrigger
}) {
  const [config, setConfig] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [enabled, setEnabled] = useState(true);
  const [showWarning, setShowWarning] = useState(false);
  const [countdown, setCountdown] = useState(null);
  const [hasTriggered, setHasTriggered] = useState(false);
  
  const checkIntervalRef = useRef(null);
  const countdownIntervalRef = useRef(null);

  // Fetch configuration on mount
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await api.get('/advanced/dead-mans-switch/config');
        setConfig(response.data);
        setEnabled(response.data.enabled);
      } catch (error) {
        console.error('Failed to fetch DMS config:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchConfig();
  }, []);

  // Register activity (heartbeat)
  const registerActivity = useCallback(async (activityType = 'touch') => {
    if (!encounterId || !enabled || !isRecording) return;
    
    try {
      await api.post(`/advanced/dead-mans-switch/activity/${encounterId}?activity_type=${activityType}`);
      setShowWarning(false);
      setCountdown(null);
    } catch (error) {
      console.error('Failed to register activity:', error);
    }
  }, [encounterId, enabled, isRecording]);

  // Check inactivity status
  const checkStatus = useCallback(async () => {
    if (!encounterId || !enabled || !isRecording || hasTriggered) return;
    
    try {
      const response = await api.get(`/advanced/dead-mans-switch/status/${encounterId}`);
      const data = response.data;
      setStatus(data);
      
      if (data.triggered && !hasTriggered) {
        // Trigger the switch!
        setHasTriggered(true);
        await triggerSwitch();
      } else if (data.warning) {
        // Show warning countdown
        setShowWarning(true);
        setCountdown(Math.ceil(data.seconds_until_trigger));
      } else {
        setShowWarning(false);
        setCountdown(null);
      }
    } catch (error) {
      console.error('Failed to check status:', error);
    }
  }, [encounterId, enabled, isRecording, hasTriggered]);

  // Trigger the dead man's switch
  const triggerSwitch = async () => {
    if (!encounterId) return;
    
    try {
      const response = await api.post(`/advanced/dead-mans-switch/trigger/${encounterId}`);
      
      toast.error(
        '🚨 DEAD MAN\'S SWITCH TRIGGERED! Emergency contacts notified.',
        { duration: 10000 }
      );
      
      if (onTrigger) {
        onTrigger(response.data);
      }
    } catch (error) {
      console.error('Failed to trigger switch:', error);
    }
  };

  // Disarm the switch (user is okay)
  const disarmSwitch = async () => {
    if (!encounterId) return;
    
    try {
      await api.post(`/advanced/dead-mans-switch/disarm/${encounterId}`);
      setHasTriggered(false);
      setShowWarning(false);
      setCountdown(null);
      toast.success('Dead Man\'s Switch disarmed - you\'re safe');
    } catch (error) {
      console.error('Failed to disarm switch:', error);
    }
  };

  // "I'm okay" button handler
  const handleImOkay = async () => {
    await registerActivity('confirm_okay');
    toast.success('Activity registered - timer reset');
  };

  // Set up activity detection and status checking
  useEffect(() => {
    if (!isRecording || !enabled || !encounterId) {
      clearInterval(checkIntervalRef.current);
      clearInterval(countdownIntervalRef.current);
      return;
    }

    // Register initial activity when recording starts
    registerActivity('recording_start');

    // Check status every 5 seconds
    checkIntervalRef.current = setInterval(checkStatus, 5000);

    // Register activity on user interactions
    const activityHandler = () => registerActivity('interaction');
    
    document.addEventListener('touchstart', activityHandler);
    document.addEventListener('click', activityHandler);
    document.addEventListener('keydown', activityHandler);

    return () => {
      clearInterval(checkIntervalRef.current);
      document.removeEventListener('touchstart', activityHandler);
      document.removeEventListener('click', activityHandler);
      document.removeEventListener('keydown', activityHandler);
    };
  }, [isRecording, enabled, encounterId, registerActivity, checkStatus]);

  // Countdown timer for warning state
  useEffect(() => {
    if (!showWarning || countdown === null) {
      clearInterval(countdownIntervalRef.current);
      return;
    }

    countdownIntervalRef.current = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(countdownIntervalRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(countdownIntervalRef.current);
  }, [showWarning, countdown]);

  if (!isRecording) {
    return null;
  }

  if (loading) {
    return (
      <Card className="border-orange-500/30 bg-orange-500/5">
        <CardContent className="py-4 text-center">
          <Loader2 className="h-5 w-5 animate-spin mx-auto text-orange-400" />
        </CardContent>
      </Card>
    );
  }

  // Triggered state
  if (hasTriggered) {
    return (
      <Card className="border-red-500 bg-red-500/10 animate-pulse" data-testid="dms-triggered">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2 text-red-400">
            <AlertTriangle className="h-5 w-5" />
            Emergency Alert Sent!
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Alert className="border-red-500/50 bg-red-500/20">
            <Bell className="h-4 w-4 text-red-500" />
            <AlertDescription className="text-red-300">
              Your emergency contacts have been notified. If you&apos;re safe, tap below to cancel.
            </AlertDescription>
          </Alert>
          <Button 
            className="w-full bg-green-600 hover:bg-green-700"
            onClick={disarmSwitch}
            data-testid="dms-disarm-btn"
          >
            <CheckCircle className="h-4 w-4 mr-2" />
            I&apos;m Okay - Cancel Alert
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Warning state - countdown active
  if (showWarning && countdown !== null) {
    return (
      <Card className="border-orange-500 bg-orange-500/10 animate-pulse" data-testid="dms-warning">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2 text-orange-400">
            <Timer className="h-5 w-5" />
            Are You Okay?
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="text-center">
            <div className="text-4xl font-bold text-orange-400 mb-2">
              {countdown}s
            </div>
            <Progress 
              value={(countdown / (config?.inactivity_threshold || 60)) * 100} 
              className="h-2 bg-orange-500/20"
            />
            <p className="text-sm text-orange-300 mt-2">
              Tap &quot;I&apos;m Okay&quot; or emergency contacts will be alerted
            </p>
          </div>
          <Button 
            className="w-full h-14 bg-green-600 hover:bg-green-700 text-lg"
            onClick={handleImOkay}
            data-testid="dms-okay-btn"
          >
            <Hand className="h-6 w-6 mr-2" />
            I&apos;m Okay
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Normal armed state
  return (
    <Card className="border-orange-500/30 bg-orange-500/5" data-testid="dms-panel">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Shield className="h-4 w-4 text-orange-400" />
            Dead Man&apos;s Switch
          </CardTitle>
          <div className="flex items-center gap-2">
            <Switch
              checked={enabled}
              onCheckedChange={(checked) => {
                setEnabled(checked);
                if (!checked) {
                  setShowWarning(false);
                  setCountdown(null);
                }
              }}
              id="dms-toggle"
            />
            <Badge 
              variant="outline" 
              className={enabled ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20'}
            >
              {enabled ? 'Armed' : 'Off'}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {enabled ? (
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              <span>Trigger in {config?.inactivity_threshold || 60}s of inactivity</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs"
              onClick={handleImOkay}
            >
              <CheckCircle className="h-3 w-3 mr-1" />
              Reset
            </Button>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            Enable to auto-alert contacts if you become unresponsive
          </p>
        )}
      </CardContent>
    </Card>
  );
}
