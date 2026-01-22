import React, { useState, useEffect, useRef } from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { callsAPI } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import {
  Video, Download, Play, Pause, Search,
  Clock, Calendar, User, Users, FileVideo,
  Filter, SortAsc, SortDesc, X, Volume2,
  VolumeX, Maximize2, SkipBack, SkipForward
} from 'lucide-react';

export default function RecordingsPage() {
  const { user } = useAuth();
  const [recordings, setRecordings] = useState([]);
  const [filteredRecordings, setFilteredRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortOrder, setSortOrder] = useState('newest');
  const [filterStatus, setFilterStatus] = useState('all');
  
  // Video player state
  const [selectedRecording, setSelectedRecording] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const videoRef = useRef(null);

  useEffect(() => {
    fetchRecordings();
  }, []);

  useEffect(() => {
    filterAndSortRecordings();
  }, [recordings, searchQuery, sortOrder, filterStatus]);

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
  };

  const closePlayer = () => {
    setSelectedRecording(null);
    setIsPlaying(false);
    if (videoRef.current) {
      videoRef.current.pause();
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

        {/* Video Player Dialog */}
        <Dialog open={!!selectedRecording} onOpenChange={() => closePlayer()}>
          <DialogContent className="max-w-4xl p-0 bg-black overflow-hidden">
            <div className="relative">
              {/* Close Button */}
              <Button
                variant="ghost"
                size="icon"
                className="absolute top-2 right-2 z-10 text-white hover:bg-white/20"
                onClick={closePlayer}
              >
                <X className="h-5 w-5" />
              </Button>

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
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  );
}
