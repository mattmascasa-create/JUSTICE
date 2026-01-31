/**
 * usePreRecordingBuffer Hook
 * 
 * Manages the pre-recording buffer that captures the last 30 seconds
 * of audio/video continuously in the background.
 */

import { useState, useEffect, useCallback } from 'react';
import preRecordingBuffer from '../services/preRecordingBuffer';

export function usePreRecordingBuffer(autoStart = false, options = {}) {
  const [isActive, setIsActive] = useState(false);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const [hasPermission, setHasPermission] = useState(false);

  // Start the buffer
  const start = useCallback(async (opts = {}) => {
    const mergedOptions = { ...options, ...opts };
    const success = await preRecordingBuffer.start(mergedOptions);
    
    if (success) {
      setIsActive(true);
      setHasPermission(true);
      setError(null);
    } else {
      setError('Failed to start pre-recording buffer');
    }
    
    return success;
  }, [options]);

  // Stop the buffer
  const stop = useCallback(() => {
    preRecordingBuffer.stop();
    setIsActive(false);
  }, []);

  // Get the buffer content
  const getBuffer = useCallback(async () => {
    return await preRecordingBuffer.getBuffer();
  }, []);

  // Get buffer and clear it
  const getBufferAndClear = useCallback(async () => {
    return await preRecordingBuffer.getBufferAndClear();
  }, []);

  // Get current stream
  const getStream = useCallback(() => {
    return preRecordingBuffer.getStream();
  }, []);

  // Subscribe to status changes
  useEffect(() => {
    preRecordingBuffer.onStatus((status, err, newStats) => {
      setIsActive(status === 'active');
      setStats(newStats);
      if (err) setError(err);
    });

    // Auto-start if requested
    if (autoStart && !preRecordingBuffer.isActive) {
      start();
    }

    // Update initial state
    setIsActive(preRecordingBuffer.isActive);
    setHasPermission(preRecordingBuffer.hasPermission);
    setStats(preRecordingBuffer.getStats());

    return () => {
      // Don't stop on unmount - keep buffer running
    };
  }, [autoStart, start]);

  // Periodic stats update
  useEffect(() => {
    if (!isActive) return;

    const interval = setInterval(() => {
      setStats(preRecordingBuffer.getStats());
    }, 1000);

    return () => clearInterval(interval);
  }, [isActive]);

  return {
    isActive,
    stats,
    error,
    hasPermission,
    start,
    stop,
    getBuffer,
    getBufferAndClear,
    getStream,
    isSupported: preRecordingBuffer.constructor.isSupported()
  };
}

export default usePreRecordingBuffer;
