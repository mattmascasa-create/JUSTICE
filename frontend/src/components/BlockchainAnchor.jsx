/**
 * BlockchainAnchor Component
 * UI for anchoring evidence to Polygon blockchain
 */

import React, { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription, DialogFooter } from './ui/dialog';
import { Alert, AlertDescription } from './ui/alert';
import { Separator } from './ui/separator';
import { 
  Link2, ExternalLink, CheckCircle, Clock, AlertTriangle, 
  Loader2, Download, Copy, Shield, Blocks, Wallet
} from 'lucide-react';
import api from '../lib/api';
import { toast } from 'sonner';

export function BlockchainAnchor({ encounterId }) {
  const [status, setStatus] = useState('unknown'); // unknown, loading, not_anchored, pending, anchored
  const [anchor, setAnchor] = useState(null);
  const [serviceStatus, setServiceStatus] = useState(null);
  const [showDialog, setShowDialog] = useState(false);
  const [anchoring, setAnchoring] = useState(false);
  const [verifying, setVerifying] = useState(false);

  // Check anchor status on mount
  useEffect(() => {
    if (encounterId) {
      checkAnchorStatus();
      checkServiceStatus();
    }
  }, [encounterId]);

  const checkServiceStatus = async () => {
    try {
      const response = await api.get('/blockchain/status');
      setServiceStatus(response.data);
    } catch (error) {
      console.error('Failed to get blockchain status:', error);
    }
  };

  const checkAnchorStatus = async () => {
    setStatus('loading');
    try {
      const response = await api.get(`/blockchain/encounter/${encounterId}`);
      if (response.data.anchored) {
        setAnchor(response.data.anchor);
        setStatus(response.data.anchor.status === 'confirmed' ? 'anchored' : 'pending');
      } else {
        setStatus('not_anchored');
      }
    } catch (error) {
      console.error('Failed to check anchor status:', error);
      setStatus('unknown');
    }
  };

  const anchorToBlockchain = async () => {
    setAnchoring(true);
    try {
      const response = await api.post(`/blockchain/anchor/${encounterId}`);
      
      if (response.data.status === 'anchored') {
        setAnchor({
          transaction_hash: response.data.transaction_hash,
          merkle_root: response.data.merkle_root,
          block_number: response.data.block_number,
          network: response.data.network,
          explorer_url: response.data.explorer_url,
          evidence_count: response.data.evidence_count,
          status: 'confirmed'
        });
        setStatus('anchored');
        toast.success('Evidence anchored to Polygon blockchain!');
      } else if (response.data.status === 'pending') {
        setStatus('pending');
        toast.info('Evidence queued for anchoring');
      }
    } catch (error) {
      console.error('Anchoring failed:', error);
      toast.error(error.response?.data?.detail || 'Failed to anchor evidence');
    } finally {
      setAnchoring(false);
    }
  };

  const verifyOnChain = async () => {
    if (!anchor?.transaction_hash) return;
    
    setVerifying(true);
    try {
      const response = await api.get(`/blockchain/verify/${anchor.transaction_hash}`);
      if (response.data.verified) {
        toast.success(`Verified! ${response.data.confirmations} confirmations on Polygon`);
        setAnchor(prev => ({
          ...prev,
          confirmations: response.data.confirmations,
          block_timestamp: response.data.block_timestamp
        }));
      }
    } catch (error) {
      toast.error('Verification failed');
    } finally {
      setVerifying(false);
    }
  };

  const downloadCertificate = async () => {
    try {
      const response = await api.get(`/blockchain/certificate/${encounterId}`);
      const certText = JSON.stringify(response.data.certificate, null, 2);
      const blob = new Blob([certText], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `blockchain-certificate-${encounterId}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Certificate downloaded');
    } catch (error) {
      toast.error('Failed to download certificate');
    }
  };

  const copyHash = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const getStatusBadge = () => {
    switch (status) {
      case 'anchored':
        return (
          <Badge className="bg-purple-500/10 text-purple-600 border-purple-500/30 gap-1">
            <Blocks className="h-3 w-3" />
            Blockchain Verified
          </Badge>
        );
      case 'pending':
        return (
          <Badge className="bg-yellow-500/10 text-yellow-600 border-yellow-500/30 gap-1">
            <Clock className="h-3 w-3" />
            Pending Confirmation
          </Badge>
        );
      case 'not_anchored':
        return (
          <Badge variant="outline" className="gap-1">
            <Link2 className="h-3 w-3" />
            Not Anchored
          </Badge>
        );
      default:
        return null;
    }
  };

  return (
    <Dialog open={showDialog} onOpenChange={setShowDialog}>
      <DialogTrigger asChild>
        <Button 
          variant="outline" 
          size="sm" 
          className={`gap-2 ${status === 'anchored' ? 'border-purple-500/30 text-purple-600' : ''}`}
        >
          <Blocks className="h-4 w-4" />
          Blockchain
          {status === 'anchored' && <CheckCircle className="h-3 w-3" />}
        </Button>
      </DialogTrigger>
      
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Blocks className="h-5 w-5 text-purple-500" />
            Blockchain Evidence Anchoring
          </DialogTitle>
          <DialogDescription>
            Permanently record evidence hashes on Polygon blockchain
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Service Status */}
          {serviceStatus && (
            <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
              <div className="flex items-center gap-2">
                <Wallet className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">Polygon {serviceStatus.network_name?.includes('Mumbai') ? 'Testnet' : 'Mainnet'}</span>
              </div>
              {serviceStatus.available ? (
                <Badge className="bg-green-500/10 text-green-600">Connected</Badge>
              ) : (
                <Badge variant="destructive">Unavailable</Badge>
              )}
            </div>
          )}

          {/* Anchor Status */}
          {status === 'anchored' && anchor && (
            <Card className="border-purple-500/30">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2 text-purple-600">
                  <CheckCircle className="h-4 w-4" />
                  Evidence Anchored
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {/* Transaction Hash */}
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Transaction Hash</p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 text-xs bg-muted p-2 rounded truncate font-mono">
                      {anchor.transaction_hash}
                    </code>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => copyHash(anchor.transaction_hash)}>
                      <Copy className="h-3 w-3" />
                    </Button>
                  </div>
                </div>

                {/* Merkle Root */}
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Merkle Root</p>
                  <code className="text-xs bg-muted p-2 rounded block truncate font-mono">
                    {anchor.merkle_root}
                  </code>
                </div>

                {/* Details Grid */}
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="p-2 bg-muted/30 rounded">
                    <p className="text-xs text-muted-foreground">Block</p>
                    <p className="font-mono">{anchor.block_number || 'Pending'}</p>
                  </div>
                  <div className="p-2 bg-muted/30 rounded">
                    <p className="text-xs text-muted-foreground">Evidence</p>
                    <p>{anchor.evidence_count} hashes</p>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 pt-2">
                  {anchor.explorer_url && (
                    <Button variant="outline" size="sm" asChild>
                      <a href={anchor.explorer_url} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="h-3 w-3 mr-1" />
                        View on Polygonscan
                      </a>
                    </Button>
                  )}
                  <Button variant="outline" size="sm" onClick={verifyOnChain} disabled={verifying}>
                    {verifying ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <CheckCircle className="h-3 w-3 mr-1" />}
                    Verify
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Not Anchored State */}
          {status === 'not_anchored' && (
            <div className="space-y-4">
              <Alert className="border-purple-500/30 bg-purple-500/5">
                <Blocks className="h-4 w-4 text-purple-500" />
                <AlertDescription>
                  Anchor your evidence to the Polygon blockchain for permanent, tamper-proof verification.
                  This creates an immutable record that can be verified by anyone.
                </AlertDescription>
              </Alert>

              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>Permanent, immutable record</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>Publicly verifiable by anyone</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>Court-admissible timestamp proof</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>Low cost (Polygon network)</span>
                </div>
              </div>

              <Button 
                onClick={anchorToBlockchain} 
                disabled={anchoring || !serviceStatus?.available}
                className="w-full bg-purple-600 hover:bg-purple-700"
              >
                {anchoring ? (
                  <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Anchoring to Blockchain...</>
                ) : (
                  <><Blocks className="h-4 w-4 mr-2" />Anchor Evidence to Polygon</>
                )}
              </Button>

              {!serviceStatus?.available && (
                <p className="text-xs text-muted-foreground text-center">
                  Blockchain service is currently unavailable. Evidence will be queued.
                </p>
              )}
            </div>
          )}

          {/* Pending State */}
          {status === 'pending' && (
            <Alert className="border-yellow-500/30 bg-yellow-500/5">
              <Clock className="h-4 w-4 text-yellow-500" />
              <AlertDescription>
                Your evidence is queued for blockchain anchoring. This will complete automatically when the service is available.
              </AlertDescription>
            </Alert>
          )}

          <Separator />

          {/* Certificate Download */}
          {status === 'anchored' && (
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted-foreground">
                Download certificate for legal proceedings
              </p>
              <Button variant="outline" size="sm" onClick={downloadCertificate}>
                <Download className="h-3 w-3 mr-1" />
                Certificate
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default BlockchainAnchor;
