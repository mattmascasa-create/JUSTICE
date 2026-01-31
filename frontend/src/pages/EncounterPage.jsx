/**
 * EncounterPage - Refactored Version
 * 
 * This is the main police encounter recording page, refactored to use
 * extracted hooks and components for better maintainability.
 * 
 * Core features:
 * - Video/audio recording with local-first storage
 * - Pre-recording buffer (captures 30 seconds BEFORE you hit record)
 * - Browser-native speech recognition (instant transcription)
 * - Real-time transcription and AI analysis
 * - Voice commands for hands-free operation
 * - Live sharing and attorney streaming
 * - SOS/Panic button functionality
 */

import React, { useState, useEffect, useRef, useCallback, Component } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { ScrollArea } from '../components/ui/scroll-area';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { encounterAPI, sosAPI, encounterCoachAPI, attorneyStreamAPI, multiCloudBackupAPI } from '../lib/api';
import { useWebSocket } from '../contexts/WebSocketContext';
import { 
  Shield, AlertTriangle, Mic, Video, 
  StopCircle, Play, Pause, Users, Share2,
  Eye, EyeOff, AlertCircle, Scale, CheckCircle, Volume2, VolumeX,
  MessageCircle, Copy, Siren, Loader2, Wifi, Clock
} from 'lucide-react';
import { toast } from 'sonner';

// Core components
import RightsCoachPanel from '../components/RightsCoachPanel';
import DeadMansSwitchPanel from '../components/DeadMansSwitchPanel';
import { QuickOfficerLookup } from '../components/QuickOfficerLookup';
import RecordingStatus from '../components/RecordingStatus';

// Services
import evidenceStorage from '../services/evidenceStorage';
import uploadManager from '../services/uploadManager';
import preRecordingBuffer from '../services/preRecordingBuffer';
import browserSpeechRecognition from '../services/browserSpeechRecognition';

// Extracted constants
import {
  encounterTypes,
  broadcastModes,
  rightsReminders as defaultRightsReminders,
  voiceCommandsConfig,
  riskLevelColors,
  riskLevelLabels,
  toneColors,
  toneIcons,
  qualityPresets,
  highlightText,
  formatDuration
} from './encounter/constants';

// Universal encounter types config
import { getRightsReminders } from '../config/encounterTypes';

// Extracted components
import { EncounterSetupScreen } from './encounter/EncounterSetupScreen';
import { ViolationsPanel } from './encounter/ViolationsPanel';
import { TranscriptionPanel } from './encounter/TranscriptionPanel';

// Extracted hooks
import { useGeolocation } from '../hooks/useGeolocation';
import { useVoiceCommands } from '../hooks/useVoiceCommands';
import { useEncounterAnalysis } from '../hooks/useEncounterAnalysis';

// ============== Error Boundary ==============
class EncounterErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Encounter Mode Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <AppLayout>
          <div className="flex flex-col items-center justify-center min-h-[60vh] p-6">
            <AlertTriangle className="h-16 w-16 text-yellow-500 mb-4" />
            <h2 className="text-xl font-bold mb-2">Something went wrong</h2>
            <p className="text-muted-foreground mb-4 text-center max-w-md">
              An error occurred in Encounter Mode. Your recording data has been saved.
            </p>
            <div className="flex gap-4">
              <Button onClick={() => window.location.href = '/encounters'}>
                View Encounters
              </Button>
              <Button variant="outline" onClick={() => this.setState({ hasError: false, error: null })}>
                Try Again
              </Button>
            </div>
          </div>
        </AppLayout>
      );
    }
    return this.props.children;
  }
}

