import React, { useState, useEffect } from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { ScrollArea } from '../components/ui/scroll-area';
import { Progress } from '../components/ui/progress';
import { Separator } from '../components/ui/separator';
import { Alert, AlertDescription } from '../components/ui/alert';
import { courtGradeAPI, encounterAPI } from '../lib/api';
import { 
  Scale, Shield, AlertTriangle, CheckCircle, XCircle, 
  FileText, Loader2, BookOpen, Gavel, Target, Info,
  Lock, Award, ChevronRight, Clock, RefreshCw
} from 'lucide-react';
import { toast } from 'sonner';

const confidenceColors = {
  very_high: 'bg-green-500 text-white',
  high: 'bg-emerald-500 text-white',
  moderate: 'bg-yellow-500 text-black',
  low: 'bg-orange-500 text-white',
  very_low: 'bg-red-500 text-white'
};

const confidenceDescriptions = {
  very_high: 'Strong evidence, verified citations, highly admissible',
  high: 'Good evidence quality, most citations verified',
  moderate: 'Mixed evidence, some citations need review',
  low: 'Weak evidence, limited legal backing',
  very_low: 'Insufficient evidence for legal proceedings'
};

export default function CourtGradeAIPage() {
  const [loading, setLoading] = useState(false);
  const [encounters, setEncounters] = useState([]);
  const [selectedEncounter, setSelectedEncounter] = useState(null);
  const [transcript, setTranscript] = useState('');
  const [encounterType, setEncounterType] = useState('general');
  const [analysis, setAnalysis] = useState(null);
  const [amendments, setAmendments] = useState([]);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [encountersRes, amendmentsRes] = await Promise.all([
        encounterAPI.list(),
        courtGradeAPI.listAmendments()
      ]);
      
      setEncounters(encountersRes.data || []);
      setAmendments(amendmentsRes.data.amendments || []);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleEncounterSelect = async (encounterId) => {
    setSelectedEncounter(encounterId);
    
    try {
      const response = await encounterAPI.get(encounterId);
      const encounter = response.data;
      
      // Build transcript from transcriptions if available
      if (encounter.transcriptions?.length > 0) {
        const fullTranscript = encounter.transcriptions
          .map(t => t.text)
          .join('\n');
        setTranscript(fullTranscript);
      }
      
      setEncounterType(encounter.encounter_type || 'general');
    } catch (error) {
      toast.error('Failed to load encounter');
    }
  };

  const runAnalysis = async () => {
    if (!transcript.trim()) {
      toast.error('Please enter or load a transcript');
      return;
    }

    setAnalyzing(true);
    try {
      const response = await courtGradeAPI.analyze(
        selectedEncounter,
        transcript,
        encounterType,
        true
      );
      
      setAnalysis(response.data);
      toast.success('Court-grade analysis complete');
    } catch (error) {
      toast.error('Analysis failed: ' + (error.response?.data?.detail || error.message));
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="court-grade-ai-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-serif text-3xl font-bold flex items-center gap-3">
              <Scale className="h-8 w-8 text-primary" />
              Court-Grade AI Analysis
            </h1>
            <p className="text-muted-foreground mt-1">
              RAG-powered legal analysis with guardrails and confidence scoring
            </p>
          </div>
          <Badge variant="outline" className="w-fit">
            <Shield className="h-3 w-3 mr-1" />
            FRE 901/707 Compliant
          </Badge>
        </div>

        {/* Input Section */}
        <div className="grid lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Encounter Data</CardTitle>
              <CardDescription>
                Select an encounter or enter a transcript manually
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Encounter Selector */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Load from Encounter</label>
                <Select 
                  value={selectedEncounter || ''} 
                  onValueChange={handleEncounterSelect}
                >
                  <SelectTrigger data-testid="encounter-select">
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

              {/* Encounter Type */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Encounter Type</label>
                <Select value={encounterType} onValueChange={setEncounterType}>
                  <SelectTrigger data-testid="type-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="general">General</SelectItem>
                    <SelectItem value="traffic_stop">Traffic Stop</SelectItem>
                    <SelectItem value="pedestrian_stop">Pedestrian Stop</SelectItem>
                    <SelectItem value="arrest">Arrest</SelectItem>
                    <SelectItem value="search">Search/Seizure</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Transcript Input */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Transcript</label>
                <Textarea
                  placeholder="Paste or load encounter transcript here..."
                  value={transcript}
                  onChange={(e) => setTranscript(e.target.value)}
                  rows={12}
                  className="font-mono text-sm"
                  data-testid="transcript-input"
                />
                <p className="text-xs text-muted-foreground">
                  {transcript.length} characters
                </p>
              </div>

              {/* Analyze Button */}
              <Button 
                className="w-full" 
                size="lg"
                onClick={runAnalysis}
                disabled={analyzing || !transcript.trim()}
                data-testid="analyze-btn"
              >
                {analyzing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Analyzing with RAG & Guardrails...
                  </>
                ) : (
                  <>
                    <Gavel className="h-4 w-4 mr-2" />
                    Run Court-Grade Analysis
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Knowledge Base Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="h-5 w-5" />
                Legal Knowledge Base
              </CardTitle>
              <CardDescription>
                Verified legal information used for analysis
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Amendments */}
                <div>
                  <h4 className="font-semibold text-sm mb-2">Constitutional Amendments</h4>
                  <div className="flex flex-wrap gap-2">
                    {amendments.map(amend => (
                      <Badge key={amend} variant="outline">
                        {amend}
                      </Badge>
                    ))}
                  </div>
                </div>

                <Separator />

                {/* Features */}
                <div className="space-y-3">
                  <div className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />
                    <div>
                      <p className="font-medium text-sm">RAG Retrieval</p>
                      <p className="text-xs text-muted-foreground">
                        Augments analysis with verified legal precedents
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <Shield className="h-4 w-4 text-blue-500 mt-0.5" />
                    <div>
                      <p className="font-medium text-sm">Guardrails</p>
                      <p className="text-xs text-muted-foreground">
                        Validates citations, checks legal basis, detects bias
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <Target className="h-4 w-4 text-purple-500 mt-0.5" />
                    <div>
                      <p className="font-medium text-sm">Confidence Scoring</p>
                      <p className="text-xs text-muted-foreground">
                        Multi-factor reliability assessment for court use
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <Lock className="h-4 w-4 text-orange-500 mt-0.5" />
                    <div>
                      <p className="font-medium text-sm">Speculation Labels</p>
                      <p className="text-xs text-muted-foreground">
                        Clearly marks uncertain conclusions
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Analysis Results */}
        {analysis && (
          <div className="space-y-6">
            {/* Confidence Score */}
            <Card className={`border-2 ${
              analysis.confidence_level === 'very_high' || analysis.confidence_level === 'high'
                ? 'border-green-500/50'
                : analysis.confidence_level === 'moderate'
                ? 'border-yellow-500/50'
                : 'border-red-500/50'
            }`}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Award className="h-5 w-5" />
                  Court Admissibility Assessment
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 gap-6">
                  {/* Confidence Level */}
                  <div className="text-center p-6 rounded-lg bg-muted/50">
                    <Badge className={`text-lg px-4 py-2 ${confidenceColors[analysis.confidence_level]}`}>
                      {analysis.confidence_level?.replace('_', ' ').toUpperCase()}
                    </Badge>
                    <p className="text-sm text-muted-foreground mt-3">
                      {confidenceDescriptions[analysis.confidence_level]}
                    </p>
                  </div>

                  {/* Score Breakdown */}
                  <div className="space-y-3">
                    <h4 className="font-semibold text-sm">Score Breakdown</h4>
                    {analysis.confidence_breakdown && Object.entries(analysis.confidence_breakdown).map(([key, value]) => (
                      <div key={key} className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span className="capitalize">{key.replace(/_/g, ' ')}</span>
                          <span className="font-medium">{(value * 100).toFixed(0)}%</span>
                        </div>
                        <Progress value={value * 100} />
                      </div>
                    ))}
                  </div>
                </div>

                {/* Court Recommendation */}
                {analysis.court_recommendation && (
                  <Alert className="mt-4">
                    <Info className="h-4 w-4" />
                    <AlertDescription>
                      {analysis.court_recommendation}
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>

            {/* Violations Detected */}
            {analysis.violations?.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-red-500" />
                    Violations Detected ({analysis.violations.length})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[400px]">
                    <div className="space-y-4">
                      {analysis.violations.map((violation, idx) => (
                        <div 
                          key={idx}
                          className="p-4 rounded-lg border"
                          data-testid={`violation-${idx}`}
                        >
                          <div className="flex items-start justify-between mb-3">
                            <div>
                              <h4 className="font-semibold">{violation.type?.replace(/_/g, ' ')}</h4>
                              <Badge variant="outline" className="mt-1">
                                {violation.amendment || violation.legal_basis}
                              </Badge>
                            </div>
                            <Badge className={
                              violation.severity >= 8 ? 'bg-red-500' :
                              violation.severity >= 5 ? 'bg-orange-500' : 'bg-yellow-500'
                            }>
                              Severity: {violation.severity}/10
                            </Badge>
                          </div>
                          
                          <p className="text-sm mb-3">{violation.description}</p>
                          
                          {violation.evidence_quote && (
                            <div className="bg-muted/50 rounded p-3 mb-3">
                              <p className="text-xs text-muted-foreground mb-1">Evidence Quote:</p>
                              <p className="text-sm italic">"{violation.evidence_quote}"</p>
                            </div>
                          )}

                          {violation.precedents?.length > 0 && (
                            <div className="mt-3 pt-3 border-t">
                              <p className="text-xs font-semibold mb-2">Relevant Precedents:</p>
                              <div className="space-y-1">
                                {violation.precedents.map((prec, pidx) => (
                                  <div key={pidx} className="flex items-center gap-2 text-xs">
                                    <Gavel className="h-3 w-3 text-muted-foreground" />
                                    <span className="font-medium">{prec.case_name}</span>
                                    {prec.relevance && (
                                      <Badge variant="outline" className="text-xs">
                                        {(prec.relevance * 100).toFixed(0)}% relevant
                                      </Badge>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            )}

            {/* Guardrails Report */}
            {analysis.guardrails && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5 text-blue-500" />
                    Guardrails Validation
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {[
                      { key: 'citations_valid', label: 'Citations Valid', icon: BookOpen },
                      { key: 'legal_basis_verified', label: 'Legal Basis Verified', icon: Gavel },
                      { key: 'no_bias_detected', label: 'No Bias Detected', icon: Target },
                      { key: 'confidence_calibrated', label: 'Confidence Calibrated', icon: Award },
                      { key: 'speculation_labeled', label: 'Speculation Labeled', icon: Info },
                      { key: 'severity_reasonable', label: 'Severity Reasonable', icon: AlertTriangle },
                    ].map(({ key, label, icon: Icon }) => (
                      <div 
                        key={key}
                        className={`p-4 rounded-lg border ${
                          analysis.guardrails[key] 
                            ? 'border-green-500/50 bg-green-500/5' 
                            : 'border-red-500/50 bg-red-500/5'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          {analysis.guardrails[key] ? (
                            <CheckCircle className="h-5 w-5 text-green-500" />
                          ) : (
                            <XCircle className="h-5 w-5 text-red-500" />
                          )}
                          <div>
                            <Icon className="h-4 w-4 text-muted-foreground mb-1" />
                            <p className="font-medium text-sm">{label}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Overall Guardrails Score */}
                  <div className="mt-4 p-4 rounded-lg bg-muted/50">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">Overall Guardrails Score</span>
                      <span className="text-2xl font-bold">
                        {((analysis.guardrails.overall_score || 0) * 100).toFixed(0)}%
                      </span>
                    </div>
                    <Progress value={(analysis.guardrails.overall_score || 0) * 100} className="mt-2" />
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Recommendations */}
            {analysis.recommendations?.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Recommended Actions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {analysis.recommendations.map((rec, idx) => (
                      <div key={idx} className="flex items-start gap-2 p-2">
                        <ChevronRight className="h-4 w-4 text-primary mt-0.5" />
                        <span className="text-sm">{rec}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
