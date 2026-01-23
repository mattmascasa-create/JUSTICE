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
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('protection');
  const [loading, setLoading] = useState(true);
  const [dmsConfig, setDmsConfig] = useState(null);
  const [witnessStats, setWitnessStats] = useState(null);
  const [foiaRequests, setFoiaRequests] = useState([]);
  const [saving, setSaving] = useState(false);
  
  // Encounters for analysis
  const [encounters, setEncounters] = useState([]);
  const [selectedEncounter, setSelectedEncounter] = useState('');
  
  // Violation Analysis State
  const [analyzingViolations, setAnalyzingViolations] = useState(false);
  const [violationAnalysis, setViolationAnalysis] = useState(null);
  
  // Legal Precedent State
  const [searchingPrecedents, setSearchingPrecedents] = useState(false);
  const [precedentResults, setPrecedentResults] = useState(null);
  
  // Case Value Estimation State
  const [estimatingValue, setEstimatingValue] = useState(false);
  const [valueEstimate, setValueEstimate] = useState(null);
  const [caseFactors, setCaseFactors] = useState({
    hasInjury: false,
    hasArrest: false,
    hasVideo: true
  });
  
  // FOIA State
  const [generatingFoia, setGeneratingFoia] = useState(false);
  const [foiaDialogOpen, setFoiaDialogOpen] = useState(false);
  const [generatedFoia, setGeneratedFoia] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [dmsRes, witnessRes, foiaRes, encountersRes] = await Promise.all([
        api.get('/advanced/dead-mans-switch/config'),
        api.get('/advanced/witness/stats'),
        api.get('/advanced/foia/my-requests'),
        encounterAPI.list('completed').catch(() => ({ data: [] }))
      ]);
      setDmsConfig(dmsRes.data);
      setWitnessStats(witnessRes.data);
      setFoiaRequests(foiaRes.data.requests || []);
      setEncounters(encountersRes.data || []);
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

  // Analyze encounter for violations
  const analyzeViolations = async () => {
    if (!selectedEncounter) {
      toast.error('Please select an encounter first');
      return;
    }
    
    setAnalyzingViolations(true);
    setViolationAnalysis(null);
    
    try {
      const encounter = encounters.find(e => e.encounter_id === selectedEncounter);
      const transcript = encounter?.transcript || 'No transcript available';
      
      const response = await violationAPI.analyze(
        selectedEncounter,
        transcript,
        encounter?.encounter_type || 'general'
      );
      
      setViolationAnalysis(response.data);
      toast.success('Violation analysis complete!');
    } catch (error) {
      console.error('Violation analysis error:', error);
      toast.error('Failed to analyze violations');
    } finally {
      setAnalyzingViolations(false);
    }
  };

  // Search legal precedents
  const searchPrecedents = async () => {
    if (!selectedEncounter) {
      toast.error('Please select an encounter first');
      return;
    }
    
    if (!violationAnalysis?.violations?.length) {
      toast.error('Please run violation analysis first');
      return;
    }
    
    setSearchingPrecedents(true);
    setPrecedentResults(null);
    
    try {
      const encounter = encounters.find(e => e.encounter_id === selectedEncounter);
      const transcript = encounter?.transcript || '';
      
      const response = await legalPrecedentAPI.searchPrecedents(
        selectedEncounter,
        violationAnalysis.violations,
        transcript,
        encounter?.encounter_type || 'general'
      );
      
      setPrecedentResults(response.data);
      toast.success('Legal precedents found!');
    } catch (error) {
      console.error('Precedent search error:', error);
      toast.error('Failed to search precedents');
    } finally {
      setSearchingPrecedents(false);
    }
  };

  // Estimate case value
  const estimateCaseValue = async () => {
    if (!violationAnalysis?.violations?.length) {
      toast.error('Please run violation analysis first');
      return;
    }
    
    setEstimatingValue(true);
    setValueEstimate(null);
    
    try {
      const response = await legalPrecedentAPI.estimateValue(
        violationAnalysis.violations,
        caseFactors.hasInjury,
        caseFactors.hasArrest,
        caseFactors.hasVideo
      );
      
      setValueEstimate(response.data);
      toast.success('Case value estimated!');
    } catch (error) {
      console.error('Value estimation error:', error);
      toast.error('Failed to estimate case value');
    } finally {
      setEstimatingValue(false);
    }
  };

  // Generate FOIA request
  const generateFoiaRequest = async () => {
    if (!selectedEncounter) {
      toast.error('Please select an encounter first');
      return;
    }
    
    setGeneratingFoia(true);
    setGeneratedFoia(null);
    
    try {
      const response = await foiaAPI.generate(selectedEncounter);
      setGeneratedFoia(response.data);
      setFoiaDialogOpen(true);
      toast.success('FOIA request generated!');
      fetchData(); // Refresh FOIA requests list
    } catch (error) {
      console.error('FOIA generation error:', error);
      toast.error('Failed to generate FOIA request');
    } finally {
      setGeneratingFoia(false);
    }
  };

  // Copy FOIA to clipboard
  const copyFoiaToClipboard = () => {
    if (generatedFoia?.request_text) {
      navigator.clipboard.writeText(generatedFoia.request_text);
      toast.success('FOIA request copied to clipboard!');
    }
  };

  // Mark FOIA as submitted
  const markFoiaSubmitted = async (requestId, method) => {
    try {
      await foiaAPI.submit(requestId, method);
      toast.success('FOIA marked as submitted!');
      setFoiaDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error('Failed to mark as submitted');
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
          {/* Encounter Selection */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Eye className="h-5 w-5" />
                Select Encounter for Analysis
              </CardTitle>
              <CardDescription>
                Choose a completed encounter to analyze for violations and build your case
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Select value={selectedEncounter} onValueChange={setSelectedEncounter}>
                <SelectTrigger data-testid="encounter-select">
                  <SelectValue placeholder="Select an encounter..." />
                </SelectTrigger>
                <SelectContent>
                  {encounters.length === 0 ? (
                    <SelectItem value="none" disabled>No completed encounters</SelectItem>
                  ) : (
                    encounters.map((enc) => (
                      <SelectItem key={enc.encounter_id} value={enc.encounter_id}>
                        {enc.encounter_type} - {new Date(enc.started_at).toLocaleDateString()}
                        {enc.location?.address && ` (${enc.location.address.substring(0, 30)}...)`}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
              
              {encounters.length === 0 && (
                <div className="mt-4 p-4 rounded-lg bg-muted text-center">
                  <p className="text-sm text-muted-foreground">
                    No completed encounters found. Start a new encounter in{' '}
                    <Button variant="link" className="p-0 h-auto" onClick={() => navigate('/encounter')}>
                      Encounter Mode
                    </Button>
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Violation Detection */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
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
                <Button 
                  onClick={analyzeViolations}
                  disabled={!selectedEncounter || analyzingViolations}
                  data-testid="analyze-violations-btn"
                >
                  {analyzingViolations ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 mr-2" />
                      Analyze
                    </>
                  )}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Amendment Types */}
              <div className="grid md:grid-cols-3 gap-3">
                <div className="flex items-center gap-3 p-3 rounded-lg border">
                  <Scale className="h-5 w-5 text-orange-500" />
                  <div>
                    <span className="font-medium text-sm">4th Amendment</span>
                    <p className="text-xs text-muted-foreground">Searches & seizures</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg border">
                  <Scale className="h-5 w-5 text-orange-500" />
                  <div>
                    <span className="font-medium text-sm">5th Amendment</span>
                    <p className="text-xs text-muted-foreground">Self-incrimination</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg border">
                  <Scale className="h-5 w-5 text-orange-500" />
                  <div>
                    <span className="font-medium text-sm">14th Amendment</span>
                    <p className="text-xs text-muted-foreground">Equal protection</p>
                  </div>
                </div>
              </div>

              {/* Violation Analysis Results */}
              {violationAnalysis && (
                <div className="space-y-4 mt-4 p-4 rounded-lg border bg-muted/30">
                  <div className="flex items-center justify-between">
                    <h4 className="font-semibold flex items-center gap-2">
                      <CheckCircle className="h-5 w-5 text-green-500" />
                      Analysis Complete
                    </h4>
                    <Badge variant={violationAnalysis.violations?.length > 0 ? 'destructive' : 'default'}>
                      {violationAnalysis.violations?.length || 0} Violations Found
                    </Badge>
                  </div>
                  
                  {violationAnalysis.violations?.length > 0 ? (
                    <div className="space-y-3">
                      {violationAnalysis.violations.map((violation, idx) => (
                        <div key={idx} className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium text-red-600">{violation.violation_type}</span>
                            <Badge variant="outline" className="text-red-500 border-red-500">
                              Severity: {violation.severity}/10
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground mb-2">{violation.explanation}</p>
                          {violation.case_law?.length > 0 && (
                            <div className="text-xs text-muted-foreground">
                              <span className="font-medium">Relevant Cases:</span> {violation.case_law.join(', ')}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No constitutional violations detected in this encounter.</p>
                  )}

                  {violationAnalysis.recommendations && (
                    <div className="pt-3 border-t">
                      <h5 className="font-medium mb-2">Recommendations</h5>
                      <p className="text-sm">{violationAnalysis.summary}</p>
                      {violationAnalysis.recommendations.immediate_actions?.length > 0 && (
                        <ul className="mt-2 space-y-1">
                          {violationAnalysis.recommendations.immediate_actions.map((action, idx) => (
                            <li key={idx} className="text-sm flex items-center gap-2">
                              <ChevronRight className="h-3 w-3" />
                              {action}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Legal Precedent Matching */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
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
                <Button 
                  onClick={searchPrecedents}
                  disabled={!violationAnalysis?.violations?.length || searchingPrecedents}
                  data-testid="search-precedents-btn"
                >
                  {searchingPrecedents ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Searching...
                    </>
                  ) : (
                    <>
                      <FileSearch className="h-4 w-4 mr-2" />
                      Find Precedents
                    </>
                  )}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {!violationAnalysis?.violations?.length && (
                <p className="text-sm text-muted-foreground text-center p-4 bg-muted rounded-lg">
                  Run violation analysis first to search for matching legal precedents
                </p>
              )}

              {/* Precedent Results */}
              {precedentResults && (
                <div className="space-y-4">
                  {/* Matching Precedents */}
                  {precedentResults.matching_precedents?.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="font-semibold">Matching Precedents</h4>
                      {precedentResults.matching_precedents.map((precedent, idx) => (
                        <div key={idx} className="p-3 rounded-lg bg-green-500/5 border border-green-500/20">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium">{precedent.case_name} ({precedent.year})</span>
                            <Badge variant="outline" className="text-green-600">
                              {precedent.relevance_score}% Match
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground">{precedent.how_it_helps}</p>
                          <p className="text-xs text-muted-foreground mt-1">Citation: {precedent.citation}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Legal Strategies */}
                  {precedentResults.legal_strategies?.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="font-semibold">Recommended Legal Strategies</h4>
                      {precedentResults.legal_strategies.map((strategy, idx) => (
                        <div key={idx} className="p-3 rounded-lg border">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant={strategy.strength === 'strong' ? 'default' : 'secondary'}>
                              {strategy.strength}
                            </Badge>
                            <span className="font-medium">{strategy.strategy}</span>
                          </div>
                          <p className="text-sm text-muted-foreground">{strategy.description}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Outcome Prediction */}
                  {precedentResults.outcome_prediction && (
                    <div className="p-4 rounded-lg bg-blue-500/5 border border-blue-500/20">
                      <h4 className="font-semibold mb-3">Outcome Prediction</h4>
                      <div className="grid md:grid-cols-2 gap-4">
                        <div>
                          <p className="text-sm text-muted-foreground">Success Probability</p>
                          <p className="text-2xl font-bold text-blue-600">
                            {precedentResults.outcome_prediction.probability_of_success}%
                          </p>
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Potential Value Range</p>
                          <p className="text-lg font-semibold">
                            {precedentResults.outcome_prediction.likely_range_if_successful}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Case Value Estimator */}
              <div className="pt-4 border-t">
                <h4 className="font-semibold mb-3 flex items-center gap-2">
                  <DollarSign className="h-5 w-5 text-green-500" />
                  Case Value Estimator
                </h4>
                <div className="grid md:grid-cols-3 gap-3 mb-4">
                  <div className="flex items-center justify-between p-3 rounded-lg border">
                    <Label htmlFor="has-injury">Physical Injury</Label>
                    <Switch
                      id="has-injury"
                      checked={caseFactors.hasInjury}
                      onCheckedChange={(val) => setCaseFactors(prev => ({...prev, hasInjury: val}))}
                    />
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg border">
                    <Label htmlFor="has-arrest">Arrest Made</Label>
                    <Switch
                      id="has-arrest"
                      checked={caseFactors.hasArrest}
                      onCheckedChange={(val) => setCaseFactors(prev => ({...prev, hasArrest: val}))}
                    />
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg border">
                    <Label htmlFor="has-video">Video Evidence</Label>
                    <Switch
                      id="has-video"
                      checked={caseFactors.hasVideo}
                      onCheckedChange={(val) => setCaseFactors(prev => ({...prev, hasVideo: val}))}
                    />
                  </div>
                </div>
                <Button 
                  onClick={estimateCaseValue}
                  disabled={!violationAnalysis?.violations?.length || estimatingValue}
                  variant="outline"
                  className="w-full"
                  data-testid="estimate-value-btn"
                >
                  {estimatingValue ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <DollarSign className="h-4 w-4 mr-2" />
                  )}
                  Estimate Case Value
                </Button>

                {valueEstimate && (
                  <div className="mt-4 p-4 rounded-lg bg-green-500/5 border border-green-500/20">
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div>
                        <p className="text-sm text-muted-foreground">Low Estimate</p>
                        <p className="text-lg font-bold">${valueEstimate.low_estimate?.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Mid Estimate</p>
                        <p className="text-xl font-bold text-green-600">${valueEstimate.mid_estimate?.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">High Estimate</p>
                        <p className="text-lg font-bold">${valueEstimate.high_estimate?.toLocaleString()}</p>
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground mt-3 text-center">{valueEstimate.disclaimer}</p>
                  </div>
                )}
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
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">{foiaRequests.length} requests</Badge>
                  <Button 
                    onClick={generateFoiaRequest}
                    disabled={!selectedEncounter || generatingFoia}
                    data-testid="generate-foia-btn"
                  >
                    {generatingFoia ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <FileText className="h-4 w-4 mr-2" />
                    )}
                    Generate FOIA
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid md:grid-cols-3 gap-3">
                <div className="flex items-center gap-3 p-3 rounded-lg bg-indigo-500/5 border border-indigo-500/20">
                  <FileText className="h-5 w-5 text-indigo-500" />
                  <span className="text-sm">Auto-generates formal requests</span>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg bg-indigo-500/5 border border-indigo-500/20">
                  <Clock className="h-5 w-5 text-indigo-500" />
                  <span className="text-sm">Tracks deadlines</span>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg bg-indigo-500/5 border border-indigo-500/20">
                  <AlertTriangle className="h-5 w-5 text-indigo-500" />
                  <span className="text-sm">Auto-escalation</span>
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
                          ) : req.days_until_due !== undefined ? (
                            <span>Due in {req.days_until_due} days</span>
                          ) : (
                            <span>Status: {req.status}</span>
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
            </CardContent>
          </Card>

          {/* FOIA Dialog */}
          <Dialog open={foiaDialogOpen} onOpenChange={setFoiaDialogOpen}>
            <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>FOIA Request Generated</DialogTitle>
                <DialogDescription>
                  Your Freedom of Information Act request is ready. Copy and send to the department.
                </DialogDescription>
              </DialogHeader>
              
              {generatedFoia && (
                <div className="space-y-4">
                  <div className="p-4 rounded-lg bg-muted">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-semibold">Submit To:</h4>
                      <Button variant="ghost" size="sm" onClick={copyFoiaToClipboard}>
                        <Copy className="h-4 w-4 mr-2" />
                        Copy
                      </Button>
                    </div>
                    {generatedFoia.submit_to?.email && (
                      <p className="text-sm">Email: {generatedFoia.submit_to.email}</p>
                    )}
                    {generatedFoia.submit_to?.address && (
                      <p className="text-sm">Address: {generatedFoia.submit_to.address}</p>
                    )}
                    {generatedFoia.submit_to?.portal && (
                      <a 
                        href={generatedFoia.submit_to.portal} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-sm text-blue-500 hover:underline flex items-center gap-1"
                      >
                        Online Portal <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                    <p className="text-sm mt-2">Response Due: {generatedFoia.deadline_days} days</p>
                  </div>

                  <Textarea
                    value={generatedFoia.request_text}
                    readOnly
                    className="min-h-[300px] font-mono text-xs"
                  />
                </div>
              )}
              
              <DialogFooter className="flex gap-2">
                <Button variant="outline" onClick={() => setFoiaDialogOpen(false)}>
                  Close
                </Button>
                <Button 
                  onClick={() => markFoiaSubmitted(generatedFoia?.request_id, 'email')}
                  disabled={!generatedFoia?.request_id}
                >
                  Mark as Submitted
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </TabsContent>
      </Tabs>
    </div>
  );
}
