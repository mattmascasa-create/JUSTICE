import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { encounterAPI, API_URL } from '../lib/api';
import { 
  Shield, MapPin, Clock, Video, Mic, FileText, AlertTriangle,
  CheckCircle, ExternalLink, Download, Scale, Users, ArrowLeft,
  Loader2, Play, AlertCircle, Gavel, Share2, Copy, SkipBack, SkipForward,
  Pause, Volume2, Maximize
} from 'lucide-react';
import { toast } from 'sonner';

export default function EncounterReportPage() {
  const { encounterId } = useParams();
  const [loading, setLoading] = useState(true);
  const [reportData, setReportData] = useState(null);
  const [error, setError] = useState(null);
  const [currentVideoIndex, setCurrentVideoIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [shareLink, setShareLink] = useState('');
  const [generatingLink, setGeneratingLink] = useState(false);
  const videoRef = useRef(null);
  const authToken = localStorage.getItem('justice-token');

  useEffect(() => {
    loadReport();
  }, [encounterId]);

  const loadReport = async () => {
    try {
      setLoading(true);
      const response = await encounterAPI.getReport(encounterId);
      setReportData(response.data);
    } catch (err) {
      console.error('Error loading report:', err);
      setError(err.response?.data?.detail || 'Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  const getVideoUrl = (filename) => {
    return `${API_URL}/encounters/${encounterId}/media/${filename}?token=${authToken}`;
  };

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handlePrevVideo = () => {
    if (currentVideoIndex > 0) {
      setCurrentVideoIndex(currentVideoIndex - 1);
      setIsPlaying(false);
    }
  };

  const handleNextVideo = () => {
    const videoFiles = reportData?.media_files?.filter(f => f.type === 'video') || [];
    if (currentVideoIndex < videoFiles.length - 1) {
      setCurrentVideoIndex(currentVideoIndex + 1);
      setIsPlaying(false);
    }
  };

  const handleVideoEnded = () => {
    const videoFiles = reportData?.media_files?.filter(f => f.type === 'video') || [];
    if (currentVideoIndex < videoFiles.length - 1) {
      setCurrentVideoIndex(currentVideoIndex + 1);
      // Auto-play next chunk
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.play();
          setIsPlaying(true);
        }
      }, 500);
    } else {
      setIsPlaying(false);
    }
  };

  const handleGenerateShareLink = async () => {
    setGeneratingLink(true);
    try {
      const response = await encounterAPI.getStreamToken(encounterId);
      const fullUrl = `${window.location.origin}${response.data.share_url}`;
      setShareLink(fullUrl);
      toast.success('Share link generated!');
    } catch (err) {
      toast.error('Failed to generate share link');
    } finally {
      setGeneratingLink(false);
    }
  };

  const handleCopyLink = () => {
    navigator.clipboard.writeText(shareLink);
    toast.success('Link copied to clipboard!');
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const formatViolation = (violation) => {
    return violation.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center space-y-4">
            <Loader2 className="h-12 w-12 animate-spin mx-auto text-primary" />
            <p className="text-muted-foreground">Loading incident report...</p>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (error || !reportData) {
    return (
      <AppLayout>
        <div className="max-w-2xl mx-auto">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error || 'Report not found'}</AlertDescription>
          </Alert>
          <Link to="/encounter">
            <Button variant="outline" className="mt-4">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Encounter Mode
            </Button>
          </Link>
        </div>
      </AppLayout>
    );
  }

  if (reportData.status === 'generating') {
    return (
      <AppLayout>
        <div className="max-w-2xl mx-auto text-center space-y-6">
          <div className="inline-flex items-center justify-center p-4 rounded-full bg-blue-500/20">
            <Loader2 className="h-12 w-12 text-blue-500 animate-spin" />
          </div>
          <h1 className="font-serif text-3xl font-bold">Generating Your Report</h1>
          <p className="text-muted-foreground">
            Our AI is analyzing your encounter recording and preparing a detailed incident report.
            This usually takes 30-60 seconds.
          </p>
          <Button onClick={loadReport} variant="outline">
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Check Status
          </Button>
        </div>
      </AppLayout>
    );
  }

  const { report, transcriptions, media_files } = reportData;
  const videoFiles = media_files?.filter(f => f.type === 'video') || [];
  const audioFiles = media_files?.filter(f => f.type === 'audio') || [];

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-6" data-testid="encounter-report">
        {/* Back Button */}
        <Link to="/dashboard">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
        </Link>

        {/* Report Header */}
        <Card className="border-2 border-primary/20">
          <CardHeader className="pb-4">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <CardTitle className="font-serif text-3xl flex items-center gap-3">
                  <Shield className="h-8 w-8 text-primary" />
                  Incident Report
                </CardTitle>
                <CardDescription>
                  Report ID: {report.report_id}
                </CardDescription>
              </div>
              {report.court_admissible && (
                <Badge className="bg-green-500/10 text-green-500 text-sm px-3 py-1">
                  <Gavel className="h-4 w-4 mr-1" />
                  Court Admissible
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Encounter Details Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-3 rounded-lg bg-muted/50 text-center">
                <p className="text-2xl font-bold">{formatDuration(report.encounter_details?.duration_seconds || 0)}</p>
                <p className="text-xs text-muted-foreground flex items-center justify-center gap-1">
                  <Clock className="h-3 w-3" /> Duration
                </p>
              </div>
              <div className="p-3 rounded-lg bg-muted/50 text-center">
                <p className="text-2xl font-bold text-red-500">{report.violations_count || 0}</p>
                <p className="text-xs text-muted-foreground flex items-center justify-center gap-1">
                  <AlertTriangle className="h-3 w-3" /> Violations
                </p>
              </div>
              <div className="p-3 rounded-lg bg-muted/50 text-center">
                <p className="text-2xl font-bold">{videoFiles.length}</p>
                <p className="text-xs text-muted-foreground flex items-center justify-center gap-1">
                  <Video className="h-3 w-3" /> Video Chunks
                </p>
              </div>
              <div className="p-3 rounded-lg bg-muted/50 text-center">
                <p className="text-2xl font-bold">{report.evidence?.total_size_mb || 0} MB</p>
                <p className="text-xs text-muted-foreground flex items-center justify-center gap-1">
                  <FileText className="h-3 w-3" /> Evidence Size
                </p>
              </div>
            </div>

            {/* Location */}
            <div className="flex items-center gap-2 text-sm">
              <MapPin className="h-4 w-4 text-muted-foreground" />
              <span>{report.encounter_details?.location || 'Location not recorded'}</span>
            </div>
          </CardContent>
        </Card>

        {/* Summary Section */}
        <Card>
          <CardHeader>
            <CardTitle className="font-serif flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Incident Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground leading-relaxed">
              {report.summary || 'Summary is being generated...'}
            </p>
          </CardContent>
        </Card>

        {/* Violations Section */}
        {report.violations?.length > 0 && (
          <Card className="border-red-500/30">
            <CardHeader>
              <CardTitle className="font-serif flex items-center gap-2 text-red-500">
                <AlertTriangle className="h-5 w-5" />
                Potential Civil Rights Violations Detected
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {report.violations.map((violation, index) => (
                <div 
                  key={index}
                  className="flex items-center gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20"
                >
                  <AlertCircle className="h-5 w-5 text-red-500" />
                  <span className="font-medium">{formatViolation(violation)}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Evidence Section */}
        <Card>
          <CardHeader>
            <CardTitle className="font-serif flex items-center gap-2">
              <Video className="h-5 w-5" />
              Recorded Evidence
            </CardTitle>
            <CardDescription>
              All recordings are automatically saved and verified
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Video Player */}
            {videoFiles.length > 0 && (
              <div className="space-y-3">
                <p className="text-sm font-medium flex items-center gap-2">
                  <Video className="h-4 w-4" />
                  Video Playback ({videoFiles.length} chunks)
                </p>
                
                {/* Main Video Player */}
                <div className="relative rounded-lg overflow-hidden bg-black aspect-video">
                  <video
                    ref={videoRef}
                    src={getVideoUrl(videoFiles[currentVideoIndex]?.filename)}
                    className="w-full h-full"
                    onEnded={handleVideoEnded}
                    onPlay={() => setIsPlaying(true)}
                    onPause={() => setIsPlaying(false)}
                    controls={false}
                  />
                  
                  {/* Custom Controls Overlay */}
                  <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-white hover:bg-white/20"
                          onClick={handlePrevVideo}
                          disabled={currentVideoIndex === 0}
                        >
                          <SkipBack className="h-5 w-5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-white hover:bg-white/20 h-12 w-12"
                          onClick={handlePlayPause}
                        >
                          {isPlaying ? (
                            <Pause className="h-6 w-6" />
                          ) : (
                            <Play className="h-6 w-6" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-white hover:bg-white/20"
                          onClick={handleNextVideo}
                          disabled={currentVideoIndex === videoFiles.length - 1}
                        >
                          <SkipForward className="h-5 w-5" />
                        </Button>
                      </div>
                      
                      <div className="flex items-center gap-3">
                        <Badge variant="secondary" className="bg-black/50">
                          Chunk {currentVideoIndex + 1} / {videoFiles.length}
                        </Badge>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-white hover:bg-white/20"
                          onClick={() => videoRef.current?.requestFullscreen()}
                        >
                          <Maximize className="h-5 w-5" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Video Chunk Thumbnails */}
                <div className="flex gap-2 overflow-x-auto pb-2">
                  {videoFiles.map((file, index) => (
                    <button
                      key={index}
                      onClick={() => {
                        setCurrentVideoIndex(index);
                        setIsPlaying(false);
                      }}
                      className={`flex-shrink-0 p-2 rounded text-xs transition-all ${
                        index === currentVideoIndex 
                          ? 'bg-primary text-primary-foreground' 
                          : 'bg-muted/50 hover:bg-muted'
                      }`}
                    >
                      <Play className="h-3 w-3 mx-auto mb-1" />
                      <span>#{index + 1}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Audio Files */}
            {audioFiles.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium flex items-center gap-2">
                  <Mic className="h-4 w-4" />
                  Audio Recordings ({audioFiles.length} chunks)
                </p>
                <div className="space-y-2">
                  {audioFiles.slice(0, 5).map((file, index) => (
                    <div key={index} className="flex items-center gap-3 p-2 rounded bg-muted/50">
                      <Volume2 className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm flex-1 truncate">{file.filename}</span>
                      <audio 
                        src={getVideoUrl(file.filename)} 
                        controls 
                        className="h-8 max-w-[200px]"
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}
                </p>
              </div>
            )}

            {/* Transcriptions */}
            {transcriptions?.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Transcriptions ({transcriptions.length} segments)
                </p>
                <div className="max-h-60 overflow-y-auto space-y-2 p-3 rounded-lg bg-muted/30 border">
                  {transcriptions.map((t, index) => (
                    <div key={index} className="text-sm">
                      <span className="text-xs text-muted-foreground font-mono">
                        [{formatDuration(Math.round(t.start_time || index * 10))}]
                      </span>
                      <p className="mt-0.5">{t.text}</p>
                      {t.violations_detected?.length > 0 && (
                        <div className="flex gap-1 mt-1">
                          {t.violations_detected.map((v, i) => (
                            <Badge key={i} variant="destructive" className="text-xs">
                              {formatViolation(v)}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recommendations Section */}
        {report.recommendations?.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="font-serif flex items-center gap-2">
                <Scale className="h-5 w-5" />
                Legal Recommendations
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {report.recommendations.map((rec, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500 mt-1 flex-shrink-0" />
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {/* Officers Section */}
        {report.officers?.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="font-serif flex items-center gap-2">
                <Users className="h-5 w-5" />
                Officers Involved
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {report.officers.map((officer, index) => (
                  <div key={index} className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                    <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <Users className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium">{officer.name || 'Unknown Officer'}</p>
                      <p className="text-sm text-muted-foreground">
                        Badge: {officer.badge_number || 'N/A'} • {officer.department || 'Unknown Department'}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Legal Resources */}
        <Card>
          <CardHeader>
            <CardTitle className="font-serif flex items-center gap-2">
              <ExternalLink className="h-5 w-5" />
              Legal Resources
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {report.legal_resources?.map((resource, index) => (
                <a
                  key={index}
                  href={resource.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                >
                  <ExternalLink className="h-4 w-4 text-primary" />
                  <span className="text-sm">{resource.name}</span>
                </a>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-3">
          <Button className="flex-1">
            <Download className="h-4 w-4 mr-2" />
            Download Full Report
          </Button>
          
          {/* Share Dialog */}
          <Dialog open={shareDialogOpen} onOpenChange={setShareDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" className="flex-1">
                <Share2 className="h-4 w-4 mr-2" />
                Share with Attorney
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle className="font-serif flex items-center gap-2">
                  <Share2 className="h-5 w-5" />
                  Share Encounter Recording
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Generate a secure link that allows your attorney or emergency contacts to view this encounter recording without needing an account.
                </p>
                
                {!shareLink ? (
                  <Button 
                    onClick={handleGenerateShareLink} 
                    className="w-full"
                    disabled={generatingLink}
                  >
                    {generatingLink ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Generating Link...
                      </>
                    ) : (
                      <>
                        <Share2 className="h-4 w-4 mr-2" />
                        Generate Secure Link
                      </>
                    )}
                  </Button>
                ) : (
                  <div className="space-y-3">
                    <div className="p-3 rounded-lg bg-muted border">
                      <p className="text-xs text-muted-foreground mb-1">Share Link (expires in 24 hours)</p>
                      <p className="text-sm font-mono break-all">{shareLink}</p>
                    </div>
                    <div className="flex gap-2">
                      <Button onClick={handleCopyLink} className="flex-1">
                        <Copy className="h-4 w-4 mr-2" />
                        Copy Link
                      </Button>
                      <Button 
                        variant="outline" 
                        onClick={() => {
                          setShareLink('');
                          handleGenerateShareLink();
                        }}
                      >
                        Regenerate
                      </Button>
                    </div>
                    <Alert className="bg-yellow-500/10 border-yellow-500/30">
                      <AlertTriangle className="h-4 w-4 text-yellow-500" />
                      <AlertDescription className="text-xs">
                        Anyone with this link can view the recording. Only share with trusted contacts.
                      </AlertDescription>
                    </Alert>
                  </div>
                )}
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>
    </AppLayout>
  );
}
