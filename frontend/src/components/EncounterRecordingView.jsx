/**
 * EncounterRecordingView Component
 * 
 * The active recording view for encounter mode. Shows:
 * - Video preview
 * - Recording controls and stats
 * - Live transcription
 * - SOS, sharing, and other panels
 * 
 * Extracted from EncounterPage to improve maintainability.
 */

import React from 'react';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Switch } from './ui/switch';
import { ScrollArea } from './ui/scroll-area';
import { 
  Shield, Video, Mic, StopCircle, Pause, Play,
  Database, Upload, Clock, Wifi, WifiOff,
  Volume2, VolumeX, MapPin, CheckCircle,
  Siren, Share2, Users, Eye, Scale, AlertTriangle,
  Cloud, CloudOff, FileText
} from 'lucide-react';

// Utility to format duration
function formatDuration(seconds) {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function EncounterRecordingView({
  // Recording state
  isRecording,
  isPaused,
  duration,
  enableVideo,
  preBufferIncluded,
  
  // Stats
  chunksSaved,
  chunksUploaded,
  videoChunkCount,
  
  // Transcription
  transcriptions,
  interimTranscript,
  browserTranscriptSupported,
  useBrowserTranscription,
  
  // Network
  isOffline,
  
  // Location
  address,
  hasLocation,
  
  // Voice commands
  voiceCommandsEnabled,
  setVoiceCommandsEnabled,
  voiceCommandsFeedback,
  manualViolationMarks,
  
  // SOS
  sosActive,
  sosSending,
  onTriggerSOS,
  onCancelSOS,
  
  // Sharing
  shareActive,
  onToggleSharing,
  viewerCount,
  
  // Controls
  onPause,
  onStop,
  
  // Refs
  videoPreviewRef,
  
  // Navigation
  onNavigate,
  
  // Children for additional panels
  children
}) {
  return (
    <div className="space-y-4 animate-in fade-in" data-testid="recording-active-view">
      {/* Recording Status Header */}
      <Card className="border-2 border-red-500/50 bg-gradient-to-r from-red-500/10 to-red-600/5">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Recording Indicator */}
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full bg-red-500 animate-pulse" />
                <span className="text-xl font-mono font-bold text-red-500">
                  {formatDuration(duration)}
                </span>
              </div>
              
              {/* Pre-buffer badge */}
              {preBufferIncluded && (
                <Badge variant="outline" className="border-green-500 text-green-500">
                  +30s captured
                </Badge>
              )}
              
              {/* Recording type */}
              <Badge variant="secondary">
                {enableVideo ? <Video className="h-3 w-3 mr-1" /> : <Mic className="h-3 w-3 mr-1" />}
                {enableVideo ? 'Video' : 'Audio'}
              </Badge>
            </div>

            {/* Stats */}
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-1" title="Chunks saved locally">
                <Database className="h-4 w-4 text-blue-500" />
                <span>{chunksSaved}</span>
              </div>
              <div className="flex items-center gap-1" title="Chunks uploaded">
                <Upload className="h-4 w-4 text-green-500" />
                <span>{chunksUploaded}</span>
              </div>
              <div className="flex items-center gap-1" title="Network status">
                {isOffline ? (
                  <WifiOff className="h-4 w-4 text-orange-500" />
                ) : (
                  <Wifi className="h-4 w-4 text-green-500" />
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left Column - Video/Audio Preview */}
        <div className="lg:col-span-2 space-y-4">
          {/* Video Preview */}
          {enableVideo && (
            <Card className="overflow-hidden">
              <video
                ref={videoPreviewRef}
                autoPlay
                muted
                playsInline
                className="w-full aspect-video bg-black"
              />
            </Card>
          )}

          {/* Audio-only visualization */}
          {!enableVideo && (
            <Card className="bg-gradient-to-br from-gray-900 to-gray-800">
              <CardContent className="p-8 flex flex-col items-center justify-center min-h-[200px]">
                <div className="relative">
                  <Mic className="h-16 w-16 text-red-500 animate-pulse" />
                  <div className="absolute inset-0 animate-ping">
                    <Mic className="h-16 w-16 text-red-500 opacity-30" />
                  </div>
                </div>
                <p className="mt-4 text-lg text-muted-foreground">Audio Recording Active</p>
              </CardContent>
            </Card>
          )}

          {/* Location */}
          {hasLocation && address && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <MapPin className="h-4 w-4" />
              <span className="truncate">{address}</span>
            </div>
          )}

          {/* Recording Controls */}
          <div className="flex items-center justify-center gap-4">
            <Button 
              variant="outline" 
              size="lg" 
              onClick={onPause}
              className="h-14"
              data-testid="pause-recording-btn"
            >
              {isPaused ? (
                <>
                  <Play className="h-5 w-5 mr-2" />
                  Resume
                </>
              ) : (
                <>
                  <Pause className="h-5 w-5 mr-2" />
                  Pause
                </>
              )}
            </Button>
            
            <Button 
              variant="destructive" 
              size="lg" 
              onClick={onStop}
              className="h-14"
              data-testid="stop-recording-btn"
            >
              <StopCircle className="h-5 w-5 mr-2" />
              End Recording
            </Button>
          </div>
        </div>

        {/* Right Column - Panels */}
        <div className="space-y-4">
          {/* SOS Button */}
          <Card className={`border-2 ${sosActive ? 'border-green-500 bg-green-500/10' : 'border-red-500/50 bg-red-500/5'}`}>
            <CardContent className="p-4">
              {sosActive ? (
                <Button 
                  variant="outline" 
                  className="w-full h-14 border-green-500 text-green-500"
                  onClick={onCancelSOS}
                >
                  <CheckCircle className="h-5 w-5 mr-2" />
                  SOS Active - Click to Cancel
                </Button>
              ) : (
                <Button 
                  variant="destructive" 
                  className="w-full h-14"
                  onClick={onTriggerSOS}
                  disabled={sosSending}
                  data-testid="sos-button"
                >
                  <Siren className="h-5 w-5 mr-2" />
                  {sosSending ? 'Sending...' : 'EMERGENCY SOS'}
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Voice Commands */}
          <Card className={`border-2 ${voiceCommandsEnabled ? 'border-purple-500/50 bg-purple-500/5' : 'border-gray-500/30'}`}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-full ${voiceCommandsEnabled ? 'bg-purple-500' : 'bg-gray-500'}`}>
                    {voiceCommandsEnabled ? <Volume2 className="h-4 w-4 text-white" /> : <VolumeX className="h-4 w-4 text-white" />}
                  </div>
                  <div>
                    <p className="font-medium text-sm">Voice Commands</p>
                    <p className="text-xs text-muted-foreground">
                      {voiceCommandsFeedback || 'Say "mark violation", "SOS"'}
                    </p>
                  </div>
                </div>
                <Switch 
                  checked={voiceCommandsEnabled} 
                  onCheckedChange={setVoiceCommandsEnabled}
                />
              </div>
              {manualViolationMarks?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {manualViolationMarks.map((mark, idx) => (
                    <Badge key={idx} variant="outline" className="text-xs border-red-500/50 text-red-400">
                      📍 {formatDuration(mark.timestamp)}
                    </Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Sharing */}
          <Card className={`border-2 ${shareActive ? 'border-green-500/50 bg-green-500/5' : 'border-gray-500/30'}`}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {shareActive ? <Eye className="h-5 w-5 text-green-500" /> : <Share2 className="h-5 w-5 text-gray-500" />}
                  <div>
                    <p className="font-medium text-sm flex items-center gap-2">
                      Live Sharing
                      {shareActive && (
                        <Badge className="bg-green-500 text-xs">
                          {viewerCount} viewing
                        </Badge>
                      )}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {shareActive ? 'Broadcasting live' : 'Share with trusted contacts'}
                    </p>
                  </div>
                </div>
                <Button 
                  variant={shareActive ? 'destructive' : 'outline'} 
                  size="sm"
                  onClick={onToggleSharing}
                >
                  {shareActive ? 'Stop' : 'Share'}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Quick Navigation */}
          <div className="grid grid-cols-3 gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              className="flex-col h-auto py-2"
              onClick={() => onNavigate('/emergency-contacts')}
            >
              <Users className="h-4 w-4 mb-1" />
              <span className="text-xs">Contacts</span>
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              className="flex-col h-auto py-2"
              onClick={() => onNavigate('/attorneys')}
            >
              <Scale className="h-4 w-4 mb-1" />
              <span className="text-xs">Attorney</span>
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              className="flex-col h-auto py-2"
              onClick={() => onNavigate('/rights')}
            >
              <FileText className="h-4 w-4 mb-1" />
              <span className="text-xs">Rights</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Live Transcription */}
      {(transcriptions.length > 0 || interimTranscript) && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-medium flex items-center gap-2">
                <Mic className="h-4 w-4" />
                Live Transcription
                {browserTranscriptSupported && useBrowserTranscription && (
                  <Badge variant="outline" className="text-xs">Browser</Badge>
                )}
              </h3>
            </div>
            <ScrollArea className="h-32">
              <div className="space-y-2 text-sm">
                {transcriptions.slice(-10).map((t, idx) => (
                  <p key={idx} className="text-muted-foreground">
                    <span className="text-xs opacity-50">[{formatDuration(Math.floor(t.timestamp / 1000))}]</span>{' '}
                    {t.text}
                  </p>
                ))}
                {interimTranscript && (
                  <p className="text-blue-400 italic animate-pulse">
                    {interimTranscript}...
                  </p>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {/* Additional panels passed as children */}
      {children}
    </div>
  );
}

export default EncounterRecordingView;
