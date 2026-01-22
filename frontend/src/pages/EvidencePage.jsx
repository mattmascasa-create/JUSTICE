import React, { useState, useEffect, useRef } from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Progress } from '../components/ui/progress';
import { evidenceAPI, casesAPI, blockchainAPI } from '../lib/api';
import { generateEvidenceReport, downloadEvidenceReport } from '../lib/reportGenerator';
import { formatDateTime, formatFileSize } from '../lib/utils';
import { 
  Upload, Search, FileText, Image, Video, Music, 
  Trash2, Download, Shield, CheckCircle, Filter, Loader2,
  FileDown, Globe, Link2
} from 'lucide-react';
import { toast } from 'sonner';

export default function EvidencePage() {
  const [evidence, setEvidence] = useState([]);
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedCase, setSelectedCase] = useState('');
  const [fileDescription, setFileDescription] = useState('');
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportDialogOpen, setReportDialogOpen] = useState(false);
  const [selectedReportCase, setSelectedReportCase] = useState('');
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [evidenceRes, casesRes] = await Promise.all([
        evidenceAPI.list(),
        casesAPI.list()
      ]);
      setEvidence(evidenceRes.data);
      setCases(casesRes.data);
    } catch (error) {
      toast.error('Failed to load evidence');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    if (!selectedReportCase) {
      toast.error('Please select a case');
      return;
    }
    
    setGeneratingReport(true);
    try {
      const response = await blockchainAPI.getEvidenceReport(selectedReportCase);
      const doc = await generateEvidenceReport(response.data);
      downloadEvidenceReport(doc, selectedReportCase);
      toast.success('Evidence report downloaded successfully!');
      setReportDialogOpen(false);
      setSelectedReportCase('');
    } catch (error) {
      console.error('Report generation error:', error);
      toast.error(error.response?.data?.detail || 'Failed to generate report');
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      // Check file size (500MB max)
      if (file.size > 500 * 1024 * 1024) {
        toast.error('File too large. Maximum size is 500MB');
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    
    if (!selectedFile || !selectedCase) {
      toast.error('Please select a file and case');
      return;
    }

    setUploading(true);
    setUploadProgress(0);

    try {
      // Simulate progress for better UX
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 10, 90));
      }, 200);

      const response = await evidenceAPI.upload(selectedFile, selectedCase, fileDescription);
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      toast.success('Evidence uploaded and verified on blockchain');
      setUploadDialogOpen(false);
      setSelectedFile(null);
      setSelectedCase('');
      setFileDescription('');
      if (fileInputRef.current) fileInputRef.current.value = '';
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload evidence');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDelete = async (evidenceId) => {
    if (!window.confirm('Are you sure you want to delete this evidence?')) return;

    try {
      await evidenceAPI.delete(evidenceId);
      toast.success('Evidence deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete evidence');
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

  const filteredEvidence = evidence.filter(ev => {
    const matchesSearch = ev.file_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = typeFilter === 'all' || ev.file_type === typeFilter;
    return matchesSearch && matchesType;
  });

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
      <div className="space-y-6" data-testid="evidence-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-serif text-3xl font-bold">Evidence Library</h1>
            <p className="text-muted-foreground mt-1">Secure, blockchain-verified evidence storage</p>
          </div>
          <div className="flex gap-2">
            {/* Generate Report Dialog */}
            <Dialog open={reportDialogOpen} onOpenChange={setReportDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" data-testid="generate-report-btn">
                  <FileDown className="h-4 w-4 mr-2" />
                  Evidence Report
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle className="font-serif flex items-center gap-2">
                    <FileDown className="h-5 w-5 text-primary" />
                    Generate Evidence Report
                  </DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <p className="text-sm text-muted-foreground">
                    Generate a comprehensive PDF report with all evidence for a case, including:
                  </p>
                  <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                    <li>SHA-256 cryptographic hashes</li>
                    <li>IPFS Content Identifiers (CIDs)</li>
                    <li>Chain of custody audit trail</li>
                    <li>Verification URLs for court use</li>
                  </ul>
                  <div className="space-y-2">
                    <Label>Select Case *</Label>
                    <Select 
                      value={selectedReportCase} 
                      onValueChange={setSelectedReportCase}
                    >
                      <SelectTrigger data-testid="report-case-select">
                        <SelectValue placeholder="Select a case" />
                      </SelectTrigger>
                      <SelectContent>
                        {cases.map((c) => {
                          const evidenceCount = evidence.filter(e => e.case_id === c.case_id).length;
                          return (
                            <SelectItem key={c.case_id} value={c.case_id}>
                              {c.title} {evidenceCount > 0 ? `(${evidenceCount} files)` : ''}
                            </SelectItem>
                          );
                        })}
                      </SelectContent>
                    </Select>
                  </div>
                  <Button 
                    className="w-full" 
                    onClick={handleGenerateReport}
                    disabled={generatingReport || !selectedReportCase}
                    data-testid="download-report-btn"
                  >
                    {generatingReport ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <FileDown className="h-4 w-4 mr-2" />
                        Download PDF Report
                      </>
                    )}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
            
            {/* Upload Dialog */}
            <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
              <DialogTrigger asChild>
                <Button data-testid="upload-evidence-btn">
                  <Upload className="h-4 w-4 mr-2" />
                  Upload Evidence
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle className="font-serif">Upload Evidence</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleUpload} className="space-y-4">
                  <div className="space-y-2">
                    <Label>Case *</Label>
                    <Select 
                      value={selectedCase} 
                      onValueChange={setSelectedCase}
                    >
                      <SelectTrigger data-testid="evidence-case-select">
                        <SelectValue placeholder="Select a case" />
                      </SelectTrigger>
                      <SelectContent>
                      {cases.map((c) => (
                        <SelectItem key={c.case_id} value={c.case_id}>{c.title}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>File *</Label>
                  <Input
                    ref={fileInputRef}
                    type="file"
                    onChange={handleFileSelect}
                    accept=".mp4,.mov,.avi,.mp3,.wav,.jpg,.jpeg,.png,.gif,.pdf,.doc,.docx"
                    data-testid="evidence-file-input"
                  />
                  {selectedFile && (
                    <p className="text-sm text-muted-foreground">
                      Selected: {selectedFile.name} ({formatFileSize(selectedFile.size)})
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label>Description</Label>
                  <Input
                    placeholder="Brief description of the evidence"
                    value={fileDescription}
                    onChange={(e) => setFileDescription(e.target.value)}
                    data-testid="evidence-description-input"
                  />
                </div>

                {uploading && (
                  <div className="space-y-2">
                    <Progress value={uploadProgress} />
                    <p className="text-sm text-center text-muted-foreground">
                      Uploading and verifying... {uploadProgress}%
                    </p>
                  </div>
                )}

                <Button type="submit" className="w-full" disabled={uploading || !selectedFile || !selectedCase} data-testid="submit-evidence-btn">
                  {uploading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Shield className="h-4 w-4 mr-2" />
                      Upload & Verify
                    </>
                  )}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
          </div>
        </div>

        {/* Info Banner */}
        <Card className="bg-green-500/10 border-green-500/20">
          <CardContent className="p-4 flex items-center gap-4">
            <CheckCircle className="h-8 w-8 text-green-500 flex-shrink-0" />
            <div>
              <p className="font-medium text-green-600 dark:text-green-400">Blockchain Verification</p>
              <p className="text-sm text-muted-foreground">
                All evidence is automatically timestamped and verified on the blockchain for tamper-proof integrity.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search evidence..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
              data-testid="evidence-search"
            />
          </div>
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-full sm:w-40" data-testid="type-filter">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="document">Documents</SelectItem>
              <SelectItem value="image">Images</SelectItem>
              <SelectItem value="video">Videos</SelectItem>
              <SelectItem value="audio">Audio</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Evidence Grid */}
        {filteredEvidence.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Shield className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">No evidence found</h3>
              <p className="text-muted-foreground mb-4">
                {evidence.length === 0 
                  ? "Start by uploading evidence for your cases." 
                  : "No evidence matches your current filters."}
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredEvidence.map((ev) => {
              const FileIcon = getFileIcon(ev.file_type);
              const caseInfo = cases.find(c => c.case_id === ev.case_id);
              
              return (
                <Card key={ev.evidence_id} data-testid={`evidence-card-${ev.evidence_id}`}>
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3 mb-3">
                      <div className="p-3 rounded-lg bg-muted">
                        <FileIcon className="h-6 w-6 text-muted-foreground" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{ev.file_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatFileSize(ev.file_size)}
                        </p>
                      </div>
                      <Badge variant="secondary">{ev.file_type}</Badge>
                    </div>

                    {caseInfo && (
                      <p className="text-sm text-muted-foreground mb-2 truncate">
                        Case: {caseInfo.title}
                      </p>
                    )}

                    {ev.blockchain_hash && (
                      <div className="flex items-center gap-2 text-xs text-green-500 mb-2">
                        <CheckCircle className="h-3 w-3" />
                        <span className="font-mono truncate">{ev.blockchain_hash.slice(0, 24)}...</span>
                      </div>
                    )}

                    {ev.ipfs_cid && (
                      <div className="flex items-center gap-2 text-xs text-blue-500 mb-2">
                        <Globe className="h-3 w-3" />
                        <span className="truncate">IPFS: {ev.ipfs_cid.slice(0, 20)}...</span>
                        <a 
                          href={`https://gateway.pinata.cloud/ipfs/${ev.ipfs_cid}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:text-blue-600"
                          title="View on IPFS"
                        >
                          <Link2 className="h-3 w-3" />
                        </a>
                      </div>
                    )}

                    <p className="text-xs text-muted-foreground mb-3">
                      Uploaded: {formatDateTime(ev.uploaded_at)}
                    </p>

                    <div className="flex justify-end gap-2">
                      <Button variant="ghost" size="icon">
                        <Download className="h-4 w-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        className="text-red-500 hover:text-red-600"
                        onClick={() => handleDelete(ev.evidence_id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
