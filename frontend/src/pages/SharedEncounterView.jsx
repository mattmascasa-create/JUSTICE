import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Alert, AlertDescription } from '../components/ui/alert';
import { ScrollArea } from '../components/ui/scroll-area';
import { Slider } from '../components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { 
  Shield, AlertTriangle, MapPin, Clock, Send, Users, Eye, 
  Radio, MessageCircle, AlertCircle, CheckCircle, XCircle,
  Volume2, Mic, User, ChevronDown, Video, Play, Pause,
  SkipBack, SkipForward, Maximize2, VideoOff, Zap, Scale,
  Target, Flag, Filter
} from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Severity colors
const severityColors = {
  critical: 'bg-red-500 text-white',
  high: 'bg-orange-500 text-white',
  medium: 'bg-yellow-500 text-black',
  low: 'bg-blue-500 text-white'
};

// Category icons
const categoryIcons = {
  violation: Scale,
  escalation: Zap,
  threat: AlertTriangle,
  rights_assertion: Shield,
  cooperation: CheckCircle,
  important_statement: MessageCircle,
  procedural_issue: Flag
};

// Category colors
const categoryColors = {
  violation: 'border-red-500/50 bg-red-500/10',
  escalation: 'border-orange-500/50 bg-orange-500/10',
  threat: 'border-red-500/50 bg-red-500/10',
  rights_assertion: 'border-green-500/50 bg-green-500/10',
  cooperation: 'border-blue-500/50 bg-blue-500/10',
  important_statement: 'border-purple-500/50 bg-purple-500/10',
  procedural_issue: 'border-yellow-500/50 bg-yellow-500/10'
};

// Tone colors for transcript display
const toneColors = {
  professional: 'border-green-500/30 bg-green-500/10',
  calm: 'border-green-500/30 bg-green-500/10',
  assertive: 'border-blue-500/30 bg-blue-500/10',
  anxious: 'border-yellow-500/30 bg-yellow-500/10',
  defensive: 'border-yellow-500/30 bg-yellow-500/10',
  compliant: 'border-green-500/30 bg-green-500/10',
  aggressive: 'border-red-500/30 bg-red-500/10',
  intimidating: 'border-orange-500/30 bg-orange-500/10',
  hostile: 'border-red-500/30 bg-red-500/10 animate-pulse',
  neutral: 'border-gray-500/30 bg-gray-500/10'
};

const speakerColors = {
  officer: 'text-blue-400',
  citizen: 'text-green-400',
  unknown: 'text-gray-400'
};

