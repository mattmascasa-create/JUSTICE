/**
 * useEncounterRecording Hook
 * 
 * Manages the core recording functionality for encounter mode,
 * including media streams, recorders, and local storage.
 * 
 * Extracted from EncounterPage to improve maintainability.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { toast } from 'sonner';
import evidenceStorage from '../services/evidenceStorage';
import uploadManager from '../services/uploadManager';
import preRecordingBuffer from '../services/preRecordingBuffer';
import browserSpeechRecognition from '../services/browserSpeechRecognition';
import { useRecordingStats } from './useRecordingStats';
import { encounterAPI } from '../lib/api';

export function useEncounterRecording(options = {}) {
  const {
    enableVideo = true,
    recordingQuality = 'balanced',
    deferAnalysis = false,
    useBrowserTranscription = true,
    onTranscription,
    onViolation,
    onAnalysisResult,
    location
  } = options;

  // Core state
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [encounter, setEncounter] = useState(null);
  const [duration, setDuration] = useState(0);
  
  // Pre-buffer state
  const [preBufferIncluded, setPreBufferIncluded] = useState(false);
  
  // Browser speech recognition
  const [interimTranscript, setInterimTranscript] = useState('');
  
  // Check browser speech recognition support (computed once, not reactive)
  const browserTranscriptSupported = typeof window !== 'undefined' && 
    browserSpeechRecognition.isSupported();

  // Refs
  const mediaRecorderRef = useRef(null);
  const audioRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const videoPreviewRef = useRef(null);
  const chunkIndexRef = useRef(0);
  const videoChunkIndexRef = useRef(0);
  const timerRef = useRef(null);

  // Recording stats (batched updates)
  const {
    stats: { chunksSaved, chunksUploaded, videoChunkCount },
    incrementChunksSaved,
    incrementChunksUploaded,
    incrementVideoChunks,
    resetStats: resetRecordingStats,
    forceSync: forceStatsSync
  } = useRecordingStats({
    batchInterval: 1000,
    enabled: isRecording
  });

  // Duration timer
  useEffect(() => {
    if (isRecording && !isPaused) {
      timerRef.current = setInterval(() => {
        setDuration(prev => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isRecording, isPaused]);

  // Check browser speech recognition support
  useEffect(() => {
    const supported = browserSpeechRecognition.isSupported();
    setBrowserTranscriptSupported(supported);
  }, []);

  // Upload manager subscription
  useEffect(() => {
    const unsubscribe = uploadManager.subscribe((event, data) => {
      if (event === 'uploaded') {
        incrementChunksUploaded(data?.size || 0);
      } else if (event === 'transcription' && encounter && data.encounterId === encounter.encounter_id) {
        onTranscription?.(data.transcription);
      }
    });
    return () => unsubscribe();
  }, [encounter, incrementChunksUploaded, onTranscription]);

  const startRecording = useCallback(async (encounterType, broadcastMode) => {
    try {
      // Get quality settings
      const qualityPresets = {
        maximum: { video: { width: 1920, height: 1080, frameRate: 30 }, audio: { sampleRate: 48000 } },
        balanced: { video: { width: 1280, height: 720, frameRate: 24 }, audio: { sampleRate: 44100 } },
        performance: { video: { width: 854, height: 480, frameRate: 15 }, audio: { sampleRate: 22050 } }
      };
      
      const quality = qualityPresets[recordingQuality] || qualityPresets.balanced;
      
      const constraints = enableVideo
        ? { video: quality.video, audio: quality.audio }
        : { audio: quality.audio };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      
      if (videoPreviewRef.current) {
        videoPreviewRef.current.srcObject = stream;
      }

      // Create encounter
      const response = await encounterAPI.start({
        latitude: location?.latitude,
        longitude: location?.longitude,
        encounter_type: encounterType,
        broadcast_mode: broadcastMode
      });
      
      setEncounter(response.data);
      await evidenceStorage.saveEncounter(response.data.encounter_id, {
        type: encounterType,
        broadcastMode,
        quality: recordingQuality
      });

      // Capture pre-buffer
      if (preRecordingBuffer.isActive) {
        const preBuffer = await preRecordingBuffer.getBufferAndClear();
        if (preBuffer && preBuffer.blob.size > 0) {
          setPreBufferIncluded(true);
          evidenceStorage.saveChunk(response.data.encounter_id, preBuffer.blob, 'video', -1, { isPreBuffer: true })
            .then(() => {
              incrementChunksSaved(preBuffer.blob.size);
              toast.success(`📹 +${Math.round(preBuffer.duration / 1000)}s pre-buffer captured!`);
            })
            .catch(err => console.log('Pre-buffer save error:', err));
        }
      }

      // Start browser speech recognition
      if (useBrowserTranscription && browserTranscriptSupported) {
        browserSpeechRecognition.start({
          onResult: (transcript, isFinal) => {
            if (isFinal) {
              onTranscription?.({ text: transcript, timestamp: Date.now(), source: 'browser' });
              setInterimTranscript('');
            } else {
              setInterimTranscript(transcript);
            }
          },
          onError: (error) => console.log('Speech recognition error:', error)
        });
      }

      // Setup media recorder
      const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus') 
        ? 'video/webm;codecs=vp9,opus' 
        : 'video/webm';
      
      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          const type = enableVideo ? 'video' : 'audio';
          const chunkIndex = videoChunkIndexRef.current++;
          const encounterId = response.data.encounter_id;
          
          evidenceStorage.saveChunk(encounterId, event.data, type, chunkIndex)
            .then(chunkId => {
              incrementChunksSaved(event.data.size);
              incrementVideoChunks();
              uploadManager.queueUpload(encounterId, chunkId, type, 'normal');
            })
            .catch(err => console.error('Failed to save chunk:', err));
        }
      };

      // Setup audio recorder for transcription (if video enabled)
      if (enableVideo) {
        const audioStream = new MediaStream(stream.getAudioTracks());
        const audioRecorder = new MediaRecorder(audioStream, {
          mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm'
        });
        audioRecorderRef.current = audioRecorder;

        audioRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            const chunkIndex = chunkIndexRef.current++;
            const encounterId = response.data.encounter_id;
            
            evidenceStorage.saveChunk(encounterId, event.data, 'audio', chunkIndex, { forTranscription: true })
              .then(chunkId => {
                incrementChunksSaved(event.data.size);
                uploadManager.queueUpload(encounterId, chunkId, 'audio', 'high');
              })
              .catch(err => console.log('Audio save error:', err));
            
            if (navigator.onLine && !deferAnalysis) {
              encounterAPI.uploadAudio(encounterId, event.data, chunkIndex)
                .then(result => {
                  if (result.data?.transcription) {
                    onTranscription?.(result.data.transcription);
                  }
                })
                .catch(err => console.log('Transcription error:', err));
            }
          }
        };
        audioRecorder.start(5000);
      }

      mediaRecorder.start(5000);
      setIsRecording(true);
      setDuration(0);
      resetRecordingStats();
      
      toast.success('🔴 Recording Started - Evidence saved locally');
      return response.data;
    } catch (error) {
      console.error('Recording error:', error);
      toast.error(error.name === 'NotAllowedError' 
        ? 'Please allow camera/microphone access' 
        : 'Failed to start recording');
      throw error;
    }
  }, [
    enableVideo, recordingQuality, deferAnalysis, useBrowserTranscription, 
    browserTranscriptSupported, location, incrementChunksSaved, incrementVideoChunks,
    resetRecordingStats, onTranscription
  ]);

  const pauseRecording = useCallback(() => {
    if (!mediaRecorderRef.current || !isRecording) return;
    
    if (isPaused) {
      mediaRecorderRef.current.resume();
      audioRecorderRef.current?.resume();
      setIsPaused(false);
      toast.info('Recording resumed');
    } else {
      mediaRecorderRef.current.pause();
      audioRecorderRef.current?.pause();
      setIsPaused(true);
      toast.info('Recording paused');
    }
  }, [isRecording, isPaused]);

  const stopRecording = useCallback(async () => {
    const currentEncounterId = encounter?.encounter_id;
    
    browserSpeechRecognition.stop();
    setInterimTranscript('');
    
    if (mediaRecorderRef.current?.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (audioRecorderRef.current?.state !== 'inactive') {
      audioRecorderRef.current.stop();
    }
    
    streamRef.current?.getTracks().forEach(track => track.stop());
    if (videoPreviewRef.current) {
      videoPreviewRef.current.srcObject = null;
    }
    
    preRecordingBuffer.stop();
    preRecordingBuffer.start({ video: enableVideo });
    
    forceStatsSync();
    
    setIsRecording(false);
    setIsPaused(false);
    setPreBufferIncluded(false);
    
    if (currentEncounterId) {
      try {
        toast.info('Processing recording...');
        await encounterAPI.end(currentEncounterId);
        toast.success('Recording ended. Report generated!');
        return { success: true, encounterId: currentEncounterId };
      } catch (error) {
        toast.error('Recording saved. Navigate to encounters to view.');
        return { success: false, encounterId: currentEncounterId };
      }
    }
    return { success: false };
  }, [encounter, enableVideo, forceStatsSync]);

  return {
    // State
    isRecording,
    isPaused,
    encounter,
    duration,
    chunksSaved,
    chunksUploaded,
    videoChunkCount,
    preBufferIncluded,
    interimTranscript,
    browserTranscriptSupported,
    
    // Refs for external access
    videoPreviewRef,
    
    // Actions
    startRecording,
    pauseRecording,
    stopRecording,
    
    // Setters for external control
    setEncounter
  };
}

export default useEncounterRecording;
