/**
 * Reconstruction3DPage
 * 
 * 3D Evidence Reconstruction viewer for encounters.
 * Creates navigable 3D scenes from encounter footage and data.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import Scene3DViewer from '../components/Scene3DViewer';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Slider } from '../components/ui/slider';
import { ScrollArea } from '../components/ui/scroll-area';
import { Alert, AlertDescription } from '../components/ui/alert';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';
import api from '../lib/api';
import {
  Box, Play, Pause, RotateCcw, Maximize2, 
  ChevronRight, AlertTriangle, Video, Mic,
  FileText, Clock, MapPin, Loader2, RefreshCw,
  Eye, Download, Share2
} from 'lucide-react';

// API functions
const reconstruction3DAPI = {
  create: (encounterId, options) => api.post('/reconstruction/create', { encounter_id: encounterId, options }),
  get: (id) => api.get(`/reconstruction/${id}`),
  getByEncounter: (encounterId) => api.get(`/reconstruction/encounter/${encounterId}`),
  list: (limit = 20) => api.get(`/reconstruction?limit=${limit}`),
  preview: (encounterId) => api.get(`/reconstruction/preview/${encounterId}`),
  delete: (id) => api.delete(`/reconstruction/${id}`)
};

export default function Reconstruction3DPage() {
  const { encounterId } = useParams();
  const navigate = useNavigate();
  
  // State
  const [reconstruction, setReconstruction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [encounters, setEncounters] = useState([]);
  const [selectedEncounter, setSelectedEncounter] = useState(encounterId || '');
  
  // Playback state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(60);
  
  // UI state
  const [selectedMarker, setSelectedMarker] = useState(null);
  const [showTimeline, setShowTimeline] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Load user's encounters for selector
  useEffect(() => {
    const loadEncounters = async () => {
      try {
        const res = await api.get('/encounters?limit=50');
        setEncounters(res.data.encounters || []);
      } catch (err) {
        console.error('Failed to load encounters:', err);
      }
    };
    loadEncounters();
  }, []);

  // Load or create reconstruction
  useEffect(() => {
    const loadReconstruction = async () => {
      if (!selectedEncounter) {
        setLoading(false);
        return;
      }
      
      setLoading(true);
      setError(null);
      
      try {
        const res = await reconstruction3DAPI.getByEncounter(selectedEncounter);
        setReconstruction(res.data.reconstruction);
        
        // Set duration from timeline
        const timeline = res.data.reconstruction?.scene_data?.timeline || [];
        if (timeline.length > 0) {
          setDuration(timeline[timeline.length - 1]?.time || 60);
        }
        
        if (res.data.cached) {
          toast.info('Loaded existing reconstruction');
        } else {
          toast.success('3D reconstruction created!');
        }
      } catch (err) {
        console.error('Failed to load reconstruction:', err);
        setError(err.response?.data?.detail || 'Failed to load reconstruction');
      } finally {
        setLoading(false);
      }
    };
    
    loadReconstruction();
  }, [selectedEncounter]);

  // Timeline playback
  useEffect(() => {
    if (!isPlaying) return;
    
    const interval = setInterval(() => {
      setCurrentTime(prev => {
        if (prev >= duration) {
          setIsPlaying(false);
          return 0;
        }
        return prev + 0.5;
      });
    }, 500);
    
    return () => clearInterval(interval);
  }, [isPlaying, duration]);

  // Handle marker click
  const handleMarkerClick = useCallback((data) => {
    setSelectedMarker(data);
    toast.info(`Selected: ${data?.label || 'Marker'}`);
  }, []);

  // Regenerate reconstruction
  const regenerateReconstruction = async () => {
    if (!selectedEncounter) return;
    
    setGenerating(true);
    try {
      // Delete existing
      if (reconstruction?.reconstruction_id) {
        await reconstruction3DAPI.delete(reconstruction.reconstruction_id);
      }
      
      // Create new
      const res = await reconstruction3DAPI.create(selectedEncounter, {
        generate_point_cloud: true
      });
      setReconstruction(res.data.reconstruction);
      toast.success('Reconstruction regenerated!');
    } catch (err) {
      toast.error('Failed to regenerate');
    } finally {
      setGenerating(false);
    }
  };

  // Get marker type icon
  const getMarkerIcon = (type) => {
    switch (type) {
      case 'violation': return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'video': return <Video className="h-4 w-4 text-blue-500" />;
      case 'audio': return <Mic className="h-4 w-4 text-purple-500" />;
      default: return <FileText className="h-4 w-4 text-gray-500" />;
    }
  };

  // Format time
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <AppLayout>
      <div className="p-6 space-y-6" data-testid="reconstruction-3d-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Box className="h-6 w-6 text-blue-500" />
              3D Evidence Reconstruction
            </h1>
            <p className="text-muted-foreground">
              Navigate and explore your encounter in 3D space
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            {reconstruction && (
              <>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={regenerateReconstruction}
                  disabled={generating}
                >
                  {generating ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <RefreshCw className="h-4 w-4 mr-2" />
                  )}
                  Regenerate
                </Button>
                <Button variant="outline" size="sm">
                  <Share2 className="h-4 w-4 mr-2" />
                  Share
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Encounter Selector */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <label className="text-sm font-medium mb-2 block">Select Encounter</label>
                <Select value={selectedEncounter} onValueChange={setSelectedEncounter}>
                  <SelectTrigger data-testid="encounter-selector">
                    <SelectValue placeholder="Choose an encounter to reconstruct..." />
                  </SelectTrigger>
                  <SelectContent>
                    {encounters.map((enc) => (
                      <SelectItem key={enc.encounter_id} value={enc.encounter_id}>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            {enc.encounter_type}
                          </Badge>
                          <span className="text-sm">
                            {new Date(enc.created_at).toLocaleDateString()}
                          </span>
                          {enc.duration && (
                            <span className="text-xs text-muted-foreground">
                              ({Math.floor(enc.duration / 60)}m)
                            </span>
                          )}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {reconstruction && (
                <div className="flex gap-4 text-sm">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-blue-500">
                      {reconstruction.metadata?.evidence_count || 0}
                    </p>
                    <p className="text-xs text-muted-foreground">Evidence</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-purple-500">
                      {reconstruction.scene_data?.markers?.filter(m => m.type === 'violation').length || 0}
                    </p>
                    <p className="text-xs text-muted-foreground">Violations</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-green-500">
                      {formatTime(reconstruction.metadata?.duration_seconds || 0)}
                    </p>
                    <p className="text-xs text-muted-foreground">Duration</p>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Error State */}
        {error && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Loading State */}
        {loading && (
          <Card className="h-[500px] flex items-center justify-center">
            <div className="text-center">
              <Loader2 className="h-12 w-12 animate-spin text-blue-500 mx-auto mb-4" />
              <p className="text-lg font-medium">Generating 3D Reconstruction...</p>
              <p className="text-sm text-muted-foreground">
                Analyzing evidence and building scene
              </p>
            </div>
          </Card>
        )}

        {/* No Encounter Selected */}
        {!loading && !selectedEncounter && (
          <Card className="h-[500px] flex items-center justify-center">
            <div className="text-center">
              <Box className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <p className="text-lg font-medium">Select an Encounter</p>
              <p className="text-sm text-muted-foreground">
                Choose an encounter above to generate its 3D reconstruction
              </p>
            </div>
          </Card>
        )}

        {/* 3D Viewer */}
        {!loading && reconstruction && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            {/* Main 3D View */}
            <Card className={`${isFullscreen ? 'col-span-4' : 'col-span-3'} overflow-hidden`}>
              <CardContent className="p-0 relative">
                <div 
                  className={`${isFullscreen ? 'h-[80vh]' : 'h-[500px]'}`}
                  data-testid="3d-canvas-container"
                >
                  <Scene3DViewer
                    sceneData={reconstruction.scene_data}
                    onMarkerClick={handleMarkerClick}
                    currentTime={currentTime}
                  />
                </div>
                
                {/* Playback Controls Overlay */}
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
                  <div className="flex items-center gap-4">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-white hover:bg-white/20"
                      onClick={() => setIsPlaying(!isPlaying)}
                    >
                      {isPlaying ? (
                        <Pause className="h-5 w-5" />
                      ) : (
                        <Play className="h-5 w-5" />
                      )}
                    </Button>
                    
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-white hover:bg-white/20"
                      onClick={() => setCurrentTime(0)}
                    >
                      <RotateCcw className="h-4 w-4" />
                    </Button>
                    
                    <div className="flex-1">
                      <Slider
                        value={[currentTime]}
                        max={duration}
                        step={0.5}
                        onValueChange={([v]) => setCurrentTime(v)}
                        className="cursor-pointer"
                      />
                    </div>
                    
                    <span className="text-white text-sm font-mono min-w-[80px]">
                      {formatTime(currentTime)} / {formatTime(duration)}
                    </span>
                    
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-white hover:bg-white/20"
                      onClick={() => setIsFullscreen(!isFullscreen)}
                    >
                      <Maximize2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Sidebar - Timeline & Info */}
            {!isFullscreen && (
              <div className="space-y-4">
                {/* Selected Marker Info */}
                {selectedMarker && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        {getMarkerIcon(selectedMarker.type)}
                        Selected Item
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <p className="text-sm font-medium">{selectedMarker.label}</p>
                      {selectedMarker.type && (
                        <Badge variant="outline">{selectedMarker.type}</Badge>
                      )}
                      {selectedMarker.evidence_id && (
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="w-full"
                          onClick={() => navigate(`/evidence/${selectedMarker.evidence_id}`)}
                        >
                          <Eye className="h-4 w-4 mr-2" />
                          View Evidence
                        </Button>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* Timeline Events */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Clock className="h-4 w-4" />
                      Timeline
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ScrollArea className="h-[300px]">
                      <div className="space-y-2">
                        {reconstruction.scene_data?.timeline?.map((event, idx) => (
                          <div 
                            key={idx}
                            className={`p-2 rounded-lg border cursor-pointer transition-colors ${
                              currentTime >= event.time && currentTime < (reconstruction.scene_data.timeline[idx + 1]?.time || duration)
                                ? 'bg-blue-500/20 border-blue-500'
                                : 'hover:bg-muted/50'
                            }`}
                            onClick={() => setCurrentTime(event.time)}
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-mono text-muted-foreground">
                                {formatTime(event.time)}
                              </span>
                              {event.event === 'violation' && (
                                <AlertTriangle className="h-3 w-3 text-red-500" />
                              )}
                            </div>
                            <p className="text-sm font-medium truncate">{event.label}</p>
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>

                {/* Scene Info */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Scene Info</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Type</span>
                      <Badge variant="outline">
                        {reconstruction.metadata?.location?.encounter_type || 'Unknown'}
                      </Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Point Cloud</span>
                      <span>{reconstruction.scene_data?.point_cloud?.points?.length || 0} points</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Markers</span>
                      <span>{reconstruction.scene_data?.markers?.length || 0}</span>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        )}

        {/* Legend */}
        {reconstruction && (
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-6 flex-wrap">
                <span className="text-sm font-medium">Legend:</span>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-red-500" />
                  <span className="text-sm">Violations</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-blue-500" />
                  <span className="text-sm">Video Evidence</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-purple-500" />
                  <span className="text-sm">Audio Evidence</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-green-500" />
                  <span className="text-sm">Movement Path</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-gray-400" />
                  <span className="text-sm">Point Cloud (Speech Activity)</span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </AppLayout>
  );
}
