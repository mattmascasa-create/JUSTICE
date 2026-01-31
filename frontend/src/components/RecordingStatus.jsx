/**
 * RecordingStatus Component
 * Shows real-time status of evidence recording and upload
 */

import React, { useState, useEffect } from 'react';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { 
  HardDrive, Upload, Cloud, CheckCircle, AlertTriangle, 
  Wifi, WifiOff, Shield, Loader2 
} from 'lucide-react';
import uploadManager from '../services/uploadManager';
import evidenceStorage from '../services/evidenceStorage';

export function RecordingStatus({ 
  isRecording, 
  chunksSaved = 0, 
  chunksUploaded = 0,
  compact = false 
}) {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [storageStats, setStorageStats] = useState(null);

  // Monitor online status
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Periodically update storage stats
  useEffect(() => {
    const updateStats = async () => {
      try {
        const stats = await evidenceStorage.getStorageStats();
        setStorageStats(stats);
      } catch (e) {
        console.error('Failed to get storage stats:', e);
      }
    };

    updateStats();
    const interval = setInterval(updateStats, 5000);
    return () => clearInterval(interval);
  }, []);

  const pendingUploads = chunksSaved - chunksUploaded;
  const uploadPercent = chunksSaved > 0 ? Math.round((chunksUploaded / chunksSaved) * 100) : 0;
  const totalSizeMB = storageStats ? (storageStats.totalSize / (1024 * 1024)).toFixed(1) : '0';

  if (compact) {
    return (
      <div className="flex items-center gap-2 text-xs">
        <Badge variant="outline" className="gap-1 bg-green-500/10 border-green-500/30">
          <HardDrive className="h-3 w-3" />
          {chunksSaved} saved
        </Badge>
        {isOnline ? (
          <Badge variant="outline" className="gap-1 bg-blue-500/10 border-blue-500/30">
            <Cloud className="h-3 w-3" />
            {chunksUploaded} synced
          </Badge>
        ) : (
          <Badge variant="outline" className="gap-1 bg-yellow-500/10 border-yellow-500/30">
            <WifiOff className="h-3 w-3" />
            Offline
          </Badge>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3 p-3 bg-muted/30 rounded-lg border" data-testid="recording-status">
      {/* Local Storage Status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-green-500/20 rounded">
            <HardDrive className="h-4 w-4 text-green-500" />
          </div>
          <div>
            <p className="text-sm font-medium">Local Storage</p>
            <p className="text-xs text-muted-foreground">Evidence saved on device</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-sm font-bold text-green-500">{chunksSaved} chunks</p>
          <p className="text-xs text-muted-foreground">{totalSizeMB} MB</p>
        </div>
      </div>

      {/* Cloud Sync Status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`p-1.5 rounded ${isOnline ? 'bg-blue-500/20' : 'bg-yellow-500/20'}`}>
            {isOnline ? (
              <Cloud className="h-4 w-4 text-blue-500" />
            ) : (
              <WifiOff className="h-4 w-4 text-yellow-500" />
            )}
          </div>
          <div>
            <p className="text-sm font-medium">Cloud Backup</p>
            <p className="text-xs text-muted-foreground">
              {isOnline ? 'Syncing to secure servers' : 'Will sync when online'}
            </p>
          </div>
        </div>
        <div className="text-right">
          {isOnline ? (
            <>
              <p className="text-sm font-bold text-blue-500">{chunksUploaded} synced</p>
              {pendingUploads > 0 && (
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  {pendingUploads} pending
                </p>
              )}
            </>
          ) : (
            <p className="text-sm font-bold text-yellow-500">Paused</p>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      {chunksSaved > 0 && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Upload Progress</span>
            <span>{uploadPercent}%</span>
          </div>
          <Progress value={uploadPercent} className="h-2" />
        </div>
      )}

      {/* Evidence Protection Notice */}
      <div className="flex items-center gap-2 p-2 bg-green-500/10 rounded border border-green-500/20">
        <Shield className="h-4 w-4 text-green-500 shrink-0" />
        <p className="text-xs text-green-700 dark:text-green-300">
          <strong>Evidence Protected:</strong> All recordings are hashed with SHA-256 for tamper-proof verification.
          {isOnline 
            ? ' Cloud backup is active.' 
            : ' Will automatically sync when connection is restored.'}
        </p>
      </div>

      {/* Warning if too many pending */}
      {pendingUploads > 10 && isOnline && (
        <div className="flex items-center gap-2 p-2 bg-yellow-500/10 rounded border border-yellow-500/20">
          <AlertTriangle className="h-4 w-4 text-yellow-500 shrink-0" />
          <p className="text-xs text-yellow-700 dark:text-yellow-300">
            {pendingUploads} chunks pending upload. Keep app open to complete sync.
          </p>
        </div>
      )}
    </div>
  );
}

export default RecordingStatus;
