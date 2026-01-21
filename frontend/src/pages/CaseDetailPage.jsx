import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import CaseTimeline from '../components/CaseTimeline';
import { casesAPI, evidenceAPI, reportAPI } from '../lib/api';
import { generateCaseReport, downloadCaseReport } from '../lib/reportGenerator';
import { formatDate, formatDateTime, getStatusColor, getSeverityColor, formatFileSize } from '../lib/utils';
import { 
  ArrowLeft, Calendar, MapPin, User, BadgeIcon, Building, 
  FileText, Image, Video, Music, Trash2, Download, Shield,
  Edit, AlertTriangle, Clock, FileDown, Loader2
} from 'lucide-react';
import { toast } from 'sonner';

export default function CaseDetailPage() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generatingReport, setGeneratingReport] = useState(false);

  useEffect(() => {
    fetchCaseData();
  }, [caseId]);

  const fetchCaseData = async () => {
    try {
      const [caseRes, evidenceRes] = await Promise.all([
        casesAPI.get(caseId),
        evidenceAPI.getByCase(caseId)
      ]);
      setCaseData(caseRes.data);
      setEvidence(evidenceRes.data);
    } catch (error) {
      toast.error('Failed to load case');
      navigate('/cases');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (newStatus) => {
    try {
      await casesAPI.update(caseId, { status: newStatus });
      setCaseData({ ...caseData, status: newStatus });
      toast.success('Status updated');
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this case? This action cannot be undone.')) {
      return;
    }

    try {
      await casesAPI.delete(caseId);
      toast.success('Case deleted');
      navigate('/cases');
    } catch (error) {
      toast.error('Failed to delete case');
    }
  };

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    try {
      const response = await reportAPI.getData(caseId);
      const doc = await generateCaseReport(response.data);
      downloadCaseReport(doc, caseId);
      toast.success('Report downloaded');
    } catch (error) {
      toast.error('Failed to generate report');
    } finally {
      setGeneratingReport(false);
    }
  };

  const getFileIcon = (type) => {
    switch (type) {
      case 'video': return Video;
      case 'audio': return Music;
      case 'image': return Image;
      default: return FileText;
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

  if (!caseData) return null;

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="case-detail-page">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/cases')} data-testid="back-to-cases">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="flex-1">
            <h1 className="font-serif text-2xl font-bold">{caseData.title}</h1>
            <p className="text-sm text-muted-foreground font-mono">ID: {caseData.case_id}</p>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleGenerateReport}
              disabled={generatingReport}
              data-testid="generate-report-btn"
            >
              {generatingReport ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <FileDown className="h-4 w-4 mr-2" />
              )}
              PDF Report
            </Button>
            <Button variant="outline" size="sm" data-testid="edit-case-btn">
              <Edit className="h-4 w-4 mr-2" />
              Edit
            </Button>
            <Button variant="destructive" size="sm" onClick={handleDelete} data-testid="delete-case-btn">
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </div>
        </div>

        {/* Status & Severity Row */}
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Status:</span>
            <Select value={caseData.status} onValueChange={handleStatusChange}>
              <SelectTrigger className="w-36" data-testid="status-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="open">Open</SelectItem>
                <SelectItem value="under_review">Under Review</SelectItem>
                <SelectItem value="resolved">Resolved</SelectItem>
                <SelectItem value="closed">Closed</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Badge className={getSeverityColor(caseData.severity)}>
            <AlertTriangle className="h-3 w-3 mr-1" />
            {caseData.severity} severity
          </Badge>
          <Badge variant="outline">{caseData.violation_type}</Badge>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            <Tabs defaultValue="details" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="details">Details</TabsTrigger>
                <TabsTrigger value="evidence">Evidence ({evidence.length})</TabsTrigger>
                <TabsTrigger value="timeline">Timeline</TabsTrigger>
              </TabsList>
              
              <TabsContent value="details" className="space-y-6">
                {/* Description */}
                <Card>
                  <CardHeader>
                    <CardTitle className="font-serif">Incident Description</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground whitespace-pre-wrap">{caseData.description}</p>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="evidence">
                {/* Evidence */}
                <Card data-testid="evidence-section">
                  <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="font-serif">Evidence ({evidence.length})</CardTitle>
                    <Link to="/evidence">
                      <Button variant="outline" size="sm">
                        Manage Evidence
                      </Button>
                    </Link>
                  </CardHeader>
                  <CardContent>
                    {evidence.length === 0 ? (
                      <div className="text-center py-8">
                        <Shield className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                        <p className="text-muted-foreground">No evidence uploaded yet</p>
                        <Link to="/evidence">
                          <Button variant="outline" size="sm" className="mt-4">
                            Upload Evidence
                          </Button>
                        </Link>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {evidence.map((ev) => {
                          const FileIcon = getFileIcon(ev.file_type);
                          return (
                            <div 
                              key={ev.evidence_id}
                              className="flex items-center justify-between p-4 rounded-lg bg-muted/50"
                            >
                              <div className="flex items-center gap-3">
                                <div className="p-2 rounded bg-background">
                                  <FileIcon className="h-5 w-5 text-muted-foreground" />
                                </div>
                                <div>
                                  <p className="font-medium">{ev.file_name}</p>
                                  <p className="text-xs text-muted-foreground">
                                    {formatFileSize(ev.file_size)} • {formatDateTime(ev.uploaded_at)}
                                  </p>
                                  {ev.blockchain_hash && (
                                    <p className="text-xs text-green-500 font-mono truncate max-w-[200px]">
                                      ✓ Verified: {ev.blockchain_hash.slice(0, 16)}...
                                    </p>
                                  )}
                                </div>
                              </div>
                              <Button variant="ghost" size="icon">
                                <Download className="h-4 w-4" />
                              </Button>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="timeline">
                <CaseTimeline caseId={caseId} />
              </TabsContent>
            </Tabs>
          </div>
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {evidence.map((ev) => {
                      const FileIcon = getFileIcon(ev.file_type);
                      return (
                        <div 
                          key={ev.evidence_id}
                          className="flex items-center justify-between p-4 rounded-lg bg-muted/50"
                        >
                          <div className="flex items-center gap-3">
                            <div className="p-2 rounded bg-background">
                              <FileIcon className="h-5 w-5 text-muted-foreground" />
                            </div>
                            <div>
                              <p className="font-medium">{ev.file_name}</p>
                              <p className="text-xs text-muted-foreground">
                                {formatFileSize(ev.file_size)} • {formatDateTime(ev.uploaded_at)}
                              </p>
                              {ev.blockchain_hash && (
                                <p className="text-xs text-green-500 font-mono truncate max-w-[200px]">
                                  ✓ Verified: {ev.blockchain_hash.slice(0, 16)}...
                                </p>
                              )}
                            </div>
                          </div>
                          <Button variant="ghost" size="icon">
                            <Download className="h-4 w-4" />
                          </Button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Incident Details */}
            <Card>
              <CardHeader>
                <CardTitle className="font-serif text-lg">Incident Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-start gap-3">
                  <Calendar className="h-5 w-5 text-muted-foreground mt-0.5" />
                  <div>
                    <p className="text-sm text-muted-foreground">Date</p>
                    <p className="font-medium">{formatDate(caseData.incident_date)}</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <MapPin className="h-5 w-5 text-muted-foreground mt-0.5" />
                  <div>
                    <p className="text-sm text-muted-foreground">Location</p>
                    <p className="font-medium">{caseData.location}</p>
                  </div>
                </div>
                {caseData.department && (
                  <div className="flex items-start gap-3">
                    <Building className="h-5 w-5 text-muted-foreground mt-0.5" />
                    <div>
                      <p className="text-sm text-muted-foreground">Department</p>
                      <p className="font-medium">{caseData.department}</p>
                    </div>
                  </div>
                )}
                {caseData.officer_name && (
                  <div className="flex items-start gap-3">
                    <User className="h-5 w-5 text-muted-foreground mt-0.5" />
                    <div>
                      <p className="text-sm text-muted-foreground">Officer</p>
                      <p className="font-medium">{caseData.officer_name}</p>
                    </div>
                  </div>
                )}
                {caseData.officer_badge && (
                  <div className="flex items-start gap-3">
                    <BadgeIcon className="h-5 w-5 text-muted-foreground mt-0.5" />
                    <div>
                      <p className="text-sm text-muted-foreground">Badge Number</p>
                      <p className="font-medium font-mono">{caseData.officer_badge}</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Timeline */}
            <Card>
              <CardHeader>
                <CardTitle className="font-serif text-lg">Timeline</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-green-500" />
                    <div>
                      <p className="text-sm font-medium">Case Created</p>
                      <p className="text-xs text-muted-foreground">{formatDateTime(caseData.created_at)}</p>
                    </div>
                  </div>
                  {caseData.updated_at !== caseData.created_at && (
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-blue-500" />
                      <div>
                        <p className="text-sm font-medium">Last Updated</p>
                        <p className="text-xs text-muted-foreground">{formatDateTime(caseData.updated_at)}</p>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle className="font-serif text-lg">Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Link to="/attorneys" className="block">
                  <Button variant="outline" className="w-full justify-start">
                    Find an Attorney
                  </Button>
                </Link>
                <Link to="/ai-attorney" className="block">
                  <Button variant="outline" className="w-full justify-start">
                    Ask AI Attorney
                  </Button>
                </Link>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
