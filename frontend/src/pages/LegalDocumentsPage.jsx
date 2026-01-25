import React, { useState, useEffect } from 'react';
import { FileText, Download, Loader2, Trash2, AlertTriangle, CheckCircle, Share2, Send, Inbox, Clock } from 'lucide-react';
import { toast } from 'sonner';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogClose } from '../components/ui/dialog';
import { encounterAPI, documentsAPI, attorneysAPI } from '../lib/api';

export default function LegalDocumentsPage() {
  const [encounters, setEncounters] = useState([]);
  const [documentTypes, setDocumentTypes] = useState([]);
  const [myDocuments, setMyDocuments] = useState([]);
  const [receivedShares, setReceivedShares] = useState([]);
  const [sentShares, setSentShares] = useState([]);
  const [attorneys, setAttorneys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [selectedEncounter, setSelectedEncounter] = useState('');
  const [selectedDocType, setSelectedDocType] = useState('');
  const [userStatement, setUserStatement] = useState('');
  const [injuries, setInjuries] = useState('');
  const [witnesses, setWitnesses] = useState('');
  const [generatedDoc, setGeneratedDoc] = useState(null);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [docToShare, setDocToShare] = useState(null);
  const [shareRecipient, setShareRecipient] = useState('');
  const [shareMessage, setShareMessage] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [encountersRes, typesRes, docsRes, receivedRes, sentRes, attorneysRes] = await Promise.all([
        encounterAPI.list(),
        documentsAPI.getTypes(),
        documentsAPI.getMyDocuments(),
        documentsAPI.getReceivedShares().catch(() => ({ data: { shares: [] } })),
        documentsAPI.getSentShares().catch(() => ({ data: { shares: [] } })),
        attorneysAPI.getMyAttorneys().catch(() => ({ data: { attorneys: [] } }))
      ]);
      
      const encountersList = encountersRes.data.encounters || encountersRes.data || [];
      setEncounters(encountersList);
      setDocumentTypes(typesRes.data.document_types || []);
      setMyDocuments(docsRes.data.documents || []);
      setReceivedShares(receivedRes.data.shares || []);
      setSentShares(sentRes.data.shares || []);
      setAttorneys(attorneysRes.data.attorneys || []);
    } catch (error) {
      console.error('Error loading data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!selectedEncounter || !selectedDocType) {
      toast.error('Please select an encounter and document type');
      return;
    }

    setGenerating(true);
    try {
      const additionalInfo = {};
      if (userStatement.trim()) additionalInfo.user_statement = userStatement;
      if (injuries.trim()) additionalInfo.injuries = injuries;
      if (witnesses.trim()) additionalInfo.witnesses = witnesses;

      const response = await documentsAPI.generate(
        selectedEncounter,
        selectedDocType,
        additionalInfo
      );

      if (response.data.success) {
        setGeneratedDoc(response.data);
        toast.success('Document generated successfully!');
        // Refresh documents list
        const docsRes = await documentsAPI.getMyDocuments();
        setMyDocuments(docsRes.data.documents || []);
      } else {
        toast.error(response.data.error || 'Failed to generate document');
      }
    } catch (error) {
      console.error('Error generating document:', error);
      toast.error('Failed to generate document. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = (content, title) => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.replace(/\s+/g, '_')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('Document downloaded');
  };

  const handleDelete = async (documentId) => {
    try {
      await documentsAPI.deleteDocument(documentId);
      toast.success('Document deleted');
      setMyDocuments(prev => prev.filter(d => d.document_id !== documentId));
    } catch (error) {
      toast.error('Failed to delete document');
    }
  };

  const openShareDialog = (doc) => {
    setDocToShare(doc);
    setShareRecipient('');
    setShareMessage('');
    setShareDialogOpen(true);
  };

  const handleShare = async () => {
    if (!docToShare || !shareRecipient) {
      toast.error('Please select a recipient');
      return;
    }

    setSharing(true);
    try {
      const response = await documentsAPI.shareDocument(
        docToShare.document_id,
        shareRecipient,
        shareMessage || undefined
      );

      if (response.data.success) {
        toast.success(response.data.message || 'Document shared successfully!');
        setShareDialogOpen(false);
        // Refresh sent shares
        const sentRes = await documentsAPI.getSentShares();
        setSentShares(sentRes.data.shares || []);
      }
    } catch (error) {
      console.error('Error sharing document:', error);
      toast.error('Failed to share document');
    } finally {
      setSharing(false);
    }
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getDocTypeIcon = (type) => {
    const icons = {
      complaint_letter: '📝',
      civil_rights_report: '⚖️',
      attorney_brief: '📋',
      evidence_summary: '📁',
      witness_statement: '👤'
    };
    return icons[type] || '📄';
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="legal-documents-page">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">AI Legal Document Generator</h1>
          <p className="text-muted-foreground mt-1">
            Generate professional legal documents from your encounter data using AI
          </p>
        </div>

        <Tabs defaultValue="generate" className="space-y-6">
          <TabsList>
            <TabsTrigger value="generate" data-testid="generate-tab">Generate Document</TabsTrigger>
            <TabsTrigger value="documents" data-testid="documents-tab">
              My Documents ({myDocuments.length})
            </TabsTrigger>
            <TabsTrigger value="received" data-testid="received-tab">
              <Inbox className="w-4 h-4 mr-1" />
              Received ({receivedShares.length})
            </TabsTrigger>
            <TabsTrigger value="sent" data-testid="sent-tab">
              <Send className="w-4 h-4 mr-1" />
              Sent ({sentShares.length})
            </TabsTrigger>
          </TabsList>

          {/* Generate Document Tab */}
          <TabsContent value="generate" className="space-y-6">
            <div className="grid lg:grid-cols-2 gap-6">
              {/* Document Configuration */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    Document Configuration
                  </CardTitle>
                  <CardDescription>
                    Select an encounter and document type to generate
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Encounter Selection */}
                  <div className="space-y-2">
                    <Label>Select Encounter</Label>
                    <Select value={selectedEncounter} onValueChange={setSelectedEncounter}>
                      <SelectTrigger data-testid="encounter-select">
                        <SelectValue placeholder="Choose an encounter..." />
                      </SelectTrigger>
                      <SelectContent>
                        {encounters.length === 0 ? (
                          <SelectItem value="none" disabled>No encounters available</SelectItem>
                        ) : (
                          encounters.map(enc => (
                            <SelectItem key={enc.encounter_id} value={enc.encounter_id}>
                              {enc.encounter_type || 'Encounter'} - {formatDate(enc.started_at || enc.created_at)}
                              {enc.location?.city && ` (${enc.location.city})`}
                            </SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Document Type Selection */}
                  <div className="space-y-2">
                    <Label>Document Type</Label>
                    <Select value={selectedDocType} onValueChange={setSelectedDocType}>
                      <SelectTrigger data-testid="doctype-select">
                        <SelectValue placeholder="Choose document type..." />
                      </SelectTrigger>
                      <SelectContent>
                        {documentTypes.map(type => (
                          <SelectItem key={type.type} value={type.type}>
                            <div className="flex items-center gap-2">
                              <span>{getDocTypeIcon(type.type)}</span>
                              <div>
                                <div className="font-medium">{type.title}</div>
                                <div className="text-xs text-muted-foreground">{type.description}</div>
                              </div>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Additional Information */}
                  <div className="space-y-2">
                    <Label>Your Statement (Optional)</Label>
                    <Textarea
                      placeholder="Provide your account of what happened..."
                      value={userStatement}
                      onChange={(e) => setUserStatement(e.target.value)}
                      className="min-h-[100px]"
                      data-testid="user-statement"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Injuries (Optional)</Label>
                      <Textarea
                        placeholder="Describe any injuries..."
                        value={injuries}
                        onChange={(e) => setInjuries(e.target.value)}
                        className="min-h-[80px]"
                        data-testid="injuries-input"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Witnesses (Optional)</Label>
                      <Textarea
                        placeholder="List any witnesses..."
                        value={witnesses}
                        onChange={(e) => setWitnesses(e.target.value)}
                        className="min-h-[80px]"
                        data-testid="witnesses-input"
                      />
                    </div>
                  </div>

                  <Button
                    onClick={handleGenerate}
                    disabled={generating || !selectedEncounter || !selectedDocType}
                    className="w-full"
                    size="lg"
                    data-testid="generate-btn"
                  >
                    {generating ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Generating Document...
                      </>
                    ) : (
                      <>
                        <FileText className="w-4 h-4 mr-2" />
                        Generate Document
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>

              {/* Document Types Info */}
              <Card>
                <CardHeader>
                  <CardTitle>Available Document Types</CardTitle>
                  <CardDescription>
                    Choose the right document for your needs
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {documentTypes.map(type => (
                      <div
                        key={type.type}
                        className={`p-4 rounded-lg border transition-colors cursor-pointer ${
                          selectedDocType === type.type
                            ? 'border-primary bg-primary/5'
                            : 'border-border hover:bg-muted/50'
                        }`}
                        onClick={() => setSelectedDocType(type.type)}
                      >
                        <div className="flex items-start gap-3">
                          <span className="text-2xl">{getDocTypeIcon(type.type)}</span>
                          <div>
                            <h4 className="font-semibold">{type.title}</h4>
                            <p className="text-sm text-muted-foreground">{type.description}</p>
                          </div>
                          {selectedDocType === type.type && (
                            <CheckCircle className="w-5 h-5 text-primary ml-auto" />
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Generated Document Preview */}
            {generatedDoc && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-green-500" />
                      Generated: {generatedDoc.title}
                    </span>
                    <Button
                      variant="outline"
                      onClick={() => handleDownload(generatedDoc.content, generatedDoc.title)}
                      data-testid="download-btn"
                    >
                      <Download className="w-4 h-4 mr-2" />
                      Download
                    </Button>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[400px] w-full rounded-lg border bg-muted/30 p-4">
                    <pre className="whitespace-pre-wrap font-mono text-sm">
                      {generatedDoc.content}
                    </pre>
                  </ScrollArea>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* My Documents Tab */}
          <TabsContent value="documents">
            {myDocuments.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <FileText className="w-16 h-16 text-muted-foreground/50 mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No Documents Yet</h3>
                  <p className="text-muted-foreground text-center max-w-md">
                    You haven't generated any legal documents yet. Select an encounter and document type to create your first document.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {myDocuments.map(doc => (
                  <Card key={doc.document_id} className="hover:shadow-md transition-shadow">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-2xl">{getDocTypeIcon(doc.document_type)}</span>
                          <div>
                            <CardTitle className="text-base">{doc.title}</CardTitle>
                            <CardDescription className="text-xs">
                              {formatDate(doc.created_at)}
                            </CardDescription>
                          </div>
                        </div>
                        <Badge variant="secondary" className="text-xs">
                          {doc.status}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <p className="text-sm text-muted-foreground line-clamp-3 mb-4">
                        {doc.content?.substring(0, 150)}...
                      </p>
                      <div className="flex gap-2">
                        <Dialog>
                          <DialogTrigger asChild>
                            <Button variant="outline" size="sm" className="flex-1">
                              View
                            </Button>
                          </DialogTrigger>
                          <DialogContent className="max-w-3xl max-h-[80vh]">
                            <DialogHeader>
                              <DialogTitle>{doc.title}</DialogTitle>
                              <DialogDescription>
                                Generated on {formatDate(doc.created_at)}
                              </DialogDescription>
                            </DialogHeader>
                            <ScrollArea className="h-[500px] mt-4">
                              <pre className="whitespace-pre-wrap font-mono text-sm p-4 bg-muted rounded-lg">
                                {doc.content}
                              </pre>
                            </ScrollArea>
                            <div className="flex justify-end gap-2 mt-4">
                              <Button
                                variant="outline"
                                onClick={() => handleDownload(doc.content, doc.title)}
                              >
                                <Download className="w-4 h-4 mr-2" />
                                Download
                              </Button>
                            </div>
                          </DialogContent>
                        </Dialog>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDownload(doc.content, doc.title)}
                        >
                          <Download className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => openShareDialog(doc)}
                          className="text-blue-600 hover:text-blue-700"
                        >
                          <Share2 className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDelete(doc.document_id)}
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Received Documents Tab */}
          <TabsContent value="received">
            {receivedShares.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Inbox className="w-16 h-16 text-muted-foreground/50 mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No Documents Received</h3>
                  <p className="text-muted-foreground text-center max-w-md">
                    You haven't received any shared documents yet. Documents shared with you by attorneys or other users will appear here.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {receivedShares.map(share => (
                  <Card key={share.share_id} className="hover:shadow-md transition-shadow">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-2xl">{getDocTypeIcon(share.document_type)}</span>
                          <div>
                            <CardTitle className="text-base">{share.document_title}</CardTitle>
                            <CardDescription className="text-xs">
                              From: {share.owner_name}
                            </CardDescription>
                          </div>
                        </div>
                        <Badge variant={share.status === 'pending' ? 'default' : 'secondary'} className="text-xs">
                          {share.status}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <p className="text-xs text-muted-foreground mb-2">
                        <Clock className="w-3 h-3 inline mr-1" />
                        {formatDate(share.shared_at)}
                      </p>
                      {share.message && (
                        <p className="text-sm text-muted-foreground italic mb-3">
                          "{share.message}"
                        </p>
                      )}
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button variant="outline" size="sm" className="w-full">
                            View Document
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-3xl max-h-[80vh]">
                          <DialogHeader>
                            <DialogTitle>{share.document_title}</DialogTitle>
                            <DialogDescription>
                              Shared by {share.owner_name} on {formatDate(share.shared_at)}
                            </DialogDescription>
                          </DialogHeader>
                          <ScrollArea className="h-[500px] mt-4">
                            <SharedDocumentContent shareId={share.share_id} />
                          </ScrollArea>
                        </DialogContent>
                      </Dialog>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Sent Documents Tab */}
          <TabsContent value="sent">
            {sentShares.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Send className="w-16 h-16 text-muted-foreground/50 mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No Documents Sent</h3>
                  <p className="text-muted-foreground text-center max-w-md">
                    You haven't shared any documents yet. Use the share button on your documents to share them with attorneys.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {sentShares.map(share => (
                  <Card key={share.share_id} className="hover:shadow-md transition-shadow">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-2xl">{getDocTypeIcon(share.document_type)}</span>
                          <div>
                            <CardTitle className="text-base">{share.document_title}</CardTitle>
                            <CardDescription className="text-xs">
                              To: {share.recipient_name}
                            </CardDescription>
                          </div>
                        </div>
                        <Badge 
                          variant={share.status === 'viewed' ? 'success' : 'secondary'} 
                          className={`text-xs ${share.status === 'viewed' ? 'bg-green-500/10 text-green-600' : ''}`}
                        >
                          {share.status}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <p className="text-xs text-muted-foreground mb-2">
                        <Clock className="w-3 h-3 inline mr-1" />
                        Sent: {formatDate(share.shared_at)}
                      </p>
                      {share.viewed_at && (
                        <p className="text-xs text-green-600">
                          <CheckCircle className="w-3 h-3 inline mr-1" />
                          Viewed: {formatDate(share.viewed_at)}
                        </p>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>

        {/* Share Dialog */}
        <Dialog open={shareDialogOpen} onOpenChange={setShareDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Share Document</DialogTitle>
              <DialogDescription>
                Share "{docToShare?.title}" with an attorney or contact
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Select Recipient</Label>
                <Select value={shareRecipient} onValueChange={setShareRecipient}>
                  <SelectTrigger>
                    <SelectValue placeholder="Choose a recipient..." />
                  </SelectTrigger>
                  <SelectContent>
                    {attorneys.length > 0 && (
                      <>
                        <SelectItem value="header-attorneys" disabled>
                          — My Attorneys —
                        </SelectItem>
                        {attorneys.map(att => (
                          <SelectItem key={att.attorney_id || att.user_id} value={att.attorney_id || att.user_id}>
                            {att.name} ({att.email})
                          </SelectItem>
                        ))}
                      </>
                    )}
                    {attorneys.length === 0 && (
                      <SelectItem value="none" disabled>
                        No attorneys connected. Find an attorney first.
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Message (Optional)</Label>
                <Textarea
                  placeholder="Add a message for the recipient..."
                  value={shareMessage}
                  onChange={(e) => setShareMessage(e.target.value)}
                  className="min-h-[80px]"
                />
              </div>
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>
              <Button onClick={handleShare} disabled={sharing || !shareRecipient}>
                {sharing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Sharing...
                  </>
                ) : (
                  <>
                    <Share2 className="w-4 h-4 mr-2" />
                    Share Document
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Info Banner */}
        <Card className="bg-amber-500/10 border-amber-500/20">
          <CardContent className="flex items-start gap-4 py-4">
            <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5" />
            <div>
              <h4 className="font-semibold text-amber-700 dark:text-amber-400">Important Notice</h4>
              <p className="text-sm text-amber-700/80 dark:text-amber-400/80">
                AI-generated documents are provided for informational purposes only. Always review generated documents carefully and consult with a qualified attorney before submitting any legal documents.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}

// Helper component to load shared document content
function SharedDocumentContent({ shareId }) {
  const [content, setContent] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadContent = async () => {
      try {
        const response = await documentsAPI.getSharedDocument(shareId);
        setContent(response.data.document?.content || 'Document content not available');
      } catch (error) {
        setContent('Failed to load document content');
      } finally {
        setLoading(false);
      }
    };
    loadContent();
  }, [shareId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-6 h-6 animate-spin" />
      </div>
    );
  }

  return (
    <pre className="whitespace-pre-wrap font-mono text-sm p-4 bg-muted rounded-lg">
      {content}
    </pre>
  );
}
