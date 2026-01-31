/**
 * Dead Man's Switch Page
 * 
 * Safety-critical feature that automatically publishes evidence
 * if the user fails to check in during an active encounter.
 * 
 * Features:
 * - Trusted contacts management
 * - Auto-publish configuration
 * - Visual check-in timer with countdown
 * - Emergency trigger button
 */

import React, { useState, useEffect, useCallback } from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Badge } from '../components/ui/badge';
import { Alert, AlertDescription } from '../components/ui/alert';
import { ScrollArea } from '../components/ui/scroll-area';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Slider } from '../components/ui/slider';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';
import api from '../lib/api';
import {
  Shield, Clock, Users, Plus, Trash2, AlertTriangle,
  CheckCircle, Phone, Mail, Timer, Heart, Zap, X,
  RefreshCw, Play, Square, Bell, Lock, Loader2
} from 'lucide-react';

// Dead Man's Switch API
const deadMansSwitchAPI = {
  getConfig: () => api.get('/dead-mans-switch/config'),
  updateConfig: (config) => api.put('/dead-mans-switch/config', config),
  getContacts: () => api.get('/dead-mans-switch/contacts'),
  addContact: (contact) => api.post('/dead-mans-switch/contacts', contact),
  removeContact: (id) => api.delete(`/dead-mans-switch/contacts/${id}`),
  startSession: (encounterId) => api.post(`/dead-mans-switch/start-session?encounter_id=${encounterId}`),
  endSession: () => api.post('/dead-mans-switch/end-session'),
  checkIn: (data) => api.post('/dead-mans-switch/check-in', data),
  getStatus: () => api.get('/dead-mans-switch/status'),
  triggerEmergency: (encounterId) => api.post(`/dead-mans-switch/trigger/${encounterId}`),
  getHistory: () => api.get('/dead-mans-switch/history')
};

