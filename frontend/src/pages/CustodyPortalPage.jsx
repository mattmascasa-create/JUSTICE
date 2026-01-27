import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Separator } from '../components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Alert, AlertDescription } from '../components/ui/alert';
import api from '../lib/api';
import { toast } from 'sonner';
import { 
  Shield, FileText, Clock, CheckCircle, XCircle, 
  AlertTriangle, Download, Eye, Lock, User,
  Link2, History, Fingerprint, Scale, ChevronRight,
  ExternalLink, Calendar, MapPin, Hash, Loader2
} from 'lucide-react';

export default function CustodyPortalPage() {
  const [searchParams] = useSearchParams();
  const tokenFromUrl = searchParams.get('token');
  
  const [accessToken, setAccessToken] = useState(tokenFromUrl || '');
  const [tokenVerified, setTokenVerified] = useState(false);
  const [tokenInfo, setTokenInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Data states
  const [evidence, setEvidence] = useState(null);
  const [chainOfCustody, setChainOfCustody] = useState(null);
  const [integrityReport, setIntegrityReport] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    if (tokenFromUrl) {
      verifyToken(tokenFromUrl);
    }
  }, [tokenFromUrl]);

  const verifyToken = async (token) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.post('/custody-portal/verify-access', { access_token: token });
      setTokenInfo(response.data);
      setTokenVerified(true);
      
      // Load all data
      await Promise.all([
        loadEvidence(token),
        loadChainOfCustody(token),
        loadIntegrityReport(token)
      ]);
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid or expired access token');
      setTokenVerified(false);
    } finally {
      setLoading(false);
    }
  };

  const loadEvidence = async (token) => {
    try {
      const response = await api.get(`/custody-portal/evidence?token=${token}`);
      setEvidence(response.data);
    } catch (err) {
      console.error('Error loading evidence:', err);
    }
  };

  const loadChainOfCustody = async (token) => {
    try {
      const response = await api.get(`/custody-portal/chain-of-custody?token=${token}`);
      setChainOfCustody(response.data);
    } catch (err) {
      console.error('Error loading chain of custody:', err);
    }
  };

  const loadIntegrityReport = async (token) => {
    try {
      const response = await api.get(`/custody-portal/integrity-report?token=${token}`);
      setIntegrityReport(response.data);
    } catch (err) {
      console.error('Error loading integrity report:', err);
    }
  };

  const downloadCourtPackage = async () => {
    try {
      const response = await api.get(`/custody-portal/download-court-package?token=${accessToken}`);
      
      // Download as JSON
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `court_package_${evidence?.evidence?.evidence_id || 'evidence'}.json`;
      a.click();
      URL.revokeObjectURL(url);
      
      toast.success('Court package downloaded');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to download court package');
    }
  };

  const handleSubmitToken = (e) => {
    e.preventDefault();
    if (accessToken.trim()) {
      verifyToken(accessToken.trim());
    }
  };

  // Token entry screen
  if (!tokenVerified) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 flex items-center justify-center p-4">
        <Card className="w-full max-w-md" data-testid="custody-portal-login">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 p-4 rounded-full bg-blue-500/10">
              <Shield className="h-12 w-12 text-blue-500" />
            </div>
            <CardTitle className="text-2xl">Evidence Chain of Custody Portal</CardTitle>
            <CardDescription>
              Enter your access token to view evidence and its complete audit trail
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmitToken} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="access-token">Access Token</Label>
                <Input
                  id="access-token"
                  type="text"
                  placeholder="Enter your secure access token"
                  value={accessToken}
                  onChange={(e) => setAccessToken(e.target.value)}
                  className="font-mono text-sm"
                  data-testid="access-token-input"
                />
              </div>
              
              {error && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              
              <Button 
                type="submit" 
                className="w-full" 
                disabled={loading || !accessToken.trim()}
                data-testid="verify-token-btn"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  <>
                    <Lock className="h-4 w-4 mr-2" />
                    Access Portal
                  </>
                )}
              </Button>
            </form>
            
            <div className="mt-6 pt-6 border-t text-center text-sm text-muted-foreground">
              <p>This portal provides secure access to evidence chain of custody records.</p>
              <p className="mt-2">
                <Scale className="h-4 w-4 inline mr-1" />
                FRE 901/707 Compliant
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-white">Loading evidence records...</p>
        </div>
      </div>
    );
  }

  // Main portal view
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 text-white" data-testid="custody-portal">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-900/50 backdrop-blur sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Shield className="h-8 w-8 text-blue-500" />
              <div>
                <h1 className="font-bold text-lg">JUSTICE Evidence Portal</h1>
                <p className="text-xs text-slate-400">Chain of Custody Viewer</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <Badge variant="outline" className="text-green-400 border-green-400/50">
                <CheckCircle className="h-3 w-3 mr-1" />
                Verified Access
              </Badge>
              <div className="text-right text-sm">
                <p className="text-slate-400">Viewing as</p>
                <p className="font-medium">{tokenInfo?.recipient_name} ({tokenInfo?.recipient_role})</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Access Info Banner */}
        <Alert className="mb-6 bg-blue-500/10 border-blue-500/30">
          <Lock className="h-4 w-4 text-blue-400" />
          <AlertDescription className="text-blue-200">
            You have <strong>{tokenInfo?.access_level}</strong> access to this evidence. 
            Access expires on {new Date(tokenInfo?.expires_at).toLocaleString()}.
            {tokenInfo?.notes && <span className="block mt-1 text-sm">Note: {tokenInfo.notes}</span>}
          </AlertDescription>
        </Alert>

        {/* Evidence Overview Card */}
        {evidence && (
          <Card className="mb-6 bg-slate-800/50 border-slate-700">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-white flex items-center gap-2">
                    <FileText className="h-5 w-5 text-blue-400" />
                    {evidence.evidence?.filename || 'Evidence File'}
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    Evidence ID: {evidence.evidence?.evidence_id}
                  </CardDescription>
                </div>
                {(tokenInfo?.access_level === 'download' || tokenInfo?.access_level === 'full') && (
                  <Button onClick={downloadCourtPackage} data-testid="download-court-package-btn">
                    <Download className="h-4 w-4 mr-2" />
                    Download Court Package
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-4 rounded-lg bg-slate-700/50">
                  <p className="text-xs text-slate-400 mb-1">File Type</p>
                  <p className="font-medium">{evidence.evidence?.file_type || 'Unknown'}</p>
                </div>
                <div className="p-4 rounded-lg bg-slate-700/50">
                  <p className="text-xs text-slate-400 mb-1">File Size</p>
                  <p className="font-medium">{formatFileSize(evidence.evidence?.file_size)}</p>
                </div>
                <div className="p-4 rounded-lg bg-slate-700/50">
                  <p className="text-xs text-slate-400 mb-1">Created</p>
                  <p className="font-medium">{new Date(evidence.evidence?.created_at).toLocaleDateString()}</p>
                </div>
                <div className="p-4 rounded-lg bg-slate-700/50">
                  <p className="text-xs text-slate-400 mb-1">Owner</p>
                  <p className="font-medium">{evidence.access_info?.owner_name}</p>
                </div>
              </div>
              
              {evidence.encounter && (
                <div className="mt-4 p-4 rounded-lg bg-slate-700/30 border border-slate-600">
                  <p className="text-sm text-slate-400 mb-2">Associated Encounter</p>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="flex items-center gap-1">
                      <Badge variant="outline">{evidence.encounter.encounter_type?.replace(/_/g, ' ')}</Badge>
                    </span>
                    {evidence.encounter.address && (
                      <span className="flex items-center gap-1 text-slate-300">
                        <MapPin className="h-3 w-3" />
                        {evidence.encounter.address}
                      </span>
                    )}
                    <span className="flex items-center gap-1 text-slate-300">
                      <Calendar className="h-3 w-3" />
                      {new Date(evidence.encounter.started_at).toLocaleString()}
                    </span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="bg-slate-800 border-slate-700">
            <TabsTrigger value="overview" className="data-[state=active]:bg-blue-600" data-testid="tab-overview">
              <Eye className="h-4 w-4 mr-2" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="custody" className="data-[state=active]:bg-blue-600" data-testid="tab-custody">
              <History className="h-4 w-4 mr-2" />
              Chain of Custody
            </TabsTrigger>
            <TabsTrigger value="integrity" className="data-[state=active]:bg-blue-600" data-testid="tab-integrity">
              <Fingerprint className="h-4 w-4 mr-2" />
              Integrity Verification
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview">
            {integrityReport && (
              <div className="grid md:grid-cols-2 gap-6">
                {/* Integrity Status */}
                <Card className="bg-slate-800/50 border-slate-700">
                  <CardHeader>
                    <CardTitle className="text-white text-lg">Integrity Status</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between p-4 rounded-lg bg-slate-700/50">
                      <span className="text-slate-300">Hash Verification</span>
                      {integrityReport.integrity?.hash_match ? (
                        <Badge className="bg-green-600">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Verified
                        </Badge>
                      ) : (
                        <Badge variant="destructive">
                          <XCircle className="h-3 w-3 mr-1" />
                          Failed
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center justify-between p-4 rounded-lg bg-slate-700/50">
                      <span className="text-slate-300">Chain of Custody</span>
                      {integrityReport.integrity?.chain_of_custody_intact ? (
                        <Badge className="bg-green-600">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Intact
                        </Badge>
                      ) : (
                        <Badge variant="destructive">
                          <XCircle className="h-3 w-3 mr-1" />
                          Broken
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center justify-between p-4 rounded-lg bg-slate-700/50">
                      <span className="text-slate-300">Blockchain Anchored</span>
                      {integrityReport.blockchain_proof ? (
                        <Badge className="bg-green-600">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Yes
                        </Badge>
                      ) : (
                        <Badge variant="secondary">
                          <Clock className="h-3 w-3 mr-1" />
                          Pending
                        </Badge>
                      )}
                    </div>
                  </CardContent>
                </Card>

                {/* Custody Summary */}
                <Card className="bg-slate-800/50 border-slate-700">
                  <CardHeader>
                    <CardTitle className="text-white text-lg">Custody Summary</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between p-4 rounded-lg bg-slate-700/50">
                      <span className="text-slate-300">Total Events</span>
                      <span className="text-xl font-bold">{integrityReport.chain_of_custody?.total_events || 0}</span>
                    </div>
                    {integrityReport.chain_of_custody?.first_event && (
                      <div className="p-4 rounded-lg bg-slate-700/50">
                        <p className="text-xs text-slate-400 mb-1">First Recorded</p>
                        <p className="text-sm">{new Date(integrityReport.chain_of_custody.first_event.timestamp).toLocaleString()}</p>
                        <p className="text-xs text-slate-400 mt-1">By: {integrityReport.chain_of_custody.first_event.actor_name}</p>
                      </div>
                    )}
                    {integrityReport.chain_of_custody?.last_event && (
                      <div className="p-4 rounded-lg bg-slate-700/50">
                        <p className="text-xs text-slate-400 mb-1">Last Activity</p>
                        <p className="text-sm">{new Date(integrityReport.chain_of_custody.last_event.timestamp).toLocaleString()}</p>
                        <p className="text-xs text-slate-400 mt-1">Action: {integrityReport.chain_of_custody.last_event.action}</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Legal Notice */}
            <Card className="mt-6 bg-slate-800/50 border-slate-700">
              <CardContent className="p-6">
                <div className="flex items-start gap-4">
                  <Scale className="h-8 w-8 text-blue-400 flex-shrink-0" />
                  <div>
                    <h3 className="font-semibold text-white mb-2">Legal Notice</h3>
                    <p className="text-sm text-slate-300">
                      {integrityReport?.legal_notice?.disclaimer || 
                        'This report is generated automatically and should be reviewed by legal counsel before use in court proceedings.'}
                    </p>
                    <div className="mt-3 flex items-center gap-4 text-xs text-slate-400">
                      <span className="flex items-center gap-1">
                        <Badge variant="outline" className="text-blue-400">
                          {integrityReport?.legal_notice?.standard || 'FRE 901/707 Compliant'}
                        </Badge>
                      </span>
                      <span>Generated for: {integrityReport?.legal_notice?.generated_for}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Chain of Custody Tab */}
          <TabsContent value="custody">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <History className="h-5 w-5 text-blue-400" />
                  Complete Chain of Custody
                </CardTitle>
                <CardDescription className="text-slate-400">
                  {chainOfCustody?.total_events || 0} recorded events
                </CardDescription>
              </CardHeader>
              <CardContent>
                {chainOfCustody?.chain_of_custody?.length > 0 ? (
                  <div className="space-y-4">
                    {chainOfCustody.chain_of_custody.map((event, index) => (
                      <div 
                        key={event.event_id || index}
                        className="relative pl-8 pb-4 border-l-2 border-slate-600 last:border-l-transparent"
                      >
                        {/* Timeline dot */}
                        <div className={`absolute -left-2 top-0 w-4 h-4 rounded-full ${
                          event.action === 'created' ? 'bg-green-500' :
                          event.action === 'verified' ? 'bg-blue-500' :
                          event.action === 'shared' ? 'bg-purple-500' :
                          event.action === 'exported' ? 'bg-yellow-500' :
                          'bg-slate-500'
                        }`} />
                        
                        <div className="bg-slate-700/50 rounded-lg p-4">
                          <div className="flex items-start justify-between">
                            <div>
                              <Badge variant="outline" className="mb-2">
                                {event.action?.toUpperCase()}
                              </Badge>
                              <p className="text-sm text-slate-300">
                                {event.actor_name || 'System'}
                              </p>
                            </div>
                            <span className="text-xs text-slate-400">
                              {new Date(event.timestamp).toLocaleString()}
                            </span>
                          </div>
                          
                          {event.details && Object.keys(event.details).length > 0 && (
                            <div className="mt-3 pt-3 border-t border-slate-600">
                              <p className="text-xs text-slate-400 mb-1">Details:</p>
                              <pre className="text-xs text-slate-300 bg-slate-800 p-2 rounded overflow-x-auto">
                                {JSON.stringify(event.details, null, 2)}
                              </pre>
                            </div>
                          )}
                          
                          {event.event_hash && (
                            <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
                              <Hash className="h-3 w-3" />
                              <span className="font-mono truncate">{event.event_hash}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 text-slate-400">
                    <History className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No custody events recorded</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Integrity Tab */}
          <TabsContent value="integrity">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Fingerprint className="h-5 w-5 text-blue-400" />
                  Cryptographic Verification
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {integrityReport?.integrity && (
                  <>
                    {/* Hash Values */}
                    <div className="space-y-3">
                      <h4 className="text-sm font-medium text-slate-300">File Hashes</h4>
                      <div className="space-y-2">
                        <div className="p-3 rounded-lg bg-slate-700/50">
                          <p className="text-xs text-slate-400 mb-1">SHA-256 (Original)</p>
                          <p className="font-mono text-xs text-slate-300 break-all">
                            {integrityReport.integrity.original_hash || 'Not available'}
                          </p>
                        </div>
                        <div className="p-3 rounded-lg bg-slate-700/50">
                          <p className="text-xs text-slate-400 mb-1">SHA-256 (Current)</p>
                          <p className="font-mono text-xs text-slate-300 break-all">
                            {integrityReport.integrity.current_hash || 'Not available'}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Verification Status */}
                    <div className="grid sm:grid-cols-3 gap-4">
                      <div className={`p-4 rounded-lg text-center ${
                        integrityReport.integrity.hash_match 
                          ? 'bg-green-500/10 border border-green-500/30' 
                          : 'bg-red-500/10 border border-red-500/30'
                      }`}>
                        {integrityReport.integrity.hash_match ? (
                          <CheckCircle className="h-8 w-8 text-green-500 mx-auto mb-2" />
                        ) : (
                          <XCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
                        )}
                        <p className="text-sm font-medium">Hash Match</p>
                        <p className="text-xs text-slate-400">
                          {integrityReport.integrity.hash_match ? 'File unmodified' : 'File modified!'}
                        </p>
                      </div>
                      
                      <div className={`p-4 rounded-lg text-center ${
                        integrityReport.integrity.chain_of_custody_intact 
                          ? 'bg-green-500/10 border border-green-500/30' 
                          : 'bg-red-500/10 border border-red-500/30'
                      }`}>
                        {integrityReport.integrity.chain_of_custody_intact ? (
                          <CheckCircle className="h-8 w-8 text-green-500 mx-auto mb-2" />
                        ) : (
                          <XCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
                        )}
                        <p className="text-sm font-medium">Custody Chain</p>
                        <p className="text-xs text-slate-400">
                          {integrityReport.integrity.custody_events} events recorded
                        </p>
                      </div>
                      
                      <div className={`p-4 rounded-lg text-center ${
                        integrityReport.integrity.blockchain_verified 
                          ? 'bg-green-500/10 border border-green-500/30' 
                          : 'bg-slate-700/50'
                      }`}>
                        {integrityReport.integrity.blockchain_verified ? (
                          <CheckCircle className="h-8 w-8 text-green-500 mx-auto mb-2" />
                        ) : (
                          <Clock className="h-8 w-8 text-slate-400 mx-auto mb-2" />
                        )}
                        <p className="text-sm font-medium">Blockchain</p>
                        <p className="text-xs text-slate-400">
                          {integrityReport.integrity.blockchain_verified ? 'Anchored' : 'Not anchored'}
                        </p>
                      </div>
                    </div>

                    {/* Warnings */}
                    {integrityReport.integrity.warnings?.length > 0 && (
                      <Alert variant="destructive">
                        <AlertTriangle className="h-4 w-4" />
                        <AlertDescription>
                          <ul className="list-disc list-inside">
                            {integrityReport.integrity.warnings.map((w, i) => (
                              <li key={i}>{w}</li>
                            ))}
                          </ul>
                        </AlertDescription>
                      </Alert>
                    )}
                  </>
                )}

                {/* Blockchain Proof */}
                {integrityReport?.blockchain_proof && (
                  <div className="space-y-3">
                    <h4 className="text-sm font-medium text-slate-300">Blockchain Proof</h4>
                    <div className="p-4 rounded-lg bg-slate-700/50">
                      <div className="grid sm:grid-cols-2 gap-4 text-sm">
                        <div>
                          <p className="text-xs text-slate-400 mb-1">Network</p>
                          <p className="text-slate-300">{integrityReport.blockchain_proof.network || 'Local'}</p>
                        </div>
                        <div>
                          <p className="text-xs text-slate-400 mb-1">Anchored At</p>
                          <p className="text-slate-300">
                            {new Date(integrityReport.blockchain_proof.anchored_at).toLocaleString()}
                          </p>
                        </div>
                        {integrityReport.blockchain_proof.transaction_hash && (
                          <div className="sm:col-span-2">
                            <p className="text-xs text-slate-400 mb-1">Transaction Hash</p>
                            <p className="font-mono text-xs text-slate-300 break-all">
                              {integrityReport.blockchain_proof.transaction_hash}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-700 mt-12 py-6">
        <div className="max-w-6xl mx-auto px-4 text-center text-sm text-slate-400">
          <p>JUSTICE Platform - Evidence Chain of Custody Portal</p>
          <p className="mt-1">Report generated at {new Date().toLocaleString()}</p>
        </div>
      </footer>
    </div>
  );
}

// Helper function
function formatFileSize(bytes) {
  if (!bytes) return 'Unknown';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  while (bytes >= 1024 && i < units.length - 1) {
    bytes /= 1024;
    i++;
  }
  return `${bytes.toFixed(1)} ${units[i]}`;
}
