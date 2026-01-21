import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Alert, AlertDescription } from '../components/ui/alert';
import { encounterAPI } from '../lib/api';
import { 
  Shield, AlertTriangle, Mic, MicOff, Video, VideoOff, 
  MapPin, Clock, FileText, Send, Users, Radio, 
  StopCircle, Play, Pause, ChevronRight, Phone, Share2,
  Eye, AlertCircle, Scale, CheckCircle
} from 'lucide-react';
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
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);
  const chunkIndexRef = useRef(0);
  const timerRef = useRef(null);

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
        broadcast_mode: broadcastMode
      });

      setEncounter(response.data);
      
      // Request media permissions
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: true,
        video: false // For now, audio only - video in future phase
      });
      streamRef.current = stream;

      // Create media recorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
          
          // Upload chunk for transcription every 10 seconds worth of audio
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

      // Record in 10-second chunks
      mediaRecorder.start(10000);
      setIsRecording(true);
      setDuration(0);
      
      toast.success('🚨 Recording started. Stay calm and know your rights.');
      
    } catch (error) {
      console.error('Recording error:', error);
      toast.error('Failed to start recording: ' + (error.response?.data?.detail || error.message));
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      if (isPaused) {
        mediaRecorderRef.current.resume();
        setIsPaused(false);
        toast.info('Recording resumed');
      } else {
        mediaRecorderRef.current.pause();
        setIsPaused(true);
        toast.info('Recording paused');
      }
    }
  };

  const stopRecording = async () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      streamRef.current?.getTracks().forEach(track => track.stop());
      
      try {
        const response = await encounterAPI.end(encounter.encounter_id);
        toast.success('Recording ended. Report is being generated.');
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
            <h1 className="font-serif text-4xl font-bold">I'm Being Pulled Over</h1>
            <p className="text-muted-foreground text-lg">
              This will record audio, pin your location, and protect your rights.
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
            By starting, your location and audio will be recorded and stored securely.
          </p>
        </div>
      </AppLayout>
    );
  }

  // Recording in progress
  return (
    <AppLayout>
      <div className="max-w-2xl mx-auto space-y-4" data-testid="encounter-recording">
        {/* Recording Status Bar */}
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

        {/* Rights Reminder */}
        <Alert className="border-blue-500/50 bg-blue-500/10">
          <Shield className="h-5 w-5 text-blue-500" />
          <AlertDescription className="text-lg font-medium">
            {rightsReminders[currentRightsIndex]}
          </AlertDescription>
        </Alert>

        {/* Violations Alert */}
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
          <Button variant="outline" size="sm" className="flex-col h-auto py-3">
            <Share2 className="h-5 w-5 mb-1" />
            <span className="text-xs">Share Location</span>
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
