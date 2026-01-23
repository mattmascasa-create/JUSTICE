import React, { useState, useEffect } from 'react';
import { 
  Bell, BellRing, BellOff, Mail, MessageCircle, FileText, 
  Gavel, Siren, AlertTriangle, Settings, Moon, RotateCcw,
  Loader2, Check, Clock, Volume2, VolumeX
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { Input } from '../components/ui/input';
import { Separator } from '../components/ui/separator';
import { Badge } from '../components/ui/badge';
import { Slider } from '../components/ui/slider';
import { toast } from 'sonner';
import api from '../lib/api';
import { usePushNotifications } from '../hooks/usePushNotifications';
import SoundPicker from '../components/SoundPicker';
import { previewSound } from '../services/notificationSounds';

const notificationTypes = [
  { key: 'messages', soundKey: 'message', label: 'Messages', icon: MessageCircle, description: 'New messages from attorneys or contacts', color: 'text-blue-500' },
  { key: 'case_updates', soundKey: 'case_update', label: 'Case Updates', icon: FileText, description: 'Status changes and updates to your cases', color: 'text-green-500' },
  { key: 'attorney_responses', soundKey: 'attorney_response', label: 'Attorney Responses', icon: Gavel, description: 'Replies and feedback from attorneys', color: 'text-purple-500' },
  { key: 'sos_alerts', soundKey: 'sos_alert', label: 'SOS Alerts', icon: Siren, description: 'Emergency alerts (recommended to keep on)', color: 'text-red-500', critical: true },
  { key: 'warnings', soundKey: 'warning', label: 'Warnings', icon: AlertTriangle, description: 'Important warnings and action required notices', color: 'text-yellow-500' },
  { key: 'system', soundKey: 'system', label: 'System Updates', icon: Settings, description: 'Maintenance notices and system announcements', color: 'text-gray-500' },
];

export default function NotificationPreferencesPage() {
  const [preferences, setPreferences] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const { isSupported: pushSupported, isSubscribed: pushSubscribed, subscribe: enablePush } = usePushNotifications();

  useEffect(() => {
    fetchPreferences();
  }, []);

  const fetchPreferences = async () => {
    try {
      const res = await api.get('/notification-preferences');
      setPreferences(res.data);
    } catch (error) {
      console.error('Failed to fetch preferences:', error);
      toast.error('Failed to load notification preferences');
    } finally {
      setLoading(false);
    }
  };

  const updatePreference = (key, value) => {
    setPreferences(prev => ({ ...prev, [key]: value }));
  };

  const savePreferences = async () => {
    setSaving(true);
    try {
      await api.put('/notification-preferences', preferences);
      toast.success('Preferences saved!');
    } catch (error) {
      console.error('Failed to save preferences:', error);
      toast.error('Failed to save preferences');
    } finally {
      setSaving(false);
    }
  };

  const resetPreferences = async () => {
    setSaving(true);
    try {
      const res = await api.post('/notification-preferences/reset');
      setPreferences(res.data.preferences);
      toast.success('Preferences reset to defaults');
    } catch (error) {
      console.error('Failed to reset preferences:', error);
      toast.error('Failed to reset preferences');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Notification Preferences</h1>
          <p className="text-muted-foreground mt-1">
            Control how and when you receive notifications
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={resetPreferences} disabled={saving}>
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset to Defaults
          </Button>
          <Button onClick={savePreferences} disabled={saving}>
            {saving ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Check className="h-4 w-4 mr-2" />
            )}
            Save Changes
          </Button>
        </div>
      </div>

      {/* Push Notifications Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/10">
                <BellRing className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle>Push Notifications</CardTitle>
                <CardDescription>
                  Receive alerts even when the app is closed
                </CardDescription>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {!pushSupported && (
                <Badge variant="secondary">Not Supported</Badge>
              )}
              {pushSupported && !pushSubscribed && (
                <Button size="sm" variant="outline" onClick={enablePush}>
                  Enable Push
                </Button>
              )}
              {pushSupported && pushSubscribed && (
                <Badge className="bg-green-500">Active</Badge>
              )}
              <Switch
                checked={preferences?.push_enabled}
                onCheckedChange={(val) => updatePreference('push_enabled', val)}
                disabled={!pushSupported}
              />
            </div>
          </div>
        </CardHeader>
        
        {preferences?.push_enabled && (
          <CardContent className="space-y-4">
            <Separator />
            <p className="text-sm text-muted-foreground">
              Choose which notification types trigger push alerts:
            </p>
            <div className="grid gap-3">
              {notificationTypes.map((type) => (
                <div 
                  key={type.key}
                  className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <type.icon className={`h-5 w-5 ${type.color}`} />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{type.label}</span>
                        {type.critical && (
                          <Badge variant="destructive" className="text-xs">Critical</Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">{type.description}</p>
                    </div>
                  </div>
                  <Switch
                    checked={preferences?.[`push_${type.key}`]}
                    onCheckedChange={(val) => updatePreference(`push_${type.key}`, val)}
                  />
                </div>
              ))}
            </div>
          </CardContent>
        )}
      </Card>

      {/* Quiet Hours Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-indigo-500/10">
                <Moon className="h-5 w-5 text-indigo-500" />
              </div>
              <div>
                <CardTitle>Quiet Hours</CardTitle>
                <CardDescription>
                  Pause push notifications during specific hours
                </CardDescription>
              </div>
            </div>
            <Switch
              checked={preferences?.quiet_hours_enabled}
              onCheckedChange={(val) => updatePreference('quiet_hours_enabled', val)}
            />
          </div>
        </CardHeader>
        
        {preferences?.quiet_hours_enabled && (
          <CardContent className="space-y-4">
            <Separator />
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <Label>From</Label>
                <Input
                  type="time"
                  value={preferences?.quiet_hours_start || '22:00'}
                  onChange={(e) => updatePreference('quiet_hours_start', e.target.value)}
                  className="w-32"
                />
              </div>
              <span className="text-muted-foreground">to</span>
              <div className="flex items-center gap-2">
                <Label>Until</Label>
                <Input
                  type="time"
                  value={preferences?.quiet_hours_end || '08:00'}
                  onChange={(e) => updatePreference('quiet_hours_end', e.target.value)}
                  className="w-32"
                />
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              Push notifications will be silenced during these hours. 
              <span className="text-red-500 font-medium"> SOS alerts will still come through.</span>
            </p>
          </CardContent>
        )}
      </Card>

      {/* Email Notifications Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-500/10">
                <Mail className="h-5 w-5 text-blue-500" />
              </div>
              <div>
                <CardTitle>Email Notifications</CardTitle>
                <CardDescription>
                  Receive important updates via email
                </CardDescription>
              </div>
            </div>
            <Switch
              checked={preferences?.email_enabled}
              onCheckedChange={(val) => updatePreference('email_enabled', val)}
            />
          </div>
        </CardHeader>
        
        {preferences?.email_enabled && (
          <CardContent className="space-y-4">
            <Separator />
            
            {/* Daily Digest */}
            <div className="flex items-center justify-between p-3 rounded-lg border">
              <div>
                <span className="font-medium">Daily Digest</span>
                <p className="text-sm text-muted-foreground">
                  Receive a summary of all notifications once daily
                </p>
              </div>
              <Switch
                checked={preferences?.email_daily_digest}
                onCheckedChange={(val) => updatePreference('email_daily_digest', val)}
              />
            </div>
            
            <Separator />
            <p className="text-sm text-muted-foreground">
              Choose which notification types trigger emails:
            </p>
            
            <div className="grid gap-3">
              {notificationTypes.filter(t => ['case_updates', 'attorney_responses', 'sos_alerts'].includes(t.key)).map((type) => (
                <div 
                  key={type.key}
                  className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <type.icon className={`h-5 w-5 ${type.color}`} />
                    <span className="font-medium">{type.label}</span>
                  </div>
                  <Switch
                    checked={preferences?.[`email_${type.key}`]}
                    onCheckedChange={(val) => updatePreference(`email_${type.key}`, val)}
                  />
                </div>
              ))}
            </div>
          </CardContent>
        )}
      </Card>

      {/* In-App Notifications Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-500/10">
                <Bell className="h-5 w-5 text-green-500" />
              </div>
              <div>
                <CardTitle>In-App Notifications</CardTitle>
                <CardDescription>
                  Show notifications within the JUSTICE app
                </CardDescription>
              </div>
            </div>
            <Switch
              checked={preferences?.in_app_enabled}
              onCheckedChange={(val) => updatePreference('in_app_enabled', val)}
            />
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            In-app notifications appear in the notification bell and as toast messages while using the app.
            Disabling this will hide all in-app notification indicators.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
