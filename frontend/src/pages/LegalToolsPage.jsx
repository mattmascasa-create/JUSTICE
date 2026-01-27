import React, { useState, useEffect } from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { legalServicesAPI, encounterAPI } from '../lib/api';
import { 
  FileText, Phone, Scale, Shield, AlertTriangle, Copy, Download,
  CheckCircle, XCircle, Loader2, ExternalLink, Search, Clock,
  Building, MapPin, User, Calendar, ChevronRight, BookOpen
} from 'lucide-react';
import { toast } from 'sonner';

const US_STATES = [
  { code: 'AL', name: 'Alabama' }, { code: 'AK', name: 'Alaska' }, { code: 'AZ', name: 'Arizona' },
  { code: 'AR', name: 'Arkansas' }, { code: 'CA', name: 'California' }, { code: 'CO', name: 'Colorado' },
  { code: 'CT', name: 'Connecticut' }, { code: 'DE', name: 'Delaware' }, { code: 'FL', name: 'Florida' },
  { code: 'GA', name: 'Georgia' }, { code: 'HI', name: 'Hawaii' }, { code: 'ID', name: 'Idaho' },
  { code: 'IL', name: 'Illinois' }, { code: 'IN', name: 'Indiana' }, { code: 'IA', name: 'Iowa' },
  { code: 'KS', name: 'Kansas' }, { code: 'KY', name: 'Kentucky' }, { code: 'LA', name: 'Louisiana' },
  { code: 'ME', name: 'Maine' }, { code: 'MD', name: 'Maryland' }, { code: 'MA', name: 'Massachusetts' },
  { code: 'MI', name: 'Michigan' }, { code: 'MN', name: 'Minnesota' }, { code: 'MS', name: 'Mississippi' },
  { code: 'MO', name: 'Missouri' }, { code: 'MT', name: 'Montana' }, { code: 'NE', name: 'Nebraska' },
  { code: 'NV', name: 'Nevada' }, { code: 'NH', name: 'New Hampshire' }, { code: 'NJ', name: 'New Jersey' },
  { code: 'NM', name: 'New Mexico' }, { code: 'NY', name: 'New York' }, { code: 'NC', name: 'North Carolina' },
  { code: 'ND', name: 'North Dakota' }, { code: 'OH', name: 'Ohio' }, { code: 'OK', name: 'Oklahoma' },
  { code: 'OR', name: 'Oregon' }, { code: 'PA', name: 'Pennsylvania' }, { code: 'RI', name: 'Rhode Island' },
  { code: 'SC', name: 'South Carolina' }, { code: 'SD', name: 'South Dakota' }, { code: 'TN', name: 'Tennessee' },
  { code: 'TX', name: 'Texas' }, { code: 'UT', name: 'Utah' }, { code: 'VT', name: 'Vermont' },
  { code: 'VA', name: 'Virginia' }, { code: 'WA', name: 'Washington' }, { code: 'WV', name: 'West Virginia' },
  { code: 'WI', name: 'Wisconsin' }, { code: 'WY', name: 'Wyoming' }, { code: 'DC', name: 'Washington D.C.' }
];

