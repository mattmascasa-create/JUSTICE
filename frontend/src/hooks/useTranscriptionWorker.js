/**
 * useTranscriptionWorker Hook
 * 
 * Manages the Web Worker for off-thread transcription processing.
 * Prevents UI lag during encounter recording.
 */

import { useEffect, useRef, useState, useCallback } from 'react';

export function useTranscriptionWorker(options = {}) {
  const {
    onResult = () => {},
    onViolationDetected = () => {},
    onError = () => {},
    enabled = true
  } = options;

  const workerRef = useRef(null);
  const [isReady, setIsReady] = useState(false);
  const [stats, setStats] = useState({ queueSize: 0, isProcessing: false });
  const pendingCallbacks = useRef(new Map());

  // Initialize worker
  useEffect(() => {
    if (!enabled) return;

    try {
      // Create worker
      workerRef.current = new Worker(
        new URL('../workers/transcriptionWorker.js', import.meta.url),
        { type: 'module' }
      );

      // Message handler
      workerRef.current.onmessage = (e) => {
        const { type, results, result, stats: workerStats, error } = e.data;

        switch (type) {
          case 'WORKER_READY':
            setIsReady(true);
            console.log('TranscriptionWorker: Ready');
            break;

          case 'BATCH_PROCESSED':
            results?.forEach(r => {
              onResult(r);
              // Check for violations
              if (r.potentialViolations?.length > 0) {
                r.potentialViolations.forEach(v => onViolationDetected(v, r));
              }
            });
            break;

          case 'IMMEDIATE_RESULT':
            if (result) {
              onResult(result);
              if (result.potentialViolations?.length > 0) {
                result.potentialViolations.forEach(v => onViolationDetected(v, result));
              }
            }
            break;

          case 'STATS':
            if (workerStats) setStats(workerStats);
            break;

          case 'ERROR':
            console.error('TranscriptionWorker error:', error);
            onError(error);
            break;

          default:
            break;
        }
      };

      workerRef.current.onerror = (error) => {
        console.error('TranscriptionWorker fatal error:', error);
        setIsReady(false);
        onError(error.message);
      };

    } catch (error) {
      console.error('Failed to create TranscriptionWorker:', error);
      setIsReady(false);
    }

    return () => {
      if (workerRef.current) {
        workerRef.current.terminate();
        workerRef.current = null;
        setIsReady(false);
      }
    };
  }, [enabled, onResult, onViolationDetected, onError]);

  /**
   * Add transcription to processing queue (non-blocking)
   */
  const addTranscription = useCallback((text, timestamp, chunkIndex) => {
    if (!workerRef.current || !isReady) {
      // Fallback: process inline if worker not available
      return;
    }

    workerRef.current.postMessage({
      type: 'ADD_TRANSCRIPTION',
      data: { text, timestamp, chunkIndex }
    });
  }, [isReady]);

  /**
   * Process transcription immediately (for critical items)
   */
  const processImmediate = useCallback((text, timestamp, chunkIndex) => {
    if (!workerRef.current || !isReady) return;

    workerRef.current.postMessage({
      type: 'PROCESS_IMMEDIATE',
      data: { text, timestamp, chunkIndex }
    });
  }, [isReady]);

  /**
   * Get current processing stats
   */
  const getStats = useCallback(() => {
    if (!workerRef.current || !isReady) return;
    workerRef.current.postMessage({ type: 'GET_STATS' });
  }, [isReady]);

  /**
   * Clear the processing queue
   */
  const clearQueue = useCallback(() => {
    if (!workerRef.current || !isReady) return;
    workerRef.current.postMessage({ type: 'CLEAR_QUEUE' });
  }, [isReady]);

  return {
    isReady,
    stats,
    addTranscription,
    processImmediate,
    getStats,
    clearQueue
  };
}

export default useTranscriptionWorker;
