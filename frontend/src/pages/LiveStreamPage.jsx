import React, { useState, useEffect, useRef } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Alert, AlertDescription } from '../components/ui/alert';
import { encounterAPI, API_URL } from '../lib/api';
import { 
  Shield, MapPin, Clock, Video, AlertTriangle, 
  Loader2, Play, Pause, SkipBack, SkipForward, 
  AlertCircle, RefreshCw, Maximize, Lock
} from 'lucide-react';

export default function LiveStreamPage() {
  const { encounterId } = useParams();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [encounterInfo, setEncounterInfo] = useState(null);
  const [mediaFiles, setMediaFiles] = useState([]);
  const [currentVideoIndex, setCurrentVideoIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLive, setIsLive] = useState(false);
  const videoRef = useRef(null);
  const pollIntervalRef = useRef(null);

  useEffect(() => {
    if (!token) {
      setError('No access token provided');
      setLoading(false);
      return;
    }
    
    verifyAccess();
    
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [encounterId, token]);

  const verifyAccess = async () => {
    try {
      setLoading(true);
      const response = await encounterAPI.verifyStreamAccess(encounterId, token);
      setEncounterInfo(response.data);
      setIsLive(response.data.status === 'active');
      
      // Load media files
      await loadMediaFiles();
      
      // If encounter is active, poll for new files
      if (response.data.status === 'active') {
        pollIntervalRef.current = setInterval(loadMediaFiles, 10000); // Poll every 10 seconds
      }
    } catch (err) {
      console.error('Access verification failed:', err);
      setError(err.response?.data?.detail || 'Access denied or link expired');
    } finally {
      setLoading(false);
    }
  };

  const loadMediaFiles = async () => {
    try {
      // Use the verify endpoint to get basic info, then fetch media
      const response = await fetch(
        `${API_URL}/live/${encounterId}/verify?token=${token}`
      );
      
      if (response.ok) {
        const data = await response.json();
        setEncounterInfo(data);
        setIsLive(data.status === 'active');
        
        // For now, we'll show available files from the encounter
        // In a real implementation, this would stream from a WebRTC connection
      }
    } catch (err) {
      console.error('Error loading media:', err);
    }
  };

  const getMediaUrl = (filename) => {
    return `${API_URL}/live/${encounterId}/media/${filename}?token=${token}`;
  };

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="h-12 w-12 animate-spin mx-auto text-red-500" />
          <p className="text-white">Verifying access...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <Card className="max-w-md w-full bg-slate-900 border-red-500/30">
          <CardContent className="p-6 text-center space-y-4">
            <div className="inline-flex items-center justify-center p-3 rounded-full bg-red-500/20">
              <Lock className="h-8 w-8 text-red-500" />
            </div>
            <h1 className="text-xl font-bold text-white">Access Denied</h1>
            <p className="text-slate-400">{error}</p>
            <Alert className="bg-slate-800 border-slate-700">
              <AlertCircle className="h-4 w-4 text-slate-400" />
              <AlertDescription className="text-slate-400 text-sm">
                This link may have expired or is invalid. Please request a new share link from the person who shared this recording with you.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-800 p-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="h-8 w-8 text-red-500" />
            <div>
              <h1 className="text-white font-bold">JUSTICE</h1>
              <p className="text-slate-400 text-xs">Encounter Recording</p>
            </div>
          </div>
          {isLive && (
            <Badge className="bg-red-500 text-white animate-pulse">
              <div className="w-2 h-2 bg-white rounded-full mr-2" />
              LIVE
            </Badge>
          )}
        </div>
      </header>

      <main className="max-w-4xl mx-auto p-4 space-y-4">
        {/* Status Card */}
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-4">
              <Badge variant={isLive ? "destructive" : "secondary"}>
                {isLive ? 'Encounter In Progress' : 'Recording Ended'}
              </Badge>
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <MapPin className="h-4 w-4" />
                {encounterInfo?.location || 'Location not available'}
              </div>
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <Clock className="h-4 w-4" />
                {encounterInfo?.started_at 
                  ? new Date(encounterInfo.started_at).toLocaleString()
                  : 'Time not available'}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Video Player */}
        <Card className="bg-slate-900 border-slate-800 overflow-hidden">
          <div className="aspect-video bg-black relative">
            {isLive ? (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center space-y-4">
                  <div className="inline-flex items-center justify-center p-4 rounded-full bg-red-500/20 animate-pulse">
                    <Video className="h-12 w-12 text-red-500" />
                  </div>
                  <p className="text-white">Live stream in progress</p>
                  <p className="text-slate-400 text-sm">
                    Video chunks are being recorded and will be available for playback when the encounter ends.
                  </p>
                  <Button onClick={loadMediaFiles} variant="outline" className="border-slate-700">
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                  </Button>
                </div>
              </div>
            ) : mediaFiles.length > 0 ? (
              <>
                <video
                  ref={videoRef}
                  src={getMediaUrl(mediaFiles[currentVideoIndex]?.filename)}
                  className="w-full h-full"
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                />
                
                {/* Controls */}
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-white hover:bg-white/20"
                        onClick={() => setCurrentVideoIndex(Math.max(0, currentVideoIndex - 1))}
                        disabled={currentVideoIndex === 0}
                      >
                        <SkipBack className="h-5 w-5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-white hover:bg-white/20 h-12 w-12"
                        onClick={handlePlayPause}
                      >
                        {isPlaying ? <Pause className="h-6 w-6" /> : <Play className="h-6 w-6" />}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-white hover:bg-white/20"
                        onClick={() => setCurrentVideoIndex(Math.min(mediaFiles.length - 1, currentVideoIndex + 1))}
                        disabled={currentVideoIndex === mediaFiles.length - 1}
                      >
                        <SkipForward className="h-5 w-5" />
                      </Button>
                    </div>
                    <Badge variant="secondary" className="bg-black/50">
                      Chunk {currentVideoIndex + 1} / {mediaFiles.length}
                    </Badge>
                  </div>
                </div>
              </>
            ) : (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center space-y-2">
                  <Video className="h-12 w-12 text-slate-600 mx-auto" />
                  <p className="text-slate-400">No video recordings available yet</p>
                </div>
              </div>
            )}
          </div>
        </Card>

        {/* Info Card */}
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Important Notice
            </CardTitle>
          </CardHeader>
          <CardContent className="text-slate-400 text-sm space-y-2">
            <p>
              This recording is being shared with you through the JUSTICE platform. 
              The content may be sensitive and depicts a real law enforcement encounter.
            </p>
            <p>
              All recordings are cryptographically verified and timestamped for legal authenticity.
            </p>
            <p className="text-xs text-slate-500">
              This link will expire in 24 hours. Do not share this link publicly.
            </p>
          </CardContent>
        </Card>
      </main>

      {/* Footer */}
      <footer className="bg-slate-900 border-t border-slate-800 p-4 mt-8">
        <div className="max-w-4xl mx-auto text-center text-slate-500 text-sm">
          <p>JUSTICE Platform - Civil Rights Defense System</p>
          <p className="text-xs mt-1">Recording protected by blockchain verification</p>
        </div>
      </footer>
    </div>
  );
}
