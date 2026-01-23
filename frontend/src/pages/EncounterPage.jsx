import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { ScrollArea } from '../components/ui/scroll-area';
import { encounterAPI } from '../lib/api';
import { useWebSocket } from '../contexts/WebSocketContext';
import { 
  Shield, AlertTriangle, Mic, MicOff, Video, VideoOff, 
  MapPin, Clock, FileText, Send, Users, Radio, 
  StopCircle, Play, Pause, ChevronRight, Phone, Share2,
  Eye, AlertCircle, Scale, CheckCircle, Camera, Volume2, VolumeX,
  MessageCircle, Copy, ExternalLink, Siren
} from 'lucide-react';
import { sosAPI } from '../lib/api';
import { toast } from 'sonner';
import RightsCoachPanel from '../components/RightsCoachPanel';

const encounterTypes = [
  { value: 'traffic_stop', label: 'Traffic Stop' },
  { value: 'pedestrian_stop', label: 'Pedestrian Stop' },
  { value: 'arrest', label: 'Arrest' },
  { value: 'search', label: 'Search/Seizure' },
  { value: 'other', label: 'Other' }
];

const broadcastModes = [
  { value: 'save', label: 'Save Only', icon: FileText, desc: 'Record and save locally' },
  { value: 'share_contacts', label: 'Share with Contacts', icon: Users, desc: 'Notify emergency contacts' },
  { value: 'share_attorney', label: 'Share with Attorney', icon: Scale, desc: 'Alert your attorney' },
  { value: 'livestream', label: 'Livestream', icon: Radio, desc: 'Stream live publicly' },
  { value: 'all', label: 'All Options', icon: Share2, desc: 'Maximum protection' }
];

const rightsReminders = [
  "You have the right to remain silent.",
  "You do not have to consent to a search.",
  "Ask: 'Am I being detained or am I free to go?'",
  "You have the right to an attorney.",
  "Do not physically resist, even if your rights are violated.",
  "Everything is being recorded for your protection."
];

// Voice commands configuration
const voiceCommands = [
  { phrases: ['mark violation', 'flag violation', 'violation'], action: 'MARK_VIOLATION', feedback: 'Violation marked!' },
  { phrases: ['call attorney', 'contact attorney', 'lawyer'], action: 'CALL_ATTORNEY', feedback: 'Contacting attorney...' },
  { phrases: ['emergency', 'sos', 'help me', 'send help'], action: 'SOS', feedback: 'Sending SOS alert!' },
  { phrases: ['end recording', 'stop recording', 'stop'], action: 'END_RECORDING', feedback: 'Ending recording...' },
  { phrases: ['pause recording', 'pause'], action: 'PAUSE', feedback: 'Recording paused' },
  { phrases: ['resume recording', 'resume', 'continue'], action: 'RESUME', feedback: 'Recording resumed' },
  { phrases: ['share link', 'share stream', 'share'], action: 'SHARE', feedback: 'Sharing stream link...' },
];

const riskLevelColors = {
  low: 'bg-green-500',
  medium: 'bg-yellow-500',
  high: 'bg-orange-500',
  critical: 'bg-red-500 animate-pulse'
};

const riskLevelLabels = {
  low: 'Normal',
  medium: 'Caution',
  high: 'Alert',
  critical: 'CRITICAL'
};

// Tone/emotion colors and icons
const toneColors = {
  professional: 'bg-green-500/20 text-green-400 border-green-500/30',
  calm: 'bg-green-500/20 text-green-400 border-green-500/30',
  assertive: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  anxious: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  defensive: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  compliant: 'bg-green-500/20 text-green-400 border-green-500/30',
  aggressive: 'bg-red-500/20 text-red-400 border-red-500/30',
  intimidating: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  hostile: 'bg-red-500/20 text-red-400 border-red-500/30 animate-pulse',
  neutral: 'bg-gray-500/20 text-gray-400 border-gray-500/30'
};

const toneIcons = {
  professional: '✓',
  calm: '😌',
  assertive: '💪',
  anxious: '😰',
  defensive: '🛡️',
  compliant: '👍',
  aggressive: '⚠️',
  intimidating: '😠',
  hostile: '🚨',
  neutral: '•'
};

const toneSeverityColors = {
  normal: 'bg-green-500',
  elevated: 'bg-yellow-500',
  concerning: 'bg-orange-500',
  critical: 'bg-red-500 animate-pulse'
};

// Keywords to highlight in transcription
const highlightKeywords = {
  danger: ['search', 'arrest', 'detain', 'weapon', 'gun', 'resist', 'jail', 'prison'],
  rights: ['silent', 'attorney', 'lawyer', 'rights', 'consent', 'free to go', 'detained'],
  command: ['license', 'registration', 'step out', 'hands up', 'don\'t move', 'stop']
};

// Helper to highlight keywords in text
const highlightText = (text) => {
  if (!text) return text;
  
  let result = text;
  
  // Mark danger words
  highlightKeywords.danger.forEach(word => {
    const regex = new RegExp(`\\b(${word})\\b`, 'gi');
    result = result.replace(regex, '<span class="text-red-400 font-medium">$1</span>');
  });
  
  // Mark rights words  
  highlightKeywords.rights.forEach(word => {
    const regex = new RegExp(`\\b(${word})\\b`, 'gi');
    result = result.replace(regex, '<span class="text-green-400 font-medium">$1</span>');
  });
  
  // Mark command words
  highlightKeywords.command.forEach(word => {
    const regex = new RegExp(`\\b(${word})\\b`, 'gi');
    result = result.replace(regex, '<span class="text-yellow-400 font-medium">$1</span>');
  });
  
  return result;
};

