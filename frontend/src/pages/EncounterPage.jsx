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
import { encounterAPI } from '../lib/api';
import { 
  Shield, AlertTriangle, Mic, MicOff, Video, VideoOff, 
  MapPin, Clock, FileText, Send, Users, Radio, 
  StopCircle, Play, Pause, ChevronRight, Phone, Share2,
  Eye, AlertCircle, Scale, CheckCircle, Camera, Volume2, VolumeX
} from 'lucide-react';
import { sosAPI } from '../lib/api';
import { toast } from 'sonner';

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

export default function EncounterPage() {
  const navigate = useNavigate();
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
  
  const mediaRecorderRef = useRef(null);
  const audioRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const videoChunksRef = useRef([]);
  const streamRef = useRef(null);
  const audioStreamRef = useRef(null);
  const videoPreviewRef = useRef(null);
  const chunkIndexRef = useRef(0);
  const videoChunkIndexRef = useRef(0);
  const timerRef = useRef(null);
  const analysisQueueRef = useRef([]);
  const lastAnalysisRef = useRef(0);

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
      // Stop all recorders
      mediaRecorderRef.current.stop();
      if (audioRecorderRef.current) audioRecorderRef.current.stop();
      
      // Stop all tracks
      streamRef.current?.getTracks().forEach(track => track.stop());
      
      // Clear video preview
      if (videoPreviewRef.current) {
        videoPreviewRef.current.srcObject = null;
      }
      
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
      const response = await encounterAPI.getStreamToken(encounter.encounter_id);
      const fullUrl = `${window.location.origin}${response.data.share_url}`;
      
      // Try to share via native share API if available
      if (navigator.share) {
        await navigator.share({
          title: 'JUSTICE - Live Encounter Recording',
          text: 'I\'m being pulled over. Watch my live recording.',
          url: fullUrl
        });
        toast.success('Shared successfully!');
      } else {
        // Fallback to clipboard
        await navigator.clipboard.writeText(fullUrl);
        toast.success('Link copied to clipboard! Share with your contacts.');
      }
    } catch (error) {
      console.error('Share error:', error);
      toast.error('Failed to generate share link');
    }
  };

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
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Live Transcription
            </CardTitle>
          </CardHeader>
          <CardContent className="max-h-48 overflow-y-auto">
            {transcriptions.length === 0 ? (
              <p className="text-muted-foreground text-center py-4">
                Transcription will appear here...
              </p>
            ) : (
              <div className="space-y-2">
                {transcriptions.map((t, i) => (
                  <div key={i} className="p-2 rounded bg-muted/50 text-sm">
                    {t.text}
                  </div>
                ))}
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
        <div className="grid grid-cols-3 gap-2">
          <Button variant="outline" size="sm" className="flex-col h-auto py-3">
            <Phone className="h-5 w-5 mb-1" />
            <span className="text-xs">Call Lawyer</span>
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
          <Button variant="outline" size="sm" className="flex-col h-auto py-3">
            <Eye className="h-5 w-5 mb-1" />
            <span className="text-xs">Know Rights</span>
          </Button>
        </div>
      </div>
    </AppLayout>
  );
}
