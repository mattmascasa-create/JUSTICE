/**
 * useRecording Hook - Bulletproof Recording System
 * 
 * Features:
 * - Local-first: All recordings saved to IndexedDB immediately
 * - Background uploads: Never blocks UI
 * - Auto-recovery: Resumes after crash or connection loss
 * - Quality options: Adjustable for device performance
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import evidenceStorage from '../services/evidenceStorage';
import uploadManager from '../services/uploadManager';
import { toast } from 'sonner';

// Quality presets
export const QUALITY_PRESETS = {
  maximum: {
    label: 'Maximum (Court Quality)',
    video: { width: 1920, height: 1080 },
    videoBitrate: 2500000, // 2.5 Mbps
    audioBitrate: 192000,
    chunkInterval: 5000, // 5 seconds
  },
  balanced: {
    label: 'Balanced (Recommended)',
    video: { width: 1280, height: 720 },
    videoBitrate: 1500000, // 1.5 Mbps
    audioBitrate: 128000,
    chunkInterval: 5000,
  },
  performance: {
    label: 'Performance (Older Devices)',
    video: { width: 854, height: 480 },
    videoBitrate: 800000, // 800 Kbps
    audioBitrate: 96000,
    chunkInterval: 5000,
  }
};

export function useRecording({ 
  encounterId, 
  onTranscription, 
  onError,
  quality = 'balanced',
  enableVideo = true,
  deferAnalysis = false 
}) {
  // State
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState(0);
  const [chunksSaved, setChunksSaved] = useState(0);
  const [chunksUploaded, setChunksUploaded] = useState(0);
  const [uploadProgress, setUploadProgress] = useState({ pending: 0, uploaded: 0 });
  const [error, setError] = useState(null);

  // Refs
  const streamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioRecorderRef = useRef(null);
  const timerRef = useRef(null);
  const videoChunkIndexRef = useRef(0);
  const audioChunkIndexRef = useRef(0);
  const videoPreviewRef = useRef(null);
  const qualityPreset = QUALITY_PRESETS[quality] || QUALITY_PRESETS.balanced;

  // Get supported MIME type
  const getSupportedMimeType = useCallback((isVideo) => {
    const types = isVideo
      ? ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm', 'video/mp4']
      : ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/wav'];
    
    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type;
      }
    }
    return '';
  }, []);

  // Subscribe to upload manager events
  useEffect(() => {
    const unsubscribe = uploadManager.subscribe((event, data) => {
      if (event === 'uploaded') {
        setChunksUploaded(prev => prev + 1);
      } else if (event === 'progress') {
        setUploadProgress({ pending: data.pending, uploaded: data.uploaded });
      } else if (event === 'transcription' && data.encounterId === encounterId) {
        if (onTranscription && !deferAnalysis) {
          onTranscription(data.transcription);
        }
      } else if (event === 'failed') {
        console.error('Chunk upload failed:', data);
      }
    });

    return unsubscribe;
  }, [encounterId, onTranscription, deferAnalysis]);

  // Duration timer
  useEffect(() => {
    if (isRecording && !isPaused) {
      timerRef.current = setInterval(() => {
        setDuration(prev => prev + 1);
      }, 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isRecording, isPaused]);

  // Save chunk to IndexedDB and queue for upload
  const saveAndQueueChunk = useCallback(async (blob, type, chunkIndex) => {
    if (!encounterId || blob.size === 0) return;

    try {
      // Save to IndexedDB first (local storage)
      const chunkId = await evidenceStorage.saveChunk(
        encounterId,
        blob,
        type,
        chunkIndex,
        { quality, deferAnalysis }
      );

      setChunksSaved(prev => prev + 1);

      // Queue for background upload
      const priority = type === 'audio' ? 'high' : 'normal'; // Prioritize audio for transcription
      await uploadManager.queueUpload(encounterId, chunkId, type, priority);

      console.log(`Recording: ${type} chunk ${chunkIndex} saved and queued`);
    } catch (err) {
      console.error('Failed to save chunk:', err);
      setError(`Failed to save ${type} chunk`);
    }
  }, [encounterId, quality, deferAnalysis]);

  // Start recording
  const startRecording = useCallback(async (videoPreview) => {
    if (!encounterId) {
      setError('No encounter ID provided');
      return false;
    }

    try {
      setError(null);
      videoPreviewRef.current = videoPreview;

      // Save encounter metadata to IndexedDB
      await evidenceStorage.saveEncounter(encounterId, {
        quality,
        enableVideo,
        deferAnalysis,
        startedAt: Date.now()
      });

      // Request media permissions
      const mediaConstraints = {
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 44100
        },
        video: enableVideo ? {
          facingMode: { ideal: 'environment' },
          width: { ideal: qualityPreset.video.width },
          height: { ideal: qualityPreset.video.height }
        } : false
      };

      const stream = await navigator.mediaDevices.getUserMedia(mediaConstraints);
      streamRef.current = stream;

      // Set up video preview
      if (enableVideo && videoPreview) {
        videoPreview.srcObject = stream;
        try {
          await videoPreview.play();
        } catch (e) {
          console.log('Video autoplay blocked');
        }
      }

      // Create main media recorder
      const mimeType = getSupportedMimeType(enableVideo);
      const recorderOptions = {
        mimeType: mimeType || undefined,
        videoBitsPerSecond: enableVideo ? qualityPreset.videoBitrate : undefined,
        audioBitsPerSecond: qualityPreset.audioBitrate
      };

      let mediaRecorder;
      try {
        mediaRecorder = new MediaRecorder(stream, recorderOptions);
      } catch (e) {
        console.warn('MediaRecorder with options failed, using default');
        mediaRecorder = new MediaRecorder(stream);
      }
      mediaRecorderRef.current = mediaRecorder;

      // Handle data from main recorder (video or audio-only)
      mediaRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0) {
          const type = enableVideo ? 'video' : 'audio';
          const index = enableVideo ? videoChunkIndexRef.current++ : audioChunkIndexRef.current++;
          await saveAndQueueChunk(event.data, type, index);
        }
      };

      mediaRecorder.onerror = (e) => {
        console.error('MediaRecorder error:', e);
        setError('Recording error occurred');
        if (onError) onError(e);
      };

      // If video is enabled, create separate audio recorder for transcription
      if (enableVideo) {
        const audioTracks = stream.getAudioTracks();
        if (audioTracks.length > 0) {
          const audioStream = new MediaStream(audioTracks);
          const audioMimeType = getSupportedMimeType(false);
          
          let audioRecorder;
          try {
            audioRecorder = new MediaRecorder(audioStream, {
              mimeType: audioMimeType || undefined,
              audioBitsPerSecond: qualityPreset.audioBitrate
            });
          } catch (e) {
            audioRecorder = new MediaRecorder(audioStream);
          }
          audioRecorderRef.current = audioRecorder;

          audioRecorder.ondataavailable = async (event) => {
            if (event.data.size > 0) {
              await saveAndQueueChunk(event.data, 'audio', audioChunkIndexRef.current++);
            }
          };

          // Start audio recorder with chunk interval
          audioRecorder.start(qualityPreset.chunkInterval);
        }
      }

      // Start main recorder
      mediaRecorder.start(qualityPreset.chunkInterval);

      setIsRecording(true);
      setIsPaused(false);
      setDuration(0);
      videoChunkIndexRef.current = 0;
      audioChunkIndexRef.current = 0;

      toast.success('🔴 Recording started - Evidence is being saved locally');
      return true;

    } catch (err) {
      console.error('Failed to start recording:', err);
      setError(err.message || 'Failed to start recording');
      if (onError) onError(err);
      
      if (err.name === 'NotAllowedError') {
        toast.error('Camera/microphone permission denied');
      } else if (err.name === 'NotFoundError') {
        toast.error('No camera/microphone found');
      } else {
        toast.error('Failed to start recording');
      }
      
      return false;
    }
  }, [encounterId, enableVideo, quality, qualityPreset, getSupportedMimeType, saveAndQueueChunk, onError, deferAnalysis]);

  // Pause recording
  const pauseRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.pause();
      if (audioRecorderRef.current) {
        audioRecorderRef.current.pause();
      }
      setIsPaused(true);
      toast.info('⏸️ Recording paused');
    }
  }, []);

  // Resume recording
  const resumeRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'paused') {
      mediaRecorderRef.current.resume();
      if (audioRecorderRef.current) {
        audioRecorderRef.current.resume();
      }
      setIsPaused(false);
      toast.success('▶️ Recording resumed');
    }
  }, []);

  // Stop recording
  const stopRecording = useCallback(async () => {
    return new Promise((resolve) => {
      const cleanup = () => {
        // Stop all tracks
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
        }

        // Clear preview
        if (videoPreviewRef.current) {
          videoPreviewRef.current.srcObject = null;
        }

        setIsRecording(false);
        setIsPaused(false);

        // Update encounter status
        if (encounterId) {
          evidenceStorage.updateEncounterStatus(encounterId, 'completed');
        }

        toast.success(`✅ Recording stopped - ${chunksSaved} chunks saved locally`);
        resolve({ chunksSaved, chunksUploaded, duration });
      };

      // Stop audio recorder first
      if (audioRecorderRef.current && audioRecorderRef.current.state !== 'inactive') {
        audioRecorderRef.current.stop();
      }

      // Stop main recorder
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.onstop = cleanup;
        mediaRecorderRef.current.stop();
      } else {
        cleanup();
      }
    });
  }, [encounterId, chunksSaved, chunksUploaded, duration]);

  // Get recording status
  const getStatus = useCallback(() => {
    return {
      isRecording,
      isPaused,
      duration,
      chunksSaved,
      chunksUploaded,
      pendingUploads: uploadProgress.pending,
      quality,
      error
    };
  }, [isRecording, isPaused, duration, chunksSaved, chunksUploaded, uploadProgress, quality, error]);

  return {
    // State
    isRecording,
    isPaused,
    duration,
    chunksSaved,
    chunksUploaded,
    uploadProgress,
    error,

    // Actions
    startRecording,
    pauseRecording,
    resumeRecording,
    stopRecording,
    getStatus,

    // Refs (for video preview)
    streamRef
  };
}

export default useRecording;
