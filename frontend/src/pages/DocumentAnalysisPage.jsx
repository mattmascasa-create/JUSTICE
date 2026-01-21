import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { analysisAPI } from '../lib/api';
import { 
  Upload, FileText, AlertTriangle, Scale, Search, 
  CheckCircle, XCircle, Loader2, FileQuestion, Mic,
  Video, File, Brain, Gavel, Users, TrendingUp
} from 'lucide-react';
import { toast } from 'sonner';

const documentTypes = [
  { value: 'police_report', label: 'Police Report', icon: FileText },
  { value: 'discovery', label: 'Discovery Documents', icon: Search },
  { value: 'court_filing', label: 'Court Filing', icon: Gavel },
  { value: 'body_cam_transcript', label: 'Body Cam Transcript', icon: Video },
  { value: 'witness_statement', label: 'Witness Statement', icon: Users },
  { value: 'other', label: 'Other Document', icon: File }
];

const analysisFocus = [
  { value: 'all', label: 'Complete Analysis' },
  { value: 'violations', label: 'Civil Rights Violations' },
  { value: 'bias', label: 'Bias & Discrimination' },
  { value: 'inconsistencies', label: 'Inconsistencies' }
];

export default function DocumentAnalysisPage() {
  const [file, setFile] = useState(null);
  const [documentType, setDocumentType] = useState('other');
  const [focus, setFocus] = useState('all');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState(null);

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setAnalysis(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'audio/*': ['.mp3', '.wav', '.m4a', '.webm'],
      'video/*': ['.mp4', '.mov', '.webm'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    maxSize: 50 * 1024 * 1024, // 50MB
    multiple: false
  });

  const handleAnalyze = async () => {
    if (!file) {
      toast.error('Please select a file first');
      return;
    }

    setIsAnalyzing(true);
    try {
      const response = await analysisAPI.analyzeDocument(file, documentType, focus);
      setAnalysis(response.data);
      toast.success('Analysis complete');
    } catch (error) {
      console.error('Analysis error:', error);
      toast.error('Analysis failed: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getFileIcon = () => {
    if (!file) return <Upload className="h-12 w-12" />;
    const ext = file.name.split('.').pop().toLowerCase();
    if (['mp3', 'wav', 'm4a'].includes(ext)) return <Mic className="h-12 w-12 text-blue-500" />;
    if (['mp4', 'mov', 'webm'].includes(ext)) return <Video className="h-12 w-12 text-purple-500" />;
    return <FileText className="h-12 w-12 text-green-500" />;
  };

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical': return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'high': return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
      case 'medium': return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      case 'low': return 'bg-green-500/10 text-green-500 border-green-500/20';
      default: return 'bg-muted text-muted-foreground';
    }
  };

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="document-analysis-page">
        {/* Header */}
        <div>
          <h1 className="font-serif text-3xl font-bold flex items-center gap-3">
            <Brain className="h-8 w-8 text-primary" />
            AI Legal Document Analyzer
          </h1>
          <p className="text-muted-foreground mt-1">
            Upload police reports, body cam footage, or legal documents for AI-powered analysis
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Upload Section */}
          <div className="space-y-4">
            {/* Dropzone */}
            <Card>
              <CardContent className="p-6">
                <div
                  {...getRootProps()}
                  className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                    isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
                  }`}
                  data-testid="file-dropzone"
                >
                  <input {...getInputProps()} />
                  <div className="flex flex-col items-center gap-3">
                    {getFileIcon()}
                    {file ? (
                      <div>
                        <p className="font-medium">{file.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {(file.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                    ) : (
                      <div>
                        <p className="font-medium">
                          {isDragActive ? 'Drop the file here' : 'Drag & drop a file here'}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          or click to select (PDF, TXT, Audio, Video - max 50MB)
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Options */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Analysis Options</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Document Type</label>
                  <Select value={documentType} onValueChange={setDocumentType}>
                    <SelectTrigger data-testid="doc-type-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {documentTypes.map(type => (
                        <SelectItem key={type.value} value={type.value}>
                          <div className="flex items-center gap-2">
                            <type.icon className="h-4 w-4" />
                            {type.label}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Analysis Focus</label>
                  <Select value={focus} onValueChange={setFocus}>
                    <SelectTrigger data-testid="focus-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {analysisFocus.map(f => (
                        <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <Button 
                  className="w-full" 
                  size="lg"
                  onClick={handleAnalyze}
                  disabled={!file || isAnalyzing}
                  data-testid="analyze-btn"
                >
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Brain className="h-5 w-5 mr-2" />
                      Analyze Document
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Results Section */}
          <div className="space-y-4">
            {!analysis ? (
              <Card className="h-full min-h-[400px] flex items-center justify-center">
                <CardContent className="text-center">
                  <FileQuestion className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
                  <p className="text-lg font-medium">No Analysis Yet</p>
                  <p className="text-muted-foreground">
                    Upload a document and click analyze to see results
                  </p>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle className="h-5 w-5 text-green-500" />
                    Analysis Results
                  </CardTitle>
                  <CardDescription>{analysis.document_type} - {file?.name}</CardDescription>
                </CardHeader>
                <CardContent>
                  <Tabs defaultValue="summary">
                    <TabsList className="grid w-full grid-cols-4">
                      <TabsTrigger value="summary">Summary</TabsTrigger>
                      <TabsTrigger value="violations">Violations</TabsTrigger>
                      <TabsTrigger value="bias">Bias</TabsTrigger>
                      <TabsTrigger value="actions">Actions</TabsTrigger>
                    </TabsList>

                    <TabsContent value="summary" className="mt-4 space-y-4">
                      <p className="text-sm">{analysis.summary || 'No summary available'}</p>
                      
                      {analysis.case_precedents?.length > 0 && (
                        <div>
                          <h4 className="font-medium mb-2 flex items-center gap-2">
                            <Gavel className="h-4 w-4" />
                            Relevant Case Law
                          </h4>
                          <div className="space-y-2">
                            {analysis.case_precedents.map((c, i) => (
                              <div key={i} className="p-3 rounded-lg bg-muted/50 text-sm">
                                <p className="font-medium">{c.case_name}</p>
                                <p className="text-muted-foreground">{c.relevance}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </TabsContent>

                    <TabsContent value="violations" className="mt-4">
                      {analysis.violations_found?.length > 0 ? (
                        <div className="space-y-3">
                          {analysis.violations_found.map((v, i) => (
                            <div key={i} className="p-3 rounded-lg border">
                              <div className="flex items-start justify-between mb-2">
                                <span className="font-medium flex items-center gap-2">
                                  <AlertTriangle className="h-4 w-4 text-orange-500" />
                                  {v.type}
                                </span>
                                <Badge className={getSeverityColor(v.severity)}>
                                  {v.severity}
                                </Badge>
                              </div>
                              <p className="text-sm text-muted-foreground">{v.description}</p>
                              {v.legal_citation && (
                                <p className="text-xs mt-2 text-blue-500">{v.legal_citation}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-center py-8">
                          <CheckCircle className="h-12 w-12 mx-auto text-green-500 mb-3" />
                          <p className="text-muted-foreground">No violations detected</p>
                        </div>
                      )}
                    </TabsContent>

                    <TabsContent value="bias" className="mt-4">
                      {analysis.bias_indicators?.length > 0 ? (
                        <div className="space-y-3">
                          {analysis.bias_indicators.map((b, i) => (
                            <div key={i} className="p-3 rounded-lg border border-orange-500/20 bg-orange-500/5">
                              <p className="font-medium">{b.indicator}</p>
                              <p className="text-sm text-muted-foreground mt-1">{b.evidence}</p>
                              <p className="text-xs text-orange-500 mt-2">Impact: {b.impact}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-center py-8">
                          <CheckCircle className="h-12 w-12 mx-auto text-green-500 mb-3" />
                          <p className="text-muted-foreground">No bias indicators detected</p>
                        </div>
                      )}

                      {analysis.inconsistencies?.length > 0 && (
                        <div className="mt-4">
                          <h4 className="font-medium mb-2">Inconsistencies Found</h4>
                          <div className="space-y-2">
                            {analysis.inconsistencies.map((inc, i) => (
                              <div key={i} className="p-2 rounded bg-yellow-500/10 text-sm">
                                <p>{inc.description}</p>
                                <p className="text-xs text-muted-foreground mt-1">
                                  Significance: {inc.significance}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </TabsContent>

                    <TabsContent value="actions" className="mt-4">
                      <div className="space-y-4">
                        <div>
                          <h4 className="font-medium mb-2 flex items-center gap-2">
                            <TrendingUp className="h-4 w-4" />
                            Recommended Actions
                          </h4>
                          {analysis.recommendations?.length > 0 ? (
                            <ul className="space-y-2">
                              {analysis.recommendations.map((rec, i) => (
                                <li key={i} className="flex items-start gap-2 text-sm">
                                  <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                                  {rec}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-muted-foreground">No specific actions recommended</p>
                          )}
                        </div>

                        {analysis.legal_issues?.length > 0 && (
                          <div>
                            <h4 className="font-medium mb-2">Legal Issues</h4>
                            <div className="space-y-2">
                              {analysis.legal_issues.map((issue, i) => (
                                <div key={i} className="p-2 rounded bg-muted/50 text-sm">
                                  <p className="font-medium">{issue.issue}</p>
                                  <p className="text-muted-foreground">{issue.implication}</p>
                                  {issue.remedy && (
                                    <p className="text-green-600 text-xs mt-1">Remedy: {issue.remedy}</p>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </TabsContent>
                  </Tabs>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
