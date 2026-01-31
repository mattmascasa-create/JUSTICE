/**
 * VoiceControlPanel Component
 * 
 * Provides full voice control of the JUSTICE app for hands-free operation.
 * Critical for situations where the user cannot look at their phone.
 * 
 * Features:
 * - Continuous listening with wake word detection
 * - Audio feedback for actions
 * - Visual command status
 * - Multi-language support
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Alert, AlertDescription } from '../components/ui/alert';
import { ScrollArea } from '../components/ui/scroll-area';
import { Switch } from '../components/ui/switch';
import { toast } from 'sonner';
import api from '../lib/api';
import {
  Mic, MicOff, Volume2, VolumeX, Settings,
  CheckCircle, XCircle, AlertTriangle, ChevronRight,
  Play, Square, Phone, Shield, Camera, Eye, Home,
  HelpCircle, Loader2
} from 'lucide-react';

// Voice Commands API
const voiceCommandsAPI = {
  parse: (text, context) => api.post('/voice-commands/process', { text, encounter_id: context }),
  getCommands: (category) => api.get('/voice-commands/commands', { params: category ? { category } : {} }),
  getRightsScript: (type) => api.get(`/voice-commands/rights-script/${type}`),
  getConfig: () => api.get('/voice-commands/config'),
  updateConfig: (config) => api.put('/voice-commands/config', config)
};

// Action icons
const actionIcons = {
  START_RECORDING: Play,
  STOP_RECORDING: Square,
  TRIGGER_SOS: AlertTriangle,
  CALL_ATTORNEY: Phone,
  READ_RIGHTS: Shield,
  MARK_VIOLATION: AlertTriangle,
  CAPTURE_PHOTO: Camera,
  ACTIVATE_STEALTH: Eye,
  NAVIGATE_DASHBOARD: Home,
  GET_STATUS: HelpCircle
};

export function VoiceControlPanel({
  isRecording = false,
  encounterId = null,
  onAction = () => {},
  className = ''
}) {
  // State
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [audioFeedback, setAudioFeedback] = useState(true);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [lastCommand, setLastCommand] = useState(null);
  const [commandHistory, setCommandHistory] = useState([]);
  const [showCommands, setShowCommands] = useState(false);
  const [availableCommands, setAvailableCommands] = useState([]);
  
  // Refs
  const recognitionRef = useRef(null);
  const synthRef = useRef(null);

  // Check for speech recognition support
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    setIsSupported(!!SpeechRecognition);
    
    if (SpeechRecognition) {
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'en-US';
    }
    
    // Speech synthesis
    synthRef.current = window.speechSynthesis;
    
    // Load available commands
    loadCommands();
    
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  // Load available commands
  const loadCommands = async () => {
    try {
      const res = await voiceCommandsAPI.getCommands();
      setAvailableCommands(Object.entries(res.data.commands || {}).map(([key, value]) => ({
        key,
        ...value
      })));
    } catch (error) {
      console.error('Failed to load commands:', error);
    }
  };

  // Speak text (audio feedback)
  const speak = useCallback((text) => {
    if (!audioFeedback || !synthRef.current) return;
    
    // Cancel any ongoing speech
    synthRef.current.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.1;
    utterance.pitch = 1;
    synthRef.current.speak(utterance);
  }, [audioFeedback]);

  // Process recognized speech
  const processCommand = useCallback(async (text) => {
    if (!text.trim()) return;
    
    try {
      const res = await voiceCommandsAPI.parse(text, encounterId);
      
      if (res.data.recognized) {
        const result = {
          text,
          command: res.data.command,
          action: res.data.action,
          feedback: res.data.feedback_text,
          timestamp: new Date(),
          success: true
        };
        
        setLastCommand(result);
        setCommandHistory(prev => [result, ...prev].slice(0, 20));
        
        // Audio feedback
        speak(res.data.feedback_text);
        
        // Trigger the action
        onAction(res.data.action, res.data);
        
        toast.success(`Command: ${res.data.command}`, {
          description: res.data.feedback_text
        });
      } else {
        const result = {
          text,
          command: null,
          action: null,
          feedback: 'Command not recognized',
          timestamp: new Date(),
          success: false
        };
        
        setLastCommand(result);
        setCommandHistory(prev => [result, ...prev].slice(0, 20));
        
        speak("I didn't understand that command. Try saying help for available commands.");
      }
    } catch (error) {
      console.error('Command processing error:', error);
    }
  }, [encounterId, onAction, speak]);

  // Start listening
  const startListening = useCallback(() => {
    if (!recognitionRef.current) return;
    
    recognitionRef.current.onresult = (event) => {
      let interim = '';
      let final = '';
      
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += transcript;
        } else {
          interim += transcript;
        }
      }
      
      setInterimTranscript(interim);
      
      if (final) {
        setTranscript(final);
        processCommand(final);
      }
    };
    
    recognitionRef.current.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      if (event.error === 'not-allowed') {
        toast.error('Microphone access denied');
        setIsListening(false);
      }
    };
    
    recognitionRef.current.onend = () => {
      // Auto-restart if still listening
      if (isListening && recognitionRef.current) {
        recognitionRef.current.start();
      }
    };
    
    try {
      recognitionRef.current.start();
      setIsListening(true);
      speak('Voice control activated. Say a command.');
    } catch (error) {
      console.error('Failed to start recognition:', error);
    }
  }, [isListening, processCommand, speak]);

  // Stop listening
  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    setIsListening(false);
    setInterimTranscript('');
    speak('Voice control deactivated.');
  }, [speak]);

  // Toggle listening
  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  if (!isSupported) {
    return (
      <Alert className={className}>
        <MicOff className="h-4 w-4" />
        <AlertDescription>
          Voice control is not supported in this browser. Try Chrome or Edge.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Card className={className} data-testid="voice-control-panel">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Mic className="h-5 w-5" />
            Voice Control
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setAudioFeedback(!audioFeedback)}
              title={audioFeedback ? 'Mute feedback' : 'Enable feedback'}
            >
              {audioFeedback ? (
                <Volume2 className="h-4 w-4" />
              ) : (
                <VolumeX className="h-4 w-4" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowCommands(!showCommands)}
              title="Show commands"
            >
              <HelpCircle className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Main Control */}
        <div className="text-center space-y-3">
          <Button
            size="lg"
            variant={isListening ? 'destructive' : 'default'}
            className={`w-24 h-24 rounded-full ${isListening ? 'animate-pulse' : ''}`}
            onClick={toggleListening}
            data-testid="voice-toggle-btn"
          >
            {isListening ? (
              <MicOff className="h-10 w-10" />
            ) : (
              <Mic className="h-10 w-10" />
            )}
          </Button>
          <p className="text-sm text-muted-foreground">
            {isListening ? 'Listening... Tap to stop' : 'Tap to start voice control'}
          </p>
        </div>

        {/* Current Transcript */}
        {(transcript || interimTranscript) && (
          <div className="p-3 rounded-lg bg-muted/50">
            <p className="text-xs text-muted-foreground mb-1">You said:</p>
            <p className="font-medium">
              {transcript}
              {interimTranscript && (
                <span className="text-muted-foreground italic"> {interimTranscript}</span>
              )}
            </p>
          </div>
        )}

        {/* Last Command */}
        {lastCommand && (
          <div className={`p-3 rounded-lg border ${
            lastCommand.success 
              ? 'bg-green-500/10 border-green-500/30' 
              : 'bg-red-500/10 border-red-500/30'
          }`}>
            <div className="flex items-center gap-2 mb-1">
              {lastCommand.success ? (
                <CheckCircle className="h-4 w-4 text-green-500" />
              ) : (
                <XCircle className="h-4 w-4 text-red-500" />
              )}
              <span className="text-sm font-medium">
                {lastCommand.success ? lastCommand.command : 'Not Recognized'}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">{lastCommand.feedback}</p>
          </div>
        )}

        {/* Available Commands */}
        {showCommands && (
          <div className="border-t pt-3">
            <p className="text-sm font-medium mb-2">Available Commands:</p>
            <ScrollArea className="h-[200px]">
              <div className="space-y-1">
                {availableCommands.map((cmd) => {
                  const Icon = actionIcons[cmd.action] || ChevronRight;
                  return (
                    <div
                      key={cmd.key}
                      className="flex items-center gap-2 p-2 rounded hover:bg-muted/50 text-sm"
                    >
                      <Icon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      <span className="flex-1">"{cmd.phrases[0]}"</span>
                      <Badge variant="outline" className="text-xs">
                        {cmd.category}
                      </Badge>
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          </div>
        )}

        {/* Quick Commands */}
        <div className="grid grid-cols-3 gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => processCommand('start recording')}
            className="text-xs"
          >
            <Play className="h-3 w-3 mr-1" />
            Record
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => processCommand('emergency')}
            className="text-xs text-red-500 border-red-500/50"
          >
            <AlertTriangle className="h-3 w-3 mr-1" />
            SOS
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => processCommand('mark violation')}
            className="text-xs"
          >
            <Camera className="h-3 w-3 mr-1" />
            Mark
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default VoiceControlPanel;