export default function EncounterPage() {
  const navigate = useNavigate();
  const { notifications } = useWebSocket();
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [encounter, setEncounter] = useState(null);
  const [encounterType, setEncounterType] = useState('traffic_stop');
  const [broadcastMode, setBroadcastMode] = useState('save');
  const [location, setLocation] = useState(null);
  const [address, setAddress] = useState('');
  const [duration, setDuration] = useState(0);
  const [transcriptions, setTranscriptions] = useState([]);
  const [violations, setViolations] = useState([]);
  const [currentRightsIndex, setCurrentRightsIndex] = useState(0);
  const [officerInfo, setOfficerInfo] = useState({ name: '', badge: '', department: '' });
  const [showOfficerForm, setShowOfficerForm] = useState(false);
  
  // AI Analysis State
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [riskLevel, setRiskLevel] = useState('low');
  const [detectedViolations, setDetectedViolations] = useState([]);
  const [biasIndicators, setBiasIndicators] = useState([]);
  const [proceduralIssues, setProceduralIssues] = useState([]);
  const [immediateAlert, setImmediateAlert] = useState(null);
  const [showViolationsPanel, setShowViolationsPanel] = useState(false);
  const [fullTranscript, setFullTranscript] = useState('');
  const [enableVideo, setEnableVideo] = useState(true);
  const [videoChunkCount, setVideoChunkCount] = useState(0);
  const [uploadingChunk, setUploadingChunk] = useState(false);
  
  // Voice Commands State
  const [voiceCommandsEnabled, setVoiceCommandsEnabled] = useState(true);
  const [lastVoiceCommand, setLastVoiceCommand] = useState(null);
  const [voiceCommandFeedback, setVoiceCommandFeedback] = useState('');
  const [manualViolationMarks, setManualViolationMarks] = useState([]);
  
  // Real-time Sharing State
  const [shareLink, setShareLink] = useState(null);
  const [shareActive, setShareActive] = useState(false);
  const [viewerCount, setViewerCount] = useState(0);
  const [guidanceMessages, setGuidanceMessages] = useState([]);
  const [autoShare, setAutoShare] = useState(true);
  
  // Screen Recording State
  const [enableScreenRecording, setEnableScreenRecording] = useState(false);
  const [screenRecordingActive, setScreenRecordingActive] = useState(false);
  const [screenRecordingSupported, setScreenRecordingSupported] = useState(false);
  const [screenChunkCount, setScreenChunkCount] = useState(0);
  
  const mediaRecorderRef = useRef(null);
  const audioRecorderRef = useRef(null);
  const screenRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const videoChunksRef = useRef([]);
  const screenChunksRef = useRef([]);
  const streamRef = useRef(null);
  const audioStreamRef = useRef(null);
  const screenStreamRef = useRef(null);
  const videoPreviewRef = useRef(null);
  const chunkIndexRef = useRef(0);
  const videoChunkIndexRef = useRef(0);
  const screenChunkIndexRef = useRef(0);
  const timerRef = useRef(null);
  const analysisQueueRef = useRef([]);
  const lastAnalysisRef = useRef(0);
  const voiceRecognitionRef = useRef(null);
  const stopRecordingRef = useRef(null);
  const shareStreamLinkRef = useRef(null);

  // Quick SOS State
  const [sosActive, setSosActive] = useState(false);
  const [sosSending, setSosSending] = useState(false);
  const [sosAlertId, setSosAlertId] = useState(null);

  // Quick SOS function - sends emergency alert to all contacts
  const triggerQuickSOS = async () => {
    if (!encounter || sosSending) return;
    
    setSosSending(true);
    
    try {
      const response = await sosAPI.createEncounterSOS({
        encounter_id: encounter.encounter_id,
        latitude: location?.coords?.latitude,
        longitude: location?.coords?.longitude,
        address: address || 'Unknown location',
        message: 'Emergency SOS - I need help during a police encounter!'
      });
      
      setSosActive(true);
      setSosAlertId(response.data.alert_id);
      
      toast.success(
        `🚨 SOS Alert Sent! ${response.data.contacts_notified} contact(s) notified.`,
        { duration: 5000 }
      );
      
      // Set immediate alert for UI
      setImmediateAlert({
        type: 'sos_active',
        message: `SOS active - ${response.data.contacts_notified} contacts notified`,
        severity: 10
      });
      
    } catch (error) {
      console.error('SOS error:', error);
      toast.error('Failed to send SOS alert. Try again or call 911.');
    } finally {
      setSosSending(false);
    }
  };

  // Cancel SOS function
  const cancelSOS = async () => {
    if (!sosAlertId) return;
    
    try {
      await sosAPI.resolve(sosAlertId);
      setSosActive(false);
      setSosAlertId(null);
      setImmediateAlert(null);
      toast.success('SOS alert cancelled');
    } catch (error) {
      console.error('Cancel SOS error:', error);
    }
  };

  // Perform real-time AI analysis on transcriptions
  const performAIAnalysis = async (text) => {
    if (!encounter || !text || text.length < 30) return;
    
    // Throttle analysis to every 15 seconds
    const now = Date.now();
    if (now - lastAnalysisRef.current < 15000) {
      analysisQueueRef.current.push(text);
      return;
    }
    lastAnalysisRef.current = now;
    
    // Combine queued text
    const combinedText = [...analysisQueueRef.current, text].join(' ');
    analysisQueueRef.current = [];
    
    // Update full transcript for analysis
    setFullTranscript(prev => prev + ' ' + combinedText);
    
    try {
      const response = await encounterAPI.analyzeRealtime(
        encounter.encounter_id,
        fullTranscript + ' ' + combinedText
      );
      
      const analysis = response.data.analysis;
      setAiAnalysis(analysis);
      
      // Update risk level
      if (analysis.risk_level) {
        setRiskLevel(analysis.risk_level);
        
        if (analysis.risk_level === 'critical' || analysis.risk_level === 'high') {
          toast.error(`⚠️ ${analysis.risk_level.toUpperCase()} RISK: Potential violation detected!`, {
            duration: 10000
          });
        }
      }
      
      // Update violations
      if (analysis.violations?.length > 0) {
        setDetectedViolations(prev => {
          const newViolations = analysis.violations.filter(
            v => !prev.some(pv => pv.type === v.type && pv.quote === v.quote)
          );
          return [...prev, ...newViolations];
        });
      }
      
      // Update bias indicators
      if (analysis.bias_indicators?.length > 0) {
        setBiasIndicators(prev => [...prev, ...analysis.bias_indicators]);
      }
      
      // Update procedural issues
      if (analysis.procedural_issues?.length > 0) {
        setProceduralIssues(prev => [...prev, ...analysis.procedural_issues]);
      }
      
      // Show immediate alert if present
      if (analysis.immediate_alert) {
        setImmediateAlert(analysis.immediate_alert);
        toast.warning(analysis.immediate_alert, { duration: 15000 });
      }
      
    } catch (error) {
      console.error('AI analysis error:', error);
    }
  };

  // Voice Command Handler
  const handleVoiceCommand = useCallback(async (command) => {
    const commandLower = command.toLowerCase().trim();
    
    for (const vc of voiceCommands) {
      for (const phrase of vc.phrases) {
        if (commandLower.includes(phrase)) {
          setLastVoiceCommand(vc.action);
          setVoiceCommandFeedback(vc.feedback);
          
          // Clear feedback after 3 seconds
          setTimeout(() => setVoiceCommandFeedback(''), 3000);
          
          // Execute the command
          switch (vc.action) {
            case 'MARK_VIOLATION':
              const mark = {
                timestamp: duration,
                time: new Date().toISOString(),
                note: 'Voice command: violation marked'
              };
              setManualViolationMarks(prev => [...prev, mark]);
              toast.success('📍 Violation marked at ' + formatDuration(duration));
              // Also add to violations list
              setViolations(prev => [...prev, `Manual mark at ${formatDuration(duration)}`]);
              // Persist to backend
              if (encounter) {
                try {
                  await encounterAPI.markViolation(encounter.encounter_id, duration, 'Voice command: violation marked');
                } catch (err) {
                  console.log('Could not persist mark:', err);
                }
              }
              break;
              
            case 'CALL_ATTORNEY':
              toast.info('📞 Contacting your attorney...', { duration: 5000 });
              // In production, this would trigger actual attorney contact
              break;
              
            case 'SOS':
              if (encounter && location) {
                try {
                  await sosAPI.create({
                    encounter_id: encounter.encounter_id,
                    latitude: location.latitude,
                    longitude: location.longitude,
                    message: 'VOICE COMMAND SOS - Immediate assistance needed'
                  });
                  toast.error('🚨 SOS ALERT SENT! Help is on the way.', { duration: 10000 });
                } catch (err) {
                  toast.error('SOS sent to emergency contacts');
                }
              }
              break;
              
            case 'END_RECORDING':
              if (stopRecordingRef.current) stopRecordingRef.current();
              break;
              
            case 'PAUSE':
              if (!isPaused && mediaRecorderRef.current) {
                mediaRecorderRef.current.pause();
                if (audioRecorderRef.current) audioRecorderRef.current.pause();
                setIsPaused(true);
                toast.info('⏸️ Recording paused');
              }
              break;
              
            case 'RESUME':
              if (isPaused && mediaRecorderRef.current) {
                mediaRecorderRef.current.resume();
                if (audioRecorderRef.current) audioRecorderRef.current.resume();
                setIsPaused(false);
                toast.success('▶️ Recording resumed');
              }
              break;
              
            case 'SHARE':
              if (shareStreamLinkRef.current) shareStreamLinkRef.current();
              break;
              
            default:
              break;
          }
          return true;
        }
      }
    }
    return false;
  }, [encounter, location, duration, isPaused]);

  // Initialize Voice Recognition
  useEffect(() => {
    if (!isRecording || !voiceCommandsEnabled) return;
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.log('Speech recognition not supported');
      return;
    }
    
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    
    recognition.onresult = (event) => {
      const last = event.results.length - 1;
      const transcript = event.results[last][0].transcript;
      console.log('Voice heard:', transcript);
      handleVoiceCommand(transcript);
    };
    
    recognition.onerror = (event) => {
      if (event.error !== 'no-speech') {
        console.log('Speech recognition error:', event.error);
      }
    };
    
    recognition.onend = () => {
      // Restart recognition if still recording
      if (isRecording && voiceCommandsEnabled) {
        try {
          recognition.start();
        } catch (e) {
          // Already started
        }
      }
    };
    
    try {
      recognition.start();
      voiceRecognitionRef.current = recognition;
    } catch (e) {
      console.log('Could not start voice recognition');
    }
    
    return () => {
      if (voiceRecognitionRef.current) {
        voiceRecognitionRef.current.stop();
        voiceRecognitionRef.current = null;
      }
    };
  }, [isRecording, voiceCommandsEnabled, handleVoiceCommand]);

  // Get user location on mount
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocation({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude
          });
        },
        (error) => {
          console.error('Geolocation error:', error);
          toast.error('Could not get your location. Please enable location services.');
        },
        { enableHighAccuracy: true }
      );
    }
  }, []);

  // Rotate rights reminders
  useEffect(() => {
    if (isRecording && !isPaused) {
      const interval = setInterval(() => {
        setCurrentRightsIndex(prev => (prev + 1) % rightsReminders.length);
      }, 8000);
      return () => clearInterval(interval);
    }
  }, [isRecording, isPaused]);

  // Check screen recording support on mount
  useEffect(() => {
    const checkScreenRecordingSupport = () => {
      // Check if getDisplayMedia is available
      if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
        setScreenRecordingSupported(true);
      } else {
        setScreenRecordingSupported(false);
      }
    };
    checkScreenRecordingSupport();
  }, []);

  // Duration timer
  useEffect(() => {
    if (isRecording && !isPaused) {
      timerRef.current = setInterval(() => {
        setDuration(prev => prev + 1);
      }, 1000);
      return () => clearInterval(timerRef.current);
    } else {
      clearInterval(timerRef.current);
    }
  }, [isRecording, isPaused]);

  // Listen for guidance messages and viewer count from WebSocket
  useEffect(() => {
    if (!encounter || notifications.length === 0) return;
    
    const latestNotifications = notifications.filter(n => 
      n.encounter_id === encounter.encounter_id
    );
    
    for (const notif of latestNotifications) {
      if (notif.type === 'guidance_message') {
        setGuidanceMessages(prev => {
          // Avoid duplicates
          if (prev.some(m => m.message_id === notif.message_id)) return prev;
          return [...prev, notif];
        });
      } else if (notif.type === 'viewer_joined' || notif.type === 'viewer_left') {
        setViewerCount(notif.viewer_count || 0);
      }
    }
  }, [notifications, encounter]);

  const formatDuration = (seconds) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const startRecording = async () => {
    if (!location) {
      toast.error('Please enable location services to start recording');
      return;
    }

    try {
      // Start encounter on backend
      const response = await encounterAPI.start({
        latitude: location.latitude,
        longitude: location.longitude,
        address: address || `${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)}`,
        encounter_type: encounterType,
        broadcast_mode: broadcastMode,
        video_enabled: enableVideo
      });

      setEncounter(response.data);
      
      // Auto-share if enabled
      if (autoShare) {
        try {
          const shareResponse = await encounterAPI.createShare(response.data.encounter_id, true);
          if (shareResponse.data.success) {
            setShareLink(shareResponse.data.full_url);
            setShareActive(true);
            toast.success(`📤 Live share enabled! ${shareResponse.data.notified_contacts?.length || 0} contacts notified.`);
          }
        } catch (shareErr) {
          console.log('Auto-share failed:', shareErr);
        }
      }
      
      // Request media permissions based on settings
      const mediaConstraints = {
        audio: true,
        video: enableVideo ? {
          facingMode: 'environment', // Use back camera
          width: { ideal: 1280 },
          height: { ideal: 720 }
        } : false
      };

      const stream = await navigator.mediaDevices.getUserMedia(mediaConstraints);
      streamRef.current = stream;

      // Show video preview if video is enabled
      if (enableVideo && videoPreviewRef.current) {
        videoPreviewRef.current.srcObject = stream;
      }

      // Determine the correct MIME type
      const videoMimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus') 
        ? 'video/webm;codecs=vp9,opus'
        : MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus')
        ? 'video/webm;codecs=vp8,opus'
        : 'video/webm';

      const audioMimeType = 'audio/webm;codecs=opus';

      // Create video/audio recorder for the full stream
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: enableVideo ? videoMimeType : audioMimeType
      });
      mediaRecorderRef.current = mediaRecorder;

      // Also create a separate audio recorder for transcription
      if (enableVideo) {
        const audioStream = new MediaStream(stream.getAudioTracks());
        const audioRecorder = new MediaRecorder(audioStream, { mimeType: audioMimeType });
        audioRecorderRef.current = audioRecorder;

        audioRecorder.ondataavailable = async (event) => {
          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data);
            
            // Upload audio chunk for transcription
            if (audioChunksRef.current.length >= 1) {
              const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
              audioChunksRef.current = [];
              
              try {
                const result = await encounterAPI.uploadAudio(
                  response.data.encounter_id,
                  blob,
                  chunkIndexRef.current++
                );
                
                if (result.data.transcription) {
                  setTranscriptions(prev => [...prev, result.data.transcription]);
                  
                  // Trigger AI analysis with new transcription
                  if (result.data.transcription.text) {
                    performAIAnalysis(result.data.transcription.text);
                  }
                  
                  if (result.data.transcription.violations_detected?.length > 0) {
                    setViolations(prev => [...prev, ...result.data.transcription.violations_detected]);
                    toast.warning('⚠️ Potential violation detected!', {
                      description: result.data.transcription.violations_detected.join(', ')
                    });
                  }
                }
              } catch (err) {
                console.error('Audio upload error:', err);
              }
            }
          }
        };

        audioRecorder.start(10000); // Record audio in 10-second chunks for transcription
      }

      // Handle video/audio chunks
      mediaRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0) {
          videoChunksRef.current.push(event.data);
          
          // Upload video chunk every 15 seconds
          if (videoChunksRef.current.length >= 1) {
            const blob = new Blob(videoChunksRef.current, { 
              type: enableVideo ? 'video/webm' : 'audio/webm' 
            });
            videoChunksRef.current = [];
            const currentChunkIndex = videoChunkIndexRef.current++;
            
            setUploadingChunk(true);
            try {
              await encounterAPI.uploadVideo(
                response.data.encounter_id,
                blob,
                currentChunkIndex
              );
              setVideoChunkCount(prev => prev + 1);
            } catch (err) {
              console.error('Video upload error:', err);
              toast.error('Failed to save video chunk');
            } finally {
              setUploadingChunk(false);
            }
          }
        }
      };

      // If audio-only, handle transcription directly
      if (!enableVideo) {
        mediaRecorder.ondataavailable = async (event) => {
          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data);
            
            if (audioChunksRef.current.length >= 1) {
              const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
              audioChunksRef.current = [];
              
              try {
                const result = await encounterAPI.uploadAudio(
                  response.data.encounter_id,
                  blob,
                  chunkIndexRef.current++
                );
                
                if (result.data.transcription) {
                  setTranscriptions(prev => [...prev, result.data.transcription]);
                  if (result.data.transcription.violations_detected?.length > 0) {
                    setViolations(prev => [...prev, ...result.data.transcription.violations_detected]);
                    toast.warning('⚠️ Potential violation detected!', {
                      description: result.data.transcription.violations_detected.join(', ')
                    });
                  }
                }
              } catch (err) {
                console.error('Upload error:', err);
              }
            }
          }
        };
      }

      // Record in 15-second chunks for video (larger chunks for better quality)
      mediaRecorder.start(15000);
      setIsRecording(true);
      setDuration(0);
      setVideoChunkCount(0);
      
      // Start screen recording if enabled and supported
      if (enableScreenRecording && screenRecordingSupported) {
        try {
          const screenStream = await navigator.mediaDevices.getDisplayMedia({
            video: {
              cursor: 'always',
              displaySurface: 'monitor'
            },
            audio: false // Don't capture system audio
          });
          screenStreamRef.current = screenStream;
          
          const screenRecorder = new MediaRecorder(screenStream, {
            mimeType: MediaRecorder.isTypeSupported('video/webm;codecs=vp9') 
              ? 'video/webm;codecs=vp9' 
              : 'video/webm'
          });
          screenRecorderRef.current = screenRecorder;
          
          screenRecorder.ondataavailable = async (event) => {
            if (event.data.size > 0) {
              screenChunksRef.current.push(event.data);
              
              if (screenChunksRef.current.length >= 1) {
                const blob = new Blob(screenChunksRef.current, { type: 'video/webm' });
                screenChunksRef.current = [];
                const currentChunkIndex = screenChunkIndexRef.current++;
                
                try {
                  await encounterAPI.uploadScreen(
                    response.data.encounter_id,
                    blob,
                    currentChunkIndex
                  );
                  setScreenChunkCount(prev => prev + 1);
                } catch (err) {
                  console.error('Screen upload error:', err);
                }
              }
            }
          };
          
          // Handle user stopping screen share via browser UI
          screenStream.getVideoTracks()[0].onended = () => {
            setScreenRecordingActive(false);
            toast.info('Screen recording stopped');
          };
          
          screenRecorder.start(15000); // 15-second chunks
          setScreenRecordingActive(true);
          toast.success('📱 Screen recording started');
        } catch (screenErr) {
          console.log('Screen recording not started:', screenErr.message);
          if (screenErr.name !== 'NotAllowedError') {
            toast.info('Screen recording unavailable on this device');
          }
        }
      }
      
      toast.success(`🚨 ${enableVideo ? 'Video' : 'Audio'} recording started. Stay calm and know your rights.`);
      
    } catch (error) {
      console.error('Recording error:', error);
      if (error.name === 'NotAllowedError') {
        toast.error('Please allow camera and microphone access to record');
      } else {
        toast.error('Failed to start recording: ' + (error.response?.data?.detail || error.message));
      }
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      if (isPaused) {
        mediaRecorderRef.current.resume();
        if (audioRecorderRef.current) audioRecorderRef.current.resume();
        setIsPaused(false);
        toast.info('Recording resumed');
      } else {
        mediaRecorderRef.current.pause();
        if (audioRecorderRef.current) audioRecorderRef.current.pause();
        setIsPaused(true);
        toast.info('Recording paused');
      }
    }
  };

  const stopRecording = async () => {
    if (mediaRecorderRef.current) {
      // Stop voice recognition
      if (voiceRecognitionRef.current) {
        voiceRecognitionRef.current.stop();
        voiceRecognitionRef.current = null;
      }
      
      // Stop all recorders
      mediaRecorderRef.current.stop();
      if (audioRecorderRef.current) audioRecorderRef.current.stop();
      if (screenRecorderRef.current) {
        screenRecorderRef.current.stop();
        screenRecorderRef.current = null;
      }
      
      // Stop all tracks
      streamRef.current?.getTracks().forEach(track => track.stop());
      screenStreamRef.current?.getTracks().forEach(track => track.stop());
      
      // Clear video preview
      if (videoPreviewRef.current) {
        videoPreviewRef.current.srcObject = null;
      }
      
      setScreenRecordingActive(false);
      
      try {
        toast.info('Processing recording and generating report...');
        const response = await encounterAPI.end(encounter.encounter_id);
        toast.success('Recording ended. Detailed report generated!');
        navigate(`/encounters/${encounter.encounter_id}`);
      } catch (error) {
        console.error('Error ending encounter:', error);
        toast.error('Error ending encounter');
      }
      
      setIsRecording(false);
      setIsPaused(false);
    }
  };
  
  // Assign to ref for voice commands
  stopRecordingRef.current = stopRecording;

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

  const shareStreamLink = async () => {
    if (!encounter) return;
    
    try {
      if (!shareActive) {
        // Create new share link
        const response = await encounterAPI.createShare(encounter.encounter_id, false);
        const fullUrl = `${window.location.origin}${response.data.share_url}`;
        setShareLink(fullUrl);
        setShareActive(true);
        
        // Try to share via native share API if available
        if (navigator.share) {
          await navigator.share({
            title: 'JUSTICE - Live Encounter Recording',
            text: 'I\'m being pulled over. Watch my live recording and send guidance.',
            url: fullUrl
          });
          toast.success('Shared successfully!');
        } else {
          // Fallback to clipboard
          await navigator.clipboard.writeText(fullUrl);
          toast.success('Share link created and copied! Share with your contacts.');
        }
      } else {
        // Copy existing link
        if (shareLink) {
          await navigator.clipboard.writeText(shareLink);
          toast.success('Link copied to clipboard!');
        }
      }
    } catch (error) {
      console.error('Share error:', error);
      toast.error('Failed to generate share link');
    }
  };
  
  // Revoke share link
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
  
  // Assign to ref for voice commands
  shareStreamLinkRef.current = shareStreamLink;

  // Not recording yet - show setup screen
  if (!isRecording) {
    return (
      <AppLayout>
        <div className="max-w-2xl mx-auto space-y-6" data-testid="encounter-setup">
          {/* Emergency Header */}
          <div className="text-center space-y-4">
            <div className="inline-flex items-center justify-center p-4 rounded-full bg-red-500/20 animate-pulse">
              <Shield className="h-16 w-16 text-red-500" />
            </div>
            <h1 className="font-serif text-4xl font-bold">I&apos;m Being Pulled Over</h1>
            <p className="text-muted-foreground text-lg">
              Record video &amp; audio, pin your location, and protect your rights.
            </p>
          </div>

          {/* Location Status */}
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <MapPin className={`h-5 w-5 ${location ? 'text-green-500' : 'text-yellow-500 animate-pulse'}`} />
                <span className="flex-1">
                  {location 
                    ? `Location: ${location.latitude.toFixed(6)}, ${location.longitude.toFixed(6)}`
                    : 'Getting your location...'}
                </span>
                {location && <CheckCircle className="h-5 w-5 text-green-500" />}
              </div>
              {location && (
                <Input
                  placeholder="Add address or landmark (optional)"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  className="mt-3"
                  data-testid="address-input"
                />
              )}
            </CardContent>
          </Card>

          {/* Recording Mode */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Camera className="h-5 w-5" />
                Recording Mode
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div className="flex items-center gap-3">
                  <Video className={`h-5 w-5 ${enableVideo ? 'text-green-500' : 'text-muted-foreground'}`} />
                  <div>
                    <p className="font-medium">Video Recording</p>
                    <p className="text-sm text-muted-foreground">
                      {enableVideo 
                        ? 'Video + audio will be recorded and saved automatically'
                        : 'Audio only - enable video for visual evidence'}
                    </p>
                  </div>
                </div>
                <Switch 
                  checked={enableVideo} 
                  onCheckedChange={setEnableVideo}
                  data-testid="video-toggle"
                />
              </div>
              {enableVideo && (
                <Alert className="bg-green-500/10 border-green-500/20">
                  <Camera className="h-4 w-4 text-green-500" />
                  <AlertDescription className="text-green-600">
                    Video recordings provide stronger evidence. Files are automatically saved in chunks.
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* Encounter Type */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Type of Encounter</CardTitle>
            </CardHeader>
            <CardContent>
              <Select value={encounterType} onValueChange={setEncounterType}>
                <SelectTrigger data-testid="encounter-type-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {encounterTypes.map(type => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          {/* Broadcast Mode */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Protection Level</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {broadcastModes.map(mode => (
                <button
                  key={mode.value}
                  onClick={() => setBroadcastMode(mode.value)}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg border transition-all ${
                    broadcastMode === mode.value 
                      ? 'border-primary bg-primary/10' 
                      : 'border-border hover:bg-muted'
                  }`}
                  data-testid={`broadcast-${mode.value}`}
                >
                  <mode.icon className="h-5 w-5" />
                  <div className="flex-1 text-left">
                    <p className="font-medium">{mode.label}</p>
                    <p className="text-xs text-muted-foreground">{mode.desc}</p>
                  </div>
                  {broadcastMode === mode.value && (
                    <CheckCircle className="h-5 w-5 text-primary" />
                  )}
                </button>
              ))}
            </CardContent>
          </Card>

          {/* Real-time Sharing Option */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Share2 className="h-5 w-5 text-blue-500" />
                Real-time Sharing
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <Label htmlFor="auto-share">Auto-share with emergency contacts</Label>
                  <p className="text-xs text-muted-foreground">
                    Contacts can watch live and send guidance messages
                  </p>
                </div>
                <Switch
                  id="auto-share"
                  checked={autoShare}
                  onCheckedChange={setAutoShare}
                  data-testid="auto-share-toggle"
                />
              </div>
            </CardContent>
          </Card>

          {/* Screen Recording Option */}
          {screenRecordingSupported && (
            <Card className="border-purple-500/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Video className="h-5 w-5 text-purple-500" />
                  Screen Recording
                  <Badge variant="outline" className="text-xs border-purple-500/50 text-purple-400">
                    Beta
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label htmlFor="screen-recording">Record screen during encounter</Label>
                    <p className="text-xs text-muted-foreground">
                      Capture texts, apps, and on-screen evidence
                    </p>
                  </div>
                  <Switch
                    id="screen-recording"
                    checked={enableScreenRecording}
                    onCheckedChange={setEnableScreenRecording}
                    data-testid="screen-recording-toggle"
                  />
                </div>
                {enableScreenRecording && (
                  <Alert className="bg-purple-500/10 border-purple-500/30">
                    <AlertCircle className="h-4 w-4 text-purple-400" />
                    <AlertDescription className="text-purple-300 text-xs">
                      You'll be asked to select which screen to share when recording starts
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          )}

          {/* Start Button */}
          <Button 
            size="lg" 
            className="w-full h-16 text-xl bg-red-600 hover:bg-red-700"
            onClick={startRecording}
            disabled={!location}
            data-testid="start-recording-btn"
          >
            <Shield className="h-6 w-6 mr-3" />
            START PROTECTION
          </Button>

          <p className="text-center text-sm text-muted-foreground">
            By starting, your location and {enableVideo ? 'video/audio' : 'audio'} will be recorded and stored securely.
          </p>
        </div>
      </AppLayout>
    );
  }

  // Recording in progress
  return (
    <AppLayout>
      <div className="max-w-2xl mx-auto space-y-4" data-testid="encounter-recording">
        {/* Video Preview (if video enabled) */}
        {enableVideo && (
          <Card className="overflow-hidden">
            <div className="relative aspect-video bg-black">
              <video 
                ref={videoPreviewRef}
                autoPlay 
                muted 
                playsInline
                className="w-full h-full object-cover"
              />
              <div className="absolute top-3 left-3 flex items-center gap-2">
                <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${isPaused ? 'bg-yellow-500' : 'bg-red-500 animate-pulse'}`}>
                  <div className="w-2 h-2 bg-white rounded-full" />
                  <span className="text-white text-sm font-bold">{isPaused ? 'PAUSED' : 'REC'}</span>
                </div>
                <Badge variant="secondary" className="bg-black/50 text-white">
                  {formatDuration(duration)}
                </Badge>
              </div>
              <div className="absolute top-3 right-3">
                <Badge variant="secondary" className="bg-black/50 text-white">
                  <Video className="h-3 w-3 mr-1" />
                  {videoChunkCount} chunks saved
                </Badge>
              </div>
              {uploadingChunk && (
                <div className="absolute bottom-3 right-3">
                  <Badge className="bg-blue-500 animate-pulse">
                    Saving...
                  </Badge>
                </div>
              )}
            </div>
          </Card>
        )}

        {/* Recording Status Bar (for audio-only mode) */}
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
                <Badge variant="destructive" className="text-lg px-4 py-1">
                  LIVE
                </Badge>
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

        {/* Voice Commands Panel */}
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
                    {voiceCommandFeedback || 'Say "mark violation", "SOS", "call attorney", "end recording"'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Switch 
                  checked={voiceCommandsEnabled}
                  onCheckedChange={setVoiceCommandsEnabled}
                  data-testid="voice-commands-toggle"
                />
              </div>
            </div>
            {voiceCommandFeedback && (
              <div className="mt-3 p-2 rounded-lg bg-purple-500/20 border border-purple-500/30 animate-pulse">
                <p className="text-sm font-medium text-purple-300 flex items-center gap-2">
                  <CheckCircle className="h-4 w-4" />
                  {voiceCommandFeedback}
                </p>
              </div>
            )}
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

        {/* AI Rights Coach Panel */}
        <RightsCoachPanel
          encounterType={encounterType}
          fullTranscript={fullTranscript}
          isRecording={isRecording}
          isPaused={isPaused}
          onGuidanceReceived={(guidance) => {
            // Handle potential violations from the coach
            if (guidance?.potential_violation) {
              setImmediateAlert({
                type: 'violation',
                message: guidance.potential_violation.explanation,
                severity: guidance.potential_violation.severity
              });
            }
          }}
        />

        {/* Real-time Sharing Status & Guidance */}
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
                    {shareActive && (
                      <Badge className="bg-blue-500">
                        <Eye className="h-3 w-3 mr-1" />
                        {viewerCount} watching
                      </Badge>
                    )}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {shareActive 
                      ? 'Contacts can watch and send guidance' 
                      : 'Share not active'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {shareActive && shareLink && (
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => {
                      navigator.clipboard.writeText(shareLink);
                      toast.success('Link copied!');
                    }}
                    data-testid="copy-share-link"
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                )}
                <Button 
                  variant={shareActive ? "destructive" : "default"}
                  size="sm"
                  onClick={shareActive ? revokeShareLink : shareStreamLink}
                  data-testid="toggle-share-btn"
                >
                  {shareActive ? 'Stop Sharing' : 'Share Now'}
                </Button>
              </div>
            </div>
            
            {/* Incoming Guidance Messages */}
            {guidanceMessages.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-blue-400 flex items-center gap-1">
                  <MessageCircle className="h-3 w-3" />
                  Guidance from viewers:
                </p>
                <ScrollArea className="h-32">
                  <div className="space-y-2 pr-3">
                    {guidanceMessages.slice(-5).map((msg, idx) => (
                      <div 
                        key={msg.message_id || idx}
                        className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20 animate-in fade-in"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-medium text-blue-400">
                            {msg.sender_name}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {new Date(msg.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <p className="text-sm">{msg.message}</p>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            )}
          </CardContent>
        </Card>

        {/* AI Risk Level Indicator */}
        <Card className={`border-2 ${
          riskLevel === 'critical' ? 'border-red-500 bg-red-500/10' :
          riskLevel === 'high' ? 'border-orange-500 bg-orange-500/10' :
          riskLevel === 'medium' ? 'border-yellow-500 bg-yellow-500/10' :
          'border-green-500/30 bg-green-500/5'
        }`}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-full ${riskLevelColors[riskLevel]}`}>
                  <Scale className="h-5 w-5 text-white" />
                </div>
                <div>
                  <p className="font-bold">AI Rights Monitor</p>
                  <p className="text-sm text-muted-foreground">
                    {detectedViolations.length > 0 
                      ? `${detectedViolations.length} potential violation(s) detected`
                      : 'Monitoring for violations...'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge className={riskLevelColors[riskLevel]}>
                  {riskLevelLabels[riskLevel]}
                </Badge>
                {detectedViolations.length > 0 && (
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => setShowViolationsPanel(!showViolationsPanel)}
                  >
                    {showViolationsPanel ? 'Hide' : 'View'} Details
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Immediate Alert */}
        {immediateAlert && (
          <Alert className="border-red-500 bg-red-500/20 animate-pulse">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            <AlertDescription className="text-red-100 font-bold">
              {immediateAlert}
            </AlertDescription>
          </Alert>
        )}

        {/* Detailed Violations Panel */}
        {showViolationsPanel && detectedViolations.length > 0 && (
          <Card className="border-red-500/30">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2 text-red-500">
                <AlertTriangle className="h-5 w-5" />
                Detected Violations & Evidence
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {detectedViolations.map((violation, index) => (
                <div key={index} className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 space-y-2">
                  <div className="flex items-center justify-between">
                    <Badge variant={violation.severity === 'critical' ? 'destructive' : 'secondary'}>
                      {violation.severity?.toUpperCase() || 'ALERT'}
                    </Badge>
                    {violation.amendment && (
                      <Badge variant="outline">{violation.amendment} Amendment</Badge>
                    )}
                  </div>
                  <p className="font-medium">{violation.type?.replace(/_/g, ' ').toUpperCase()}</p>
                  <p className="text-sm text-muted-foreground">{violation.description}</p>
                  {violation.quote && (
                    <div className="p-2 rounded bg-black/20 border-l-2 border-red-500">
                      <p className="text-sm italic">"{violation.quote}"</p>
                    </div>
                  )}
                  {violation.legal_citation && (
                    <p className="text-xs text-muted-foreground">
                      <Scale className="h-3 w-3 inline mr-1" />
                      {violation.legal_citation}
                    </p>
                  )}
                  {violation.defense_strategy && (
                    <p className="text-xs text-green-500">
                      <CheckCircle className="h-3 w-3 inline mr-1" />
                      Defense: {violation.defense_strategy}
                    </p>
                  )}
                </div>
              ))}

              {/* Bias Indicators */}
              {biasIndicators.length > 0 && (
                <div className="pt-2 border-t">
                  <p className="font-medium text-sm mb-2 flex items-center gap-2">
                    <Users className="h-4 w-4" />
                    Bias Indicators Detected
                  </p>
                  {biasIndicators.map((bias, index) => (
                    <div key={index} className="p-2 rounded bg-orange-500/10 text-sm mb-1">
                      <Badge variant="outline" className="mb-1">{bias.type}</Badge>
                      <p className="text-muted-foreground">{bias.evidence}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Procedural Issues */}
              {proceduralIssues.length > 0 && (
                <div className="pt-2 border-t">
                  <p className="font-medium text-sm mb-2 flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Procedural Issues
                  </p>
                  {proceduralIssues.map((issue, index) => (
                    <div key={index} className="p-2 rounded bg-yellow-500/10 text-sm mb-1">
                      <p className="font-medium">{issue.issue}</p>
                      <p className="text-xs text-muted-foreground">Should be: {issue.proper_procedure}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Evidence Summary */}
              {aiAnalysis?.evidence_value && (
                <div className="pt-2 border-t">
                  <p className="font-medium text-sm mb-2 flex items-center gap-2">
                    <Scale className="h-4 w-4 text-green-500" />
                    Case Strength: {aiAnalysis.evidence_value.case_strength?.toUpperCase()}
                  </p>
                  {aiAnalysis.evidence_value.recommended_actions?.length > 0 && (
                    <div className="space-y-1">
                      {aiAnalysis.evidence_value.recommended_actions.map((action, i) => (
                        <p key={i} className="text-xs flex items-center gap-2">
                          <CheckCircle className="h-3 w-3 text-green-500" />
                          {action}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Violations Alert (Simple) */}
        {violations.length > 0 && (
          <Alert className="border-orange-500/50 bg-orange-500/10">
            <AlertTriangle className="h-5 w-5 text-orange-500" />
            <AlertDescription>
              <p className="font-bold">⚠️ Potential violations detected:</p>
              <ul className="mt-1 list-disc list-inside">
                {[...new Set(violations)].map((v, i) => (
                  <li key={i} className="text-sm">{v.replace(/_/g, ' ')}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        {/* Live Transcription */}
        <Card className="border-2 border-blue-500/30">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="h-5 w-5 text-blue-500" />
                Live Transcription
                <Badge variant="outline" className="ml-2 text-xs bg-blue-500/10 border-blue-500/30">
                  <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse mr-1" />
                  LIVE
                </Badge>
              </CardTitle>
              <Badge variant="secondary">
                {transcriptions.length} segment{transcriptions.length !== 1 ? 's' : ''}
              </Badge>
            </div>
            {/* Speaker Legend */}
            <div className="flex flex-wrap gap-3 text-xs mt-2">
              <div className="flex items-center gap-1">
                <span className="w-3 h-3 rounded bg-blue-500/30 border border-blue-500/50" />
                <span className="text-muted-foreground">👮 Officer</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="w-3 h-3 rounded bg-green-500/30 border border-green-500/50" />
                <span className="text-muted-foreground">🙋 Citizen</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-red-400">Red</span>
                <span className="text-muted-foreground">= Danger</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-green-400">Green</span>
                <span className="text-muted-foreground">= Rights</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-yellow-400">Yellow</span>
                <span className="text-muted-foreground">= Commands</span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div 
              className="max-h-64 overflow-y-auto space-y-3 scroll-smooth"
              ref={(el) => { if (el) el.scrollTop = el.scrollHeight; }}
            >
              {transcriptions.length === 0 ? (
                <div className="text-center py-8">
                  <Mic className="h-8 w-8 mx-auto text-muted-foreground/50 mb-2" />
                  <p className="text-muted-foreground">
                    Listening for speech...
                  </p>
                  <p className="text-xs text-muted-foreground/70 mt-1">
                    Transcription will appear here as you speak (with speaker labels)
                  </p>
                </div>
              ) : (
                <>
                  {transcriptions.map((t, i) => (
                    <div 
                      key={i} 
                      className={`p-3 rounded-lg border transition-all ${
                        t.violations_detected?.length > 0 
                          ? 'bg-red-500/10 border-red-500/30' 
                          : t.speaker === 'Officer' 
                            ? 'bg-blue-500/5 border-blue-500/20'
                            : t.speaker === 'Citizen'
                              ? 'bg-green-500/5 border-green-500/20'
                              : 'bg-muted/30 border-border/50'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <div className="flex items-center flex-wrap gap-2">
                          <Badge variant="outline" className="text-xs font-mono">
                            {formatDuration(t.chunk_index ? t.chunk_index * 10 : i * 10)}
                          </Badge>
                          {/* Speaker Badge */}
                          {t.speaker && t.speaker !== 'unknown' && (
                            <Badge 
                              variant="outline" 
                              className={`text-xs ${
                                t.speaker === 'Officer' 
                                  ? 'bg-blue-500/20 border-blue-500/50 text-blue-400' 
                                  : 'bg-green-500/20 border-green-500/50 text-green-400'
                              }`}
                            >
                              {t.speaker === 'Officer' ? '👮' : '🙋'} {t.speaker}
                              {t.speaker_confidence > 0 && (
                                <span className="ml-1 opacity-70">
                                  {Math.round(t.speaker_confidence * 100)}%
                                </span>
                              )}
                            </Badge>
                          )}
                          {/* Tone Badge */}
                          {t.tone && t.tone !== 'neutral' && (
                            <Badge 
                              variant="outline" 
                              className={`text-xs ${toneColors[t.tone] || toneColors.neutral}`}
                            >
                              {toneIcons[t.tone] || '•'} {t.tone}
                              {t.tone_confidence > 0 && (
                                <span className="ml-1 opacity-70">
                                  {Math.round(t.tone_confidence * 100)}%
                                </span>
                              )}
                            </Badge>
                          )}
                          {/* Escalation Alert */}
                          {t.escalation_detected && (
                            <Badge variant="destructive" className="text-xs animate-pulse">
                              📈 {t.escalation_direction === 'escalating' ? 'ESCALATING' : 'TENSION'}
                            </Badge>
                          )}
                          {t.violations_detected?.length > 0 && (
                            <Badge variant="destructive" className="text-xs">
                              <AlertTriangle className="h-3 w-3 mr-1" />
                              Violation
                            </Badge>
                          )}
                        </div>
                        <span className="text-xs text-muted-foreground">
                          Segment {i + 1}
                        </span>
                      </div>
                      {/* Display labeled text if available, otherwise original text */}
                      <p 
                        className="text-sm leading-relaxed"
                        dangerouslySetInnerHTML={{ 
                          __html: highlightText(t.labeled_text || t.text) || 'Processing...' 
                        }}
                      />
                      {/* Emotion Indicators */}
                      {t.emotion_indicators?.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-border/30">
                          <div className="flex flex-wrap gap-1">
                            {t.emotion_indicators.map((ei, idx) => (
                              <Badge 
                                key={idx}
                                variant="outline"
                                className={`text-xs ${
                                  ei.severity === 'critical' ? 'bg-red-500/30 text-red-300 border-red-500/50 animate-pulse' :
                                  ei.severity === 'high' ? 'bg-orange-500/30 text-orange-300 border-orange-500/50' :
                                  ei.severity === 'medium' ? 'bg-yellow-500/30 text-yellow-300 border-yellow-500/50' :
                                  'bg-gray-500/30 text-gray-300 border-gray-500/50'
                                }`}
                              >
                                {ei.type}: "{ei.evidence?.slice(0, 30)}..."
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                      {/* Officer Demeanor Concerns */}
                      {t.officer_demeanor?.concerns?.length > 0 && (
                        <div className="mt-2 p-2 rounded bg-red-500/10 border border-red-500/20">
                          <p className="text-xs text-red-400 font-medium mb-1">⚠️ Officer Conduct Concerns:</p>
                          <ul className="text-xs text-red-300 space-y-0.5">
                            {t.officer_demeanor.concerns.map((c, idx) => (
                              <li key={idx}>• {c}</li>
                            ))}
                          </ul>
                          {t.officer_demeanor.aggression_level > 0.5 && (
                            <div className="mt-1 flex items-center gap-2">
                              <span className="text-xs text-red-400">Aggression:</span>
                              <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                                <div 
                                  className="h-full bg-red-500 transition-all"
                                  style={{width: `${t.officer_demeanor.aggression_level * 100}%`}}
                                />
                              </div>
                              <span className="text-xs text-red-400">{Math.round(t.officer_demeanor.aggression_level * 100)}%</span>
                            </div>
                          )}
                        </div>
                      )}
                      {/* Show speaker changes if multiple speakers detected */}
                      {t.speaker_changes?.length > 1 && (
                        <div className="mt-2 pt-2 border-t border-border/30">
                          <p className="text-xs text-muted-foreground mb-1">Multiple speakers detected:</p>
                          <div className="space-y-1">
                            {t.speaker_changes.map((change, idx) => (
                              <div key={idx} className="flex items-start gap-2 text-xs">
                                <Badge 
                                  variant="outline" 
                                  className={`text-xs shrink-0 ${
                                    change.speaker === 'Officer' 
                                      ? 'bg-blue-500/20 text-blue-400' 
                                      : 'bg-green-500/20 text-green-400'
                                  }`}
                                >
                                  {change.speaker}
                                  {change.tone && <span className="ml-1 opacity-70">({change.tone})</span>}
                                </Badge>
                                <span className="text-muted-foreground">{change.text}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {t.violations_detected?.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-red-500/20">
                          <p className="text-xs text-red-400">
                            <AlertCircle className="h-3 w-3 inline mr-1" />
                            {t.violations_detected.join(', ')}
                          </p>
                        </div>
                      )}
                    </div>
                  ))}
                  {/* Typing indicator for active transcription */}
                  {!isPaused && (
                    <div className="flex items-center gap-2 p-2 text-muted-foreground">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{animationDelay: '0ms'}} />
                        <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{animationDelay: '150ms'}} />
                        <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{animationDelay: '300ms'}} />
                      </div>
                      <span className="text-xs">Listening...</span>
                    </div>
                  )}
                </>
              )}
            </div>
            {/* Full Transcript Summary */}
            {fullTranscript && fullTranscript.length > 50 && (
              <div className="mt-3 pt-3 border-t">
                <details className="text-sm">
                  <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                    View full transcript ({fullTranscript.split(' ').length} words)
                  </summary>
                  <div className="mt-2 p-3 bg-muted/30 rounded-lg max-h-32 overflow-y-auto text-xs leading-relaxed">
                    {fullTranscript}
                  </div>
                </details>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Officer Info */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Officer Information</CardTitle>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setShowOfficerForm(!showOfficerForm)}
              >
                {showOfficerForm ? 'Cancel' : 'Add Officer'}
              </Button>
            </div>
          </CardHeader>
          {showOfficerForm && (
            <CardContent className="space-y-3">
              <Input
                placeholder="Officer Name"
                value={officerInfo.name}
                onChange={(e) => setOfficerInfo(prev => ({ ...prev, name: e.target.value }))}
              />
              <Input
                placeholder="Badge Number"
                value={officerInfo.badge}
                onChange={(e) => setOfficerInfo(prev => ({ ...prev, badge: e.target.value }))}
              />
              <Input
                placeholder="Department"
                value={officerInfo.department}
                onChange={(e) => setOfficerInfo(prev => ({ ...prev, department: e.target.value }))}
              />
              <Button onClick={addOfficerInfo} className="w-full">
                Save Officer Info
              </Button>
            </CardContent>
          )}
        </Card>

        {/* Control Buttons */}
        <div className="grid grid-cols-2 gap-4">
          <Button 
            variant="outline" 
            size="lg"
            onClick={pauseRecording}
            className="h-14"
          >
            {isPaused ? <Play className="h-5 w-5 mr-2" /> : <Pause className="h-5 w-5 mr-2" />}
            {isPaused ? 'Resume' : 'Pause'}
          </Button>
          <Button 
            variant="destructive" 
            size="lg"
            onClick={stopRecording}
            className="h-14"
            data-testid="stop-recording-btn"
          >
            <StopCircle className="h-5 w-5 mr-2" />
            End Recording
          </Button>
        </div>

        {/* Quick Actions */}
        <div className="space-y-3">
          {/* Quick SOS Button - Prominent */}
          {sosActive ? (
            <Button 
              variant="outline"
              size="lg"
              className="w-full h-16 border-2 border-green-500 bg-green-500/20 hover:bg-green-500/30 text-green-400"
              onClick={cancelSOS}
              data-testid="cancel-sos-btn"
            >
              <CheckCircle className="h-6 w-6 mr-2" />
              <div className="flex flex-col items-start">
                <span className="font-bold">SOS Active - Contacts Notified</span>
                <span className="text-xs opacity-70">Click to cancel SOS</span>
              </div>
            </Button>
          ) : (
            <Button 
              variant="destructive"
              size="lg"
              className="w-full h-16 bg-red-600 hover:bg-red-700 animate-pulse"
              onClick={triggerQuickSOS}
              disabled={sosSending || !encounter}
              data-testid="quick-sos-btn"
            >
              <Siren className="h-6 w-6 mr-2" />
              <div className="flex flex-col items-start">
                <span className="font-bold">{sosSending ? 'Sending SOS...' : 'QUICK SOS'}</span>
                <span className="text-xs opacity-70">Alert all emergency contacts</span>
              </div>
            </Button>
          )}

          {/* Other Quick Actions */}
          <div className="grid grid-cols-3 gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              className="flex-col h-auto py-3"
              onClick={() => navigate('/emergency-contacts')}
            >
              <Users className="h-5 w-5 mb-1" />
              <span className="text-xs">Contacts</span>
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              className="flex-col h-auto py-3"
              onClick={shareStreamLink}
              data-testid="share-live-btn"
            >
              <Share2 className="h-5 w-5 mb-1" />
              <span className="text-xs">Share Live</span>
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              className="flex-col h-auto py-3"
              onClick={() => navigate('/rights')}
            >
              <Eye className="h-5 w-5 mb-1" />
              <span className="text-xs">Know Rights</span>
            </Button>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
