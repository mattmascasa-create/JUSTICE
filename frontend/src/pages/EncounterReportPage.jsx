import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { Alert, AlertDescription } from '../components/ui/alert';
import { encounterAPI } from '../lib/api';
import { 
  Shield, MapPin, Clock, Video, Mic, FileText, AlertTriangle,
  CheckCircle, ExternalLink, Download, Scale, Users, ArrowLeft,
  Loader2, Play, AlertCircle, Gavel
} from 'lucide-react';
import { toast } from 'sonner';

export default function EncounterReportPage() {
  const { encounterId } = useParams();
  const [loading, setLoading] = useState(true);
  const [reportData, setReportData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadReport();
  }, [encounterId]);

  const loadReport = async () => {
    try {
      setLoading(true);
      const response = await encounterAPI.getReport(encounterId);
      setReportData(response.data);
    } catch (err) {
      console.error('Error loading report:', err);
      setError(err.response?.data?.detail || 'Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const formatViolation = (violation) => {
    return violation.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center space-y-4">
            <Loader2 className="h-12 w-12 animate-spin mx-auto text-primary" />
            <p className="text-muted-foreground">Loading incident report...</p>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (error || !reportData) {
    return (
      <AppLayout>
        <div className="max-w-2xl mx-auto">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error || 'Report not found'}</AlertDescription>
          </Alert>
          <Link to="/encounter">
            <Button variant="outline" className="mt-4">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Encounter Mode
            </Button>
          </Link>
        </div>
      </AppLayout>
    );
  }

  if (reportData.status === 'generating') {
    return (
      <AppLayout>
        <div className="max-w-2xl mx-auto text-center space-y-6">
          <div className="inline-flex items-center justify-center p-4 rounded-full bg-blue-500/20">
            <Loader2 className="h-12 w-12 text-blue-500 animate-spin" />
          </div>
          <h1 className="font-serif text-3xl font-bold">Generating Your Report</h1>
          <p className="text-muted-foreground">
            Our AI is analyzing your encounter recording and preparing a detailed incident report.
            This usually takes 30-60 seconds.
          </p>
          <Button onClick={loadReport} variant="outline">
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Check Status
          </Button>
        </div>
      </AppLayout>
    );
  }

  const { report, transcriptions, media_files } = reportData;
  const videoFiles = media_files?.filter(f => f.type === 'video') || [];
  const audioFiles = media_files?.filter(f => f.type === 'audio') || [];

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-6" data-testid="encounter-report">
        {/* Back Button */}
        <Link to="/dashboard">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
        </Link>

        {/* Report Header */}
        <Card className="border-2 border-primary/20">
          <CardHeader className="pb-4">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <CardTitle className="font-serif text-3xl flex items-center gap-3">
                  <Shield className="h-8 w-8 text-primary" />
                  Incident Report
                </CardTitle>
                <CardDescription>
                  Report ID: {report.report_id}
                </CardDescription>
              </div>
              {report.court_admissible && (
                <Badge className="bg-green-500/10 text-green-500 text-sm px-3 py-1">
                  <Gavel className="h-4 w-4 mr-1" />
                  Court Admissible
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Encounter Details Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-3 rounded-lg bg-muted/50 text-center">
                <p className="text-2xl font-bold">{formatDuration(report.encounter_details?.duration_seconds || 0)}</p>
                <p className="text-xs text-muted-foreground flex items-center justify-center gap-1">
                  <Clock className="h-3 w-3" /> Duration
                </p>
              </div>
              <div className="p-3 rounded-lg bg-muted/50 text-center">
                <p className="text-2xl font-bold text-red-500">{report.violations_count || 0}</p>
                <p className="text-xs text-muted-foreground flex items-center justify-center gap-1">
                  <AlertTriangle className="h-3 w-3" /> Violations
                </p>
              </div>
              <div className="p-3 rounded-lg bg-muted/50 text-center">
                <p className="text-2xl font-bold">{videoFiles.length}</p>
                <p className="text-xs text-muted-foreground flex items-center justify-center gap-1">
                  <Video className="h-3 w-3" /> Video Chunks
                </p>
              </div>
              <div className="p-3 rounded-lg bg-muted/50 text-center">
                <p className="text-2xl font-bold">{report.evidence?.total_size_mb || 0} MB</p>
                <p className="text-xs text-muted-foreground flex items-center justify-center gap-1">
                  <FileText className="h-3 w-3" /> Evidence Size
                </p>
              </div>
            </div>

            {/* Location */}
            <div className="flex items-center gap-2 text-sm">
              <MapPin className="h-4 w-4 text-muted-foreground" />
              <span>{report.encounter_details?.location || 'Location not recorded'}</span>
            </div>
          </CardContent>
        </Card>

        {/* Summary Section */}
        <Card>
          <CardHeader>
            <CardTitle className="font-serif flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Incident Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground leading-relaxed">
              {report.summary || 'Summary is being generated...'}
            </p>
          </CardContent>
        </Card>

        {/* Violations Section */}
        {report.violations?.length > 0 && (
          <Card className="border-red-500/30">
            <CardHeader>
              <CardTitle className="font-serif flex items-center gap-2 text-red-500">
                <AlertTriangle className="h-5 w-5" />
                Potential Civil Rights Violations Detected
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {report.violations.map((violation, index) => (
                <div 
                  key={index}
                  className="flex items-center gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20"
                >
                  <AlertCircle className="h-5 w-5 text-red-500" />
                  <span className="font-medium">{formatViolation(violation)}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Evidence Section */}
        <Card>
          <CardHeader>
            <CardTitle className="font-serif flex items-center gap-2">
              <Video className="h-5 w-5" />
              Recorded Evidence
            </CardTitle>
            <CardDescription>
              All recordings are automatically saved and verified
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Video Files */}
            {videoFiles.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium flex items-center gap-2">
                  <Video className="h-4 w-4" />
                  Video Recordings ({videoFiles.length} chunks)
                </p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  {videoFiles.slice(0, 8).map((file, index) => (
                    <div 
                      key={index}
                      className="p-2 rounded bg-muted/50 text-center text-xs"
                    >
                      <Play className="h-4 w-4 mx-auto mb-1 text-primary" />
                      <span className="truncate block">{file.filename}</span>
                      <span className="text-muted-foreground">
                        {(file.size_bytes / 1024).toFixed(0)} KB
                      </span>
                    </div>
                  ))}
                </div>
                {videoFiles.length > 8 && (
                  <p className="text-xs text-muted-foreground">
                    +{videoFiles.length - 8} more video chunks
                  </p>
                )}
              </div>
            )}

            {/* Audio Files */}
            {audioFiles.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium flex items-center gap-2">
                  <Mic className="h-4 w-4" />
                  Audio Recordings ({audioFiles.length} chunks)
                </p>
              </div>
            )}

            {/* Transcriptions */}
            {transcriptions?.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Transcriptions ({transcriptions.length} segments)
                </p>
                <div className="max-h-60 overflow-y-auto space-y-2 p-3 rounded-lg bg-muted/30 border">
                  {transcriptions.map((t, index) => (
                    <div key={index} className="text-sm">
                      <span className="text-xs text-muted-foreground font-mono">
                        [{formatDuration(Math.round(t.start_time || index * 10))}]
                      </span>
                      <p className="mt-0.5">{t.text}</p>
                      {t.violations_detected?.length > 0 && (
                        <div className="flex gap-1 mt-1">
                          {t.violations_detected.map((v, i) => (
                            <Badge key={i} variant="destructive" className="text-xs">
                              {formatViolation(v)}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recommendations Section */}
        {report.recommendations?.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="font-serif flex items-center gap-2">
                <Scale className="h-5 w-5" />
                Legal Recommendations
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {report.recommendations.map((rec, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500 mt-1 flex-shrink-0" />
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {/* Officers Section */}
        {report.officers?.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="font-serif flex items-center gap-2">
                <Users className="h-5 w-5" />
                Officers Involved
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {report.officers.map((officer, index) => (
                  <div key={index} className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                    <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <Users className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium">{officer.name || 'Unknown Officer'}</p>
                      <p className="text-sm text-muted-foreground">
                        Badge: {officer.badge_number || 'N/A'} • {officer.department || 'Unknown Department'}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Legal Resources */}
        <Card>
          <CardHeader>
            <CardTitle className="font-serif flex items-center gap-2">
              <ExternalLink className="h-5 w-5" />
              Legal Resources
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {report.legal_resources?.map((resource, index) => (
                <a
                  key={index}
                  href={resource.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                >
                  <ExternalLink className="h-4 w-4 text-primary" />
                  <span className="text-sm">{resource.name}</span>
                </a>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-3">
          <Button className="flex-1">
            <Download className="h-4 w-4 mr-2" />
            Download Full Report
          </Button>
          <Button variant="outline" className="flex-1">
            <Users className="h-4 w-4 mr-2" />
            Share with Attorney
          </Button>
        </div>
      </div>
    </AppLayout>
  );
}