// ============== Main Component ==============
export default function EncounterPage() {
  const navigate = useNavigate();
  const { notifications } = useWebSocket();
  
  // ===== Core Recording State =====
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [encounter, setEncounter] = useState(null);
  const [duration, setDuration] = useState(0);
  
  // ===== Setup Configuration =====
  const [encounterType, setEncounterType] = useState('traffic_stop');
  const [broadcastMode, setBroadcastMode] = useState('save');
  const [enableVideo, setEnableVideo] = useState(true);
  const [recordingQuality, setRecordingQuality] = useState('balanced');
  const [deferAnalysis, setDeferAnalysis] = useState(false);
  
  // ===== Recording Data =====
  const [transcriptions, setTranscriptions] = useState([]);
  const [violations, setViolations] = useState([]);
  const [chunksSaved, setChunksSaved] = useState(0);
  const [chunksUploaded, setChunksUploaded] = useState(0);
  const [videoChunkCount, setVideoChunkCount] = useState(0);
  
  // ===== Pre-Recording Buffer State =====
  const [preBufferActive, setPreBufferActive] = useState(false);
  const [preBufferStats, setPreBufferStats] = useState(null);
  const [preBufferIncluded, setPreBufferIncluded] = useState(false);
  
  // ===== Browser Speech Recognition State =====
  const [useBrowserTranscription, setUseBrowserTranscription] = useState(true);
  const [browserTranscriptSupported, setBrowserTranscriptSupported] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState('');
  
  // ===== UI State =====
  const [currentRightsIndex, setCurrentRightsIndex] = useState(0);
  const [showViolationsPanel, setShowViolationsPanel] = useState(false);
  const [showCoachingPanel, setShowCoachingPanel] = useState(true);
  const [stealthActivated, setStealthActivated] = useState(false);
  
  // ===== Officer Info =====
  const [officerInfo, setOfficerInfo] = useState({ name: '', badge: '', department: '' });
  const [showOfficerForm, setShowOfficerForm] = useState(false);
  const [lookedUpOfficer, setLookedUpOfficer] = useState(null);
  
  // ===== Sharing State =====
  const [shareLink, setShareLink] = useState(null);
  const [shareActive, setShareActive] = useState(false);
  const [viewerCount, setViewerCount] = useState(0);
  const [guidanceMessages, setGuidanceMessages] = useState([]);
  
  // ===== Attorney Stream State =====
  const [attorneyStreamActive, setAttorneyStreamActive] = useState(false);
  const [streamSession, setStreamSession] = useState(null);
  const [showStreamDialog, setShowStreamDialog] = useState(false);
  const [streamAttorneyEmail, setStreamAttorneyEmail] = useState('');
  const [streamingToAttorney, setStreamingToAttorney] = useState(false);
  
  // ===== SOS State =====
  const [sosActive, setSosActive] = useState(false);
  const [sosSending, setSosSending] = useState(false);
  const [sosAlertId, setSosAlertId] = useState(null);
  
  // ===== Network State =====
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  const [syncingOfflineData, setSyncingOfflineData] = useState(false);
  
  // ===== Refs =====
  const mediaRecorderRef = useRef(null);
  const audioRecorderRef = useRef(null);
  const videoChunksRef = useRef([]);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);
  const videoPreviewRef = useRef(null);
  const chunkIndexRef = useRef(0);
  const videoChunkIndexRef = useRef(0);
  const timerRef = useRef(null);

  // ===== Custom Hooks =====
  const { location, address, setAddress, hasLocation } = useGeolocation();
  
  const analysis = useEncounterAnalysis({
    encounter,
    encounterType,
    encounterAPI,
    encounterCoachAPI,
    enabled: !deferAnalysis,
    coachingEnabled: true
  });

  // Voice commands - handlers defined after other functions
  const [voiceCommandsEnabled, setVoiceCommandsEnabled] = useState(true);
  const [manualViolationMarks, setManualViolationMarks] = useState([]);

  // ===== Duration Timer =====
  useEffect(() => {
    if (isRecording && !isPaused) {
      timerRef.current = setInterval(() => {
        setDuration(prev => prev + 1);
      }, 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isRecording, isPaused]);

  // ===== Pre-Recording Buffer Initialization =====
  useEffect(() => {
    // Start pre-recording buffer on component mount
    setBrowserTranscriptSupported(browserSpeechRecognition.isSupported);
    
    const startPreBuffer = async () => {
      if (preRecordingBuffer.constructor.isSupported()) {
        const success = await preRecordingBuffer.start({ video: enableVideo });
        setPreBufferActive(success);
        if (success) {
          console.log('Pre-recording buffer started');
        }
      }
    };
    
    startPreBuffer();
    
    // Update pre-buffer stats periodically
    const statsInterval = setInterval(() => {
      if (preRecordingBuffer.isActive) {
        setPreBufferStats(preRecordingBuffer.getStats());
      }
    }, 2000);
    
    return () => {
      clearInterval(statsInterval);
      // Don't stop pre-buffer on unmount - it runs in background
    };
  }, [enableVideo]);

  // ===== Rights Reminder Rotation =====
  useEffect(() => {
    if (!isRecording) return;
    const interval = setInterval(() => {
      setCurrentRightsIndex(prev => (prev + 1) % rightsReminders.length);
    }, 15000);
    return () => clearInterval(interval);
  }, [isRecording]);

  // ===== Upload Manager Subscription =====
  useEffect(() => {
    const unsubscribe = uploadManager.subscribe((event, data) => {
      if (event === 'uploaded') {
        setChunksUploaded(prev => prev + 1);
      } else if (event === 'transcription' && encounter && data.encounterId === encounter.encounter_id) {
        if (data.transcription && !deferAnalysis) {
          setTranscriptions(prev => [...prev, data.transcription]);
          if (data.transcription.text) {
            analysis.processTranscription(data.transcription.text);
          }
        }
      }
    });
    return unsubscribe;
  }, [encounter, deferAnalysis, analysis]);

  // ===== Network Status =====
  useEffect(() => {
    const handleOnline = () => {
      setIsOffline(false);
      toast.success('📶 Back online! Syncing data...');
    };
    const handleOffline = () => {
      setIsOffline(true);
      toast.warning('📴 You are offline. Recording continues locally.');
    };
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // ===== WebSocket Guidance Messages =====
  useEffect(() => {
    if (!notifications?.length || !encounter) return;
    const guidanceNotifs = notifications.filter(
      n => n.type === 'guidance_message' && n.encounter_id === encounter.encounter_id
    );
    if (guidanceNotifs.length > 0) {
      setGuidanceMessages(prev => [...prev, ...guidanceNotifs]);
      guidanceNotifs.forEach(msg => {
        toast.info(`💬 ${msg.sender_name}: ${msg.message}`, { duration: 10000 });
      });
    }
  }, [notifications, encounter]);

  // ===== Recording Functions =====
  const startRecording = async () => {
    if (!location) {
      toast.error('Please enable location services');
      return;
    }

    try {
      // Create encounter on backend
      const response = await encounterAPI.start({
        latitude: location.latitude,
        longitude: location.longitude,
        address: address || undefined,
        encounter_type: encounterType,
        broadcast_mode: broadcastMode
      });
      
      setEncounter(response.data);
      await evidenceStorage.saveEncounter(response.data.encounter_id, {
        type: encounterType,
        broadcastMode,
        quality: recordingQuality
      });

      // ===== CAPTURE PRE-BUFFER (last 30 seconds) =====
      let preBuffer = null;
      if (preRecordingBuffer.isActive) {
        preBuffer = await preRecordingBuffer.getBufferAndClear();
        if (preBuffer && preBuffer.blob.size > 0) {
          setPreBufferIncluded(true);
          console.log(`Pre-buffer captured: ${preBuffer.duration}ms, ${preBuffer.chunkCount} chunks`);
          
          // Save pre-buffer as first chunk (fire and forget)
          evidenceStorage.saveChunk(response.data.encounter_id, preBuffer.blob, 'video', -1, { isPreBuffer: true })
            .then(() => {
              setChunksSaved(prev => prev + 1);
              toast.success(`📹 +${Math.round(preBuffer.duration / 1000)}s pre-buffer captured!`);
            })
            .catch(err => console.log('Pre-buffer save error:', err));
        }
      }

      // Get media stream - try to reuse pre-buffer stream first
      let stream = preRecordingBuffer.getStream();
      const preset = qualityPresets[recordingQuality];
      
      if (!stream || !stream.active) {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true },
          video: enableVideo ? {
            facingMode: { ideal: 'environment' },
            width: { ideal: preset.video?.width || 1280 },
            height: { ideal: preset.video?.height || 720 }
          } : false
        });
      }
      
      streamRef.current = stream;
      if (enableVideo && videoPreviewRef.current) {
        videoPreviewRef.current.srcObject = stream;
        videoPreviewRef.current.play().catch(() => {});
      }

      // ===== START BROWSER SPEECH RECOGNITION =====
      if (useBrowserTranscription && browserSpeechRecognition.isSupported) {
        browserSpeechRecognition.clearTranscript();
        
        browserSpeechRecognition.on('result', (result) => {
          // Add final transcript
          setTranscriptions(prev => [...prev, {
            text: result.text,
            timestamp: result.timestamp,
            confidence: result.confidence,
            source: 'browser'
          }]);
          setInterimTranscript('');
          
          // Send to AI analysis if enabled
          if (!deferAnalysis && result.text) {
            analysis.processTranscription(result.text);
          }
        });
        
        browserSpeechRecognition.on('interim', (result) => {
          setInterimTranscript(result.text);
        });
        
        browserSpeechRecognition.start();
        console.log('Browser speech recognition started');
      }

      // Setup media recorder
      const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus') 
        ? 'video/webm;codecs=vp9,opus' 
        : 'video/webm';
      
      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      // NON-BLOCKING: Video/audio chunk handler - fire and forget
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          const type = enableVideo ? 'video' : 'audio';
          const chunkIndex = videoChunkIndexRef.current++;
          const encounterId = response.data.encounter_id;
          
          // Fire and forget - don't await
          evidenceStorage.saveChunk(encounterId, event.data, type, chunkIndex)
            .then(chunkId => {
              setChunksSaved(prev => prev + 1);
              setVideoChunkCount(prev => prev + 1);
              uploadManager.queueUpload(encounterId, chunkId, type, 'normal');
            })
            .catch(err => console.error('Failed to save chunk:', err));
        }
      };

      // Setup separate audio recorder for transcription (only if video enabled)
      if (enableVideo) {
        const audioStream = new MediaStream(stream.getAudioTracks());
        const audioRecorder = new MediaRecorder(audioStream, {
          mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm'
        });
        audioRecorderRef.current = audioRecorder;

        // NON-BLOCKING: Audio chunk handler for transcription - fire and forget
        audioRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            const chunkIndex = chunkIndexRef.current++;
            const encounterId = response.data.encounter_id;
            const audioBlob = event.data;
            
            // Save locally first (fire and forget)
            evidenceStorage.saveChunk(encounterId, audioBlob, 'audio', chunkIndex, { forTranscription: true })
              .then(chunkId => {
                setChunksSaved(prev => prev + 1);
                uploadManager.queueUpload(encounterId, chunkId, 'audio', 'high');
              })
              .catch(err => console.log('Audio save error:', err));
            
            // Transcription upload in background (fire and forget)
            if (navigator.onLine && !deferAnalysis) {
              encounterAPI.uploadAudio(encounterId, audioBlob, chunkIndex)
                .then(result => {
                  if (result.data?.transcription) {
                    setTranscriptions(prev => [...prev, result.data.transcription]);
                    if (result.data.transcription.text) {
                      analysis.processTranscription(result.data.transcription.text);
                    }
                    if (result.data.transcription.violations_detected?.length > 0) {
                      setViolations(prev => [...prev, ...result.data.transcription.violations_detected]);
                    }
                  }
                })
                .catch(err => console.log('Transcription error:', err));
            }
          }
        };
        audioRecorder.start(5000);
      } else {
        // Audio-only mode: Use main recorder for transcription too
        // NON-BLOCKING transcription for audio-only
        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            const chunkIndex = videoChunkIndexRef.current++;
            const encounterId = response.data.encounter_id;
            const audioBlob = event.data;
            
            // Save locally (fire and forget)
            evidenceStorage.saveChunk(encounterId, audioBlob, 'audio', chunkIndex)
              .then(chunkId => {
                setChunksSaved(prev => prev + 1);
                setVideoChunkCount(prev => prev + 1);
                uploadManager.queueUpload(encounterId, chunkId, 'audio', 'normal');
              })
              .catch(err => console.error('Failed to save chunk:', err));
            
            // Transcription (fire and forget)
            if (navigator.onLine && !deferAnalysis) {
              encounterAPI.uploadAudio(encounterId, audioBlob, chunkIndex)
                .then(result => {
                  if (result.data?.transcription) {
                    setTranscriptions(prev => [...prev, result.data.transcription]);
                    if (result.data.transcription.text) {
                      analysis.processTranscription(result.data.transcription.text);
                    }
                  }
                })
                .catch(err => console.log('Transcription error:', err));
            }
          }
        };
      }

      mediaRecorder.start(5000);
      setIsRecording(true);
      setDuration(0);
      setChunksSaved(0);
      setChunksUploaded(0);
      setVideoChunkCount(0);
      
      toast.success('🔴 Recording Started - Evidence saved locally');
    } catch (error) {
      console.error('Recording error:', error);
      toast.error(error.name === 'NotAllowedError' 
        ? 'Please allow camera/microphone access' 
        : 'Failed to start recording');
    }
  };

  const pauseRecording = () => {
    if (!mediaRecorderRef.current || !isRecording) return;
    
    if (isPaused) {
      mediaRecorderRef.current.resume();
      audioRecorderRef.current?.resume();
      setIsPaused(false);
      toast.info('Recording resumed');
    } else {
      mediaRecorderRef.current.pause();
      audioRecorderRef.current?.pause();
      setIsPaused(true);
      toast.info('Recording paused');
    }
  };

  const stopRecording = async () => {
    const currentEncounterId = encounter?.encounter_id;
    
    // Stop browser speech recognition
    browserSpeechRecognition.stop();
    setInterimTranscript('');
    
    // Stop recorders
    if (mediaRecorderRef.current?.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (audioRecorderRef.current?.state !== 'inactive') {
      audioRecorderRef.current.stop();
    }
    
    // Stop tracks
    streamRef.current?.getTracks().forEach(track => track.stop());
    if (videoPreviewRef.current) {
      videoPreviewRef.current.srcObject = null;
    }
    
    // Restart pre-recording buffer for next time
    preRecordingBuffer.stop();
    preRecordingBuffer.start({ video: enableVideo });
    
    setIsRecording(false);
    setIsPaused(false);
    setPreBufferIncluded(false);
    
    if (currentEncounterId) {
      try {
        toast.info('Processing recording...');
        await encounterAPI.end(currentEncounterId);
        toast.success('Recording ended. Report generated!');
        navigate(`/encounters/${currentEncounterId}`);
      } catch (error) {
        toast.error('Recording saved. Navigate to encounters to view.');
        navigate('/encounters');
      }
    }
  };

  // ===== SOS Functions =====
  const triggerQuickSOS = async () => {
    if (!encounter || sosSending) return;
    setSosSending(true);
    
    try {
      const response = await sosAPI.createEncounterSOS({
        encounter_id: encounter.encounter_id,
        latitude: location?.latitude,
        longitude: location?.longitude,
        address: address || 'Unknown location',
        message: 'Emergency SOS - I need help during a police encounter!'
      });
      
      setSosActive(true);
      setSosAlertId(response.data.alert_id);
      toast.success(`🚨 SOS Alert Sent! ${response.data.contacts_notified} contact(s) notified.`);
      analysis.clearAlert();
    } catch (error) {
      toast.error('Failed to send SOS. Try again or call 911.');
    } finally {
      setSosSending(false);
    }
  };

  const cancelSOS = async () => {
    if (!sosAlertId) return;
    try {
      await sosAPI.resolve(sosAlertId);
      setSosActive(false);
      setSosAlertId(null);
      toast.success('SOS alert cancelled');
    } catch (error) {
      console.error('Cancel SOS error:', error);
    }
  };

  // ===== Sharing Functions =====
  const shareStreamLink = async () => {
    if (!encounter) return;
    
    try {
      if (!shareActive) {
        const response = await encounterAPI.createShare(encounter.encounter_id, false);
        const fullUrl = `${window.location.origin}${response.data.share_url}`;
        setShareLink(fullUrl);
        setShareActive(true);
        
        if (navigator.share) {
          await navigator.share({
            title: 'JUSTICE - Live Encounter Recording',
            text: "I'm being pulled over. Watch my live recording.",
            url: fullUrl
          });
        } else {
          await navigator.clipboard.writeText(fullUrl);
          toast.success('Share link copied!');
        }
      } else if (shareLink) {
        await navigator.clipboard.writeText(shareLink);
        toast.success('Link copied!');
      }
    } catch (error) {
      toast.error('Failed to create share link');
    }
  };

  const revokeShareLink = async () => {
    if (!encounter) return;
    try {
      await encounterAPI.revokeShare(encounter.encounter_id);
      setShareLink(null);
      setShareActive(false);
      setViewerCount(0);
      toast.info('Share link revoked');
    } catch (error) {
      console.error('Revoke error:', error);
    }
  };

  // ===== Attorney Stream Functions =====
  const startAttorneyStream = async () => {
    if (!encounter) {
      toast.error('Start recording first');
      return;
    }
    
    setStreamingToAttorney(true);
    try {
      const response = await attorneyStreamAPI.createStream(
        encounter.encounter_id,
        streamAttorneyEmail || null,
        address || (location ? `${location.latitude}, ${location.longitude}` : null)
      );
      
      setStreamSession(response.data);
      setAttorneyStreamActive(true);
      setShowStreamDialog(false);
      
      if (response.data.stream_url) {
        await navigator.clipboard.writeText(response.data.stream_url);
        toast.success('🎥 Attorney stream started! Link copied.');
      }
    } catch (error) {
      toast.error('Failed to start attorney stream');
    } finally {
      setStreamingToAttorney(false);
    }
  };

  const endAttorneyStream = async () => {
    if (!streamSession) return;
    try {
      await attorneyStreamAPI.endStream(streamSession.stream_code, 'user');
      setStreamSession(null);
      setAttorneyStreamActive(false);
      toast.info('Attorney stream ended');
    } catch (error) {
      console.error('End stream error:', error);
    }
  };

  // ===== Cloud Backup =====
  const triggerCloudBackup = async () => {
    if (!encounter) return;
    try {
      const response = await multiCloudBackupAPI.backupAllEncounter(encounter.encounter_id);
      toast.success(`☁️ Backed up to ${response.data.successful_backups} cloud providers`);
    } catch (error) {
      toast.error('Cloud backup failed');
    }
  };

  // ===== Officer Info =====
  const addOfficerInfo = async () => {
    if (!encounter) return;
    try {
      await encounterAPI.addOfficer(encounter.encounter_id, officerInfo);
      toast.success('Officer information recorded');
      setShowOfficerForm(false);
      setOfficerInfo({ name: '', badge: '', department: '' });
    } catch (error) {
      toast.error('Failed to add officer info');
    }
  };

  // ===== Voice Commands Setup =====
  const voiceCommands = useVoiceCommands({
    isRecording,
    enabled: voiceCommandsEnabled,
    encounter,
    location,
    duration,
    isPaused,
    onMarkViolation: (mark) => {
      setManualViolationMarks(prev => [...prev, mark]);
      setViolations(prev => [...prev, `Manual mark at ${formatDuration(mark.timestamp)}`]);
    },
    onSOS: triggerQuickSOS,
    onEndRecording: stopRecording,
    onPause: () => {
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.pause();
        audioRecorderRef.current?.pause();
        setIsPaused(true);
      }
    },
    onResume: () => {
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.resume();
        audioRecorderRef.current?.resume();
        setIsPaused(false);
      }
    },
    onShare: shareStreamLink,
    encounterAPI,
    sosAPI
  });

  // ============== RENDER ==============

  // Setup Screen (not recording)
  if (!isRecording) {
    return (
      <AppLayout>
        <EncounterSetupScreen
          location={location}
          address={address}
          onAddressChange={setAddress}
          enableVideo={enableVideo}
          onEnableVideoChange={setEnableVideo}
          recordingQuality={recordingQuality}
          onRecordingQualityChange={setRecordingQuality}
          deferAnalysis={deferAnalysis}
          onDeferAnalysisChange={setDeferAnalysis}
          encounterType={encounterType}
          onEncounterTypeChange={setEncounterType}
          broadcastMode={broadcastMode}
          onBroadcastModeChange={setBroadcastMode}
          onStartRecording={startRecording}
          isStarting={false}
        />
      </AppLayout>
    );
  }

  // Stealth Mode
  if (stealthActivated && isRecording) {
    return (
      <div className="fixed inset-0 bg-black z-50" data-testid="stealth-mode-screen">
        <div className="absolute bottom-2 right-2 opacity-5">
          <div className="w-1 h-1 bg-red-500 rounded-full animate-pulse" />
        </div>
        <div className="absolute top-4 left-4 opacity-0 hover:opacity-10 transition-opacity">
          <p className="text-white text-xs">Recording: {formatDuration(duration)} | Triple-tap to exit</p>
        </div>
        <button
          className="absolute bottom-4 left-4 w-12 h-12 opacity-0 active:opacity-5"
          onClick={() => setStealthActivated(false)}
        />
      </div>
    );
  }

  // Recording Screen
  return (
    <AppLayout>
      <div className="max-w-2xl mx-auto space-y-4" data-testid="encounter-recording">
        {/* Offline Banner */}
        {isOffline && (
          <Alert className="border-yellow-500/50 bg-yellow-500/10">
            <AlertTriangle className="h-4 w-4 text-yellow-500" />
            <AlertDescription>
              <span className="font-bold">Offline Mode</span> - Recording locally. Will sync when connected.
            </AlertDescription>
          </Alert>
        )}

        {/* Stealth Mode Toggle */}
        <Card className="border-gray-800 bg-gray-900/50">
          <CardContent className="p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <EyeOff className="h-4 w-4 text-gray-400" />
                <span className="text-sm font-medium">Stealth Mode</span>
              </div>
              <Switch checked={stealthActivated} onCheckedChange={setStealthActivated} />
            </div>
          </CardContent>
        </Card>

        {/* Video Preview */}
        {enableVideo && (
          <Card className="overflow-hidden">
            <div className="relative aspect-video bg-black">
              <video ref={videoPreviewRef} autoPlay muted playsInline className="w-full h-full object-cover" />
              <div className="absolute top-3 left-3 flex items-center gap-2">
                <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${isPaused ? 'bg-yellow-500' : 'bg-red-500 animate-pulse'}`}>
                  <div className="w-2 h-2 bg-white rounded-full" />
                  <span className="text-white text-sm font-bold">{isPaused ? 'PAUSED' : 'REC'}</span>
                </div>
                <Badge variant="secondary" className="bg-black/50 text-white">{formatDuration(duration)}</Badge>
              </div>
              <div className="absolute top-3 right-3">
                <Badge variant="secondary" className="bg-black/50 text-white">
                  <Video className="h-3 w-3 mr-1" />{videoChunkCount} chunks
                </Badge>
              </div>
            </div>
          </Card>
        )}

        {/* Audio-Only Status */}
        {!enableVideo && (
          <Card className="bg-red-500/10 border-red-500/50">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-full ${isPaused ? 'bg-yellow-500' : 'bg-red-500 animate-pulse'}`}>
                    <Mic className="h-5 w-5 text-white" />
                  </div>
                  <div>
                    <p className="font-bold text-lg">{isPaused ? 'PAUSED' : 'RECORDING'}</p>
                    <p className="text-sm text-muted-foreground font-mono">{formatDuration(duration)}</p>
                  </div>
                </div>
                <Badge variant="destructive" className="text-lg px-4 py-1">LIVE</Badge>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Rights Reminder */}
        <Alert className="border-blue-500/50 bg-blue-500/10">
          <Shield className="h-5 w-5 text-blue-500" />
          <AlertDescription className="text-lg font-medium">
            {rightsReminders[currentRightsIndex]}
          </AlertDescription>
        </Alert>

        {/* Recording Status */}
        <RecordingStatus isRecording={isRecording} chunksSaved={chunksSaved} chunksUploaded={chunksUploaded} />

        {/* Voice Commands */}
        <Card className={`border-2 ${voiceCommandsEnabled ? 'border-purple-500/50 bg-purple-500/5' : 'border-gray-500/30'}`}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-full ${voiceCommandsEnabled ? 'bg-purple-500 animate-pulse' : 'bg-gray-500'}`}>
                  {voiceCommandsEnabled ? <Volume2 className="h-5 w-5 text-white" /> : <VolumeX className="h-5 w-5 text-white" />}
                </div>
                <div>
                  <p className="font-bold flex items-center gap-2">
                    Voice Commands
                    <Badge variant={voiceCommandsEnabled ? 'default' : 'secondary'} className={voiceCommandsEnabled ? 'bg-purple-500' : ''}>
                      {voiceCommandsEnabled ? 'LISTENING' : 'OFF'}
                    </Badge>
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {voiceCommands.feedback || 'Say "mark violation", "SOS", "end recording"'}
                  </p>
                </div>
              </div>
              <Switch checked={voiceCommandsEnabled} onCheckedChange={setVoiceCommandsEnabled} />
            </div>
            {manualViolationMarks.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {manualViolationMarks.map((mark, idx) => (
                  <Badge key={idx} variant="outline" className="border-red-500/50 text-red-400">
                    📍 {formatDuration(mark.timestamp)}
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* AI Rights Coach */}
        <RightsCoachPanel
          encounterType={encounterType}
          fullTranscript={analysis.fullTranscript}
          isRecording={isRecording}
          isPaused={isPaused}
        />

        {/* Dead Man's Switch */}
        <DeadMansSwitchPanel
          encounterId={encounter?.encounter_id}
          isRecording={isRecording}
          onTrigger={() => {
            if (!shareActive) shareStreamLink();
          }}
        />

        {/* Share Status */}
        <Card className={`border-2 ${shareActive ? 'border-blue-500/50 bg-blue-500/5' : 'border-gray-500/30'}`}>
          <CardContent className="p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-full ${shareActive ? 'bg-blue-500' : 'bg-gray-500'}`}>
                  <Share2 className="h-5 w-5 text-white" />
                </div>
                <div>
                  <p className="font-bold flex items-center gap-2">
                    Live Share
                    {shareActive && <Badge className="bg-blue-500"><Eye className="h-3 w-3 mr-1" />{viewerCount} watching</Badge>}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {shareActive ? 'Contacts can watch and send guidance' : 'Share not active'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {shareActive && shareLink && (
                  <Button variant="outline" size="sm" onClick={() => navigator.clipboard.writeText(shareLink).then(() => toast.success('Copied!'))}>
                    <Copy className="h-4 w-4" />
                  </Button>
                )}
                <Button variant={shareActive ? "destructive" : "default"} size="sm" onClick={shareActive ? revokeShareLink : shareStreamLink}>
                  {shareActive ? 'Stop Sharing' : 'Share Now'}
                </Button>
              </div>
            </div>
            
            {guidanceMessages.length > 0 && (
              <ScrollArea className="h-32">
                <div className="space-y-2">
                  {guidanceMessages.slice(-5).map((msg, idx) => (
                    <div key={msg.message_id || idx} className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-blue-400">{msg.sender_name}</span>
                        <span className="text-xs text-muted-foreground">{new Date(msg.timestamp).toLocaleTimeString()}</span>
                      </div>
                      <p className="text-sm">{msg.message}</p>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>

        {/* AI Risk Monitor */}
        <Card className={`border-2 ${
          analysis.riskLevel === 'critical' ? 'border-red-500 bg-red-500/10' :
          analysis.riskLevel === 'high' ? 'border-orange-500 bg-orange-500/10' :
          analysis.riskLevel === 'medium' ? 'border-yellow-500 bg-yellow-500/10' :
          'border-green-500/30 bg-green-500/5'
        }`}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-full ${riskLevelColors[analysis.riskLevel]}`}>
                  <Scale className="h-5 w-5 text-white" />
                </div>
                <div>
                  <p className="font-bold">AI Rights Monitor</p>
                  <p className="text-sm text-muted-foreground">
                    {analysis.detectedViolations.length > 0 
                      ? `${analysis.detectedViolations.length} potential violation(s)` 
                      : 'Monitoring...'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge className={riskLevelColors[analysis.riskLevel]}>{riskLevelLabels[analysis.riskLevel]}</Badge>
                {analysis.hasViolations && (
                  <Button variant="outline" size="sm" onClick={() => setShowViolationsPanel(!showViolationsPanel)}>
                    {showViolationsPanel ? 'Hide' : 'View'}
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Violations Panel */}
        {showViolationsPanel && (
          <ViolationsPanel
            isOpen={showViolationsPanel}
            onClose={() => setShowViolationsPanel(false)}
            riskLevel={analysis.riskLevel}
            detectedViolations={analysis.detectedViolations}
            biasIndicators={analysis.biasIndicators}
            proceduralIssues={analysis.proceduralIssues}
            manualMarks={manualViolationMarks}
          />
        )}

        {/* Transcription */}
        <TranscriptionPanel transcriptions={transcriptions} maxHeight="200px" />

        {/* Officer Info */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Officer Information</CardTitle>
              <div className="flex gap-2">
                <QuickOfficerLookup onOfficerFound={setLookedUpOfficer} />
                <Button variant="outline" size="sm" onClick={() => setShowOfficerForm(!showOfficerForm)}>
                  {showOfficerForm ? 'Cancel' : 'Add Manually'}
                </Button>
              </div>
            </div>
          </CardHeader>
          {lookedUpOfficer && (
            <CardContent className="pb-2">
              <div className={`p-3 rounded-lg border-2 ${
                lookedUpOfficer.warning_level?.level === 'high' ? 'bg-red-500/10 border-red-500/30' :
                lookedUpOfficer.warning_level?.level === 'elevated' ? 'bg-orange-500/10 border-orange-500/30' :
                'bg-green-500/10 border-green-500/30'
              }`}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold">{lookedUpOfficer.full_name}</p>
                    <p className="text-xs text-muted-foreground">Badge #{lookedUpOfficer.badge_number}</p>
                  </div>
                  <div className="text-right">
                    <p className={`text-xl font-bold ${lookedUpOfficer.accountability_score >= 60 ? 'text-green-500' : 'text-red-500'}`}>
                      {lookedUpOfficer.accountability_score}
                    </p>
                    <p className="text-xs">Score</p>
                  </div>
                </div>
              </div>
            </CardContent>
          )}
          {showOfficerForm && (
            <CardContent className="space-y-3">
              <Input placeholder="Officer Name" value={officerInfo.name} onChange={(e) => setOfficerInfo(p => ({ ...p, name: e.target.value }))} />
              <Input placeholder="Badge Number" value={officerInfo.badge} onChange={(e) => setOfficerInfo(p => ({ ...p, badge: e.target.value }))} />
              <Input placeholder="Department" value={officerInfo.department} onChange={(e) => setOfficerInfo(p => ({ ...p, department: e.target.value }))} />
              <Button onClick={addOfficerInfo} className="w-full">Save Officer Info</Button>
            </CardContent>
          )}
        </Card>

        {/* Control Buttons */}
        <div className="grid grid-cols-2 gap-4">
          <Button variant="outline" size="lg" onClick={pauseRecording} className="h-14">
            {isPaused ? <Play className="h-5 w-5 mr-2" /> : <Pause className="h-5 w-5 mr-2" />}
            {isPaused ? 'Resume' : 'Pause'}
          </Button>
          <Button variant="destructive" size="lg" onClick={stopRecording} className="h-14" data-testid="stop-recording-btn">
            <StopCircle className="h-5 w-5 mr-2" />
            End Recording
          </Button>
        </div>

        {/* Quick Actions */}
        <div className="space-y-3">
          {/* SOS Button */}
          {sosActive ? (
            <Button variant="outline" size="lg" className="w-full h-16 border-2 border-green-500 bg-green-500/20 text-green-400" onClick={cancelSOS}>
              <CheckCircle className="h-6 w-6 mr-2" />
              <div className="flex flex-col items-start">
                <span className="font-bold">SOS Active - Contacts Notified</span>
                <span className="text-xs opacity-70">Click to cancel</span>
              </div>
            </Button>
          ) : (
            <Button variant="destructive" size="lg" className="w-full h-16 bg-red-600 hover:bg-red-700 animate-pulse" onClick={triggerQuickSOS} disabled={sosSending || !encounter}>
              <Siren className="h-6 w-6 mr-2" />
              <div className="flex flex-col items-start">
                <span className="font-bold">{sosSending ? 'Sending SOS...' : 'QUICK SOS'}</span>
                <span className="text-xs opacity-70">Alert all emergency contacts</span>
              </div>
            </Button>
          )}

          {/* Quick Nav */}
          <div className="grid grid-cols-3 gap-2">
            <Button variant="outline" size="sm" className="flex-col h-auto py-3" onClick={() => navigate('/emergency-contacts')}>
              <Users className="h-5 w-5 mb-1" /><span className="text-xs">Contacts</span>
            </Button>
            <Button variant="outline" size="sm" className="flex-col h-auto py-3" onClick={shareStreamLink}>
              <Share2 className="h-5 w-5 mb-1" /><span className="text-xs">Share Live</span>
            </Button>
            <Button variant="outline" size="sm" className="flex-col h-auto py-3" onClick={() => navigate('/rights')}>
              <Eye className="h-5 w-5 mb-1" /><span className="text-xs">Know Rights</span>
            </Button>
          </div>

          {/* Attorney Stream & Cloud Backup */}
          <div className="grid grid-cols-2 gap-2">
            {attorneyStreamActive ? (
              <Button variant="outline" className="border-green-500 text-green-500 h-12" onClick={endAttorneyStream}>
                <Video className="h-4 w-4 mr-2" />
                <div className="flex flex-col items-start">
                  <span className="text-xs font-bold">Attorney Watching</span>
                  <span className="text-xs opacity-70">End stream</span>
                </div>
              </Button>
            ) : (
              <Dialog open={showStreamDialog} onOpenChange={setShowStreamDialog}>
                <DialogTrigger asChild>
                  <Button variant="outline" className="border-blue-500 text-blue-500 h-12">
                    <Video className="h-4 w-4 mr-2" />
                    <div className="flex flex-col items-start">
                      <span className="text-xs font-bold">Stream to Attorney</span>
                      <span className="text-xs opacity-70">Live video</span>
                    </div>
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Stream to Your Attorney</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 pt-4">
                    <p className="text-sm text-muted-foreground">Your attorney will receive a secure link.</p>
                    <div className="space-y-2">
                      <Label>Attorney Email (optional)</Label>
                      <Input type="email" placeholder="attorney@lawfirm.com" value={streamAttorneyEmail} onChange={(e) => setStreamAttorneyEmail(e.target.value)} />
                    </div>
                    <Button className="w-full" onClick={startAttorneyStream} disabled={streamingToAttorney}>
                      {streamingToAttorney ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Video className="h-4 w-4 mr-2" />}
                      Start Live Stream
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            )}
            
            <Button variant="outline" className="border-purple-500 text-purple-500 h-12" onClick={triggerCloudBackup} disabled={!encounter}>
              <Wifi className="h-4 w-4 mr-2" />
              <div className="flex flex-col items-start">
                <span className="text-xs font-bold">Cloud Backup</span>
                <span className="text-xs opacity-70">Multi-cloud</span>
              </div>
            </Button>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}

// Export with error boundary
export function EncounterPageWithErrorBoundary() {
  return (
    <EncounterErrorBoundary>
      <EncounterPage />
    </EncounterErrorBoundary>
  );
}