export default function DeadMansSwitchPage() {
  // Config state
  const [config, setConfig] = useState({
    enabled: false,
    check_in_interval_minutes: 15,
    grace_period_minutes: 5,
    auto_publish_to_contacts: true,
    auto_publish_to_cloud: true,
    auto_notify_attorney: true,
    secret_disable_phrase: ''
  });
  
  // Contacts state
  const [contacts, setContacts] = useState([]);
  const [showAddContact, setShowAddContact] = useState(false);
  const [newContact, setNewContact] = useState({
    name: '',
    email: '',
    phone: '',
    relationship: 'emergency_contact',
    notify_methods: ['email']
  });
  
  // Session state
  const [sessionStatus, setSessionStatus] = useState(null);
  const [countdown, setCountdown] = useState(null);
  
  // Loading states
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [addingContact, setAddingContact] = useState(false);

  // Load data
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [configRes, contactsRes, statusRes] = await Promise.all([
        deadMansSwitchAPI.getConfig(),
        deadMansSwitchAPI.getContacts(),
        deadMansSwitchAPI.getStatus()
      ]);
      
      setConfig(configRes.data);
      setContacts(contactsRes.data.contacts || []);
      setSessionStatus(statusRes.data);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Countdown timer
  useEffect(() => {
    if (!sessionStatus?.active) {
      setCountdown(null);
      return;
    }

    const updateCountdown = () => {
      const secondsLeft = sessionStatus.seconds_until_deadline;
      setCountdown(secondsLeft);
    };

    updateCountdown();
    const interval = setInterval(() => {
      setCountdown(prev => prev !== null ? Math.max(0, prev - 1) : null);
    }, 1000);

    return () => clearInterval(interval);
  }, [sessionStatus]);

  // Refresh status periodically when active
  useEffect(() => {
    if (!sessionStatus?.active) return;

    const interval = setInterval(async () => {
      try {
        const res = await deadMansSwitchAPI.getStatus();
        setSessionStatus(res.data);
      } catch (error) {
        console.error('Status refresh error:', error);
      }
    }, 30000); // Every 30 seconds

    return () => clearInterval(interval);
  }, [sessionStatus?.active]);

  // Save config
  const saveConfig = async () => {
    try {
      setSaving(true);
      await deadMansSwitchAPI.updateConfig(config);
      toast.success('Configuration saved');
    } catch (error) {
      toast.error('Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  // Add contact
  const handleAddContact = async () => {
    if (!newContact.name || !newContact.email) {
      toast.error('Name and email are required');
      return;
    }

    try {
      setAddingContact(true);
      await deadMansSwitchAPI.addContact(newContact);
      toast.success(`Added ${newContact.name} as trusted contact`);
      setShowAddContact(false);
      setNewContact({
        name: '',
        email: '',
        phone: '',
        relationship: 'emergency_contact',
        notify_methods: ['email']
      });
      loadData();
    } catch (error) {
      toast.error('Failed to add contact');
    } finally {
      setAddingContact(false);
    }
  };

  // Remove contact
  const handleRemoveContact = async (contactId, contactName) => {
    if (!window.confirm(`Remove ${contactName} from trusted contacts?`)) return;

    try {
      await deadMansSwitchAPI.removeContact(contactId);
      toast.success('Contact removed');
      loadData();
    } catch (error) {
      toast.error('Failed to remove contact');
    }
  };

  // Check in
  const handleCheckIn = async () => {
    try {
      const res = await deadMansSwitchAPI.checkIn({ status: 'ok' });
      toast.success(res.data.message);
      loadData();
    } catch (error) {
      toast.error('Check-in failed');
    }
  };

  // Format countdown
  const formatCountdown = (seconds) => {
    if (seconds === null) return '--:--';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
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

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-6" data-testid="dead-mans-switch-page">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center p-4 rounded-full bg-red-500/20">
            <Shield className="h-12 w-12 text-red-500" />
          </div>
          <h1 className="text-3xl font-bold">Dead Man's Switch</h1>
          <p className="text-muted-foreground max-w-lg mx-auto">
            If you don't check in during an encounter, your evidence is automatically
            sent to trusted contacts. <strong>Your safety backup plan.</strong>
          </p>
        </div>

        {/* Active Session Status */}
        {sessionStatus?.active && (
          <Card className="border-2 border-red-500/50 bg-red-500/5">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <div className="h-3 w-3 rounded-full bg-red-500 animate-pulse" />
                    <span className="font-bold text-red-500">SWITCH ACTIVE</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {sessionStatus.contacts_to_notify} contacts will be notified if you don't check in
                  </p>
                </div>
                
                <div className="text-center">
                  <div className={`text-4xl font-mono font-bold ${
                    countdown !== null && countdown < 120 ? 'text-red-500 animate-pulse' : ''
                  }`}>
                    {formatCountdown(countdown)}
                  </div>
                  <p className="text-xs text-muted-foreground">until check-in required</p>
                </div>
                
                <Button
                  size="lg"
                  className="bg-green-500 hover:bg-green-600"
                  onClick={handleCheckIn}
                >
                  <CheckCircle className="h-5 w-5 mr-2" />
                  I'm OK - Check In
                </Button>
              </div>
              
              {countdown !== null && countdown < 120 && (
                <Alert className="mt-4 bg-red-500/20 border-red-500/50">
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                  <AlertDescription className="text-red-500">
                    <strong>Warning:</strong> Check in soon or emergency alerts will be sent!
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        )}

        {/* Configuration */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Timer className="h-5 w-5" />
                  Configuration
                </CardTitle>
                <CardDescription>
                  Set up how the Dead Man's Switch behaves
                </CardDescription>
              </div>
              <Switch
                checked={config.enabled}
                onCheckedChange={(enabled) => setConfig(c => ({ ...c, enabled }))}
                data-testid="dms-enable-toggle"
              />
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Check-in Interval */}
            <div className="space-y-2">
              <Label>Check-in Interval: {config.check_in_interval_minutes} minutes</Label>
              <Slider
                value={[config.check_in_interval_minutes]}
                onValueChange={([v]) => setConfig(c => ({ ...c, check_in_interval_minutes: v }))}
                min={5}
                max={60}
                step={5}
              />
              <p className="text-xs text-muted-foreground">
                How often you need to check in during an encounter
              </p>
            </div>

            {/* Grace Period */}
            <div className="space-y-2">
              <Label>Grace Period: {config.grace_period_minutes} minutes</Label>
              <Slider
                value={[config.grace_period_minutes]}
                onValueChange={([v]) => setConfig(c => ({ ...c, grace_period_minutes: v }))}
                min={1}
                max={15}
                step={1}
              />
              <p className="text-xs text-muted-foreground">
                Extra time after deadline before alerts are sent
              </p>
            </div>

            {/* Auto-actions */}
            <div className="space-y-3">
              <Label>When Triggered:</Label>
              
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-blue-500" />
                  <span className="text-sm">Notify trusted contacts</span>
                </div>
                <Switch
                  checked={config.auto_publish_to_contacts}
                  onCheckedChange={(v) => setConfig(c => ({ ...c, auto_publish_to_contacts: v }))}
                />
              </div>
              
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-yellow-500" />
                  <span className="text-sm">Auto-publish evidence to cloud</span>
                </div>
                <Switch
                  checked={config.auto_publish_to_cloud}
                  onCheckedChange={(v) => setConfig(c => ({ ...c, auto_publish_to_cloud: v }))}
                />
              </div>
              
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div className="flex items-center gap-2">
                  <Heart className="h-4 w-4 text-purple-500" />
                  <span className="text-sm">Alert my attorney</span>
                </div>
                <Switch
                  checked={config.auto_notify_attorney}
                  onCheckedChange={(v) => setConfig(c => ({ ...c, auto_notify_attorney: v }))}
                />
              </div>
            </div>

            {/* Secret Phrase */}
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Lock className="h-4 w-4" />
                Secret Disable Phrase (optional)
              </Label>
              <Input
                type="password"
                placeholder="A phrase only you know to cancel alerts"
                value={config.secret_disable_phrase || ''}
                onChange={(e) => setConfig(c => ({ ...c, secret_disable_phrase: e.target.value }))}
              />
              <p className="text-xs text-muted-foreground">
                If set, you'll need this phrase to cancel an impending trigger
              </p>
            </div>

            <Button onClick={saveConfig} disabled={saving} className="w-full">
              {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Save Configuration
            </Button>
          </CardContent>
        </Card>

        {/* Trusted Contacts */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  Trusted Contacts ({contacts.length})
                </CardTitle>
                <CardDescription>
                  These people will be notified if the switch triggers
                </CardDescription>
              </div>
              <Dialog open={showAddContact} onOpenChange={setShowAddContact}>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="h-4 w-4 mr-2" />
                    Add Contact
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Add Trusted Contact</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label>Name *</Label>
                      <Input
                        placeholder="John Doe"
                        value={newContact.name}
                        onChange={(e) => setNewContact(c => ({ ...c, name: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Email *</Label>
                      <Input
                        type="email"
                        placeholder="john@example.com"
                        value={newContact.email}
                        onChange={(e) => setNewContact(c => ({ ...c, email: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Phone (for SMS)</Label>
                      <Input
                        type="tel"
                        placeholder="+1234567890"
                        value={newContact.phone}
                        onChange={(e) => setNewContact(c => ({ ...c, phone: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Relationship</Label>
                      <Select
                        value={newContact.relationship}
                        onValueChange={(v) => setNewContact(c => ({ ...c, relationship: v }))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="emergency_contact">Emergency Contact</SelectItem>
                          <SelectItem value="attorney">Attorney</SelectItem>
                          <SelectItem value="family">Family Member</SelectItem>
                          <SelectItem value="friend">Friend</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Notify Via</Label>
                      <div className="flex gap-2">
                        <Button
                          type="button"
                          variant={newContact.notify_methods.includes('email') ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => {
                            const methods = newContact.notify_methods.includes('email')
                              ? newContact.notify_methods.filter(m => m !== 'email')
                              : [...newContact.notify_methods, 'email'];
                            setNewContact(c => ({ ...c, notify_methods: methods }));
                          }}
                        >
                          <Mail className="h-4 w-4 mr-1" /> Email
                        </Button>
                        <Button
                          type="button"
                          variant={newContact.notify_methods.includes('sms') ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => {
                            const methods = newContact.notify_methods.includes('sms')
                              ? newContact.notify_methods.filter(m => m !== 'sms')
                              : [...newContact.notify_methods, 'sms'];
                            setNewContact(c => ({ ...c, notify_methods: methods }));
                          }}
                        >
                          <Phone className="h-4 w-4 mr-1" /> SMS
                        </Button>
                      </div>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setShowAddContact(false)}>Cancel</Button>
                    <Button onClick={handleAddContact} disabled={addingContact}>
                      {addingContact ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                      Add Contact
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          </CardHeader>
          <CardContent>
            {contacts.length > 0 ? (
              <ScrollArea className="h-[250px]">
                <div className="space-y-2">
                  {contacts.map((contact) => (
                    <div
                      key={contact.contact_id}
                      className="flex items-center justify-between p-3 rounded-lg border"
                    >
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                          <Users className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <p className="font-medium">{contact.name}</p>
                          <p className="text-sm text-muted-foreground">{contact.email}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{contact.relationship}</Badge>
                        <div className="flex gap-1">
                          {contact.notify_methods?.includes('email') && (
                            <Mail className="h-4 w-4 text-muted-foreground" />
                          )}
                          {contact.notify_methods?.includes('sms') && (
                            <Phone className="h-4 w-4 text-muted-foreground" />
                          )}
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-red-500 hover:text-red-600"
                          onClick={() => handleRemoveContact(contact.contact_id, contact.name)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            ) : (
              <div className="text-center py-8">
                <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="font-medium">No trusted contacts yet</p>
                <p className="text-sm text-muted-foreground mb-4">
                  Add people who should be notified in an emergency
                </p>
                <Button onClick={() => setShowAddContact(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Your First Contact
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* How It Works */}
        <Card>
          <CardHeader>
            <CardTitle>How It Works</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-3 gap-4">
              <div className="text-center p-4 rounded-lg bg-muted/50">
                <div className="h-12 w-12 rounded-full bg-blue-500/20 flex items-center justify-center mx-auto mb-3">
                  <Play className="h-6 w-6 text-blue-500" />
                </div>
                <h4 className="font-medium mb-1">1. Start Encounter</h4>
                <p className="text-sm text-muted-foreground">
                  When you start recording, the switch activates automatically
                </p>
              </div>
              
              <div className="text-center p-4 rounded-lg bg-muted/50">
                <div className="h-12 w-12 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-3">
                  <CheckCircle className="h-6 w-6 text-green-500" />
                </div>
                <h4 className="font-medium mb-1">2. Check In</h4>
                <p className="text-sm text-muted-foreground">
                  Tap "I'm OK" every {config.check_in_interval_minutes} minutes to reset the timer
                </p>
              </div>
              
              <div className="text-center p-4 rounded-lg bg-muted/50">
                <div className="h-12 w-12 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-3">
                  <Bell className="h-6 w-6 text-red-500" />
                </div>
                <h4 className="font-medium mb-1">3. Auto-Alert</h4>
                <p className="text-sm text-muted-foreground">
                  If you miss a check-in, contacts are notified and evidence is preserved
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}
