import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Shield, Brain, Users, AlertTriangle, Scale, FileText,
  Loader2, CheckCircle, XCircle, Clock, MapPin, Radio,
  Siren, Eye, Gavel, FileSearch, ChevronRight, Settings,
  Zap, Heart, Bell, Play, Copy, ExternalLink, DollarSign
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Switch } from '../components/ui/switch';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Slider } from '../components/ui/slider';
import { Label } from '../components/ui/label';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '../components/ui/dialog';
import { toast } from 'sonner';
import api, { violationAPI, legalPrecedentAPI, foiaAPI, encounterAPI } from '../lib/api';

export default function AdvancedFeaturesPage() {
  const [activeTab, setActiveTab] = useState('protection');
  const [loading, setLoading] = useState(true);
  const [dmsConfig, setDmsConfig] = useState(null);
  const [witnessStats, setWitnessStats] = useState(null);
  const [foiaRequests, setFoiaRequests] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [dmsRes, witnessRes, foiaRes] = await Promise.all([
        api.get('/advanced/dead-mans-switch/config'),
        api.get('/advanced/witness/stats'),
        api.get('/advanced/foia/my-requests')
      ]);
      setDmsConfig(dmsRes.data);
      setWitnessStats(witnessRes.data);
      setFoiaRequests(foiaRes.data.requests || []);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const updateDmsConfig = async (key, value) => {
    const newConfig = { ...dmsConfig, [key]: value };
    setDmsConfig(newConfig);
    
    setSaving(true);
    try {
      await api.put('/advanced/dead-mans-switch/config', newConfig);
      toast.success('Settings saved');
    } catch (error) {
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const enableWitnessMode = async () => {
    if (!navigator.geolocation) {
      toast.error('Geolocation not supported');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          await api.post('/advanced/witness/enable', {
            lat: position.coords.latitude,
            lng: position.coords.longitude
          });
          toast.success('Witness mode enabled!');
          fetchData();
        } catch (error) {
          toast.error('Failed to enable witness mode');
        }
      },
      (error) => {
        toast.error('Location access required for witness mode');
      }
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Zap className="h-8 w-8 text-yellow-500" />
            Advanced Features
          </h1>
          <p className="text-muted-foreground mt-1">
            Next-level protection and legal tools
          </p>
        </div>
      </div>

      {/* Feature Cards Overview */}
      <div className="grid md:grid-cols-3 gap-4">
        <Card className="border-blue-500/30 bg-gradient-to-br from-blue-500/5 to-transparent">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-xl bg-blue-500/10">
                <Brain className="h-6 w-6 text-blue-500" />
              </div>
              <div>
                <h3 className="font-semibold">AI Rights Coach</h3>
                <p className="text-sm text-muted-foreground">Real-time legal guidance</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-red-500/30 bg-gradient-to-br from-red-500/5 to-transparent">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-xl bg-red-500/10">
                <Siren className="h-6 w-6 text-red-500" />
              </div>
              <div>
                <h3 className="font-semibold">Dead Man's Switch</h3>
                <p className="text-sm text-muted-foreground">Auto emergency response</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-purple-500/30 bg-gradient-to-br from-purple-500/5 to-transparent">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-xl bg-purple-500/10">
                <Users className="h-6 w-6 text-purple-500" />
              </div>
              <div>
                <h3 className="font-semibold">Witness Network</h3>
                <p className="text-sm text-muted-foreground">{witnessStats?.reputation_score || 0} reputation</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="protection" className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Protection Features
          </TabsTrigger>
          <TabsTrigger value="legal" className="flex items-center gap-2">
            <Scale className="h-4 w-4" />
            Legal Strategy
          </TabsTrigger>
        </TabsList>

        {/* Protection Features Tab */}
        <TabsContent value="protection" className="space-y-6">
          {/* Dead Man's Switch */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-red-500/10">
                    <Siren className="h-6 w-6 text-red-500" />
                  </div>
                  <div>
                    <CardTitle>Dead Man's Switch</CardTitle>
                    <CardDescription>
                      Automatic emergency response when you become unresponsive
                    </CardDescription>
                  </div>
                </div>
                <Switch
                  checked={dmsConfig?.enabled}
                  onCheckedChange={(val) => updateDmsConfig('enabled', val)}
                />
              </div>
            </CardHeader>

            {dmsConfig?.enabled && (
              <CardContent className="space-y-6">
                {/* Inactivity Threshold */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label>Inactivity Threshold</Label>
                    <span className="text-sm font-mono bg-muted px-2 py-1 rounded">
                      {dmsConfig?.inactivity_threshold}s
                    </span>
                  </div>
                  <Slider
                    value={[dmsConfig?.inactivity_threshold || 60]}
                    onValueChange={([val]) => updateDmsConfig('inactivity_threshold', val)}
                    min={30}
                    max={120}
                    step={5}
                  />
                  <p className="text-xs text-muted-foreground">
                    Time without activity before triggering emergency protocols
                  </p>
                </div>

                {/* Warning Time */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label>Warning Time</Label>
                    <span className="text-sm font-mono bg-muted px-2 py-1 rounded">
                      {dmsConfig?.warning_time}s
                    </span>
                  </div>
                  <Slider
                    value={[dmsConfig?.warning_time || 45]}
                    onValueChange={([val]) => updateDmsConfig('warning_time', val)}
                    min={15}
                    max={60}
                    step={5}
                  />
                  <p className="text-xs text-muted-foreground">
                    When to show warning before triggering
                  </p>
                </div>

                {/* Actions */}
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="flex items-center justify-between p-3 rounded-lg border">
                    <div className="flex items-center gap-2">
                      <Radio className="h-4 w-4 text-red-500" />
                      <span>Auto Broadcast Live</span>
                    </div>
                    <Switch
                      checked={dmsConfig?.auto_broadcast}
                      onCheckedChange={(val) => updateDmsConfig('auto_broadcast', val)}
                    />
                  </div>

                  <div className="flex items-center justify-between p-3 rounded-lg border">
                    <div className="flex items-center gap-2">
                      <Bell className="h-4 w-4 text-yellow-500" />
                      <span>Alert Emergency Contacts</span>
                    </div>
                    <Switch
                      checked={dmsConfig?.notify_emergency_contacts}
                      onCheckedChange={(val) => updateDmsConfig('notify_emergency_contacts', val)}
                    />
                  </div>

                  <div className="flex items-center justify-between p-3 rounded-lg border">
                    <div className="flex items-center gap-2">
                      <Users className="h-4 w-4 text-purple-500" />
                      <span>Alert Witness Network</span>
                    </div>
                    <Switch
                      checked={dmsConfig?.notify_witness_network}
                      onCheckedChange={(val) => updateDmsConfig('notify_witness_network', val)}
                    />
                  </div>

                  <div className="flex items-center justify-between p-3 rounded-lg border">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-blue-500" />
                      <span>Force Upload Evidence</span>
                    </div>
                    <Switch
                      checked={dmsConfig?.auto_upload}
                      onCheckedChange={(val) => updateDmsConfig('auto_upload', val)}
                    />
                  </div>
                </div>
              </CardContent>
            )}
          </Card>

          {/* Witness Network */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-purple-500/10">
                    <Users className="h-6 w-6 text-purple-500" />
                  </div>
                  <div>
                    <CardTitle>Witness Network</CardTitle>
                    <CardDescription>
                      Community-based protection - get alerts when someone nearby needs witnesses
                    </CardDescription>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-4 rounded-lg bg-muted/50">
                  <div className="text-2xl font-bold">{witnessStats?.total_witnessed || 0}</div>
                  <div className="text-sm text-muted-foreground">Encounters Witnessed</div>
                </div>
                <div className="text-center p-4 rounded-lg bg-muted/50">
                  <div className="text-2xl font-bold">{witnessStats?.recordings_submitted || 0}</div>
                  <div className="text-sm text-muted-foreground">Recordings Submitted</div>
                </div>
                <div className="text-center p-4 rounded-lg bg-muted/50">
                  <div className="text-2xl font-bold">{witnessStats?.reputation_score || 0}</div>
                  <div className="text-sm text-muted-foreground">Reputation Score</div>
                </div>
              </div>

              {/* Badge */}
              {witnessStats?.badge && (
                <div className="flex items-center justify-center gap-3 p-4 rounded-lg border">
                  <Badge 
                    variant="outline" 
                    className={`text-${witnessStats.badge.color}-500 border-${witnessStats.badge.color}-500`}
                  >
                    Level {witnessStats.badge.level}
                  </Badge>
                  <span className="font-semibold">{witnessStats.badge.name}</span>
                </div>
              )}

              {/* Enable Button */}
              <Button 
                onClick={enableWitnessMode}
                className="w-full bg-purple-600 hover:bg-purple-700"
              >
                <MapPin className="h-4 w-4 mr-2" />
                Enable Witness Mode (1 mile radius)
              </Button>

              <p className="text-xs text-muted-foreground text-center">
                You'll be alerted when encounters happen within 1 mile of your location
              </p>
            </CardContent>
          </Card>

          {/* AI Rights Coach */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/10">
                  <Brain className="h-6 w-6 text-blue-500" />
                </div>
                <div>
                  <CardTitle>AI Rights Coach</CardTitle>
                  <CardDescription>
                    Real-time legal guidance during encounters - powered by GPT-5.2
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center gap-3 p-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <span>Analyzes conversation in real-time</span>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <span>Suggests legally safe responses</span>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <span>Flags potential rights violations instantly</span>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <span>Cites relevant constitutional amendments</span>
                </div>
              </div>
              <p className="text-sm text-muted-foreground mt-4">
                The AI Rights Coach activates automatically during encounters in Encounter Mode.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Legal Strategy Tab */}
        <TabsContent value="legal" className="space-y-6">
          {/* Violation Detection */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-orange-500/10">
                  <AlertTriangle className="h-6 w-6 text-orange-500" />
                </div>
                <div>
                  <CardTitle>Automatic Violation Detection</CardTitle>
                  <CardDescription>
                    AI analyzes your encounters for constitutional rights violations
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center gap-3 p-3 rounded-lg border">
                  <Scale className="h-5 w-5 text-orange-500" />
                  <div>
                    <span className="font-medium">4th Amendment Violations</span>
                    <p className="text-sm text-muted-foreground">Unreasonable searches & seizures</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg border">
                  <Scale className="h-5 w-5 text-orange-500" />
                  <div>
                    <span className="font-medium">5th Amendment Violations</span>
                    <p className="text-sm text-muted-foreground">Self-incrimination & due process</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg border">
                  <Scale className="h-5 w-5 text-orange-500" />
                  <div>
                    <span className="font-medium">Excessive Force</span>
                    <p className="text-sm text-muted-foreground">Physical force beyond what's necessary</p>
                  </div>
                </div>
              </div>
              <p className="text-sm text-muted-foreground mt-4">
                Run analysis after an encounter to get a detailed violation report with legal citations.
              </p>
            </CardContent>
          </Card>

          {/* Legal Precedent Matching */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-green-500/10">
                  <Gavel className="h-6 w-6 text-green-500" />
                </div>
                <div>
                  <CardTitle>Legal Precedent Matching</CardTitle>
                  <CardDescription>
                    Find similar successful cases and predict outcomes
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center gap-3 p-3 rounded-lg bg-green-500/5 border border-green-500/20">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <span>Matches your case to relevant legal precedents</span>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg bg-green-500/5 border border-green-500/20">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <span>Finds similar successful court cases</span>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg bg-green-500/5 border border-green-500/20">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <span>Predicts case outcome probability</span>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg bg-green-500/5 border border-green-500/20">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <span>Estimates potential case value</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* FOIA Automation */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-indigo-500/10">
                    <FileSearch className="h-6 w-6 text-indigo-500" />
                  </div>
                  <div>
                    <CardTitle>FOIA Automation</CardTitle>
                    <CardDescription>
                      One-click body cam footage requests
                    </CardDescription>
                  </div>
                </div>
                <Badge variant="secondary">{foiaRequests.length} requests</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex items-center gap-3 p-3 rounded-lg bg-indigo-500/5 border border-indigo-500/20">
                  <FileText className="h-5 w-5 text-indigo-500" />
                  <span>Auto-generates formal FOIA requests</span>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg bg-indigo-500/5 border border-indigo-500/20">
                  <Clock className="h-5 w-5 text-indigo-500" />
                  <span>Tracks deadlines and sends reminders</span>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg bg-indigo-500/5 border border-indigo-500/20">
                  <AlertTriangle className="h-5 w-5 text-indigo-500" />
                  <span>Auto-escalates if department doesn't respond</span>
                </div>
              </div>

              {/* Recent FOIA Requests */}
              {foiaRequests.length > 0 && (
                <div className="space-y-2">
                  <h4 className="font-medium">Recent Requests</h4>
                  {foiaRequests.slice(0, 3).map((req) => (
                    <div key={req.request_id} className="flex items-center justify-between p-3 rounded-lg border">
                      <div>
                        <span className="font-medium">{req.department?.name || 'Police Dept'}</span>
                        <p className="text-sm text-muted-foreground">
                          {req.overdue ? (
                            <span className="text-red-500">Overdue by {Math.abs(req.days_until_due)} days</span>
                          ) : (
                            <span>Due in {req.days_until_due} days</span>
                          )}
                        </p>
                      </div>
                      <Badge variant={req.status === 'completed' ? 'default' : 'secondary'}>
                        {req.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}

              <Button variant="outline" className="w-full">
                View All FOIA Requests
                <ChevronRight className="h-4 w-4 ml-2" />
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
