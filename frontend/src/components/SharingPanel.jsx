/**
 * SharingPanel Component
 * 
 * Manages live sharing and attorney streaming functionality
 * for encounter recordings.
 */

import React, { useState, useCallback } from 'react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { 
  Share2, Copy, Users, Scale, Loader2, 
  Eye, EyeOff, CheckCircle 
} from 'lucide-react';
import { toast } from 'sonner';
import { encounterAPI, attorneyStreamAPI } from '../lib/api';

export function SharingPanel({ 
  encounter, 
  isRecording,
  viewerCount: externalViewerCount,
  className = '' 
}) {
  // Sharing state
  const [shareLink, setShareLink] = useState(null);
  const [shareActive, setShareActive] = useState(false);
  const [viewerCount, setViewerCount] = useState(externalViewerCount || 0);
  
  // Attorney stream state
  const [attorneyStreamActive, setAttorneyStreamActive] = useState(false);
  const [streamSession, setStreamSession] = useState(null);
  const [showStreamDialog, setShowStreamDialog] = useState(false);
  const [streamAttorneyEmail, setStreamAttorneyEmail] = useState('');
  const [streamingToAttorney, setStreamingToAttorney] = useState(false);

  const toggleSharing = useCallback(async () => {
    if (!encounter) return;
    
    try {
      if (shareActive) {
        await encounterAPI.stopSharing(encounter.encounter_id);
        setShareActive(false);
        setShareLink(null);
        setViewerCount(0);
        toast.info('Sharing stopped');
      } else {
        const response = await encounterAPI.startSharing(encounter.encounter_id);
        setShareLink(response.data.share_url);
        setShareActive(true);
        toast.success('Live sharing enabled!');
      }
    } catch (error) {
      toast.error('Sharing failed');
    }
  }, [encounter, shareActive]);

  const copyShareLink = useCallback(() => {
    if (shareLink) {
      navigator.clipboard.writeText(shareLink);
      toast.success('Link copied!');
    }
  }, [shareLink]);

  const startAttorneyStream = useCallback(async () => {
    if (!encounter || !streamAttorneyEmail) {
      toast.error('Please enter attorney email');
      return;
    }
    
    setStreamingToAttorney(true);
    try {
      const response = await attorneyStreamAPI.start({
        encounter_id: encounter.encounter_id,
        attorney_email: streamAttorneyEmail
      });
      
      setStreamSession(response.data);
      setAttorneyStreamActive(true);
      setShowStreamDialog(false);
      toast.success('Attorney stream started!', {
        description: `${streamAttorneyEmail} has been notified`
      });
    } catch (error) {
      toast.error('Failed to start attorney stream');
    } finally {
      setStreamingToAttorney(false);
    }
  }, [encounter, streamAttorneyEmail]);

  const stopAttorneyStream = useCallback(async () => {
    if (!streamSession) return;
    
    try {
      await attorneyStreamAPI.stop(streamSession.session_id);
      setAttorneyStreamActive(false);
      setStreamSession(null);
      toast.info('Attorney stream ended');
    } catch (error) {
      toast.error('Failed to stop stream');
    }
  }, [streamSession]);

  if (!isRecording) return null;

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Live Sharing Card */}
      <Card className={`border-2 ${shareActive ? 'border-green-500/50 bg-green-500/5' : 'border-gray-500/30'}`}>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-full ${shareActive ? 'bg-green-500' : 'bg-gray-500'}`}>
                {shareActive ? <Eye className="h-5 w-5 text-white" /> : <EyeOff className="h-5 w-5 text-white" />}
              </div>
              <div>
                <p className="font-bold flex items-center gap-2">
                  Live Sharing
                  {shareActive && (
                    <Badge variant="default" className="bg-green-500">
                      <Users className="h-3 w-3 mr-1" />
                      {viewerCount} viewing
                    </Badge>
                  )}
                </p>
                <p className="text-sm text-muted-foreground">
                  {shareActive ? 'Anyone with link can view' : 'Share live feed with trusted contacts'}
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              {shareActive && shareLink && (
                <Button variant="ghost" size="icon" onClick={copyShareLink}>
                  <Copy className="h-4 w-4" />
                </Button>
              )}
              <Button 
                variant={shareActive ? 'destructive' : 'outline'} 
                size="sm"
                onClick={toggleSharing}
                data-testid="share-toggle-btn"
              >
                <Share2 className="h-4 w-4 mr-2" />
                {shareActive ? 'Stop' : 'Share'}
              </Button>
            </div>
          </div>
          
          {shareActive && shareLink && (
            <div className="mt-3 p-2 bg-muted rounded flex items-center justify-between">
              <code className="text-xs truncate flex-1">{shareLink}</code>
              <Button variant="ghost" size="sm" onClick={copyShareLink}>
                <Copy className="h-3 w-3" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Attorney Stream Card */}
      <Card className={`border-2 ${attorneyStreamActive ? 'border-blue-500/50 bg-blue-500/5' : 'border-gray-500/30'}`}>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-full ${attorneyStreamActive ? 'bg-blue-500' : 'bg-gray-500'}`}>
                <Scale className={`h-5 w-5 ${attorneyStreamActive ? 'text-white' : 'text-white'}`} />
              </div>
              <div>
                <p className="font-bold flex items-center gap-2">
                  Attorney Stream
                  {attorneyStreamActive && (
                    <Badge variant="default" className="bg-blue-500">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      LIVE
                    </Badge>
                  )}
                </p>
                <p className="text-sm text-muted-foreground">
                  {attorneyStreamActive 
                    ? `Streaming to ${streamSession?.attorney_email}` 
                    : 'Stream directly to your attorney'}
                </p>
              </div>
            </div>
            
            {attorneyStreamActive ? (
              <Button 
                variant="destructive" 
                size="sm"
                onClick={stopAttorneyStream}
              >
                End Stream
              </Button>
            ) : (
              <Dialog open={showStreamDialog} onOpenChange={setShowStreamDialog}>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm" data-testid="attorney-stream-btn">
                    <Scale className="h-4 w-4 mr-2" />
                    Stream
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Stream to Attorney</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div>
                      <label className="text-sm font-medium">Attorney Email</label>
                      <Input 
                        type="email" 
                        placeholder="attorney@lawfirm.com"
                        value={streamAttorneyEmail}
                        onChange={(e) => setStreamAttorneyEmail(e.target.value)}
                        className="mt-1"
                      />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Your attorney will receive a notification with a secure link 
                      to view your live stream and provide real-time guidance.
                    </p>
                    <Button 
                      className="w-full" 
                      onClick={startAttorneyStream}
                      disabled={streamingToAttorney || !streamAttorneyEmail}
                    >
                      {streamingToAttorney ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Starting...
                        </>
                      ) : (
                        <>
                          <Scale className="h-4 w-4 mr-2" />
                          Start Attorney Stream
                        </>
                      )}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default SharingPanel;
