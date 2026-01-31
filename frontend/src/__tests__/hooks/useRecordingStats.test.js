/**
 * Tests for useRecordingStats Hook
 * 
 * This hook manages recording statistics with batched updates
 * to prevent UI lag during high-frequency recording operations.
 */

import { renderHook, act } from '@testing-library/react';
import { useRecordingStats } from '../../hooks/useRecordingStats';

describe('useRecordingStats', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should initialize with zero stats', () => {
    const { result } = renderHook(() => useRecordingStats());
    
    expect(result.current.stats).toEqual({
      chunksSaved: 0,
      chunksUploaded: 0,
      videoChunkCount: 0,
      audioChunkCount: 0,
      bytesRecorded: 0,
      bytesUploaded: 0
    });
  });

  it('should increment chunks saved without immediate re-render', () => {
    const { result } = renderHook(() => useRecordingStats({ batchInterval: 1000 }));
    
    // Increment multiple times rapidly
    act(() => {
      result.current.incrementChunksSaved(1024);
      result.current.incrementChunksSaved(2048);
      result.current.incrementChunksSaved(512);
    });

    // Stats should not update immediately (still batched)
    expect(result.current.stats.chunksSaved).toBe(0);
    
    // After batch interval, stats should sync
    act(() => {
      jest.advanceTimersByTime(1000);
    });
    
    expect(result.current.stats.chunksSaved).toBe(3);
    expect(result.current.stats.bytesRecorded).toBe(3584);
  });

  it('should increment chunks uploaded correctly', () => {
    const { result } = renderHook(() => useRecordingStats({ batchInterval: 500 }));
    
    act(() => {
      result.current.incrementChunksUploaded(1000);
      result.current.incrementChunksUploaded(2000);
    });
    
    act(() => {
      jest.advanceTimersByTime(500);
    });
    
    expect(result.current.stats.chunksUploaded).toBe(2);
    expect(result.current.stats.bytesUploaded).toBe(3000);
  });

  it('should track video and audio chunks separately', () => {
    const { result } = renderHook(() => useRecordingStats({ batchInterval: 100 }));
    
    act(() => {
      result.current.incrementVideoChunks();
      result.current.incrementVideoChunks();
      result.current.incrementAudioChunks();
      result.current.incrementAudioChunks();
      result.current.incrementAudioChunks();
    });
    
    act(() => {
      jest.advanceTimersByTime(100);
    });
    
    expect(result.current.stats.videoChunkCount).toBe(2);
    expect(result.current.stats.audioChunkCount).toBe(3);
  });

  it('should reset all stats correctly', () => {
    const { result } = renderHook(() => useRecordingStats({ batchInterval: 100 }));
    
    // Add some data
    act(() => {
      result.current.incrementChunksSaved(1000);
      result.current.incrementChunksUploaded(500);
      result.current.incrementVideoChunks();
    });
    
    act(() => {
      jest.advanceTimersByTime(100);
    });
    
    // Verify data exists
    expect(result.current.stats.chunksSaved).toBe(1);
    
    // Reset
    act(() => {
      result.current.resetStats();
    });
    
    // Verify reset
    expect(result.current.stats).toEqual({
      chunksSaved: 0,
      chunksUploaded: 0,
      videoChunkCount: 0,
      audioChunkCount: 0,
      bytesRecorded: 0,
      bytesUploaded: 0
    });
  });

  it('should force sync immediately when requested', () => {
    const { result } = renderHook(() => useRecordingStats({ batchInterval: 10000 }));
    
    act(() => {
      result.current.incrementChunksSaved(500);
      result.current.incrementChunksSaved(500);
    });
    
    // Without force sync, stats remain at 0
    expect(result.current.stats.chunksSaved).toBe(0);
    
    // Force sync
    act(() => {
      result.current.forceSync();
    });
    
    // Now stats should be updated
    expect(result.current.stats.chunksSaved).toBe(2);
  });

  it('should return current stats via getCurrentStats', () => {
    const { result } = renderHook(() => useRecordingStats({ batchInterval: 10000 }));
    
    act(() => {
      result.current.incrementChunksSaved(100);
      result.current.incrementChunksUploaded(50);
    });
    
    // getCurrentStats should return immediate values (not batched)
    const currentStats = result.current.getCurrentStats();
    expect(currentStats.chunksSaved).toBe(1);
    expect(currentStats.chunksUploaded).toBe(1);
  });

  it('should not start timer when disabled', () => {
    const { result } = renderHook(() => useRecordingStats({ enabled: false }));
    
    act(() => {
      result.current.incrementChunksSaved(100);
    });
    
    act(() => {
      jest.advanceTimersByTime(5000);
    });
    
    // Stats should remain at 0 since batching is disabled
    expect(result.current.stats.chunksSaved).toBe(0);
  });

  it('should handle rapid increments efficiently', () => {
    const { result } = renderHook(() => useRecordingStats({ batchInterval: 1000 }));
    
    // Simulate 100 rapid chunk saves (like during recording)
    act(() => {
      for (let i = 0; i < 100; i++) {
        result.current.incrementChunksSaved(1024);
      }
    });
    
    // Stats should still be 0 (batched)
    expect(result.current.stats.chunksSaved).toBe(0);
    
    // After batch interval
    act(() => {
      jest.advanceTimersByTime(1000);
    });
    
    // All 100 increments should be reflected
    expect(result.current.stats.chunksSaved).toBe(100);
    expect(result.current.stats.bytesRecorded).toBe(102400);
  });
});
