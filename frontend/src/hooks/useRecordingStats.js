/**
 * useRecordingStats Hook
 * 
 * Optimized state management for recording statistics.
 * Uses refs internally and batches updates to reduce re-renders
 * that cause UI lag during encounter mode.
 */

import { useState, useRef, useCallback, useEffect } from 'react';

export function useRecordingStats(options = {}) {
  const {
    batchInterval = 1000,  // How often to sync ref values to state (ms)
    enabled = true
  } = options;

  // Internal refs for high-frequency updates (no re-renders)
  const statsRef = useRef({
    chunksSaved: 0,
    chunksUploaded: 0,
    videoChunkCount: 0,
    audioChunkCount: 0,
    bytesRecorded: 0,
    bytesUploaded: 0,
    lastUpdateTime: Date.now()
  });

  // External state (batched updates for UI)
  const [displayStats, setDisplayStats] = useState({
    chunksSaved: 0,
    chunksUploaded: 0,
    videoChunkCount: 0,
    audioChunkCount: 0,
    bytesRecorded: 0,
    bytesUploaded: 0
  });

  // Batch update timer ref
  const batchTimerRef = useRef(null);

  // Function to sync refs to state (called periodically)
  const syncToState = useCallback(() => {
    const current = statsRef.current;
    setDisplayStats({
      chunksSaved: current.chunksSaved,
      chunksUploaded: current.chunksUploaded,
      videoChunkCount: current.videoChunkCount,
      audioChunkCount: current.audioChunkCount,
      bytesRecorded: current.bytesRecorded,
      bytesUploaded: current.bytesUploaded
    });
  }, []);

  // Start batch update timer when enabled
  useEffect(() => {
    if (!enabled) return;

    batchTimerRef.current = setInterval(syncToState, batchInterval);
    
    return () => {
      if (batchTimerRef.current) {
        clearInterval(batchTimerRef.current);
      }
    };
  }, [enabled, batchInterval, syncToState]);

  // HIGH-FREQUENCY update functions (NO re-renders)
  const incrementChunksSaved = useCallback((byteSize = 0) => {
    statsRef.current.chunksSaved += 1;
    statsRef.current.bytesRecorded += byteSize;
  }, []);

  const incrementChunksUploaded = useCallback((byteSize = 0) => {
    statsRef.current.chunksUploaded += 1;
    statsRef.current.bytesUploaded += byteSize;
  }, []);

  const incrementVideoChunks = useCallback(() => {
    statsRef.current.videoChunkCount += 1;
  }, []);

  const incrementAudioChunks = useCallback(() => {
    statsRef.current.audioChunkCount += 1;
  }, []);

  // Reset all stats
  const resetStats = useCallback(() => {
    statsRef.current = {
      chunksSaved: 0,
      chunksUploaded: 0,
      videoChunkCount: 0,
      audioChunkCount: 0,
      bytesRecorded: 0,
      bytesUploaded: 0,
      lastUpdateTime: Date.now()
    };
    setDisplayStats({
      chunksSaved: 0,
      chunksUploaded: 0,
      videoChunkCount: 0,
      audioChunkCount: 0,
      bytesRecorded: 0,
      bytesUploaded: 0
    });
  }, []);

  // Get current stats (direct ref access for immediate reads)
  const getCurrentStats = useCallback(() => {
    return { ...statsRef.current };
  }, []);

  // Force immediate sync (for when recording stops)
  const forceSync = useCallback(() => {
    syncToState();
  }, [syncToState]);

  return {
    // Display values for UI (batched updates)
    stats: displayStats,
    
    // High-frequency incrementers (no re-renders)
    incrementChunksSaved,
    incrementChunksUploaded,
    incrementVideoChunks,
    incrementAudioChunks,
    
    // Utilities
    resetStats,
    getCurrentStats,
    forceSync
  };
}

export default useRecordingStats;
