/**
 * useVoiceCommands Hook
 * Handles voice command recognition and execution during encounters
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { toast } from 'sonner';
import { voiceCommandsConfig, formatDuration } from '../pages/encounter/constants';

export function useVoiceCommands({
  isRecording,
  enabled = true,
  encounter,
  location,
  duration,
  isPaused,
  onMarkViolation,
  onCallAttorney,
  onSOS,
  onEndRecording,
  onPause,
  onResume,
  onShare,
  encounterAPI,
  sosAPI
}) {
  const [lastCommand, setLastCommand] = useState(null);
  const [feedback, setFeedback] = useState('');
  const recognitionRef = useRef(null);

  const handleCommand = useCallback(async (command) => {
    const commandLower = command.toLowerCase().trim();
    
    for (const vc of voiceCommandsConfig) {
      for (const phrase of vc.phrases) {
        if (commandLower.includes(phrase)) {
          setLastCommand(vc.action);
          setFeedback(vc.feedback);
          
          setTimeout(() => setFeedback(''), 3000);
          
          switch (vc.action) {
            case 'MARK_VIOLATION':
              if (onMarkViolation) {
                onMarkViolation({
                  timestamp: duration,
                  time: new Date().toISOString(),
                  note: 'Voice command: violation marked'
                });
              }
              toast.success('📍 Violation marked at ' + formatDuration(duration));
              
              if (encounter && encounterAPI) {
                try {
                  await encounterAPI.markViolation(encounter.encounter_id, duration, 'Voice command: violation marked');
                } catch (err) {
                  console.log('Could not persist mark:', err);
                }
              }
              break;
              
            case 'CALL_ATTORNEY':
              toast.info('📞 Contacting your attorney...', { duration: 5000 });
              if (onCallAttorney) onCallAttorney();
              break;
              
            case 'SOS':
              if (encounter && location && sosAPI) {
                try {
                  await sosAPI.create({
                    encounter_id: encounter.encounter_id,
                    latitude: location.latitude,
                    longitude: location.longitude,
                    message: 'VOICE COMMAND SOS - Immediate assistance needed'
                  });
                  toast.error('🚨 SOS ALERT SENT! Help is on the way.', { duration: 10000 });
                  if (onSOS) onSOS();
                } catch (err) {
                  toast.error('SOS sent to emergency contacts');
                }
              }
              break;
              
            case 'END_RECORDING':
              if (onEndRecording) onEndRecording();
              break;
              
            case 'PAUSE':
              if (!isPaused && onPause) {
                onPause();
                toast.info('⏸️ Recording paused');
              }
              break;
              
            case 'RESUME':
              if (isPaused && onResume) {
                onResume();
                toast.success('▶️ Recording resumed');
              }
              break;
              
            case 'SHARE':
              if (onShare) onShare();
              break;
              
            default:
              break;
          }
          return true;
        }
      }
    }
    return false;
  }, [encounter, location, duration, isPaused, onMarkViolation, onCallAttorney, onSOS, onEndRecording, onPause, onResume, onShare, encounterAPI, sosAPI]);

  useEffect(() => {
    if (!isRecording || !enabled) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
        recognitionRef.current = null;
      }
      return;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.log('Speech recognition not supported');
      return;
    }
    
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    
    recognition.onresult = (event) => {
      const last = event.results.length - 1;
      const transcript = event.results[last][0].transcript;
      console.log('Voice heard:', transcript);
      handleCommand(transcript);
    };
    
    recognition.onerror = (event) => {
      if (event.error !== 'no-speech') {
        console.log('Speech recognition error:', event.error);
      }
    };
    
    recognition.onend = () => {
      if (isRecording && enabled) {
        try {
          recognition.start();
        } catch (e) {
          // Already started
        }
      }
    };
    
    try {
      recognition.start();
      recognitionRef.current = recognition;
    } catch (e) {
      console.log('Could not start voice recognition');
    }
    
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
        recognitionRef.current = null;
      }
    };
  }, [isRecording, enabled, handleCommand]);

  return {
    lastCommand,
    feedback,
    isSupported: typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)
  };
}

export default useVoiceCommands;
