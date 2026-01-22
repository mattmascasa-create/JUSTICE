import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { ScrollArea } from '../components/ui/scroll-area';
import { callsAPI, API_URL } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import {
  Video, VideoOff, Mic, MicOff, PhoneOff,
  Monitor, MonitorOff, Maximize2, Minimize2,
  Phone, User, Clock, Circle, Square, Download,
  FileText, MessageSquare, Send, ChevronRight, ChevronLeft,
  Bookmark, AlertCircle, HelpCircle, CheckSquare
} from 'lucide-react';

// ICE servers for WebRTC (public STUN servers)
const ICE_SERVERS = {
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' },
    { urls: 'stun:stun2.l.google.com:19302' },
  ]
};

export default function VideoCallPage() {
  const { callId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, token } = useAuth();
  
  // Call state
  const [callInfo, setCallInfo] = useState(null);
  const [callStatus, setCallStatus] = useState('connecting'); // connecting, ringing, active, ended
  const [duration, setDuration] = useState(0);
  
  // Media state
  const [localStream, setLocalStream] = useState(null);
  const [remoteStream, setRemoteStream] = useState(null);
  const [isVideoEnabled, setIsVideoEnabled] = useState(true);
  const [isAudioEnabled, setIsAudioEnabled] = useState(true);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  // Recording state
  const [isRecording, setIsRecording] = useState(false);
  const [recordingId, setRecordingId] = useState(null);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  
  // Live transcription state
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState([]);
  const [liveNotes, setLiveNotes] = useState([]);
  const [showTranscriptPanel, setShowTranscriptPanel] = useState(false);
  const [noteInput, setNoteInput] = useState('');
  const [selectedNoteType, setSelectedNoteType] = useState('general');
  
  // Refs
  const localVideoRef = useRef(null);
  const remoteVideoRef = useRef(null);
  const peerConnectionRef = useRef(null);
  const wsRef = useRef(null);
  const screenStreamRef = useRef(null);
  const durationIntervalRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const recordedChunksRef = useRef([]);
  const recordingIntervalRef = useRef(null);
  const transcriptRecorderRef = useRef(null);
  const transcriptChunkIndexRef = useRef(0);
  const transcriptEndRef = useRef(null);
  
  const isIncoming = searchParams.get('incoming') === 'true';

  // Initialize WebRTC and WebSocket
  useEffect(() => {
    if (!callId || !token) return;
    
    initializeCall();
    
    return () => {
      cleanup();
    };
  }, [callId, token]);

  // Duration timer
  useEffect(() => {
    if (callStatus === 'active') {
      durationIntervalRef.current = setInterval(() => {
        setDuration(prev => prev + 1);
      }, 1000);
    }
    return () => {
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
      }
    };
  }, [callStatus]);

  const initializeCall = async () => {
    try {
      // Get local media stream
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true
      });
      setLocalStream(stream);
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
      }

      // Initialize WebSocket for signaling
      const wsUrl = API_URL.replace('http', 'ws').replace('/api', '');
      const ws = new WebSocket(`${wsUrl}/api/calls/signal/${callId}?token=${token}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('Signaling connected');
        if (!isIncoming) {
          // Caller: create offer after connection
          setCallStatus('ringing');
          createPeerConnection(stream);
        } else {
          // Callee: wait for offer
          setCallStatus('ringing');
          createPeerConnection(stream);
        }
      };

      ws.onmessage = async (event) => {
        const message = JSON.parse(event.data);
        await handleSignalingMessage(message);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        toast.error('Connection error');
      };

      ws.onclose = () => {
        console.log('Signaling disconnected');
      };

    } catch (error) {
      console.error('Failed to initialize call:', error);
      toast.error('Failed to access camera/microphone');
      navigate(-1);
    }
  };

  const createPeerConnection = (stream) => {
    const pc = new RTCPeerConnection(ICE_SERVERS);
    peerConnectionRef.current = pc;

    // Add local tracks
    stream.getTracks().forEach(track => {
      pc.addTrack(track, stream);
    });

    // Handle incoming tracks
    pc.ontrack = (event) => {
      console.log('Received remote track');
      setRemoteStream(event.streams[0]);
      if (remoteVideoRef.current) {
        remoteVideoRef.current.srcObject = event.streams[0];
      }
    };

    // Handle ICE candidates
    pc.onicecandidate = (event) => {
      if (event.candidate && wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'ice-candidate',
          data: event.candidate
        }));
      }
    };

    pc.onconnectionstatechange = () => {
      console.log('Connection state:', pc.connectionState);
      if (pc.connectionState === 'connected') {
        setCallStatus('active');
      } else if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
        toast.error('Connection lost');
        endCall();
      }
    };

    // If caller, create and send offer
    if (!isIncoming) {
      createAndSendOffer(pc);
    }
  };

  const createAndSendOffer = async (pc) => {
    try {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'offer',
          data: offer
        }));
      }
    } catch (error) {
      console.error('Failed to create offer:', error);
    }
  };

  const handleSignalingMessage = async (message) => {
    const pc = peerConnectionRef.current;
    if (!pc) return;

    switch (message.type) {
      case 'offer':
        console.log('Received offer');
        await pc.setRemoteDescription(new RTCSessionDescription(message.data));
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        wsRef.current?.send(JSON.stringify({
          type: 'answer',
          data: answer
        }));
        break;

      case 'answer':
        console.log('Received answer');
        await pc.setRemoteDescription(new RTCSessionDescription(message.data));
        break;

      case 'ice-candidate':
        console.log('Received ICE candidate');
        if (message.data) {
          await pc.addIceCandidate(new RTCIceCandidate(message.data));
        }
        break;

      case 'call-ended':
        toast.info('Call ended by other party');
        cleanup();
        navigate(-1);
        break;

      case 'screen-share-start':
        toast.info('Remote user started screen sharing');
        break;

      case 'screen-share-stop':
        toast.info('Remote user stopped screen sharing');
        break;

      case 'recording-started':
        toast.info('Recording started by other party');
        setIsRecording(true);
        break;

      case 'recording-stopped':
        toast.info('Recording stopped');
        setIsRecording(false);
        break;

      case 'live-transcript':
        // Received live transcript segment from other party
        if (message.segment) {
          setLiveTranscript(prev => [...prev, message.segment]);
        }
        break;

      case 'live-note':
        // Received live note from other party
        if (message.note) {
          setLiveNotes(prev => [...prev, message.note]);
          toast.info(`Note added by ${message.note.user_name}`);
        }
        break;

      case 'transcription-started':
        toast.info('Live transcription started');
        setIsTranscribing(true);
        break;

      case 'transcription-stopped':
        toast.info('Live transcription stopped');
        setIsTranscribing(false);
        break;
    }
  };

  const toggleVideo = () => {
    if (localStream) {
      const videoTrack = localStream.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.enabled = !videoTrack.enabled;
        setIsVideoEnabled(videoTrack.enabled);
      }
    }
  };

  const toggleAudio = () => {
    if (localStream) {
      const audioTrack = localStream.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setIsAudioEnabled(audioTrack.enabled);
      }
    }
  };

  const toggleScreenShare = async () => {
    if (isScreenSharing) {
      // Stop screen sharing
      if (screenStreamRef.current) {
        screenStreamRef.current.getTracks().forEach(track => track.stop());
      }
      
      // Replace with camera
      const videoTrack = localStream?.getVideoTracks()[0];
      if (videoTrack && peerConnectionRef.current) {
        const sender = peerConnectionRef.current.getSenders().find(s => s.track?.kind === 'video');
        if (sender) {
          sender.replaceTrack(videoTrack);
        }
      }
      
      setIsScreenSharing(false);
      wsRef.current?.send(JSON.stringify({ type: 'screen-share-stop' }));
    } else {
      try {
        const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
        screenStreamRef.current = screenStream;
        
        const screenTrack = screenStream.getVideoTracks()[0];
        if (peerConnectionRef.current) {
          const sender = peerConnectionRef.current.getSenders().find(s => s.track?.kind === 'video');
          if (sender) {
            sender.replaceTrack(screenTrack);
          }
        }
        
        // Handle when user stops sharing via browser UI
        screenTrack.onended = () => {
          toggleScreenShare();
        };
        
        setIsScreenSharing(true);
        wsRef.current?.send(JSON.stringify({ type: 'screen-share-start' }));
      } catch (error) {
        console.error('Screen share failed:', error);
        toast.error('Failed to share screen');
      }
    }
  };

  // Recording functions
  const startRecording = async () => {
    try {
      // Notify server
      const res = await callsAPI.startRecording(callId);
      setRecordingId(res.data.recording_id);
      
      // Create combined stream (local + remote audio, remote video)
      const combinedStream = new MediaStream();
      
      // Add remote video and audio
      if (remoteStream) {
        remoteStream.getTracks().forEach(track => combinedStream.addTrack(track));
      }
      
      // Add local audio (for full conversation)
      if (localStream) {
        const localAudio = localStream.getAudioTracks()[0];
        if (localAudio) {
          combinedStream.addTrack(localAudio);
        }
      }
      
      // Create MediaRecorder
      const options = { mimeType: 'video/webm;codecs=vp9,opus' };
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options.mimeType = 'video/webm';
      }
      
      const mediaRecorder = new MediaRecorder(combinedStream, options);
      mediaRecorderRef.current = mediaRecorder;
      recordedChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.start(1000); // Collect data every second
      setIsRecording(true);
      setRecordingDuration(0);
      
      // Start recording duration timer
      recordingIntervalRef.current = setInterval(() => {
        setRecordingDuration(prev => prev + 1);
      }, 1000);
      
      toast.success('Recording started');
    } catch (error) {
      console.error('Failed to start recording:', error);
      toast.error(error.response?.data?.detail || 'Failed to start recording');
    }
  };

  const stopRecording = async () => {
    try {
      // Stop MediaRecorder
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      
      // Stop timer
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current);
      }
      
      // Notify server
      await callsAPI.stopRecording(callId);
      
      setIsRecording(false);
      toast.success('Recording stopped');
      
      // Upload the recording
      if (recordedChunksRef.current.length > 0 && recordingId) {
        await uploadRecording();
      }
    } catch (error) {
      console.error('Failed to stop recording:', error);
      toast.error('Failed to stop recording');
      setIsRecording(false);
    }
  };

  const uploadRecording = async () => {
    if (recordedChunksRef.current.length === 0 || !recordingId) return;
    
    setIsUploading(true);
    toast.info('Uploading recording...');
    
    try {
      const blob = new Blob(recordedChunksRef.current, { type: 'video/webm' });
      const res = await callsAPI.uploadRecording(callId, recordingId, blob);
      
      toast.success('Recording saved to cloud!');
      
      // Clear chunks
      recordedChunksRef.current = [];
      setRecordingId(null);
    } catch (error) {
      console.error('Failed to upload recording:', error);
      toast.error('Failed to upload recording');
      
      // Offer to download locally
      const blob = new Blob(recordedChunksRef.current, { type: 'video/webm' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `call_recording_${callId}.webm`;
      a.click();
      URL.revokeObjectURL(url);
      
      toast.info('Recording downloaded locally instead');
    } finally {
      setIsUploading(false);
    }
  };

  // Live Transcription Functions
  const startLiveTranscription = async () => {
    if (!localStream) {
      toast.error('No audio stream available');
      return;
    }

    try {
      // Create audio-only stream for transcription
      const audioStream = new MediaStream();
      const localAudio = localStream.getAudioTracks()[0];
      if (localAudio) {
        audioStream.addTrack(localAudio);
      }

      // Create MediaRecorder for audio chunks
      const options = { mimeType: 'audio/webm;codecs=opus' };
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options.mimeType = 'audio/webm';
      }

      const recorder = new MediaRecorder(audioStream, options);
      transcriptRecorderRef.current = recorder;
      transcriptChunkIndexRef.current = 0;

      recorder.ondataavailable = async (event) => {
        if (event.data.size > 0 && isTranscribing) {
          try {
            const res = await callsAPI.sendAudioChunk(
              callId, 
              event.data, 
              transcriptChunkIndexRef.current
            );
            
            if (res.data.success && res.data.segment) {
              setLiveTranscript(prev => [...prev, res.data.segment]);
            }
            
            transcriptChunkIndexRef.current++;
          } catch (error) {
            console.error('Transcription chunk error:', error);
          }
        }
      };

      // Record in 5-second chunks
      recorder.start(5000);
      setIsTranscribing(true);
      setShowTranscriptPanel(true);
      
      // Notify other party
      wsRef.current?.send(JSON.stringify({ type: 'transcription-started' }));
      
      toast.success('Live transcription started');
    } catch (error) {
      console.error('Failed to start live transcription:', error);
      toast.error('Failed to start transcription');
    }
  };

  const stopLiveTranscription = async () => {
    if (transcriptRecorderRef.current && transcriptRecorderRef.current.state !== 'inactive') {
      transcriptRecorderRef.current.stop();
    }
    
    setIsTranscribing(false);
    
    // Notify other party
    wsRef.current?.send(JSON.stringify({ type: 'transcription-stopped' }));
    
    // Save transcript
    if (liveTranscript.length > 0 || liveNotes.length > 0) {
      try {
        await callsAPI.saveLiveTranscript(callId);
        toast.success('Live transcript saved');
      } catch (error) {
        console.error('Failed to save transcript:', error);
      }
    }
  };

  const addNote = async () => {
    if (!noteInput.trim()) return;

    try {
      const res = await callsAPI.addLiveNote(
        callId,
        noteInput,
        duration,
        selectedNoteType
      );

      if (res.data.success) {
        setLiveNotes(prev => [...prev, res.data.note]);
        setNoteInput('');
        toast.success('Note added');
      }
    } catch (error) {
      console.error('Failed to add note:', error);
      toast.error('Failed to add note');
    }
  };

  const formatTimestamp = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getNoteTypeIcon = (type) => {
    switch (type) {
      case 'important': return <AlertCircle className="h-3 w-3 text-red-400" />;
      case 'action_item': return <CheckSquare className="h-3 w-3 text-green-400" />;
      case 'question': return <HelpCircle className="h-3 w-3 text-yellow-400" />;
      default: return <Bookmark className="h-3 w-3 text-blue-400" />;
    }
  };

  const endCall = async () => {
    // Stop transcription if active
    if (isTranscribing) {
      await stopLiveTranscription();
    }
    
    // Stop recording if active
    if (isRecording) {
      await stopRecording();
    }
    
    try {
      await callsAPI.endCall(callId);
    } catch (error) {
      console.error('Failed to end call:', error);
    }
    
    wsRef.current?.send(JSON.stringify({ type: 'call-ended' }));
    cleanup();
    navigate(-1);
  };

  const cleanup = () => {
    // Stop all tracks
    localStream?.getTracks().forEach(track => track.stop());
    remoteStream?.getTracks().forEach(track => track.stop());
    screenStreamRef.current?.getTracks().forEach(track => track.stop());
    
    // Stop recording if active
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    
    // Close peer connection
    peerConnectionRef.current?.close();
    
    // Close WebSocket
    wsRef.current?.close();
    
    // Clear intervals
    if (durationIntervalRef.current) {
      clearInterval(durationIntervalRef.current);
    }
    if (recordingIntervalRef.current) {
      clearInterval(recordingIntervalRef.current);
    }
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black flex flex-col" data-testid="video-call-page">
      {/* Remote Video (Full Screen) */}
      <div className="flex-1 relative">
        <video
          ref={remoteVideoRef}
          autoPlay
          playsInline
          className="w-full h-full object-cover"
          data-testid="remote-video"
        />
        
        {/* Status Overlay */}
        {callStatus !== 'active' && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/70">
            <div className="text-center text-white">
              <div className="h-24 w-24 rounded-full bg-gray-700 flex items-center justify-center mx-auto mb-4">
                <User className="h-12 w-12" />
              </div>
              <h2 className="text-2xl font-semibold mb-2">
                {callStatus === 'connecting' && 'Connecting...'}
                {callStatus === 'ringing' && (isIncoming ? 'Incoming Call' : 'Calling...')}
              </h2>
              {callStatus === 'ringing' && (
                <div className="flex items-center justify-center gap-2 text-gray-400">
                  <Phone className="h-4 w-4 animate-pulse" />
                  <span>Waiting for answer...</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Local Video (Picture-in-Picture) */}
        <div className="absolute top-4 right-4 w-48 h-36 rounded-lg overflow-hidden shadow-lg border-2 border-white/20">
          <video
            ref={localVideoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
            data-testid="local-video"
          />
          {!isVideoEnabled && (
            <div className="absolute inset-0 bg-gray-800 flex items-center justify-center">
              <VideoOff className="h-8 w-8 text-gray-400" />
            </div>
          )}
        </div>

        {/* Call Info Overlay */}
        <div className="absolute top-4 left-4 flex items-center gap-3">
          {callStatus === 'active' && (
            <Badge variant="secondary" className="bg-green-500/20 text-green-400 border-green-500/30">
              <Clock className="h-3 w-3 mr-1" />
              {formatDuration(duration)}
            </Badge>
          )}
          {isRecording && (
            <Badge variant="secondary" className="bg-red-500/20 text-red-400 border-red-500/30 animate-pulse">
              <Circle className="h-3 w-3 mr-1 fill-red-500" />
              REC {formatDuration(recordingDuration)}
            </Badge>
          )}
          {isUploading && (
            <Badge variant="secondary" className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30">
              <Download className="h-3 w-3 mr-1 animate-bounce" />
              Uploading...
            </Badge>
          )}
          {isScreenSharing && (
            <Badge variant="secondary" className="bg-blue-500/20 text-blue-400 border-blue-500/30">
              <Monitor className="h-3 w-3 mr-1" />
              Screen Sharing
            </Badge>
          )}
        </div>
      </div>

      {/* Controls */}
      <div className="bg-gray-900/90 p-6">
        <div className="flex items-center justify-center gap-4">
          <Button
            variant="outline"
            size="lg"
            className={`rounded-full h-14 w-14 ${!isAudioEnabled ? 'bg-red-500/20 border-red-500 text-red-400' : 'border-white/20 text-white'}`}
            onClick={toggleAudio}
            data-testid="toggle-audio-btn"
          >
            {isAudioEnabled ? <Mic className="h-6 w-6" /> : <MicOff className="h-6 w-6" />}
          </Button>

          <Button
            variant="outline"
            size="lg"
            className={`rounded-full h-14 w-14 ${!isVideoEnabled ? 'bg-red-500/20 border-red-500 text-red-400' : 'border-white/20 text-white'}`}
            onClick={toggleVideo}
            data-testid="toggle-video-btn"
          >
            {isVideoEnabled ? <Video className="h-6 w-6" /> : <VideoOff className="h-6 w-6" />}
          </Button>

          <Button
            variant="outline"
            size="lg"
            className={`rounded-full h-14 w-14 ${isScreenSharing ? 'bg-blue-500/20 border-blue-500 text-blue-400' : 'border-white/20 text-white'}`}
            onClick={toggleScreenShare}
            data-testid="toggle-screen-btn"
          >
            {isScreenSharing ? <MonitorOff className="h-6 w-6" /> : <Monitor className="h-6 w-6" />}
          </Button>

          {/* Recording Button */}
          <Button
            variant="outline"
            size="lg"
            className={`rounded-full h-14 w-14 ${isRecording ? 'bg-red-500 border-red-500 text-white animate-pulse' : 'border-white/20 text-white'}`}
            onClick={isRecording ? stopRecording : startRecording}
            disabled={callStatus !== 'active' || isUploading}
            data-testid="toggle-recording-btn"
            title={isRecording ? 'Stop Recording' : 'Start Recording'}
          >
            {isRecording ? <Square className="h-6 w-6" /> : <Circle className="h-6 w-6" />}
          </Button>

          <Button
            variant="destructive"
            size="lg"
            className="rounded-full h-16 w-16"
            onClick={endCall}
            data-testid="end-call-btn"
          >
            <PhoneOff className="h-7 w-7" />
          </Button>

          <Button
            variant="outline"
            size="lg"
            className="rounded-full h-14 w-14 border-white/20 text-white"
            onClick={toggleFullscreen}
            data-testid="fullscreen-btn"
          >
            {isFullscreen ? <Minimize2 className="h-6 w-6" /> : <Maximize2 className="h-6 w-6" />}
          </Button>
        </div>
      </div>
    </div>
  );
}
