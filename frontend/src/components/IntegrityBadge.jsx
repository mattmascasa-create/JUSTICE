/**
 * IntegrityBadge Component
 * Displays evidence integrity verification status with visual indicators
 */

import React, { useState, useEffect } from 'react';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from './ui/dialog';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Separator } from './ui/separator';
import { 
  Shield, ShieldCheck, ShieldAlert, Lock, FileCheck, 
  CheckCircle, AlertTriangle, Copy, Download, Loader2,
  Link2, Hash
} from 'lucide-react';
import { encounterAPI } from '../lib/api';
import evidenceStorage from '../services/evidenceStorage';
import { toast } from 'sonner';

export function IntegrityBadge({ encounterId, compact = false }) {
  const [status, setStatus] = useState('unknown'); // unknown, verifying, verified, warning
  const [report, setReport] = useState(null);
  const [localReport, setLocalReport] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  const [loading, setLoading] = useState(false);

  // Verify integrity on mount
  useEffect(() => {
    if (encounterId) {
      verifyLocalIntegrity();
    }
  }, [encounterId]);

  const verifyLocalIntegrity = async () => {
    try {
      setStatus('verifying');
      const localVerification = await evidenceStorage.generateIntegrityReport(encounterId);
      setLocalReport(localVerification);
      
      if (localVerification.verification.status === 'VERIFIED') {
        setStatus('verified');
      } else {
        setStatus('warning');
      }
    } catch (error) {
      console.error('Local integrity check failed:', error);
      setStatus('unknown');
    }
  };

  const verifyServerIntegrity = async () => {
    setLoading(true);
    try {
      const response = await encounterAPI.verifyIntegrity(encounterId);
      setReport(response.data.report);
      
      if (response.data.report.verification.status === 'VERIFIED') {
        setStatus('verified');
        toast.success('Evidence integrity verified!');
      } else {
        setStatus('warning');
        toast.warning('Integrity verification found issues');
      }
    } catch (error) {
      console.error('Server integrity check failed:', error);
      toast.error('Failed to verify server-side integrity');
    } finally {
      setLoading(false);
    }
  };

  const getCertificate = async () => {
    setLoading(true);
    try {
      const response = await encounterAPI.getIntegrityCertificate(encounterId);
      
      // Create downloadable certificate
      const certText = JSON.stringify(response.data.certificate, null, 2);
      const blob = new Blob([certText], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `integrity-certificate-${encounterId}.json`;
      a.click();
      URL.revokeObjectURL(url);
      
      toast.success('Certificate downloaded');
    } catch (error) {
      toast.error('Failed to generate certificate');
    } finally {
      setLoading(false);
    }
  };

  const copyHash = (hash) => {
    navigator.clipboard.writeText(hash);
    toast.success('Hash copied to clipboard');
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'verified':
        return <ShieldCheck className="h-4 w-4 text-green-500" />;
      case 'warning':
        return <ShieldAlert className="h-4 w-4 text-yellow-500" />;
      case 'verifying':
        return <Loader2 className="h-4 w-4 animate-spin" />;
      default:
        return <Shield className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'verified':
        return 'bg-green-500/10 text-green-600 border-green-500/30';
      case 'warning':
        return 'bg-yellow-500/10 text-yellow-600 border-yellow-500/30';
      case 'verifying':
        return 'bg-blue-500/10 text-blue-600 border-blue-500/30';
      default:
        return 'bg-muted text-muted-foreground';
    }
  };

  if (compact) {
    return (
      <Badge variant="outline" className={`gap-1 ${getStatusColor()}`}>
        {getStatusIcon()}
        {status === 'verified' ? 'Verified' : status === 'warning' ? 'Check Required' : 'Integrity'}
      </Badge>
    );
  }

  return (
    <Dialog open={showDetails} onOpenChange={setShowDetails}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className={`gap-2 ${getStatusColor()}`}>
          {getStatusIcon()}
          <span>Evidence Integrity</span>
          {status === 'verified' && <CheckCircle className="h-3 w-3" />}
        </Button>
      </DialogTrigger>
      
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Lock className="h-5 w-5" />
            Evidence Integrity Verification
          </DialogTitle>
          <DialogDescription>
            Cryptographic verification ensures your evidence has not been tampered with
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Status Card */}
          <Card className={status === 'verified' ? 'border-green-500/50' : status === 'warning' ? 'border-yellow-500/50' : ''}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-full ${status === 'verified' ? 'bg-green-500/20' : 'bg-yellow-500/20'}`}>
                    {status === 'verified' ? (
                      <ShieldCheck className="h-6 w-6 text-green-500" />
                    ) : (
                      <ShieldAlert className="h-6 w-6 text-yellow-500" />
                    )}
                  </div>
                  <div>
                    <p className="font-bold text-lg">
                      {status === 'verified' ? 'Evidence Verified' : 'Verification Status'}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {status === 'verified' 
                        ? 'All evidence chunks have valid cryptographic signatures'
                        : 'Click verify to check evidence integrity'}
                    </p>
                  </div>
                </div>
                <Button onClick={verifyServerIntegrity} disabled={loading}>
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileCheck className="h-4 w-4 mr-2" />}
                  Verify
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Local Verification Results */}
          {localReport && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Hash className="h-4 w-4" />
                  Local Verification (Device)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div className="text-center p-2 bg-muted/30 rounded">
                    <p className="text-2xl font-bold">{localReport.verification?.totalChunks || 0}</p>
                    <p className="text-xs text-muted-foreground">Total Chunks</p>
                  </div>
                  <div className="text-center p-2 bg-muted/30 rounded">
                    <p className="text-2xl font-bold">{localReport.verification?.audioChunks || 0}</p>
                    <p className="text-xs text-muted-foreground">Audio</p>
                  </div>
                  <div className="text-center p-2 bg-muted/30 rounded">
                    <p className="text-2xl font-bold">{localReport.verification?.videoChunks || 0}</p>
                    <p className="text-xs text-muted-foreground">Video</p>
                  </div>
                </div>
                
                <div className="flex items-center gap-2 p-2 bg-muted/30 rounded">
                  <Link2 className="h-4 w-4" />
                  <span className="text-sm">Chain Integrity:</span>
                  {localReport.verification?.chainIntact ? (
                    <Badge className="bg-green-500">Intact</Badge>
                  ) : (
                    <Badge variant="destructive">Broken</Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Server Verification Results */}
          {report && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4" />
                  Server Verification
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="p-3 bg-muted/30 rounded">
                  <p className="text-sm font-medium mb-2">Hash Algorithm: {report.hash_algorithm}</p>
                  <p className="text-sm">Status: <Badge className={report.verification.chain_intact ? 'bg-green-500' : 'bg-yellow-500'}>{report.verification.status}</Badge></p>
                </div>
                
                {report.evidence_chain?.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Evidence Chain:</p>
                    <div className="max-h-40 overflow-y-auto space-y-1">
                      {report.evidence_chain.slice(0, 5).map((chunk, idx) => (
                        <div key={idx} className="flex items-center gap-2 p-2 bg-muted/20 rounded text-xs">
                          <Badge variant="outline">{chunk.type}</Badge>
                          <span>#{chunk.index}</span>
                          <code className="flex-1 truncate font-mono text-muted-foreground">
                            {chunk.content_hash?.substring(0, 24)}...
                          </code>
                          <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => copyHash(chunk.content_hash)}>
                            <Copy className="h-3 w-3" />
                          </Button>
                        </div>
                      ))}
                      {report.evidence_chain.length > 5 && (
                        <p className="text-xs text-muted-foreground text-center">
                          + {report.evidence_chain.length - 5} more chunks
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          <Separator />

          {/* Actions */}
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Certificates can be used as evidence in legal proceedings
            </p>
            <Button onClick={getCertificate} disabled={loading} variant="outline">
              <Download className="h-4 w-4 mr-2" />
              Download Certificate
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default IntegrityBadge;