export default function SharedEncounterView() {
  const { encounterId } = useParams();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [encounter, setEncounter] = useState(null);
  const [transcriptions, setTranscriptions] = useState([]);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [senderName, setSenderName] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
  const [connected, setConnected] = useState(false);
  const [viewerCount, setViewerCount] = useState(1);
  
  // Video streaming state
  const [videoChunks, setVideoChunks] = useState([]);
  const [currentChunkIndex, setCurrentChunkIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLive, setIsLive] = useState(true);
  const [videoError, setVideoError] = useState(false);
  
  // Screen recording state
  const [screenChunks, setScreenChunks] = useState([]);
  const [currentScreenChunkIndex, setCurrentScreenChunkIndex] = useState(0);
  const [hasScreenRecording, setHasScreenRecording] = useState(false);
  const [showPiP, setShowPiP] = useState(true); // Picture-in-picture camera overlay
  
  // AI Evidence Highlights state
  const [highlights, setHighlights] = useState([]);
  const [highlightFilter, setHighlightFilter] = useState('all');
  const [showHighlights, setShowHighlights] = useState(true);
  
  const wsRef = useRef(null);
  const transcriptEndRef = useRef(null);
  const messagesEndRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const videoRef = useRef(null);
  const screenVideoRef = useRef(null);
  const mediaSourceRef = useRef(null);

  // Fetch initial encounter data
  const fetchEncounter = useCallback(async () => {
    if (!token) {
      setError('No share token provided');
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/encounters/shared/${encounterId}?token=${token}`);
      
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to load shared encounter');
      }
      
      const data = await response.json();
      setEncounter(data);
      setTranscriptions(data.transcriptions || []);
      setMessages(data.guidance_messages || []);
      setHasScreenRecording(data.has_screen_recording || false);
      setHighlights(data.evidence_highlights || []);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }, [encounterId, token]);

  // Connect to WebSocket for real-time updates
  const connectWebSocket = useCallback(() => {
    if (!token || wsRef.current?.readyState === WebSocket.OPEN) return;

    const wsUrl = `${API_URL.replace('https://', 'wss://').replace('http://', 'ws://')}/api/ws/shared/${encounterId}?token=${token}`;
    
    try {
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setConnected(true);
        toast.success('Connected to live feed');
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          switch (data.type) {
            case 'transcription':
              setTranscriptions(prev => [...prev, data]);
              break;
            case 'new_message':
              setMessages(prev => [...prev, data]);
              break;
            case 'share_revoked':
              setError('The encounter owner has ended the share session');
              wsRef.current?.close();
              break;
            case 'encounter_ended':
              setEncounter(prev => ({ ...prev, status: 'completed' }));
              toast.info('The encounter has ended');
              break;
            case 'viewer_count':
              setViewerCount(data.count);
              break;
            case 'video_chunk':
              // New video chunk available
              setVideoChunks(prev => {
                if (prev.some(c => c.index === data.chunk_index)) return prev;
                return [...prev, {
                  index: data.chunk_index,
                  filename: data.filename,
                  timestamp: data.timestamp
                }].sort((a, b) => a.index - b.index);
              });
              // Auto-play latest chunk if in live mode
              if (isLive) {
                setCurrentChunkIndex(data.chunk_index);
              }
              break;
            case 'screen_chunk':
              // New screen recording chunk available
              setHasScreenRecording(true);
              setScreenChunks(prev => {
                if (prev.some(c => c.index === data.chunk_index)) return prev;
                return [...prev, {
                  index: data.chunk_index,
                  filename: data.filename,
                  timestamp: data.timestamp
                }].sort((a, b) => a.index - b.index);
              });
              if (isLive) {
                setCurrentScreenChunkIndex(data.chunk_index);
              }
              break;
            case 'highlights_updated':
              // AI evidence highlights updated
              setHighlights(data.highlights || []);
              toast.info(`🎯 ${data.count} evidence highlights identified`);
              break;
            default:
              console.log('Unknown message type:', data.type);
          }
        } catch (e) {
          console.error('Error parsing WebSocket message:', e);
        }
      };
      
      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected');
        setConnected(false);
        // Attempt to reconnect after 5 seconds
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 5000);
      };
      
      wsRef.current.onerror = (err) => {
        console.error('WebSocket error:', err);
      };
    } catch (err) {
      console.error('Failed to connect WebSocket:', err);
    }
  }, [encounterId, token]);

  // Send guidance message
  const sendGuidanceMessage = async () => {
    if (!newMessage.trim() || sendingMessage) return;
    
    const name = senderName.trim() || 'Anonymous';
    
    setSendingMessage(true);
    try {
      // Try WebSocket first
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'guidance',
          sender_name: name,
          message: newMessage.trim()
        }));
        setNewMessage('');
      } else {
        // Fall back to HTTP
        const response = await fetch(
          `${API_URL}/api/encounters/shared/${encounterId}/message?token=${token}&message=${encodeURIComponent(newMessage.trim())}&sender_name=${encodeURIComponent(name)}`,
          { method: 'POST' }
        );
        
        if (response.ok) {
          setNewMessage('');
        } else {
          const data = await response.json();
          toast.error(data.detail || 'Failed to send message');
        }
      }
    } catch (err) {
      toast.error('Failed to send message');
    } finally {
      setSendingMessage(false);
    }
  };

  // Fetch video chunks
  const fetchVideoChunks = useCallback(async () => {
    if (!token) return;
    
    try {
      const response = await fetch(`${API_URL}/api/encounters/shared/${encounterId}/video/chunks?token=${token}`);
      if (response.ok) {
        const data = await response.json();
        setVideoChunks(data.chunks || []);
        if (data.chunks?.length > 0 && isLive) {
          setCurrentChunkIndex(data.chunks[data.chunks.length - 1].index);
        }
      }
    } catch (err) {
      console.log('Could not fetch video chunks:', err);
    }
  }, [encounterId, token, isLive]);

  // Fetch screen recording chunks
  const fetchScreenChunks = useCallback(async () => {
    if (!token || !hasScreenRecording) return;
    
    try {
      const response = await fetch(`${API_URL}/api/encounters/shared/${encounterId}/screen/chunks?token=${token}`);
      if (response.ok) {
        const data = await response.json();
        setScreenChunks(data.chunks || []);
        if (data.chunks?.length > 0 && isLive) {
          setCurrentScreenChunkIndex(data.chunks[data.chunks.length - 1].index);
        }
      }
    } catch (err) {
      console.log('Could not fetch screen chunks:', err);
    }
  }, [encounterId, token, isLive, hasScreenRecording]);

  // Get video URL for a chunk
  const getVideoChunkUrl = useCallback((filename) => {
    return `${API_URL}/api/encounters/shared/${encounterId}/video/${filename}?token=${token}`;
  }, [encounterId, token]);

  // Get screen recording URL for a chunk
  const getScreenChunkUrl = useCallback((filename) => {
    return `${API_URL}/api/encounters/shared/${encounterId}/screen/${filename}?token=${token}`;
  }, [encounterId, token]);

  // Handle chunk navigation
  const goToChunk = (index) => {
    if (index >= 0 && index < videoChunks.length) {
      setCurrentChunkIndex(index);
      setIsLive(index === videoChunks.length - 1);
      setIsPlaying(true);
      // Sync screen recording if available
      if (screenChunks.length > 0 && index < screenChunks.length) {
        setCurrentScreenChunkIndex(index);
      }
    }
  };

  const goLive = () => {
    if (videoChunks.length > 0) {
      setCurrentChunkIndex(videoChunks.length - 1);
      setIsLive(true);
      setIsPlaying(true);
    }
    if (screenChunks.length > 0) {
      setCurrentScreenChunkIndex(screenChunks.length - 1);
    }
  };

  // Auto-advance to next chunk when video ends
  const handleVideoEnded = () => {
    if (currentChunkIndex < videoChunks.length - 1) {
      setCurrentChunkIndex(prev => prev + 1);
      // Sync screen if available
      if (currentScreenChunkIndex < screenChunks.length - 1) {
        setCurrentScreenChunkIndex(prev => prev + 1);
      }
    } else {
      setIsLive(true);
      setIsPlaying(false);
    }
  };

  // Format time for timeline
  const formatChunkTime = (index) => {
    const seconds = index * 15; // Each chunk is ~15 seconds
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Jump to highlight timestamp
  const jumpToHighlight = (timestamp) => {
    // Parse timestamp (format: "00:45" or "01:23")
    const parts = timestamp.split(':');
    let totalSeconds = 0;
    if (parts.length === 2) {
      totalSeconds = parseInt(parts[0]) * 60 + parseInt(parts[1]);
    } else if (parts.length === 3) {
      totalSeconds = parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + parseInt(parts[2]);
    }
    
    // Calculate chunk index (15 seconds per chunk)
    const chunkIndex = Math.floor(totalSeconds / 15);
    
    if (chunkIndex < videoChunks.length) {
      goToChunk(chunkIndex);
      toast.info(`Jumped to ${timestamp}`);
    }
  };

  // Filter highlights
  const filteredHighlights = highlights.filter(h => 
    highlightFilter === 'all' || h.category === highlightFilter || h.severity === highlightFilter
  );

  // Scroll to bottom of transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcriptions]);

  // Scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Initial load and WebSocket connection
  useEffect(() => {
    fetchEncounter();
    fetchVideoChunks();
    fetchScreenChunks();
    connectWebSocket();
    
    // Polling fallback for updates
    const pollInterval = setInterval(async () => {
      if (!connected && token) {
        try {
          const response = await fetch(`${API_URL}/api/encounters/shared/${encounterId}/updates?token=${token}`);
          if (response.ok) {
            const data = await response.json();
            if (data.transcriptions?.length > 0) {
              setTranscriptions(prev => {
                const newItems = data.transcriptions.filter(
                  t => !prev.some(p => p.segment_id === t.segment_id)
                );
                return [...prev, ...newItems];
              });
            }
            if (data.messages?.length > 0) {
              setMessages(prev => {
                const newItems = data.messages.filter(
                  m => !prev.some(p => p.message_id === m.message_id)
                );
                return [...prev, ...newItems];
              });
            }
            if (data.status) {
              setEncounter(prev => prev ? { ...prev, status: data.status } : prev);
            }
          }
        } catch (e) {
          console.error('Polling error:', e);
        }
      }
    }, 5000);
    
    // Poll for video chunks
    const videoInterval = setInterval(fetchVideoChunks, 10000);
    
    // Poll for screen chunks
    const screenInterval = setInterval(fetchScreenChunks, 10000);
    
    return () => {
      clearInterval(pollInterval);
      clearInterval(videoInterval);
      clearInterval(screenInterval);
      clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [fetchEncounter, fetchVideoChunks, fetchScreenChunks, connectWebSocket, connected, encounterId, token]);

  // Format duration
  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Format timestamp
  const formatTime = (isoString) => {
    if (!isoString) return '';
    return new Date(isoString).toLocaleTimeString();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <Radio className="h-12 w-12 text-blue-400 animate-pulse mx-auto mb-4" />
          <p className="text-white text-lg">Loading shared encounter...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <Card className="max-w-md w-full bg-slate-800 border-red-500/30">
          <CardContent className="pt-6 text-center">
            <XCircle className="h-16 w-16 text-red-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Access Denied</h2>
            <p className="text-gray-400">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 p-4" data-testid="shared-encounter-view">
      {/* Header */}
      <div className="max-w-6xl mx-auto mb-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <Shield className="h-8 w-8 text-blue-400" />
            <div>
              <h1 className="text-xl font-bold text-white">Live Encounter</h1>
              <p className="text-sm text-gray-400">
                Shared by {encounter?.owner_name || 'Unknown'}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Connection Status */}
            <Badge 
              variant="outline" 
              className={connected ? 'border-green-500 text-green-400' : 'border-yellow-500 text-yellow-400'}
              data-testid="connection-status"
            >
              <div className={`w-2 h-2 rounded-full mr-2 ${connected ? 'bg-green-500' : 'bg-yellow-500 animate-pulse'}`} />
              {connected ? 'Live' : 'Reconnecting...'}
            </Badge>
            
            {/* Encounter Status */}
            <Badge 
              variant="outline"
              className={encounter?.status === 'active' ? 'border-red-500 text-red-400' : 'border-gray-500 text-gray-400'}
            >
              <Radio className={`h-3 w-3 mr-2 ${encounter?.status === 'active' ? 'animate-pulse' : ''}`} />
              {encounter?.status === 'active' ? 'Recording' : 'Ended'}
            </Badge>
            
            {/* Viewer Count */}
            <Badge variant="outline" className="border-blue-500/30 text-blue-400">
              <Eye className="h-3 w-3 mr-2" />
              {viewerCount} viewing
            </Badge>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content - Transcript */}
        <div className="lg:col-span-2 space-y-4">
          {/* Location & Info */}
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div className="flex items-center gap-2 text-gray-300">
                  <MapPin className="h-4 w-4 text-red-400" />
                  <span className="text-sm">{encounter?.location?.address || 'Location not available'}</span>
                </div>
                <div className="flex items-center gap-4 text-sm text-gray-400">
                  <div className="flex items-center gap-1">
                    <Clock className="h-4 w-4" />
                    <span>{formatDuration(encounter?.duration_seconds || 0)}</span>
                  </div>
                  <span>Started {formatTime(encounter?.started_at)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Video Player */}
          <Card className="bg-slate-800 border-slate-700 overflow-hidden">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center justify-between text-white">
                <div className="flex items-center gap-2">
                  <Video className="h-5 w-5 text-red-400" />
                  {hasScreenRecording && screenChunks.length > 0 ? 'Screen Recording' : 'Live Video Feed'}
                  {hasScreenRecording && screenChunks.length > 0 && (
                    <Badge variant="outline" className="text-xs border-purple-500/50 text-purple-400">
                      + Camera PiP
                    </Badge>
                  )}
                  {videoChunks.length > 0 && (
                    <Badge variant="outline" className="text-xs border-gray-600">
                      {videoChunks.length} chunks
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {hasScreenRecording && screenChunks.length > 0 && videoChunks.length > 0 && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setShowPiP(!showPiP)}
                      className="text-xs"
                      data-testid="toggle-pip-btn"
                    >
                      {showPiP ? 'Hide Camera' : 'Show Camera'}
                    </Button>
                  )}
                  {!isLive && videoChunks.length > 0 && (
                    <Button 
                      size="sm" 
                      variant="destructive"
                      onClick={goLive}
                      className="text-xs"
                      data-testid="go-live-btn"
                    >
                      <Radio className="h-3 w-3 mr-1 animate-pulse" />
                      Go Live
                    </Button>
                  )}
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {videoChunks.length === 0 && screenChunks.length === 0 ? (
                <div className="aspect-video bg-slate-900 flex flex-col items-center justify-center">
                  <VideoOff className="h-16 w-16 text-gray-600 mb-4" />
                  <p className="text-gray-500">Waiting for video...</p>
                  <p className="text-xs text-gray-600 mt-1">Video will appear when recording starts</p>
                </div>
              ) : (
                <>
                  {/* Video element - Show screen if available, else camera */}
                  <div className="relative aspect-video bg-black">
                    {/* Main video (screen recording if available, else camera) */}
                    {hasScreenRecording && screenChunks.length > 0 ? (
                      <video
                        ref={screenVideoRef}
                        className="w-full h-full object-contain"
                        src={screenChunks[currentScreenChunkIndex] ? getScreenChunkUrl(screenChunks[currentScreenChunkIndex].filename) : ''}
                        autoPlay={isPlaying}
                        onEnded={handleVideoEnded}
                        controls={false}
                        playsInline
                        data-testid="screen-player"
                      />
                    ) : (
                      <video
                        ref={videoRef}
                        className="w-full h-full object-contain"
                        src={videoChunks[currentChunkIndex] ? getVideoChunkUrl(videoChunks[currentChunkIndex].filename) : ''}
                        autoPlay={isPlaying}
                        onEnded={handleVideoEnded}
                        onError={() => setVideoError(true)}
                        onLoadStart={() => setVideoError(false)}
                        controls={false}
                        playsInline
                        data-testid="video-player"
                      />
                    )}
                    
                    {/* Picture-in-Picture Camera overlay (when screen recording is main) */}
                    {hasScreenRecording && screenChunks.length > 0 && showPiP && videoChunks.length > 0 && (
                      <div className="absolute bottom-3 right-3 w-1/4 aspect-video rounded-lg overflow-hidden border-2 border-white/30 shadow-lg">
                        <video
                          ref={videoRef}
                          className="w-full h-full object-cover"
                          src={videoChunks[currentChunkIndex] ? getVideoChunkUrl(videoChunks[currentChunkIndex].filename) : ''}
                          autoPlay={isPlaying}
                          controls={false}
                          playsInline
                          muted
                          data-testid="pip-video-player"
                        />
                        <div className="absolute bottom-1 left-1">
                          <Badge className="bg-blue-500/80 text-white text-xs px-1 py-0">
                            Camera
                          </Badge>
                        </div>
                      </div>
                    )}
                    
                    {/* Live indicator */}
                    {isLive && encounter?.status === 'active' && (
                      <div className="absolute top-3 left-3">
                        <Badge className="bg-red-500 text-white animate-pulse">
                          <Radio className="h-3 w-3 mr-1" />
                          LIVE
                        </Badge>
                      </div>
                    )}
                    
                    {/* Screen recording indicator */}
                    {hasScreenRecording && screenChunks.length > 0 && (
                      <div className="absolute top-3 left-20">
                        <Badge className="bg-purple-500/80 text-white">
                          <Video className="h-3 w-3 mr-1" />
                          Screen
                        </Badge>
                      </div>
                    )}
                    
                    {/* Chunk info */}
                    <div className="absolute top-3 right-3">
                      <Badge variant="secondary" className="bg-black/60 text-white">
                        {formatChunkTime(currentChunkIndex)} / {formatChunkTime(Math.max(videoChunks.length, screenChunks.length) - 1)}
                      </Badge>
                    </div>
                    
                    {/* Error overlay */}
                    {videoError && (
                      <div className="absolute inset-0 bg-black/80 flex items-center justify-center">
                        <div className="text-center">
                          <AlertCircle className="h-10 w-10 text-red-400 mx-auto mb-2" />
                          <p className="text-gray-400">Video unavailable</p>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {/* Video Controls */}
                  <div className="p-3 bg-slate-900 space-y-3">
                    {/* Timeline */}
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-gray-400 w-12">{formatChunkTime(currentChunkIndex)}</span>
                      <Slider
                        value={[currentChunkIndex]}
                        max={Math.max(videoChunks.length - 1, 0)}
                        step={1}
                        onValueChange={([val]) => goToChunk(val)}
                        className="flex-1"
                        data-testid="video-timeline"
                      />
                      <span className="text-xs text-gray-400 w-12 text-right">{formatChunkTime(videoChunks.length - 1)}</span>
                    </div>
                    
                    {/* Playback controls */}
                    <div className="flex items-center justify-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => goToChunk(currentChunkIndex - 1)}
                        disabled={currentChunkIndex === 0}
                        data-testid="prev-chunk-btn"
                      >
                        <SkipBack className="h-4 w-4" />
                      </Button>
                      
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          if (videoRef.current) {
                            if (isPlaying) {
                              videoRef.current.pause();
                            } else {
                              videoRef.current.play();
                            }
                            setIsPlaying(!isPlaying);
                          }
                        }}
                        data-testid="play-pause-btn"
                      >
                        {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                      </Button>
                      
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => goToChunk(currentChunkIndex + 1)}
                        disabled={currentChunkIndex >= videoChunks.length - 1}
                        data-testid="next-chunk-btn"
                      >
                        <SkipForward className="h-4 w-4" />
                      </Button>
                      
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          if (videoRef.current) {
                            videoRef.current.requestFullscreen?.();
                          }
                        }}
                        data-testid="fullscreen-btn"
                      >
                        <Maximize2 className="h-4 w-4" />
                      </Button>
                    </div>
                    
                    {/* Chunk thumbnails/timeline markers */}
                    {videoChunks.length > 1 && videoChunks.length <= 20 && (
                      <div className="flex gap-1 overflow-x-auto pb-2">
                        {videoChunks.map((chunk, idx) => (
                          <button
                            key={chunk.index}
                            onClick={() => goToChunk(idx)}
                            className={`flex-shrink-0 w-12 h-8 rounded text-xs flex items-center justify-center transition-all ${
                              idx === currentChunkIndex 
                                ? 'bg-blue-500 text-white' 
                                : 'bg-slate-700 text-gray-400 hover:bg-slate-600'
                            }`}
                            data-testid={`chunk-btn-${idx}`}
                          >
                            {formatChunkTime(idx)}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Live Transcript */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-white">
                <Mic className="h-5 w-5 text-blue-400" />
                Live Transcript
                {encounter?.status === 'active' && (
                  <span className="ml-2 flex items-center gap-1 text-sm font-normal text-green-400">
                    <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                    Listening...
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px] pr-4" data-testid="transcript-scroll">
                {transcriptions.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-gray-500">
                    <Volume2 className="h-12 w-12 mb-3 opacity-50" />
                    <p>Waiting for audio...</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {transcriptions.map((t, idx) => (
                      <div 
                        key={t.segment_id || idx}
                        className={`p-3 rounded-lg border ${toneColors[t.tone] || toneColors.neutral}`}
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <User className={`h-4 w-4 ${speakerColors[t.speaker] || speakerColors.unknown}`} />
                          <span className={`text-sm font-medium ${speakerColors[t.speaker] || speakerColors.unknown}`}>
                            {t.speaker === 'officer' ? '👮 Officer' : t.speaker === 'citizen' ? '🙋 Citizen' : 'Unknown'}
                          </span>
                          {t.tone && t.tone !== 'neutral' && (
                            <Badge variant="outline" className="text-xs">
                              {t.tone}
                            </Badge>
                          )}
                          {t.violations_detected?.length > 0 && (
                            <Badge variant="destructive" className="text-xs">
                              <AlertTriangle className="h-3 w-3 mr-1" />
                              Violation
                            </Badge>
                          )}
                        </div>
                        <p className="text-gray-200">{t.labeled_text || t.text}</p>
                      </div>
                    ))}
                    <div ref={transcriptEndRef} />
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Violations Alert */}
          {encounter?.violations?.length > 0 && (
            <Alert className="bg-red-500/10 border-red-500/30">
              <AlertTriangle className="h-4 w-4 text-red-400" />
              <AlertDescription className="text-red-300">
                <strong>{encounter.violations.length}</strong> potential violation(s) detected during this encounter
              </AlertDescription>
            </Alert>
          )}
        </div>

        {/* Sidebar - Guidance Messages */}
        <div className="space-y-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-white">
                <MessageCircle className="h-5 w-5 text-green-400" />
                Live Guidance
              </CardTitle>
            </CardHeader>
            <CardContent>
              {/* Messages List */}
              <ScrollArea className="h-[300px] pr-4 mb-4" data-testid="messages-scroll">
                {messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-gray-500">
                    <MessageCircle className="h-10 w-10 mb-2 opacity-50" />
                    <p className="text-sm">No messages yet</p>
                    <p className="text-xs text-gray-600">Send guidance to help the user</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {messages.map((m, idx) => (
                      <div 
                        key={m.message_id || idx}
                        className="p-3 rounded-lg bg-slate-700/50 border border-slate-600"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-blue-400">
                            {m.sender_name || 'Anonymous'}
                          </span>
                          <span className="text-xs text-gray-500">
                            {formatTime(m.timestamp || m.created_at)}
                          </span>
                        </div>
                        <p className="text-sm text-gray-200">{m.message}</p>
                      </div>
                    ))}
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </ScrollArea>

              {/* Send Message Form */}
              {encounter?.status === 'active' && (
                <div className="space-y-3">
                  <Input
                    placeholder="Your name (optional)"
                    value={senderName}
                    onChange={(e) => setSenderName(e.target.value)}
                    className="bg-slate-700 border-slate-600 text-white"
                    maxLength={50}
                    data-testid="sender-name-input"
                  />
                  <div className="flex gap-2">
                    <Input
                      placeholder="Send guidance message..."
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && sendGuidanceMessage()}
                      className="bg-slate-700 border-slate-600 text-white"
                      maxLength={200}
                      data-testid="message-input"
                    />
                    <Button 
                      onClick={sendGuidanceMessage}
                      disabled={!newMessage.trim() || sendingMessage}
                      className="bg-green-600 hover:bg-green-700"
                      data-testid="send-message-btn"
                    >
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                  <p className="text-xs text-gray-500 text-center">
                    Max 200 characters. Be concise and helpful.
                  </p>
                </div>
              )}

              {encounter?.status !== 'active' && (
                <Alert className="bg-slate-700">
                  <CheckCircle className="h-4 w-4 text-gray-400" />
                  <AlertDescription className="text-gray-400">
                    This encounter has ended. Messaging is disabled.
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* Quick Guidance Tips */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-gray-400">Quick Tips to Send</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {[
                "Stay calm, you're doing great",
                "Ask: Am I free to go?",
                "Don't consent to searches",
                "You can remain silent",
                "Ask for badge number"
              ].map((tip, idx) => (
                <Button
                  key={idx}
                  variant="outline"
                  size="sm"
                  className="w-full text-left justify-start text-xs border-slate-600 hover:bg-slate-700"
                  onClick={() => {
                    setNewMessage(tip);
                  }}
                  disabled={encounter?.status !== 'active'}
                  data-testid={`quick-tip-${idx}`}
                >
                  {tip}
                </Button>
              ))}
            </CardContent>
          </Card>

          {/* AI Evidence Highlights */}
          {highlights.length > 0 && (
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center justify-between text-white">
                  <div className="flex items-center gap-2">
                    <Target className="h-5 w-5 text-yellow-400" />
                    Evidence Highlights
                    <Badge variant="outline" className="text-xs border-yellow-500/50 text-yellow-400">
                      {filteredHighlights.length}
                    </Badge>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowHighlights(!showHighlights)}
                    className="text-xs"
                  >
                    {showHighlights ? 'Hide' : 'Show'}
                  </Button>
                </CardTitle>
              </CardHeader>
              {showHighlights && (
                <CardContent className="space-y-3">
                  {/* Filter */}
                  <Select value={highlightFilter} onValueChange={setHighlightFilter}>
                    <SelectTrigger className="w-full bg-slate-700 border-slate-600">
                      <Filter className="h-4 w-4 mr-2" />
                      <SelectValue placeholder="Filter highlights" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Highlights</SelectItem>
                      <SelectItem value="critical">Critical Only</SelectItem>
                      <SelectItem value="high">High Priority</SelectItem>
                      <SelectItem value="violation">Violations</SelectItem>
                      <SelectItem value="escalation">Escalations</SelectItem>
                      <SelectItem value="rights_assertion">Rights Assertions</SelectItem>
                    </SelectContent>
                  </Select>

                  {/* Highlights List */}
                  <ScrollArea className="h-[350px] pr-2" data-testid="highlights-scroll">
                    <div className="space-y-2">
                      {filteredHighlights.map((highlight, idx) => {
                        const CategoryIcon = categoryIcons[highlight.category] || Flag;
                        return (
                          <div
                            key={highlight.highlight_id || idx}
                            className={`p-3 rounded-lg border cursor-pointer transition-all hover:scale-[1.02] ${categoryColors[highlight.category] || 'border-gray-500/30 bg-gray-500/10'}`}
                            onClick={() => jumpToHighlight(highlight.timestamp)}
                            data-testid={`highlight-${idx}`}
                          >
                            <div className="flex items-start justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <CategoryIcon className="h-4 w-4" />
                                <Badge className={`text-xs ${severityColors[highlight.severity] || 'bg-gray-500'}`}>
                                  {highlight.severity?.toUpperCase()}
                                </Badge>
                              </div>
                              <Badge variant="outline" className="text-xs font-mono">
                                {highlight.timestamp}
                              </Badge>
                            </div>
                            <h4 className="font-medium text-sm text-white mb-1">
                              {highlight.title}
                            </h4>
                            {highlight.quote && (
                              <p className="text-xs text-gray-400 italic mb-2 line-clamp-2">
                                "{highlight.quote}"
                              </p>
                            )}
                            <p className="text-xs text-gray-300 mb-2">
                              {highlight.description}
                            </p>
                            {highlight.legal_relevance && (
                              <div className="flex items-start gap-1 text-xs text-yellow-400/80">
                                <Scale className="h-3 w-3 mt-0.5 flex-shrink-0" />
                                <span>{highlight.legal_relevance}</span>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </ScrollArea>
                </CardContent>
              )}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
