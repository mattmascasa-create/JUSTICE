/**
 * EncounterSetupScreen Component
 * Pre-recording setup UI for encounter mode
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Switch } from '../../components/ui/switch';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Alert, AlertDescription } from '../../components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { 
  Shield, Camera, Video, MapPin, CheckCircle, 
  FileText, Users, Scale, Radio, Share2
} from 'lucide-react';
import { encounterTypes, broadcastModes, qualityPresets } from './constants';

// Icon mapping for broadcast modes
const broadcastIcons = {
  FileText, Users, Scale, Radio, Share2
};

export function EncounterSetupScreen({
  location,
  address,
  onAddressChange,
  enableVideo,
  onEnableVideoChange,
  recordingQuality,
  onRecordingQualityChange,
  deferAnalysis,
  onDeferAnalysisChange,
  encounterType,
  onEncounterTypeChange,
  broadcastMode,
  onBroadcastModeChange,
  onStartRecording,
  isStarting = false
}) {
  return (
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
              onChange={(e) => onAddressChange(e.target.value)}
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
          {/* Video Toggle */}
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
              onCheckedChange={onEnableVideoChange}
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
          
          {/* Recording Quality Settings */}
          <div className="pt-2 border-t">
            <div className="flex items-center justify-between mb-3">
              <Label className="text-sm font-medium">Recording Quality</Label>
              <Badge variant="outline" className="text-xs">
                {qualityPresets[recordingQuality]?.icon} {qualityPresets[recordingQuality]?.label?.split(' ')[0]}
              </Badge>
            </div>
            <div className="space-y-2">
              {Object.entries(qualityPresets).map(([key, preset]) => (
                <button
                  key={key}
                  onClick={() => onRecordingQualityChange(key)}
                  className={`w-full flex items-center gap-3 p-2 rounded-lg border text-left text-sm transition-all ${
                    recordingQuality === key 
                      ? 'border-primary bg-primary/10' 
                      : 'border-border hover:bg-muted'
                  }`}
                >
                  <span className="text-lg">{preset.icon}</span>
                  <div className="flex-1">
                    <p className="font-medium">{preset.label}</p>
                    <p className="text-xs text-muted-foreground">{preset.desc}</p>
                  </div>
                  {recordingQuality === key && (
                    <CheckCircle className="h-4 w-4 text-primary" />
                  )}
                </button>
              ))}
            </div>
          </div>
          
          {/* Performance Mode Toggle */}
          <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30">
            <div>
              <p className="text-sm font-medium">Defer AI Analysis</p>
              <p className="text-xs text-muted-foreground">
                Faster recording, analyze after encounter
              </p>
            </div>
            <Switch 
              checked={deferAnalysis} 
              onCheckedChange={onDeferAnalysisChange}
            />
          </div>
        </CardContent>
      </Card>

      {/* Encounter Type */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Type of Encounter</CardTitle>
        </CardHeader>
        <CardContent>
          <Select value={encounterType} onValueChange={onEncounterTypeChange}>
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
          {broadcastModes.map(mode => {
            const IconComponent = broadcastIcons[mode.icon] || FileText;
            return (
              <button
                key={mode.value}
                onClick={() => onBroadcastModeChange(mode.value)}
                className={`w-full flex items-center gap-3 p-3 rounded-lg border transition-all ${
                  broadcastMode === mode.value 
                    ? 'border-primary bg-primary/10' 
                    : 'border-border hover:bg-muted'
                }`}
              >
                <div className={`p-2 rounded-lg ${broadcastMode === mode.value ? 'bg-primary/20' : 'bg-muted'}`}>
                  <IconComponent className="h-5 w-5" />
                </div>
                <div className="flex-1 text-left">
                  <p className="font-medium">{mode.label}</p>
                  <p className="text-sm text-muted-foreground">{mode.desc}</p>
                </div>
                {broadcastMode === mode.value && (
                  <CheckCircle className="h-5 w-5 text-primary" />
                )}
              </button>
            );
          })}
        </CardContent>
      </Card>

      {/* Start Button */}
      <Button 
        size="lg" 
        className="w-full h-16 text-xl bg-red-600 hover:bg-red-700"
        onClick={onStartRecording}
        disabled={!location || isStarting}
        data-testid="start-recording-btn"
      >
        <Shield className="mr-2 h-6 w-6" />
        {isStarting ? 'Starting...' : 'Start Recording & Protection'}
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        Recording will continue even if the app is minimized.
        All data is stored locally first for maximum reliability.
      </p>
    </div>
  );
}

export default EncounterSetupScreen;
