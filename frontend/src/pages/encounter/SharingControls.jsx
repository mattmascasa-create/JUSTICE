/**
 * SharingControls Component
 * Controls for sharing encounter stream and attorney connection
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { 
  Share2, Copy, ExternalLink, Scale, Video, 
  Phone, Users, CheckCircle, Loader2, X 
} from 'lucide-react';
import { toast } from 'sonner';

export function SharingControls({
  encounter,
  shareLink,
  shareActive,
  viewerCount = 0,
  attorneyStreamActive,
  connectedAttorney,
  onCreateShare,
  onRevokeShare,
  onStartAttorneyStream,
  onEndAttorneyStream,
  isCreatingShare = false,
  isStartingStream = false
}) {
  const [showStreamDialog, setShowStreamDialog] = useState(false);
  const [attorneyEmail, setAttorneyEmail] = useState('');

  const copyShareLink = async () => {
    if (shareLink) {
      try {
        await navigator.clipboard.writeText(shareLink);
        toast.success('Share link copied to clipboard!');
      } catch (err) {
        toast.error('Failed to copy link');
      }
    }
  };

  const handleStartStream = () => {
    onStartAttorneyStream(attorneyEmail);
    setShowStreamDialog(false);
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Share2 className="h-5 w-5" />
          Sharing & Backup
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Share Link Section */}
        <div className="p-3 rounded-lg bg-muted/50">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Public Share Link</span>
            {shareActive && (
              <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/30">
                <Users className="h-3 w-3 mr-1" />
                {viewerCount} viewer{viewerCount !== 1 ? 's' : ''}
              </Badge>
            )}
          </div>
          
          {shareActive && shareLink ? (
            <div className="space-y-2">
              <div className="flex gap-2">
                <Input 
                  value={shareLink} 
                  readOnly 
                  className="text-xs bg-background"
                />
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={copyShareLink}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="flex-1"
                  onClick={() => window.open(shareLink, '_blank')}
                >
                  <ExternalLink className="h-4 w-4 mr-1" />
                  Open
                </Button>
                <Button 
                  variant="destructive" 
                  size="sm" 
                  className="flex-1"
                  onClick={onRevokeShare}
                >
                  <X className="h-4 w-4 mr-1" />
                  Revoke
                </Button>
              </div>
            </div>
          ) : (
            <Button 
              variant="outline" 
              className="w-full"
              onClick={onCreateShare}
              disabled={isCreatingShare || !encounter}
            >
              {isCreatingShare ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Share2 className="h-4 w-4 mr-2" />
              )}
              Create Share Link
            </Button>
          )}
        </div>

        {/* Attorney Stream Section */}
        <div className="p-3 rounded-lg bg-muted/50">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Attorney Live Stream</span>
            {attorneyStreamActive && (
              <Badge variant="outline" className="bg-blue-500/10 text-blue-500 border-blue-500/30">
                <Video className="h-3 w-3 mr-1" />
                Live
              </Badge>
            )}
          </div>
          
          {attorneyStreamActive ? (
            <div className="space-y-2">
              {connectedAttorney && (
                <div className="flex items-center gap-2 p-2 bg-blue-500/10 rounded-lg">
                  <Scale className="h-4 w-4 text-blue-500" />
                  <span className="text-sm">{connectedAttorney.email || connectedAttorney.name}</span>
                  <CheckCircle className="h-4 w-4 text-green-500 ml-auto" />
                </div>
              )}
              <Button 
                variant="destructive" 
                size="sm" 
                className="w-full"
                onClick={onEndAttorneyStream}
              >
                End Attorney Stream
              </Button>
            </div>
          ) : (
            <Dialog open={showStreamDialog} onOpenChange={setShowStreamDialog}>
              <DialogTrigger asChild>
                <Button 
                  variant="outline" 
                  className="w-full"
                  disabled={!encounter}
                >
                  <Scale className="h-4 w-4 mr-2" />
                  Connect Attorney
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2">
                    <Scale className="h-5 w-5" />
                    Start Attorney Live Stream
                  </DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <p className="text-sm text-muted-foreground">
                    Your attorney will receive a secure link to watch your encounter in real-time 
                    and can provide guidance through the chat.
                  </p>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Attorney Email (optional)</label>
                    <Input 
                      type="email"
                      placeholder="attorney@lawfirm.com"
                      value={attorneyEmail}
                      onChange={(e) => setAttorneyEmail(e.target.value)}
                    />
                    <p className="text-xs text-muted-foreground">
                      Leave blank to generate a link you can share manually
                    </p>
                  </div>
                  <Button 
                    className="w-full"
                    onClick={handleStartStream}
                    disabled={isStartingStream}
                  >
                    {isStartingStream ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Video className="h-4 w-4 mr-2" />
                    )}
                    Start Live Stream
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          )}
        </div>

        {/* Quick Actions */}
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            className="flex-1"
            onClick={() => {
              if (navigator.share && shareLink) {
                navigator.share({
                  title: 'JUSTICE - Live Encounter',
                  text: 'Watch my live police encounter',
                  url: shareLink
                });
              } else if (shareLink) {
                copyShareLink();
              } else {
                toast.info('Create a share link first');
              }
            }}
          >
            <Phone className="h-4 w-4 mr-1" />
            Quick Share
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default SharingControls;
