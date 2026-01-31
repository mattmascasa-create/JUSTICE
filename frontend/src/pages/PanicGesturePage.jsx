/**
 * Panic Gesture Page
 * 
 * Configure secret gestures (shake, button presses) to instantly
 * start stealth recording when you can't safely interact with your phone.
 * 
 * Features:
 * - Gesture type selection
 * - Sensitivity configuration
 * - Test gesture functionality
 * - Auto-stealth mode
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { Alert, AlertDescription } from '../components/ui/alert';
import { ScrollArea } from '../components/ui/scroll-area';
import { RadioGroup, RadioGroupItem } from '../components/ui/radio-group';
import { toast } from 'sonner';
import api from '../lib/api';
import {
  Smartphone, Vibrate, Shield, Eye, Video, Mic,
  Users, Clock, CheckCircle, AlertTriangle, RefreshCw,
  Loader2, Zap, Volume2, Power, Hand
} from 'lucide-react';

// Panic Gesture API
const panicAPI = {
  getConfig: () => api.get('/panic-gesture/config'),
  updateConfig: (config) => api.put('/panic-gesture/config', config),
  trigger: (data) => api.post('/panic-gesture/trigger', data),
  test: () => api.post('/panic-gesture/test'),
  getPresets: () => api.get('/panic-gesture/presets'),
  getHistory: (limit) => api.get('/panic-gesture/history', { params: { limit } })
};

// Gesture icons
const gestureIcons = {
  shake: Vibrate,
  volume_triple: Volume2,
  power_triple: Power,
  squeeze: Hand
};

export default function PanicGesturePage() {
  // Config state
  const [config, setConfig] = useState({
    enabled: true,
    gesture_type: 'shake',
    sensitivity: 'medium',
    shake_threshold: 3,
    shake_duration_ms: 1000,
    auto_stealth: true,
    auto_record_video: true,
    auto_record_audio: true,
    notify_contacts: false,
    confirmation_vibrate: true,
    cooldown_seconds: 30
  });
  
  // Other state
  const [presets, setPresets] = useState([]);
  const [history, setHistory] = useState([]);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [shakeDetected, setShakeDetected] = useState(false);
  const [shakeCount, setShakeCount] = useState(0);
  
  // Loading states
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Shake detection refs
  const lastAcceleration = useRef({ x: 0, y: 0, z: 0 });
  const shakeTimerRef = useRef(null);
  const shakeCountRef = useRef(0);

  // Load data
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [configRes, presetsRes, historyRes] = await Promise.all([
        panicAPI.getConfig(),
        panicAPI.getPresets(),
        panicAPI.getHistory(10)
      ]);
      
      setConfig(configRes.data);
      setPresets(presetsRes.data.presets || []);
      setHistory(historyRes.data.triggers || []);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Shake detection
  useEffect(() => {
    if (!config.enabled || config.gesture_type !== 'shake' || !testing) return;

    const handleMotion = (event) => {
      const { accelerationIncludingGravity } = event;
      if (!accelerationIncludingGravity) return;

      const { x, y, z } = accelerationIncludingGravity;
      const last = lastAcceleration.current;
      
      const deltaX = Math.abs(x - last.x);
      const deltaY = Math.abs(y - last.y);
      const deltaZ = Math.abs(z - last.z);
      
      // Threshold based on sensitivity
      const thresholds = { low: 25, medium: 15, high: 10 };
      const threshold = thresholds[config.sensitivity] || 15;
      
      if (deltaX + deltaY + deltaZ > threshold) {
        shakeCountRef.current += 1;
        setShakeCount(shakeCountRef.current);
        
        // Reset shake count after duration
        if (shakeTimerRef.current) clearTimeout(shakeTimerRef.current);
        shakeTimerRef.current = setTimeout(() => {
          shakeCountRef.current = 0;
          setShakeCount(0);
        }, config.shake_duration_ms);
        
        // Check if threshold reached
        if (shakeCountRef.current >= config.shake_threshold) {
          setShakeDetected(true);
          setTestResult({ success: true, message: 'Shake detected!' });
          
          // Vibrate if supported
          if (config.confirmation_vibrate && navigator.vibrate) {
            navigator.vibrate([100, 50, 100]);
          }
          
          // Reset
          shakeCountRef.current = 0;
          setShakeCount(0);
        }
      }
      
      lastAcceleration.current = { x, y, z };
    };

    // Request permission on iOS
    if (typeof DeviceMotionEvent !== 'undefined' && typeof DeviceMotionEvent.requestPermission === 'function') {
      DeviceMotionEvent.requestPermission()
        .then(permission => {
          if (permission === 'granted') {
            window.addEventListener('devicemotion', handleMotion);
          }
        })
        .catch(console.error);
    } else {
      window.addEventListener('devicemotion', handleMotion);
    }

    return () => {
      window.removeEventListener('devicemotion', handleMotion);
      if (shakeTimerRef.current) clearTimeout(shakeTimerRef.current);
    };
  }, [config, testing]);

  // Save config
  const saveConfig = async () => {
    try {
      setSaving(true);
      await panicAPI.updateConfig(config);
      toast.success('Settings saved');
    } catch (error) {
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  // Test gesture
  const startTest = () => {
    setTesting(true);
    setTestResult(null);
    setShakeDetected(false);
    setShakeCount(0);
    shakeCountRef.current = 0;
    
    toast.info(`Testing ${config.gesture_type} gesture. Try it now!`);
    
    // Auto-end test after 10 seconds
    setTimeout(() => {
      setTesting(false);
      if (!testResult) {
        setTestResult({ success: false, message: 'No gesture detected. Try again or adjust sensitivity.' });
      }
    }, 10000);
  };

  // Manual trigger for testing
  const manualTrigger = async () => {
    try {
      // Get location if available
      let location = null;
      if (navigator.geolocation) {
        try {
          const pos = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 });
          });
          location = { latitude: pos.coords.latitude, longitude: pos.coords.longitude };
        } catch (e) {
          // Location not available
        }
      }

      const response = await panicAPI.trigger({
        gesture_type: config.gesture_type,
        trigger_source: 'manual_test',
        ...location
      });

      toast.success('Panic recording started!', {
        description: `Encounter ID: ${response.data.encounter_id}`
      });
    } catch (error) {
      toast.error(error.response?.data?.message || 'Failed to trigger panic recording');
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppLayout>
    );
  }

  const selectedPreset = presets.find(p => p.id === config.gesture_type);

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-6" data-testid="panic-gesture-page">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center p-4 rounded-full bg-orange-500/20">
            <Vibrate className="h-12 w-12 text-orange-500" />
          </div>
          <h1 className="text-3xl font-bold">Panic Gesture</h1>
          <p className="text-muted-foreground max-w-lg mx-auto">
            A secret gesture to start stealth recording when you cannot safely use your phone.
            <strong> Your hidden safety net.</strong>
          </p>
        </div>

        {/* Main Toggle */}
        <Card className={config.enabled ? 'border-2 border-green-500/30 bg-green-500/5' : ''}>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-full ${config.enabled ? 'bg-green-500/20' : 'bg-muted'}`}>
                  <Shield className={`h-6 w-6 ${config.enabled ? 'text-green-500' : 'text-muted-foreground'}`} />
                </div>
                <div>
                  <h3 className="font-bold text-lg">Panic Gesture Protection</h3>
                  <p className="text-sm text-muted-foreground">
                    {config.enabled ? 'Active - your secret gesture is ready' : 'Disabled - enable to protect yourself'}
                  </p>
                </div>
              </div>
              <Switch
                checked={config.enabled}
                onCheckedChange={(enabled) => setConfig(c => ({ ...c, enabled }))}
                className="scale-125"
                data-testid="panic-enable-toggle"
              />
            </div>
          </CardContent>
        </Card>

        {/* Gesture Selection */}
        <Card>
          <CardHeader>
            <CardTitle>Select Your Gesture</CardTitle>
            <CardDescription>Choose a secret gesture to trigger emergency recording</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <RadioGroup
              value={config.gesture_type}
              onValueChange={(gesture_type) => setConfig(c => ({ ...c, gesture_type }))}
            >
              <div className="grid md:grid-cols-2 gap-3">
                {presets.map((preset) => {
                  const Icon = gestureIcons[preset.id] || Vibrate;
                  const isSelected = config.gesture_type === preset.id;
                  return (
                    <label
                      key={preset.id}
                      className={`flex items-start gap-3 p-4 rounded-lg border cursor-pointer transition-all ${
                        isSelected ? 'border-primary bg-primary/10' : 'hover:bg-muted/50'
                      }`}
                    >
                      <RadioGroupItem value={preset.id} className="mt-1" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-2xl">{preset.icon}</span>
                          <span className="font-medium">{preset.name}</span>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">{preset.description}</p>
                        {preset.platform_note && (
                          <p className="text-xs text-yellow-500 mt-1">{preset.platform_note}</p>
                        )}
                      </div>
                    </label>
                  );
                })}
              </div>
            </RadioGroup>

            {/* Sensitivity */}
            {selectedPreset && (
              <div className="space-y-2 pt-4 border-t">
                <Label>Sensitivity</Label>
                <RadioGroup
                  value={config.sensitivity}
                  onValueChange={(sensitivity) => setConfig(c => ({ ...c, sensitivity }))}
                  className="flex gap-4"
                >
                  {['low', 'medium', 'high'].map((level) => (
                    <label key={level} className="flex items-center gap-2 cursor-pointer">
                      <RadioGroupItem value={level} />
                      <span className="capitalize">{level}</span>
                    </label>
                  ))}
                </RadioGroup>
                <p className="text-xs text-muted-foreground">
                  Higher sensitivity = easier to trigger (may have false positives)
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Test Area */}
        <Card className={testing ? 'border-2 border-yellow-500/50 animate-pulse' : ''}>
          <CardHeader>
            <CardTitle>Test Your Gesture</CardTitle>
            <CardDescription>Make sure your gesture works before you need it</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {testing ? (
              <div className="text-center py-6 space-y-4">
                <div className="inline-flex items-center justify-center p-4 rounded-full bg-yellow-500/20 animate-bounce">
                  {React.createElement(gestureIcons[config.gesture_type] || Vibrate, {
                    className: "h-12 w-12 text-yellow-500"
                  })}
                </div>
                <p className="font-medium text-yellow-500">
                  Testing... Try the {selectedPreset?.name || 'gesture'} now!
                </p>
                <p className="text-sm text-muted-foreground">
                  Shakes detected: {shakeCount} / {config.shake_threshold}
                </p>
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className="bg-yellow-500 h-2 rounded-full transition-all"
                    style={{ width: `${Math.min(100, (shakeCount / config.shake_threshold) * 100)}%` }}
                  />
                </div>
                <Button variant="outline" onClick={() => setTesting(false)}>
                  Cancel Test
                </Button>
              </div>
            ) : testResult ? (
              <Alert className={testResult.success ? 'bg-green-500/10 border-green-500/30' : 'bg-red-500/10 border-red-500/30'}>
                {testResult.success ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : (
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                )}
                <AlertDescription className={testResult.success ? 'text-green-500' : 'text-red-500'}>
                  {testResult.message}
                </AlertDescription>
              </Alert>
            ) : null}

            <div className="flex gap-3">
              <Button onClick={startTest} disabled={testing} className="flex-1">
                <Vibrate className="h-4 w-4 mr-2" />
                {testing ? 'Testing...' : 'Start Test'}
              </Button>
              <Button variant="outline" onClick={manualTrigger}>
                <Zap className="h-4 w-4 mr-2" />
                Manual Trigger
              </Button>
            </div>

            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Manual trigger will actually start an encounter in stealth mode. Use for testing only.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>

        {/* Auto Actions */}
        <Card>
          <CardHeader>
            <CardTitle>When Triggered</CardTitle>
            <CardDescription>What happens when your panic gesture is detected</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-2 gap-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div className="flex items-center gap-2">
                  <Eye className="h-5 w-5 text-purple-500" />
                  <span>Stealth Mode</span>
                </div>
                <Switch
                  checked={config.auto_stealth}
                  onCheckedChange={(auto_stealth) => setConfig(c => ({ ...c, auto_stealth }))}
                />
              </div>
              
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div className="flex items-center gap-2">
                  <Video className="h-5 w-5 text-blue-500" />
                  <span>Record Video</span>
                </div>
                <Switch
                  checked={config.auto_record_video}
                  onCheckedChange={(auto_record_video) => setConfig(c => ({ ...c, auto_record_video }))}
                />
              </div>
              
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div className="flex items-center gap-2">
                  <Mic className="h-5 w-5 text-green-500" />
                  <span>Record Audio</span>
                </div>
                <Switch
                  checked={config.auto_record_audio}
                  onCheckedChange={(auto_record_audio) => setConfig(c => ({ ...c, auto_record_audio }))}
                />
              </div>
              
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div className="flex items-center gap-2">
                  <Users className="h-5 w-5 text-red-500" />
                  <span>Notify Contacts</span>
                </div>
                <Switch
                  checked={config.notify_contacts}
                  onCheckedChange={(notify_contacts) => setConfig(c => ({ ...c, notify_contacts }))}
                />
              </div>
              
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div className="flex items-center gap-2">
                  <Vibrate className="h-5 w-5 text-yellow-500" />
                  <span>Vibrate to Confirm</span>
                </div>
                <Switch
                  checked={config.confirmation_vibrate}
                  onCheckedChange={(confirmation_vibrate) => setConfig(c => ({ ...c, confirmation_vibrate }))}
                />
              </div>
              
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div className="flex items-center gap-2">
                  <Clock className="h-5 w-5 text-gray-500" />
                  <span>Cooldown: {config.cooldown_seconds}s</span>
                </div>
              </div>
            </div>

            <Button onClick={saveConfig} disabled={saving} className="w-full">
              {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Save Settings
            </Button>
          </CardContent>
        </Card>

        {/* History */}
        {history.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Trigger History</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[200px]">
                <div className="space-y-2">
                  {history.map((trigger) => (
                    <div key={trigger.trigger_id} className="flex items-center justify-between p-3 rounded-lg border">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-orange-500" />
                        <span className="text-sm capitalize">{trigger.gesture_type} triggered</span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {new Date(trigger.triggered_at).toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        )}
      </div>
    </AppLayout>
  );
}