export default function LegalToolsPage() {
  const [activeTab, setActiveTab] = useState('foia');
  const [loading, setLoading] = useState(false);
  const [encounters, setEncounters] = useState([]);
  const [hotlines, setHotlines] = useState([]);
  const [stateResources, setStateResources] = useState([]);
  const [selectedState, setSelectedState] = useState('');
  
  // FOIA Form State
  const [foiaForm, setFoiaForm] = useState({
    requester_name: '',
    requester_address: '',
    requester_email: '',
    department_name: '',
    department_address: '',
    incident_date: '',
    incident_location: '',
    officer_names: '',
    officer_badges: '',
    state: 'DEFAULT',
    additional_details: ''
  });
  const [generatedFOIA, setGeneratedFOIA] = useState(null);
  
  // Miranda Analysis State
  const [mirandaTranscript, setMirandaTranscript] = useState('');
  const [selectedEncounter, setSelectedEncounter] = useState('');
  const [mirandaResult, setMirandaResult] = useState(null);
  
  // Legal Brief State
  const [briefEncounter, setBriefEncounter] = useState('');
  const [plaintiffName, setPlaintiffName] = useState('');
  const [generatedBrief, setGeneratedBrief] = useState(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [encountersRes, hotlinesRes] = await Promise.all([
        encounterAPI.list(),
        legalServicesAPI.getHotlines()
      ]);
      
      setEncounters(encountersRes.data || []);
      setHotlines(hotlinesRes.data.hotlines || []);
    } catch (error) {
      console.error('Error loading data:', error);
    }
  };

  const loadStateResources = async (state) => {
    setSelectedState(state);
    try {
      const response = await legalServicesAPI.getStateResources(state);
      setStateResources(response.data.resources || []);
    } catch (error) {
      toast.error('Failed to load state resources');
    }
  };

  // FOIA Generation
  const generateFOIA = async () => {
    setLoading(true);
    try {
      const data = {
        ...foiaForm,
        officer_names: foiaForm.officer_names ? foiaForm.officer_names.split(',').map(n => n.trim()) : null,
        officer_badges: foiaForm.officer_badges ? foiaForm.officer_badges.split(',').map(b => b.trim()) : null
      };
      
      const response = await legalServicesAPI.generateFOIA(data);
      setGeneratedFOIA(response.data);
      toast.success('FOIA request generated!');
    } catch (error) {
      toast.error('Failed to generate FOIA request');
    } finally {
      setLoading(false);
    }
  };

  // Miranda Analysis
  const analyzeMiranda = async () => {
    if (!mirandaTranscript && !selectedEncounter) {
      toast.error('Please enter a transcript or select an encounter');
      return;
    }
    
    setLoading(true);
    try {
      let response;
      if (selectedEncounter) {
        response = await legalServicesAPI.analyzeEncounterMiranda(selectedEncounter);
      } else {
        response = await legalServicesAPI.analyzeMiranda(mirandaTranscript, 'general');
      }
      
      setMirandaResult(response.data);
      
      if (response.data.miranda_violation) {
        toast.warning('⚠️ Potential Miranda violation detected!');
      } else {
        toast.success('Miranda analysis complete');
      }
    } catch (error) {
      toast.error('Failed to analyze transcript');
    } finally {
      setLoading(false);
    }
  };

  // Legal Brief Generation
  const generateBrief = async () => {
    if (!briefEncounter || !plaintiffName) {
      toast.error('Please select an encounter and enter plaintiff name');
      return;
    }
    
    setLoading(true);
    try {
      const response = await legalServicesAPI.generateBriefFromEncounter(briefEncounter, plaintiffName);
      setGeneratedBrief(response.data);
      toast.success('Legal brief generated!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate legal brief');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard!');
  };

  const downloadAsFile = (content, filename) => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="legal-tools-page">
        {/* Header */}
        <div>
          <h1 className="font-serif text-3xl font-bold flex items-center gap-3">
            <Scale className="h-8 w-8 text-primary" />
            Legal Tools
          </h1>
          <p className="text-muted-foreground mt-1">
            Generate legal documents, analyze rights violations, and access legal resources
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="foia">FOIA Generator</TabsTrigger>
            <TabsTrigger value="miranda">Miranda Detector</TabsTrigger>
            <TabsTrigger value="brief">Legal Brief</TabsTrigger>
            <TabsTrigger value="hotlines">Legal Hotlines</TabsTrigger>
          </TabsList>

          {/* FOIA Generator Tab */}
          <TabsContent value="foia" className="space-y-6">
            <div className="grid lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="h-5 w-5" />
                    Body Camera Footage Request
                  </CardTitle>
                  <CardDescription>
                    Generate a formal FOIA/Public Records request for police recordings
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Your Name *</Label>
                      <Input
                        value={foiaForm.requester_name}
                        onChange={(e) => setFoiaForm({...foiaForm, requester_name: e.target.value})}
                        placeholder="John Doe"
                        data-testid="foia-name"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Your Email *</Label>
                      <Input
                        type="email"
                        value={foiaForm.requester_email}
                        onChange={(e) => setFoiaForm({...foiaForm, requester_email: e.target.value})}
                        placeholder="john@example.com"
                        data-testid="foia-email"
                      />
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Your Address *</Label>
                    <Input
                      value={foiaForm.requester_address}
                      onChange={(e) => setFoiaForm({...foiaForm, requester_address: e.target.value})}
                      placeholder="123 Main St, City, State ZIP"
                      data-testid="foia-address"
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Department Name *</Label>
                      <Input
                        value={foiaForm.department_name}
                        onChange={(e) => setFoiaForm({...foiaForm, department_name: e.target.value})}
                        placeholder="City Police Department"
                        data-testid="foia-dept"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>State *</Label>
                      <Select 
                        value={foiaForm.state} 
                        onValueChange={(v) => setFoiaForm({...foiaForm, state: v})}
                      >
                        <SelectTrigger data-testid="foia-state">
                          <SelectValue placeholder="Select state" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="DEFAULT">Federal (Default)</SelectItem>
                          {US_STATES.map(s => (
                            <SelectItem key={s.code} value={s.code}>{s.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Department Address *</Label>
                    <Input
                      value={foiaForm.department_address}
                      onChange={(e) => setFoiaForm({...foiaForm, department_address: e.target.value})}
                      placeholder="456 Police Plaza, City, State ZIP"
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Incident Date *</Label>
                      <Input
                        type="date"
                        value={foiaForm.incident_date}
                        onChange={(e) => setFoiaForm({...foiaForm, incident_date: e.target.value})}
                        data-testid="foia-date"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Incident Location *</Label>
                      <Input
                        value={foiaForm.incident_location}
                        onChange={(e) => setFoiaForm({...foiaForm, incident_location: e.target.value})}
                        placeholder="123 Street Name"
                      />
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Officer Names (comma-separated)</Label>
                      <Input
                        value={foiaForm.officer_names}
                        onChange={(e) => setFoiaForm({...foiaForm, officer_names: e.target.value})}
                        placeholder="Officer Smith, Officer Jones"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Badge Numbers (comma-separated)</Label>
                      <Input
                        value={foiaForm.officer_badges}
                        onChange={(e) => setFoiaForm({...foiaForm, officer_badges: e.target.value})}
                        placeholder="1234, 5678"
                      />
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Additional Details</Label>
                    <Textarea
                      value={foiaForm.additional_details}
                      onChange={(e) => setFoiaForm({...foiaForm, additional_details: e.target.value})}
                      placeholder="Any additional context about the incident..."
                      rows={3}
                    />
                  </div>
                  
                  <Button 
                    className="w-full" 
                    onClick={generateFOIA} 
                    disabled={loading}
                    data-testid="generate-foia-btn"
                  >
                    {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <FileText className="h-4 w-4 mr-2" />}
                    Generate FOIA Request
                  </Button>
                </CardContent>
              </Card>

              {/* Generated FOIA Preview */}
              <Card>
                <CardHeader>
                  <CardTitle>Generated Request</CardTitle>
                </CardHeader>
                <CardContent>
                  {generatedFOIA ? (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <Badge variant="outline">{generatedFOIA.request_id}</Badge>
                        <div className="flex gap-2">
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => copyToClipboard(generatedFOIA.letter)}
                          >
                            <Copy className="h-4 w-4 mr-1" /> Copy
                          </Button>
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => downloadAsFile(generatedFOIA.letter, `FOIA_Request_${generatedFOIA.request_id}.txt`)}
                          >
                            <Download className="h-4 w-4 mr-1" /> Download
                          </Button>
                        </div>
                      </div>
                      
                      <Alert>
                        <AlertDescription>
                          <p className="font-semibold">Applicable Law: {generatedFOIA.foia_law?.name}</p>
                          <p className="text-sm">Response deadline: {generatedFOIA.foia_law?.deadline}</p>
                        </AlertDescription>
                      </Alert>
                      
                      <ScrollArea className="h-[400px] border rounded p-4">
                        <pre className="text-xs whitespace-pre-wrap font-mono">
                          {generatedFOIA.letter}
                        </pre>
                      </ScrollArea>
                    </div>
                  ) : (
                    <div className="text-center py-12 text-muted-foreground">
                      <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>Fill out the form to generate your FOIA request</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Miranda Detector Tab */}
          <TabsContent value="miranda" className="space-y-6">
            <div className="grid lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5" />
                    Miranda Rights Analysis
                  </CardTitle>
                  <CardDescription>
                    Analyze if Miranda rights should have been read during an encounter
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label>Select Encounter (Optional)</Label>
                    <Select value={selectedEncounter} onValueChange={setSelectedEncounter}>
                      <SelectTrigger data-testid="miranda-encounter-select">
                        <SelectValue placeholder="Select an encounter" />
                      </SelectTrigger>
                      <SelectContent>
                        {encounters.map(enc => (
                          <SelectItem key={enc.encounter_id} value={enc.encounter_id}>
                            {enc.encounter_type} - {new Date(enc.created_at).toLocaleDateString()}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="text-center text-muted-foreground">— OR —</div>
                  
                  <div className="space-y-2">
                    <Label>Paste Transcript</Label>
                    <Textarea
                      value={mirandaTranscript}
                      onChange={(e) => setMirandaTranscript(e.target.value)}
                      placeholder="Paste the encounter transcript here..."
                      rows={10}
                      className="font-mono text-sm"
                      data-testid="miranda-transcript"
                    />
                  </div>
                  
                  <Button 
                    className="w-full" 
                    onClick={analyzeMiranda}
                    disabled={loading}
                    data-testid="analyze-miranda-btn"
                  >
                    {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Search className="h-4 w-4 mr-2" />}
                    Analyze for Miranda Violations
                  </Button>
                </CardContent>
              </Card>

              {/* Miranda Results */}
              <Card>
                <CardHeader>
                  <CardTitle>Analysis Results</CardTitle>
                </CardHeader>
                <CardContent>
                  {mirandaResult ? (
                    <div className="space-y-4">
                      {/* Violation Status */}
                      <div className={`p-4 rounded-lg ${
                        mirandaResult.miranda_violation 
                          ? 'bg-red-500/20 border-2 border-red-500' 
                          : 'bg-green-500/20 border-2 border-green-500'
                      }`}>
                        <div className="flex items-center gap-3">
                          {mirandaResult.miranda_violation ? (
                            <XCircle className="h-8 w-8 text-red-500" />
                          ) : (
                            <CheckCircle className="h-8 w-8 text-green-500" />
                          )}
                          <div>
                            <p className="font-bold text-lg">
                              {mirandaResult.miranda_violation ? 'POTENTIAL MIRANDA VIOLATION' : 'No Violation Detected'}
                            </p>
                            <p className="text-sm opacity-80">
                              Confidence: {(mirandaResult.confidence * 100).toFixed(0)}%
                            </p>
                          </div>
                        </div>
                      </div>
                      
                      {/* Indicators */}
                      <div className="grid grid-cols-2 gap-4">
                        <div className="p-3 rounded bg-muted/50">
                          <p className="text-sm font-semibold mb-2">Custody Indicators</p>
                          <div className="flex flex-wrap gap-1">
                            {mirandaResult.custody_indicators?.length > 0 ? (
                              mirandaResult.custody_indicators.map((ind, i) => (
                                <Badge key={i} variant="destructive" className="text-xs">{ind}</Badge>
                              ))
                            ) : (
                              <span className="text-xs text-muted-foreground">None detected</span>
                            )}
                          </div>
                        </div>
                        <div className="p-3 rounded bg-muted/50">
                          <p className="text-sm font-semibold mb-2">Interrogation Indicators</p>
                          <div className="flex flex-wrap gap-1">
                            {mirandaResult.interrogation_indicators?.length > 0 ? (
                              mirandaResult.interrogation_indicators.map((ind, i) => (
                                <Badge key={i} variant="secondary" className="text-xs">{ind}</Badge>
                              ))
                            ) : (
                              <span className="text-xs text-muted-foreground">None detected</span>
                            )}
                          </div>
                        </div>
                      </div>
                      
                      {/* Summary */}
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span>Miranda Rights Read:</span>
                          <span className={mirandaResult.miranda_read ? 'text-green-500' : 'text-red-500'}>
                            {mirandaResult.miranda_read ? 'Yes' : 'No'}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>In Custody (Likely):</span>
                          <span>{mirandaResult.in_custody_likely ? 'Yes' : 'No'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Interrogation (Likely):</span>
                          <span>{mirandaResult.interrogation_likely ? 'Yes' : 'No'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Miranda Required:</span>
                          <span className={mirandaResult.miranda_required ? 'text-orange-500 font-bold' : ''}>
                            {mirandaResult.miranda_required ? 'Yes' : 'No'}
                          </span>
                        </div>
                      </div>
                      
                      {/* Recommendations */}
                      {mirandaResult.recommendations?.length > 0 && (
                        <div className="pt-4 border-t">
                          <p className="font-semibold mb-2">Recommendations</p>
                          <ul className="space-y-1">
                            {mirandaResult.recommendations.map((rec, i) => (
                              <li key={i} className="text-sm flex items-start gap-2">
                                <ChevronRight className="h-4 w-4 mt-0.5 text-primary" />
                                {rec}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      
                      {/* Legal Basis */}
                      {mirandaResult.legal_basis && (
                        <Alert>
                          <BookOpen className="h-4 w-4" />
                          <AlertDescription>
                            <p className="font-semibold">{mirandaResult.legal_basis.case}</p>
                            <p className="text-sm mt-1">{mirandaResult.legal_basis.holding}</p>
                          </AlertDescription>
                        </Alert>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-12 text-muted-foreground">
                      <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>Select an encounter or paste a transcript to analyze</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Legal Brief Tab */}
          <TabsContent value="brief" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Scale className="h-5 w-5" />
                  Generate Legal Brief from Encounter
                </CardTitle>
                <CardDescription>
                  Create a draft Section 1983 civil rights complaint based on detected violations
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Select Encounter *</Label>
                    <Select value={briefEncounter} onValueChange={setBriefEncounter}>
                      <SelectTrigger data-testid="brief-encounter-select">
                        <SelectValue placeholder="Select an encounter with violations" />
                      </SelectTrigger>
                      <SelectContent>
                        {encounters.map(enc => (
                          <SelectItem key={enc.encounter_id} value={enc.encounter_id}>
                            {enc.encounter_type} - {new Date(enc.created_at).toLocaleDateString()}
                            {enc.ai_analysis?.violations?.length > 0 && (
                              <span className="ml-2 text-red-500">
                                ({enc.ai_analysis.violations.length} violations)
                              </span>
                            )}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Plaintiff Name *</Label>
                    <Input
                      value={plaintiffName}
                      onChange={(e) => setPlaintiffName(e.target.value)}
                      placeholder="Your full legal name"
                      data-testid="plaintiff-name"
                    />
                  </div>
                </div>
                
                <Button 
                  onClick={generateBrief}
                  disabled={loading || !briefEncounter || !plaintiffName}
                  data-testid="generate-brief-btn"
                >
                  {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <FileText className="h-4 w-4 mr-2" />}
                  Generate Legal Brief
                </Button>
                
                {generatedBrief && (
                  <div className="mt-6 space-y-4">
                    <div className="flex items-center justify-between">
                      <Badge variant="outline">{generatedBrief.brief_id}</Badge>
                      <div className="flex gap-2">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => copyToClipboard(generatedBrief.template_brief)}
                        >
                          <Copy className="h-4 w-4 mr-1" /> Copy
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => downloadAsFile(generatedBrief.template_brief, `Legal_Brief_${generatedBrief.brief_id}.txt`)}
                        >
                          <Download className="h-4 w-4 mr-1" /> Download
                        </Button>
                      </div>
                    </div>
                    
                    <Alert variant="destructive">
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>
                        {generatedBrief.disclaimer}
                      </AlertDescription>
                    </Alert>
                    
                    <ScrollArea className="h-[500px] border rounded p-4">
                      <pre className="text-xs whitespace-pre-wrap font-mono">
                        {generatedBrief.template_brief}
                      </pre>
                    </ScrollArea>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Legal Hotlines Tab */}
          <TabsContent value="hotlines" className="space-y-6">
            <div className="grid lg:grid-cols-2 gap-6">
              {/* National Hotlines */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Phone className="h-5 w-5" />
                    National Civil Rights Hotlines
                  </CardTitle>
                  <CardDescription>
                    24/7 legal assistance for civil rights violations
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {hotlines.map((hotline, idx) => (
                      <div key={idx} className="p-4 rounded-lg border">
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-semibold">{hotline.name}</p>
                            <p className="text-sm text-muted-foreground">{hotline.description}</p>
                          </div>
                          <Button variant="outline" size="sm" asChild>
                            <a href={`tel:${hotline.phone.replace(/[^0-9]/g, '')}`}>
                              <Phone className="h-4 w-4 mr-1" />
                              Call
                            </a>
                          </Button>
                        </div>
                        <div className="mt-2 flex items-center gap-4 text-sm">
                          <span className="flex items-center gap-1">
                            <Phone className="h-3 w-3" />
                            {hotline.phone}
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {hotline.hours}
                          </span>
                        </div>
                        <Button variant="link" size="sm" className="p-0 h-auto mt-1" asChild>
                          <a href={hotline.website} target="_blank" rel="noopener noreferrer">
                            <ExternalLink className="h-3 w-3 mr-1" />
                            Visit Website
                          </a>
                        </Button>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* State Resources */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MapPin className="h-5 w-5" />
                    State-Specific Resources
                  </CardTitle>
                  <CardDescription>
                    Local civil rights organizations in your state
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Select value={selectedState} onValueChange={loadStateResources}>
                    <SelectTrigger data-testid="state-resources-select">
                      <SelectValue placeholder="Select your state" />
                    </SelectTrigger>
                    <SelectContent>
                      {US_STATES.map(s => (
                        <SelectItem key={s.code} value={s.code}>{s.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  
                  {stateResources.length > 0 ? (
                    <div className="space-y-3">
                      {stateResources.map((resource, idx) => (
                        <div key={idx} className="p-3 rounded-lg border">
                          <p className="font-semibold">{resource.name}</p>
                          <p className="text-sm">{resource.phone}</p>
                          <Button variant="link" size="sm" className="p-0 h-auto" asChild>
                            <a href={resource.website} target="_blank" rel="noopener noreferrer">
                              <ExternalLink className="h-3 w-3 mr-1" />
                              Website
                            </a>
                          </Button>
                        </div>
                      ))}
                    </div>
                  ) : selectedState ? (
                    <p className="text-sm text-muted-foreground">
                      No specific resources found. Contact your local bar association for referrals.
                    </p>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      Select a state to see local resources
                    </p>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Emergency Note */}
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <strong>In case of immediate danger, call 911.</strong> For legal emergencies during encounters, 
                use the JUSTICE app's SOS feature to alert your attorney and emergency contacts.
              </AlertDescription>
            </Alert>
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  );
}
