import React, { useState, useEffect, useRef } from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import { callsAPI } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import {
  Video, Download, Play, Pause, Search,
  Clock, Calendar, User, Users, FileVideo,
  Filter, SortAsc, SortDesc, X, Volume2,
  VolumeX, Maximize2, SkipBack, SkipForward,
  FileText, Loader2, Copy, CheckCircle,
  Sparkles, ListChecks, AlertTriangle, Lightbulb
} from 'lucide-react';

export default function RecordingsPage() {
  const { user } = useAuth();
  const [recordings, setRecordings] = useState([]);
  const [filteredRecordings, setFilteredRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortOrder, setSortOrder] = useState('newest');
  const [filterStatus, setFilterStatus] = useState('all');
  
  // Transcript search
  const [transcriptSearchQuery, setTranscriptSearchQuery] = useState('');
  const [transcriptSearchResults, setTranscriptSearchResults] = useState([]);
  const [searchingTranscripts, setSearchingTranscripts] = useState(false);
  
  // Video player state
  const [selectedRecording, setSelectedRecording] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [activeTab, setActiveTab] = useState('video');
  
  // Transcript state
  const [transcript, setTranscript] = useState(null);
  const [transcribing, setTranscribing] = useState({});
  
  // AI Summary state
  const [summary, setSummary] = useState(null);
  const [summarizing, setSummarizing] = useState(false);
  
  const videoRef = useRef(null);

  useEffect(() => {
    fetchRecordings();
  }, []);

  useEffect(() => {
    filterAndSortRecordings();
  }, [recordings, searchQuery, sortOrder, filterStatus]);

  // Fetch transcript when recording is selected
  useEffect(() => {
    if (selectedRecording) {
      fetchTranscript(selectedRecording.recording_id);
      fetchSummary(selectedRecording.recording_id);
    } else {
      setTranscript(null);
      setSummary(null);
    }
  }, [selectedRecording]);

  const fetchRecordings = async () => {
    try {
      const res = await callsAPI.getMyRecordings(100);
      setRecordings(res.data.recordings || []);
    } catch (error) {
      console.error('Error fetching recordings:', error);
      toast.error('Failed to load recordings');
    } finally {
      setLoading(false);
    }
  };

  const filterAndSortRecordings = () => {
    let filtered = [...recordings];

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(rec =>
        rec.caller_name?.toLowerCase().includes(query) ||
        rec.recipient_name?.toLowerCase().includes(query) ||
        rec.recording_id?.toLowerCase().includes(query) ||
        rec.call_id?.toLowerCase().includes(query)
      );
    }

    // Filter by status
    if (filterStatus !== 'all') {
      filtered = filtered.filter(rec => rec.status === filterStatus);
    }

    // Sort
    filtered.sort((a, b) => {
      const dateA = new Date(a.started_at);
      const dateB = new Date(b.started_at);
      return sortOrder === 'newest' ? dateB - dateA : dateA - dateB;
    });

    setFilteredRecordings(filtered);
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'Unknown size';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const handleDownload = async (recording) => {
    if (recording.download_url || recording.s3_url) {
      window.open(recording.download_url || recording.s3_url, '_blank');
      toast.success('Download started');
    } else if (recording.local_path) {
      toast.info('Recording stored locally on server');
    } else {
      toast.error('Recording not available for download');
    }
  };

  const openPlayer = (recording) => {
    if (!recording.download_url && !recording.s3_url) {
      toast.error('Recording not available for playback');
      return;
    }
    setSelectedRecording(recording);
    setIsPlaying(false);
    setCurrentTime(0);
    setActiveTab('video');
  };

  const closePlayer = () => {
    setSelectedRecording(null);
    setIsPlaying(false);
    setTranscript(null);
    setSummary(null);
    if (videoRef.current) {
      videoRef.current.pause();
    }
  };

  const fetchSummary = async (recordingId) => {
    try {
      const res = await callsAPI.getSummary(recordingId);
      if (res.data.has_summary) {
        setSummary(res.data);
      } else {
        setSummary({ has_summary: false });
      }
    } catch (error) {
      console.error('Error fetching summary:', error);
      setSummary({ has_summary: false });
    }
  };

  const handleGenerateSummary = async () => {
    if (!selectedRecording) return;
    
    setSummarizing(true);
    try {
      toast.info('Generating AI summary... This may take a minute.');
      const res = await callsAPI.generateSummary(selectedRecording.recording_id);
      
      if (res.data.status === 'completed' || res.data.status === 'already_summarized') {
        toast.success('Summary generated!');
        setSummary({
          has_summary: true,
          summary: res.data.summary,
          summarized_at: res.data.summarized_at
        });
      }
    } catch (error) {
      console.error('Summary generation error:', error);
      toast.error(error.response?.data?.detail || 'Failed to generate summary');
    } finally {
      setSummarizing(false);
    }
  };

  const fetchTranscript = async (recordingId) => {
    try {
      const res = await callsAPI.getTranscript(recordingId);
      if (res.data.has_transcript) {
        setTranscript(res.data);
      } else {
        setTranscript({ has_transcript: false, transcription_status: res.data.transcription_status });
      }
    } catch (error) {
      console.error('Error fetching transcript:', error);
      setTranscript({ has_transcript: false, transcription_status: 'error' });
    }
  };

  const handleTranscribe = async (recording) => {
    const recordingId = recording.recording_id;
    setTranscribing(prev => ({ ...prev, [recordingId]: true }));
    
    try {
      toast.info('Starting transcription... This may take a few minutes.');
      const res = await callsAPI.transcribeRecording(recordingId);
      
      if (res.data.status === 'completed' || res.data.status === 'already_transcribed') {
        toast.success('Transcription complete!');
        setTranscript({
          has_transcript: true,
          transcript: res.data.transcript,
          segments: res.data.segments,
          transcribed_at: res.data.transcribed_at
        });
        
        // Update recording in list
        setRecordings(prev => prev.map(r => 
          r.recording_id === recordingId 
            ? { ...r, transcript: res.data.transcript, transcribed_at: res.data.transcribed_at }
            : r
        ));
      }
    } catch (error) {
      console.error('Transcription error:', error);
      toast.error(error.response?.data?.detail || 'Transcription failed');
    } finally {
      setTranscribing(prev => ({ ...prev, [recordingId]: false }));
    }
  };

  const handleSearchTranscripts = async () => {
    if (!transcriptSearchQuery.trim()) return;
    
    setSearchingTranscripts(true);
    try {
      const res = await callsAPI.searchTranscripts(transcriptSearchQuery);
      setTranscriptSearchResults(res.data.results || []);
      if (res.data.results?.length === 0) {
        toast.info('No matches found in transcripts');
      }
    } catch (error) {
      console.error('Search error:', error);
      toast.error('Search failed');
    } finally {
      setSearchingTranscripts(false);
    }
  };

  const copyTranscript = () => {
    // Prefer speaker transcript if available
    const textToCopy = transcript?.speaker_transcript || transcript?.transcript;
    if (textToCopy) {
      // Clean up markdown formatting for clipboard
      const cleanText = textToCopy
        .replace(/\*\*/g, '')
        .replace(/<[^>]+>/g, '');
      navigator.clipboard.writeText(cleanText);
      toast.success('Transcript copied to clipboard');
    }
  };

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };

  const handleSeek = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    const time = percent * duration;
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  const skip = (seconds) => {
    if (videoRef.current) {
      videoRef.current.currentTime = Math.max(0, Math.min(duration, videoRef.current.currentTime + seconds));
    }
  };

  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const toggleFullscreen = () => {
    if (videoRef.current) {
      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else {
        videoRef.current.requestFullscreen();
      }
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      completed: 'bg-green-100 text-green-800',
      awaiting_upload: 'bg-yellow-100 text-yellow-800',
      uploading: 'bg-blue-100 text-blue-800',
      recording: 'bg-red-100 text-red-800',
      failed: 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="recordings-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-serif text-3xl font-bold">Recordings Library</h1>
            <p className="text-muted-foreground mt-1">
              {recordings.length} recording{recordings.length !== 1 ? 's' : ''} saved
            </p>
          </div>
          <Badge variant="secondary" className="flex items-center gap-2">
            <FileVideo className="h-4 w-4" />
            {formatFileSize(recordings.reduce((acc, r) => acc + (r.file_size_bytes || 0), 0))} total
          </Badge>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-col sm:flex-row gap-4">
              {/* Search */}
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by name or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                  data-testid="search-recordings"
                />
              </div>

              {/* Status Filter */}
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="w-[160px]" data-testid="filter-status">
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="awaiting_upload">Awaiting Upload</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>

              {/* Sort Order */}
              <Select value={sortOrder} onValueChange={setSortOrder}>
                <SelectTrigger className="w-[160px]" data-testid="sort-order">
                  {sortOrder === 'newest' ? <SortDesc className="h-4 w-4 mr-2" /> : <SortAsc className="h-4 w-4 mr-2" />}
                  <SelectValue placeholder="Sort" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="newest">Newest First</SelectItem>
                  <SelectItem value="oldest">Oldest First</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Recordings Grid */}
        {filteredRecordings.length > 0 ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredRecordings.map((recording, index) => (
              <Card 
                key={recording.recording_id} 
                className="hover:shadow-lg transition-shadow"
                data-testid={`recording-card-${index}`}
              >
                <CardContent className="p-0">
                  {/* Thumbnail / Preview */}
                  <div 
                    className="relative h-40 bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center cursor-pointer group"
                    onClick={() => openPlayer(recording)}
                  >
                    <Video className="h-12 w-12 text-gray-500 group-hover:text-white transition-colors" />
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
                      <Play className="h-16 w-16 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    {/* Duration Badge */}
                    <div className="absolute bottom-2 right-2 bg-black/70 text-white text-xs px-2 py-1 rounded">
                      {formatDuration(recording.duration_seconds)}
                    </div>
                    {/* Status Badge */}
                    <Badge className={`absolute top-2 left-2 ${getStatusColor(recording.status)}`}>
                      {recording.status?.replace(/_/g, ' ')}
                    </Badge>
                  </div>

                  {/* Info */}
                  <div className="p-4 space-y-3">
                    {/* Participants */}
                    <div className="flex items-center gap-2">
                      <Users className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium truncate">
                        {recording.caller_name || 'Unknown'} ↔ {recording.recipient_name || 'Unknown'}
                      </span>
                    </div>

                    {/* Date */}
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="h-4 w-4" />
                      <span>{formatDate(recording.started_at)}</span>
                    </div>

                    {/* Size */}
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <FileVideo className="h-4 w-4" />
                      <span>{formatFileSize(recording.file_size_bytes)}</span>
                      {recording.transcript && (
                        <Badge variant="secondary" className="ml-auto text-xs bg-blue-100 text-blue-800">
                          <FileText className="h-3 w-3 mr-1" />
                          Transcribed
                        </Badge>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 pt-2">
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="flex-1"
                        onClick={() => openPlayer(recording)}
                        disabled={!recording.download_url && !recording.s3_url}
                        data-testid={`play-${index}`}
                      >
                        <Play className="h-4 w-4 mr-1" />
                        Play
                      </Button>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="flex-1"
                        onClick={() => handleDownload(recording)}
                        disabled={!recording.download_url && !recording.s3_url}
                        data-testid={`download-${index}`}
                      >
                        <Download className="h-4 w-4 mr-1" />
                        Download
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="p-12 text-center">
              <FileVideo className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-xl font-semibold">No Recordings Found</h3>
              <p className="text-muted-foreground mt-2">
                {searchQuery || filterStatus !== 'all' 
                  ? 'Try adjusting your search or filters'
                  : 'Start a video call and record it to see recordings here'}
              </p>
            </CardContent>
          </Card>
        )}

        {/* Transcript Search Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Search Transcripts
            </CardTitle>
            <CardDescription>
              Search across all transcribed call recordings
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search in transcripts..."
                  value={transcriptSearchQuery}
                  onChange={(e) => setTranscriptSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearchTranscripts()}
                  className="pl-10"
                  data-testid="search-transcripts"
                />
              </div>
              <Button 
                onClick={handleSearchTranscripts}
                disabled={searchingTranscripts || !transcriptSearchQuery.trim()}
              >
                {searchingTranscripts ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              </Button>
            </div>

            {/* Search Results */}
            {transcriptSearchResults.length > 0 && (
              <div className="mt-4 space-y-3">
                <p className="text-sm text-muted-foreground">
                  Found {transcriptSearchResults.length} recording(s) matching &quot;{transcriptSearchQuery}&quot;
                </p>
                {transcriptSearchResults.map((result, index) => (
                  <Card key={result.recording_id} className="bg-muted/50">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">
                          {result.caller_name} ↔ {result.recipient_name}
                        </span>
                        <span className="text-sm text-muted-foreground">
                          {formatDate(result.started_at)}
                        </span>
                      </div>
                      {result.excerpts.map((excerpt, i) => (
                        <p key={i} className="text-sm text-muted-foreground bg-background p-2 rounded mt-2">
                          {excerpt.excerpt}
                        </p>
                      ))}
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="mt-2"
                        onClick={() => {
                          const rec = recordings.find(r => r.recording_id === result.recording_id);
                          if (rec) openPlayer(rec);
                        }}
                      >
                        <Play className="h-3 w-3 mr-1" />
                        View Recording
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Video Player Dialog */}
        <Dialog open={!!selectedRecording} onOpenChange={() => closePlayer()}>
          <DialogContent className="max-w-4xl p-0 bg-black overflow-hidden max-h-[90vh]">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full">
              <div className="bg-gray-900 px-4 py-2 flex items-center justify-between">
                <TabsList className="bg-gray-800">
                  <TabsTrigger value="video" className="data-[state=active]:bg-gray-700">
                    <Video className="h-4 w-4 mr-2" />
                    Video
                  </TabsTrigger>
                  <TabsTrigger value="transcript" className="data-[state=active]:bg-gray-700">
                    <FileText className="h-4 w-4 mr-2" />
                    Transcript
                  </TabsTrigger>
                </TabsList>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-white hover:bg-white/20"
                  onClick={closePlayer}
                >
                  <X className="h-5 w-5" />
                </Button>
              </div>

              <TabsContent value="video" className="m-0">
                <div className="relative">
                  {/* Video */}
                  <video
                    ref={videoRef}
                    src={selectedRecording?.download_url || selectedRecording?.s3_url}
                    className="w-full aspect-video bg-black"
                    onTimeUpdate={handleTimeUpdate}
                    onLoadedMetadata={handleLoadedMetadata}
                    onEnded={() => setIsPlaying(false)}
                    onClick={togglePlay}
                    data-testid="video-player"
                  />

              {/* Controls Overlay */}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
                {/* Progress Bar */}
                <div 
                  className="h-1 bg-white/30 rounded-full mb-3 cursor-pointer"
                  onClick={handleSeek}
                >
                  <div 
                    className="h-full bg-primary rounded-full"
                    style={{ width: `${(currentTime / duration) * 100}%` }}
                  />
                </div>

                {/* Controls */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-white hover:bg-white/20"
                      onClick={() => skip(-10)}
                    >
                      <SkipBack className="h-5 w-5" />
                    </Button>
                    
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-white hover:bg-white/20 h-12 w-12"
                      onClick={togglePlay}
                      data-testid="play-pause-btn"
                    >
                      {isPlaying ? <Pause className="h-6 w-6" /> : <Play className="h-6 w-6" />}
                    </Button>

                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-white hover:bg-white/20"
                      onClick={() => skip(10)}
                    >
                      <SkipForward className="h-5 w-5" />
                    </Button>

                    <span className="text-white text-sm ml-2">
                      {formatDuration(currentTime)} / {formatDuration(duration)}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-white hover:bg-white/20"
                      onClick={toggleMute}
                    >
                      {isMuted ? <VolumeX className="h-5 w-5" /> : <Volume2 className="h-5 w-5" />}
                    </Button>

                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-white hover:bg-white/20"
                      onClick={toggleFullscreen}
                    >
                      <Maximize2 className="h-5 w-5" />
                    </Button>

                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-white hover:bg-white/20"
                      onClick={() => handleDownload(selectedRecording)}
                    >
                      <Download className="h-4 w-4 mr-1" />
                      Download
                    </Button>
                  </div>
                </div>

                {/* Recording Info */}
                <div className="mt-3 pt-3 border-t border-white/20 text-white/80 text-sm">
                  <div className="flex items-center justify-between">
                    <span>
                      <Users className="h-4 w-4 inline mr-1" />
                      {selectedRecording?.caller_name} ↔ {selectedRecording?.recipient_name}
                    </span>
                    <span>
                      <Calendar className="h-4 w-4 inline mr-1" />
                      {formatDate(selectedRecording?.started_at)}
                    </span>
                  </div>
                </div>
              </div>
                </div>
              </TabsContent>

              {/* Transcript Tab */}
              <TabsContent value="transcript" className="m-0 bg-gray-900">
                <div className="p-4 min-h-[400px] max-h-[60vh] overflow-auto">
                  {transcript?.has_transcript ? (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-green-400">
                          <CheckCircle className="h-4 w-4" />
                          <span className="text-sm">Transcribed {transcript.transcribed_at ? formatDate(transcript.transcribed_at) : ''}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          {transcript.speaker_labels && (
                            <div className="flex items-center gap-2 text-xs">
                              <Badge variant="outline" className="border-blue-500 text-blue-400">
                                <User className="h-3 w-3 mr-1" />
                                Attorney: {transcript.speaker_labels.attorney}
                              </Badge>
                              <Badge variant="outline" className="border-purple-500 text-purple-400">
                                <User className="h-3 w-3 mr-1" />
                                Client: {transcript.speaker_labels.client}
                              </Badge>
                            </div>
                          )}
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-white border-white/30 hover:bg-white/10"
                            onClick={copyTranscript}
                          >
                            <Copy className="h-4 w-4 mr-1" />
                            Copy
                          </Button>
                        </div>
                      </div>
                      
                      {/* Speaker-labeled transcript with timestamps */}
                      <ScrollArea className="h-[400px]">
                        {transcript.speaker_segments && transcript.speaker_segments.length > 0 ? (
                          <div className="space-y-3">
                            <p className="text-xs text-white/50 mb-2">
                              💡 Click any segment to jump to that moment in the video
                            </p>
                            {transcript.speaker_segments.map((segment, index) => {
                              const startTime = segment.start || 0;
                              const mins = Math.floor(startTime / 60);
                              const secs = Math.floor(startTime % 60);
                              const timeStr = `${mins}:${secs.toString().padStart(2, '0')}`;
                              
                              return (
                                <div 
                                  key={index} 
                                  className={`p-3 rounded-lg cursor-pointer transition-all hover:scale-[1.01] hover:shadow-lg ${
                                    segment.speaker === 'attorney' 
                                      ? 'bg-blue-900/30 border-l-4 border-blue-500 hover:bg-blue-900/50' 
                                      : segment.speaker === 'client'
                                        ? 'bg-purple-900/30 border-l-4 border-purple-500 hover:bg-purple-900/50'
                                        : 'bg-gray-800/50 border-l-4 border-gray-500 hover:bg-gray-800/70'
                                  }`}
                                  onClick={() => {
                                    // Switch to video tab and seek
                                    setActiveTab('video');
                                    setTimeout(() => {
                                      if (videoRef.current) {
                                        videoRef.current.currentTime = startTime;
                                        videoRef.current.play();
                                        setIsPlaying(true);
                                      }
                                    }, 100);
                                  }}
                                  data-testid={`transcript-segment-${index}`}
                                >
                                  <div className="flex items-center justify-between mb-1">
                                    <span className={`text-xs font-semibold ${
                                      segment.speaker === 'attorney' 
                                        ? 'text-blue-400' 
                                        : segment.speaker === 'client' 
                                          ? 'text-purple-400'
                                          : 'text-gray-400'
                                    }`}>
                                      {segment.speaker === 'attorney' 
                                        ? `Attorney (${transcript.speaker_labels?.attorney || 'Unknown'})` 
                                        : segment.speaker === 'client'
                                          ? `Client (${transcript.speaker_labels?.client || 'Unknown'})`
                                          : 'Speaker'}
                                    </span>
                                    <Badge 
                                      variant="outline" 
                                      className="text-xs border-white/20 text-white/60 hover:bg-white/10"
                                    >
                                      <Clock className="h-3 w-3 mr-1" />
                                      {timeStr}
                                    </Badge>
                                  </div>
                                  <p className="text-white/90 leading-relaxed">
                                    {segment.text}
                                  </p>
                                </div>
                              );
                            })}
                          </div>
                        ) : transcript.speaker_transcript ? (
                          <div 
                            className="text-white/90 leading-relaxed prose prose-invert max-w-none"
                            dangerouslySetInnerHTML={{ 
                              __html: transcript.speaker_transcript
                                .replace(/\*\*Attorney[^:]*:\*\*/g, '<span class="text-blue-400 font-semibold">Attorney:</span>')
                                .replace(/\*\*Client[^:]*:\*\*/g, '<span class="text-purple-400 font-semibold">Client:</span>')
                                .replace(/\n/g, '<br/>')  
                            }}
                          />
                        ) : (
                          <p className="text-white/90 whitespace-pre-wrap leading-relaxed">
                            {transcript.transcript}
                          </p>
                        )}
                      </ScrollArea>
                    </div>
                  ) : transcript?.transcription_status === 'processing' ? (
                    <div className="flex flex-col items-center justify-center h-full text-white/70">
                      <Loader2 className="h-12 w-12 animate-spin mb-4" />
                      <p>Transcription in progress...</p>
                      <p className="text-sm">This may take a few minutes</p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full text-white/70">
                      <FileText className="h-12 w-12 mb-4 opacity-50" />
                      <p className="mb-4">No transcript available</p>
                      <Button
                        onClick={() => handleTranscribe(selectedRecording)}
                        disabled={transcribing[selectedRecording?.recording_id]}
                        className="bg-blue-600 hover:bg-blue-700"
                      >
                        {transcribing[selectedRecording?.recording_id] ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Transcribing...
                          </>
                        ) : (
                          <>
                            <FileText className="h-4 w-4 mr-2" />
                            Transcribe with Speaker ID
                          </>
                        )}
                      </Button>
                      <p className="text-sm mt-2 text-white/50">
                        AI identifies who said what in the conversation
                      </p>
                    </div>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  );
}
