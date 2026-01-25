import React, { useState } from 'react';
import { Shield, CheckCircle, AlertTriangle, ExternalLink, Loader2, Lock, Clock, FileText, Link2 } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Card, CardContent } from './ui/card';
import { Separator } from './ui/separator';
import { ScrollArea } from './ui/scroll-area';
import { evidenceIntegrityAPI } from '../lib/api';
import { toast } from 'sonner';

export function EvidenceVerificationBadge({ evidenceId, showDetails = false, className = '' }) {
  const [loading, setLoading] = useState(false);
  const [verificationData, setVerificationData] = useState(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [custodyChain, setCustodyChain] = useState([]);

  const handleVerify = async () => {
    setLoading(true);
    try {
      const response = await evidenceIntegrityAPI.verify(evidenceId);
      setVerificationData(response.data);
      if (response.data.is_valid) {
        toast.success('Evidence integrity verified!');
      } else {
        toast.warning('Evidence verification issues detected');
      }
    } catch (error) {
      toast.error('Failed to verify evidence');
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetails = async () => {
    setLoading(true);
    try {
      const [verifyRes, custodyRes] = await Promise.all([
        evidenceIntegrityAPI.verify(evidenceId),
        evidenceIntegrityAPI.getCustodyChain(evidenceId)
      ]);
      setVerificationData(verifyRes.data);
      setCustodyChain(custodyRes.data.chain || []);
      setDetailsOpen(true);
    } catch (error) {
      toast.error('Failed to load verification details');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Badge variant="outline" className={className}>
        <Loader2 className="w-3 h-3 mr-1 animate-spin" />
        Verifying...
      </Badge>
    );
  }

  if (!verificationData) {
    return (
      <Button 
        variant="outline" 
        size="sm" 
        onClick={showDetails ? handleViewDetails : handleVerify}
        className={className}
        data-testid="verify-evidence-btn"
      >
        <Shield className="w-4 h-4 mr-1" />
        Verify
      </Button>
    );
  }

  return (
    <>
      <Badge 
        variant={verificationData.is_valid ? 'default' : 'destructive'}
        className={`cursor-pointer ${className}`}
        onClick={handleViewDetails}
        data-testid="verification-badge"
      >
        {verificationData.is_valid ? (
          <>
            <CheckCircle className="w-3 h-3 mr-1" />
            Court-Verified
          </>
        ) : (
          <>
            <AlertTriangle className="w-3 h-3 mr-1" />
            Issues Detected
          </>
        )}
      </Badge>

      {/* Verification Details Dialog */}
      <Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-primary" />
              Court-Grade Evidence Verification
            </DialogTitle>
            <DialogDescription>
              Cryptographic verification and chain of custody for legal proceedings
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6">
            {/* Verification Status */}
            <Card className={verificationData.is_valid ? 'border-green-500/50 bg-green-500/5' : 'border-red-500/50 bg-red-500/5'}>
              <CardContent className="pt-4">
                <div className="flex items-center gap-3">
                  {verificationData.is_valid ? (
                    <CheckCircle className="w-8 h-8 text-green-500" />
                  ) : (
                    <AlertTriangle className="w-8 h-8 text-red-500" />
                  )}
                  <div>
                    <p className="font-semibold text-lg">
                      {verificationData.is_valid ? 'Evidence Integrity Verified' : 'Verification Issues Detected'}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Last verified: {new Date(verificationData.last_verified).toLocaleString()}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Hash Verification */}
            <div>
              <h4 className="font-semibold mb-3 flex items-center gap-2">
                <Lock className="w-4 h-4" />
                Cryptographic Hashes
              </h4>
              <div className="space-y-2 bg-muted/50 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Hash Match:</span>
                  <Badge variant={verificationData.hash_match ? 'default' : 'destructive'}>
                    {verificationData.hash_match ? 'Verified' : 'Mismatch'}
                  </Badge>
                </div>
                <Separator />
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Original SHA-256:</p>
                  <code className="text-xs bg-background p-2 rounded block break-all">
                    {verificationData.original_hash}
                  </code>
                </div>
                {verificationData.current_hash !== verificationData.original_hash && (
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Current Hash:</p>
                    <code className="text-xs bg-background p-2 rounded block break-all text-red-500">
                      {verificationData.current_hash}
                    </code>
                  </div>
                )}
              </div>
            </div>

            {/* Blockchain Proof */}
            <div>
              <h4 className="font-semibold mb-3 flex items-center gap-2">
                <Link2 className="w-4 h-4" />
                Blockchain Anchoring
              </h4>
              <div className="bg-muted/50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-muted-foreground">Status:</span>
                  <Badge variant={verificationData.blockchain_verified ? 'default' : 'secondary'}>
                    {verificationData.blockchain_verified ? 'Anchored' : 'Local Only'}
                  </Badge>
                </div>
                {verificationData.blockchain_proof && (
                  <div className="space-y-2 mt-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Network:</span>
                      <span className="capitalize">{verificationData.blockchain_proof.network}</span>
                    </div>
                    {verificationData.blockchain_proof.tx_hash && (
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Transaction Hash:</p>
                        <code className="text-xs bg-background p-2 rounded block break-all">
                          {verificationData.blockchain_proof.tx_hash}
                        </code>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Chain of Custody */}
            <div>
              <h4 className="font-semibold mb-3 flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Chain of Custody ({custodyChain.length} events)
              </h4>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-muted-foreground">Chain Integrity:</span>
                <Badge variant={verificationData.chain_of_custody_intact ? 'default' : 'destructive'}>
                  {verificationData.chain_of_custody_intact ? 'Intact' : 'Broken'}
                </Badge>
              </div>
              <ScrollArea className="h-[200px] border rounded-lg">
                <div className="p-4 space-y-3">
                  {custodyChain.map((event, index) => (
                    <div key={event.event_id || index} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div className="w-2 h-2 rounded-full bg-primary" />
                        {index < custodyChain.length - 1 && (
                          <div className="w-0.5 h-full bg-border" />
                        )}
                      </div>
                      <div className="flex-1 pb-3">
                        <div className="flex items-center justify-between">
                          <Badge variant="outline" className="capitalize text-xs">
                            {event.action?.replace(/_/g, ' ')}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {new Date(event.timestamp).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          User: {event.user_id?.substring(0, 12)}...
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>

            {/* Warnings */}
            {verificationData.warnings?.length > 0 && (
              <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
                <h4 className="font-semibold text-yellow-700 dark:text-yellow-400 mb-2 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  Warnings
                </h4>
                <ul className="space-y-1">
                  {verificationData.warnings.map((warning, idx) => (
                    <li key={idx} className="text-sm text-yellow-700 dark:text-yellow-400">
                      • {warning}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Legal Notice */}
            <div className="text-xs text-muted-foreground bg-muted/50 rounded-lg p-3">
              <p>
                <strong>Legal Notice:</strong> This verification report is generated by the JUSTICE Platform 
                for use in legal proceedings. The cryptographic hashes provide mathematical proof that the 
                evidence has not been altered since its original capture. The chain of custody documents 
                every access to this evidence per FRE 901/707 requirements.
              </p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

export function CourtPackageButton({ evidenceId, className = '' }) {
  const [loading, setLoading] = useState(false);

  const handleDownload = async () => {
    setLoading(true);
    try {
      const response = await evidenceIntegrityAPI.getCourtPackage(evidenceId);
      if (response.data.success) {
        // Create a JSON download
        const blob = new Blob([JSON.stringify(response.data.package, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `JUSTICE_Court_Package_${evidenceId}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        toast.success('Court package downloaded');
      }
    } catch (error) {
      toast.error('Failed to generate court package');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button 
      variant="outline" 
      size="sm" 
      onClick={handleDownload}
      disabled={loading}
      className={className}
      data-testid="court-package-btn"
    >
      {loading ? (
        <Loader2 className="w-4 h-4 mr-1 animate-spin" />
      ) : (
        <FileText className="w-4 h-4 mr-1" />
      )}
      Court Package
    </Button>
  );
}

export default EvidenceVerificationBadge;
