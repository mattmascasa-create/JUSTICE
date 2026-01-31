/**
 * RecordingControls Component
 * 
 * Control buttons for starting, pausing, and stopping recordings.
 * Also displays recording status and chunk statistics.
 */

import React from 'react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Card, CardContent } from './ui/card';
import { 
  Play, Pause, StopCircle, Video, Mic, 
  Clock, Database, Upload, Wifi, WifiOff
} from 'lucide-react';

// Format duration in MM:SS or HH:MM:SS
function formatDuration(seconds) {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Format bytes to human readable
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export function RecordingControls({
  isRecording,
  isPaused,
  duration,
  chunksSaved,
  chunksUploaded,
  videoChunkCount,
  enableVideo,
  isOffline,
  preBufferIncluded,
  onStart,
  onPause,
  onStop,
  className = ''
}) {
  if (!isRecording) {
    return (
      <Button 
        size="lg" 
        onClick={onStart}
        className="h-16 px-8 text-lg bg-red-500 hover:bg-red-600"
        data-testid="start-recording-btn"
      >
        {enableVideo ? <Video className="h-6 w-6 mr-3" /> : <Mic className="h-6 w-6 mr-3" />}
        Start Recording
      </Button>
    );
  }

  return (
    <Card className={`border-red-500/50 bg-red-500/5 ${className}`}>
      <CardContent className="p-4 space-y-4">
        {/* Recording Timer */}
        <div className="flex items-center justify-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
            <span className="text-2xl font-mono font-bold text-red-500">
              {formatDuration(duration)}
            </span>
          </div>
          {preBufferIncluded && (
            <Badge variant="outline" className="border-green-500 text-green-500">
              +30s pre-buffer
            </Badge>
          )}
        </div>

        {/* Stats Row */}
        <div className="flex items-center justify-center gap-6 text-sm">
          <div className="flex items-center gap-1">
            <Database className="h-4 w-4 text-blue-500" />
            <span>{chunksSaved} saved</span>
          </div>
          <div className="flex items-center gap-1">
            <Upload className="h-4 w-4 text-green-500" />
            <span>{chunksUploaded} uploaded</span>
          </div>
          <div className="flex items-center gap-1">
            {enableVideo ? <Video className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
            <span>{videoChunkCount} chunks</span>
          </div>
          <div className="flex items-center gap-1">
            {isOffline ? (
              <WifiOff className="h-4 w-4 text-orange-500" />
            ) : (
              <Wifi className="h-4 w-4 text-green-500" />
            )}
            <span className={isOffline ? 'text-orange-500' : 'text-green-500'}>
              {isOffline ? 'Offline' : 'Online'}
            </span>
          </div>
        </div>

        {/* Control Buttons */}
        <div className="flex items-center justify-center gap-4">
          <Button 
            variant="outline" 
            size="lg" 
            onClick={onPause}
            className="h-12 px-6"
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
            className="h-12 px-6"
            data-testid="stop-recording-btn"
          >
            <StopCircle className="h-5 w-5 mr-2" />
            End Recording
          </Button>
        </div>

        {/* Offline Notice */}
        {isOffline && (
          <div className="text-center text-sm text-orange-500">
            Recording offline - will sync when connected
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default RecordingControls;
