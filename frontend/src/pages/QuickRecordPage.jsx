/**
 * QuickRecordPage - One-Tap Recording
 * 
 * This page starts recording IMMEDIATELY when opened.
 * Designed for PWA shortcut - user taps icon, recording starts in 1 second.
 * 
 * Features:
 * - Auto-starts with pre-buffer (captures last 30 seconds)
 * - Minimal UI - just essential controls
 * - Browser speech recognition (no server latency)
 * - Works offline
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardContent } from '../components/ui/card';
import { Alert, AlertDescription } from '../components/ui/alert';
import { 
  Shield, StopCircle, Mic, Video, MapPin, 
  AlertTriangle, Share2, Siren, Clock, CheckCircle,
  Loader2, WifiOff
} from 'lucide-react';
import { toast } from 'sonner';
import { encounterAPI, sosAPI } from '../lib/api';
import preRecordingBuffer from '../services/preRecordingBuffer';
import browserSpeechRecognition from '../services/browserSpeechRecognition';
import evidenceStorage from '../services/evidenceStorage';

// Rights reminders - cycle through these
const RIGHTS_REMINDERS = [
  "You have the right to remain silent.",
  "Do not consent to searches.",
  "Ask: Am I free to go?",
  "You have the right to an attorney.",
  "Stay calm. Everything is being recorded."
];

export default function QuickRecordPage() {
  const navigate = useNavigate();
  
  // Core state
  const [status, setStatus] = useState('initializing'); // initializing, recording, stopping, error
  const [encounter, setEncounter] = useState(null);
  const [duration, setDuration] = useState(0);
  const [location, setLocation] = useState(null);
  
  // Recording state
  const [chunkCount, setChunkCount] = useState(0);
  const [preBufferIncluded, setPreBufferIncluded] = useState(false);
  
  // Transcription state
  const [transcripts, setTranscripts] = useState([]);
  const [interimText, setInterimText] = useState('');
  const [useBrowserTranscription, setUseBrowserTranscription] = useState(true);
  
  // UI state
  const [currentRightsIndex, setCurrentRightsIndex] = useState(0);
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  const [sosSent, setSosSent] = useState(false);
  
  // Refs
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const videoRef = useRef(null);
  const timerRef = useRef(null);
  const chunkIndexRef = useRef(0);

  // Format duration as MM:SS
  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Get location
  const getLocation = useCallback(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLocation({
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude
          });
        },
        (err) => console.log('Location error:', err),
        { enableHighAccuracy: true }
      );
    }
  }, []);

  // Start recording immediately
  const startRecording = useCallback(async () => {
    try {
      setStatus('initializing');
      
      // Get location
      getLocation();
      
      // Check for pre-buffer
      let preBuffer = null;
      if (preRecordingBuffer.isActive) {
        preBuffer = await preRecordingBuffer.getBufferAndClear();
        if (preBuffer) {
          setPreBufferIncluded(true);
          console.log(`Pre-buffer included: ${preBuffer.duration}ms, ${preBuffer.chunkCount} chunks`);
        }
      }
      
      // Get media stream (use pre-buffer stream if available, else request new)
      let stream = preRecordingBuffer.getStream();
      if (!stream || !stream.active) {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true },
          video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
        });
      }
      
      streamRef.current = stream;
      
      // Show video preview
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play().catch(() => {});
      }
      
      // Create encounter on backend
      const encounterData = {
        latitude: location?.latitude || 0,
        longitude: location?.longitude || 0,
        encounter_type: 'traffic_stop',
        broadcast_mode: 'save',
        quick_start: true
      };
      
      let encounterId;
      try {
        const response = await encounterAPI.start(encounterData);
        setEncounter(response.data);
        encounterId = response.data.encounter_id;
        
        // Save pre-buffer if we have it
        if (preBuffer && encounterId) {
          evidenceStorage.saveChunk(encounterId, preBuffer.blob, 'video', -1, { isPreBuffer: true })
            .then(() => console.log('Pre-buffer saved'))
            .catch(err => console.log('Pre-buffer save error:', err));
        }
      } catch (err) {
        // Offline mode - generate local encounter ID
        encounterId = `local_${Date.now()}`;
        setEncounter({ encounter_id: encounterId, offline: true });
        toast.warning('Offline mode - recording locally');
      }
      
      // Save encounter metadata locally
      await evidenceStorage.saveEncounter(encounterId, {
        type: 'traffic_stop',
        quickStart: true,
        preBufferIncluded: !!preBuffer
      });
      
      // Setup MediaRecorder
      const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus')
        ? 'video/webm;codecs=vp9,opus'
        : 'video/webm';
      
      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          const chunkIndex = chunkIndexRef.current++;
          
          // Save chunk (fire and forget)
          evidenceStorage.saveChunk(encounterId, event.data, 'video', chunkIndex)
            .then(() => setChunkCount(prev => prev + 1))
            .catch(err => console.error('Chunk save error:', err));
        }
      };
      
      mediaRecorder.start(3000); // 3-second chunks for faster saving
      
      // Start browser speech recognition
      if (browserSpeechRecognition.isSupported && useBrowserTranscription) {
        browserSpeechRecognition.on('result', (result) => {
          setTranscripts(prev => [...prev, {
            text: result.text,
            timestamp: result.timestamp,
            confidence: result.confidence
          }]);
          setInterimText('');
        });
        
        browserSpeechRecognition.on('interim', (result) => {
          setInterimText(result.text);
        });
        
        browserSpeechRecognition.start();
      }
      
      // Start duration timer
      timerRef.current = setInterval(() => {
        setDuration(prev => prev + 1);
      }, 1000);
      
      // Rotate rights reminders
      const rightsInterval = setInterval(() => {
        setCurrentRightsIndex(prev => (prev + 1) % RIGHTS_REMINDERS.length);
      }, 8000);
      
      setStatus('recording');
      toast.success('🔴 Recording started!');
      
      return () => clearInterval(rightsInterval);
    } catch (error) {
      console.error('Start recording error:', error);
      setStatus('error');
      toast.error(error.name === 'NotAllowedError' 
        ? 'Camera/microphone permission denied' 
        : 'Failed to start recording');
    }
  }, [location, getLocation, useBrowserTranscription]);

  // Stop recording
  const stopRecording = useCallback(async () => {
    setStatus('stopping');
    
    // Stop timer
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    
    // Stop speech recognition
    browserSpeechRecognition.stop();
    
    // Stop media recorder
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    
    // Stop stream tracks
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    
    // End encounter on backend
    if (encounter?.encounter_id && !encounter.offline) {
      try {
        await encounterAPI.end(encounter.encounter_id);
        toast.success('Recording saved! Generating report...');
        navigate(`/encounters/${encounter.encounter_id}`);
      } catch (err) {
        toast.info('Recording saved locally');
        navigate('/encounters');
      }
    } else {
      toast.info('Recording saved locally');
      navigate('/encounters');
    }
  }, [encounter, navigate]);

  // Quick SOS
  const triggerSOS = useCallback(async () => {
    if (sosSent) return;
    
    try {
      await sosAPI.createEncounterSOS({
        encounter_id: encounter?.encounter_id,
        latitude: location?.latitude,
        longitude: location?.longitude,
        message: 'QUICK SOS - Emergency assistance needed!'
      });
      setSosSent(true);
      toast.success('🚨 SOS Alert Sent!');
    } catch (err) {
      toast.error('SOS failed - call 911');
    }
  }, [encounter, location, sosSent]);

  // Share link
  const shareRecording = useCallback(async () => {
    if (!encounter?.encounter_id) return;
    
    try {
      const response = await encounterAPI.createShare(encounter.encounter_id, false);
      const url = `${window.location.origin}${response.data.share_url}`;
      
      if (navigator.share) {
        await navigator.share({
          title: 'JUSTICE - Live Recording',
          text: 'Watch my live police encounter recording',
          url
        });
      } else {
        await navigator.clipboard.writeText(url);
        toast.success('Link copied!');
      }
    } catch (err) {
      toast.error('Share failed');
    }
  }, [encounter]);

  // Auto-start on mount
  useEffect(() => {
    startRecording();
    
    // Network status
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      
      // Cleanup on unmount
      if (timerRef.current) clearInterval(timerRef.current);
      browserSpeechRecognition.stop();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Error state
  if (status === 'error') {
    return (
      <div className="fixed inset-0 bg-black flex flex-col items-center justify-center p-4">
        <AlertTriangle className="h-16 w-16 text-red-500 mb-4" />
        <h1 className="text-white text-xl mb-2">Recording Failed</h1>
        <p className="text-gray-400 text-center mb-4">
          Please grant camera and microphone permissions
        </p>
        <Button onClick={() => window.location.reload()}>Try Again</Button>
        <Button variant="outline" className="mt-2" onClick={() => navigate('/encounter')}>
          Use Full Mode
        </Button>
      </div>
    );
  }

  // Loading state
  if (status === 'initializing') {
    return (
      <div className="fixed inset-0 bg-black flex flex-col items-center justify-center p-4">
        <Loader2 className="h-16 w-16 text-red-500 animate-spin mb-4" />
        <h1 className="text-white text-xl">Starting Recording...</h1>
        <p className="text-gray-400 text-sm mt-2">Capturing pre-buffer</p>
      </div>
    );
  }

  // Recording UI - Minimal and focused
  return (
    <div className="fixed inset-0 bg-black flex flex-col" data-testid="quick-record-page">
      {/* Video Preview */}
      <div className="relative flex-1">
        <video 
          ref={videoRef} 
          autoPlay 
          muted 
          playsInline 
          className="w-full h-full object-cover"
        />
        
        {/* Recording Indicator */}
        <div className="absolute top-4 left-4 flex items-center gap-2">
          <div className="flex items-center gap-2 px-3 py-2 rounded-full bg-red-500 animate-pulse">
            <div className="w-3 h-3 bg-white rounded-full" />
            <span className="text-white font-bold">REC</span>
          </div>
          <Badge className="bg-black/70 text-white text-lg font-mono">
            {formatDuration(duration)}
          </Badge>
        </div>
        
        {/* Status badges */}
        <div className="absolute top-4 right-4 flex flex-col gap-2">
          {preBufferIncluded && (
            <Badge className="bg-green-500 text-white">
              <CheckCircle className="h-3 w-3 mr-1" /> +30s buffer
            </Badge>
          )}
          <Badge className="bg-black/70 text-white">
            <Video className="h-3 w-3 mr-1" /> {chunkCount} chunks
          </Badge>
          {isOffline && (
            <Badge className="bg-yellow-500 text-black">
              <WifiOff className="h-3 w-3 mr-1" /> Offline
            </Badge>
          )}
        </div>
        
        {/* Location indicator */}
        {location && (
          <div className="absolute bottom-20 left-4">
            <Badge className="bg-black/70 text-white">
              <MapPin className="h-3 w-3 mr-1" />
              {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
            </Badge>
          </div>
        )}
      </div>
      
      {/* Rights Reminder */}
      <div className="bg-blue-600 px-4 py-3">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-white flex-shrink-0" />
          <p className="text-white font-medium text-lg">
            {RIGHTS_REMINDERS[currentRightsIndex]}
          </p>
        </div>
      </div>
      
      {/* Live Transcription */}
      {(transcripts.length > 0 || interimText) && (
        <div className="bg-gray-900 px-4 py-2 max-h-24 overflow-y-auto">
          <p className="text-white text-sm">
            {transcripts.slice(-2).map(t => t.text).join(' ')}
            {interimText && (
              <span className="text-gray-400 italic"> {interimText}</span>
            )}
          </p>
        </div>
      )}
      
      {/* Control Bar */}
      <div className="bg-gray-900 p-4 safe-area-inset-bottom">
        <div className="flex items-center justify-between gap-2">
          {/* SOS Button */}
          <Button
            variant={sosSent ? "outline" : "destructive"}
            size="lg"
            className={`flex-1 h-14 ${sosSent ? 'border-green-500 text-green-500' : 'bg-red-600 hover:bg-red-700'}`}
            onClick={triggerSOS}
            disabled={sosSent}
          >
            {sosSent ? (
              <><CheckCircle className="h-5 w-5 mr-2" /> SOS Sent</>
            ) : (
              <><Siren className="h-5 w-5 mr-2" /> SOS</>
            )}
          </Button>
          
          {/* Stop Button */}
          <Button
            variant="outline"
            size="lg"
            className="flex-[2] h-14 border-white text-white hover:bg-white hover:text-black"
            onClick={stopRecording}
            data-testid="stop-recording-btn"
          >
            <StopCircle className="h-6 w-6 mr-2" />
            END RECORDING
          </Button>
          
          {/* Share Button */}
          <Button
            variant="outline"
            size="lg"
            className="flex-1 h-14 border-blue-500 text-blue-500"
            onClick={shareRecording}
            disabled={!encounter?.encounter_id || encounter?.offline}
          >
            <Share2 className="h-5 w-5 mr-2" /> Share
          </Button>
        </div>
      </div>
    </div>
  );
}
