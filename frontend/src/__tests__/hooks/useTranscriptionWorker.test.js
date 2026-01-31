/**
 * Tests for useTranscriptionWorker Hook
 * 
 * This hook manages the Web Worker for off-thread transcription processing
 * to prevent UI lag during encounter recording.
 */

import { renderHook, act } from '@testing-library/react';

// Mock Worker
class MockWorker {
  constructor() {
    this.onmessage = null;
    this.onerror = null;
    this.postMessage = jest.fn();
    this.terminate = jest.fn();
    
    // Simulate worker ready after construction
    setTimeout(() => {
      if (this.onmessage) {
        this.onmessage({ data: { type: 'WORKER_READY' } });
      }
    }, 0);
  }
}

// Store reference to mock for testing
let mockWorkerInstance = null;
global.Worker = jest.fn().mockImplementation((...args) => {
  mockWorkerInstance = new MockWorker(...args);
  return mockWorkerInstance;
});

// Import after mocking
import { useTranscriptionWorker } from '../../hooks/useTranscriptionWorker';

describe('useTranscriptionWorker', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockWorkerInstance = null;
  });

  it('should initialize and become ready', async () => {
    const { result } = renderHook(() => useTranscriptionWorker());
    
    // Wait for worker to be ready
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    expect(result.current.isReady).toBe(true);
  });

  it('should not create worker when disabled', () => {
    renderHook(() => useTranscriptionWorker({ enabled: false }));
    
    expect(global.Worker).not.toHaveBeenCalled();
  });

  it('should add transcription to queue', async () => {
    const { result } = renderHook(() => useTranscriptionWorker());
    
    // Wait for ready
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    act(() => {
      result.current.addTranscription('Hello world', 1000, 0);
    });
    
    expect(mockWorkerInstance.postMessage).toHaveBeenCalledWith({
      type: 'ADD_TRANSCRIPTION',
      data: { text: 'Hello world', timestamp: 1000, chunkIndex: 0 }
    });
  });

  it('should process transcription immediately when requested', async () => {
    const { result } = renderHook(() => useTranscriptionWorker());
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    act(() => {
      result.current.processImmediate('Urgent text', 2000, 1);
    });
    
    expect(mockWorkerInstance.postMessage).toHaveBeenCalledWith({
      type: 'PROCESS_IMMEDIATE',
      data: { text: 'Urgent text', timestamp: 2000, chunkIndex: 1 }
    });
  });

  it('should call onResult callback when results are received', async () => {
    const onResult = jest.fn();
    const { result } = renderHook(() => useTranscriptionWorker({ onResult }));
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    // Simulate worker sending batch results
    act(() => {
      mockWorkerInstance.onmessage({
        data: {
          type: 'BATCH_PROCESSED',
          results: [
            { text: 'Test 1', timestamp: 100, potentialViolations: [] },
            { text: 'Test 2', timestamp: 200, potentialViolations: [] }
          ]
        }
      });
    });
    
    expect(onResult).toHaveBeenCalledTimes(2);
  });

  it('should call onViolationDetected when violations found', async () => {
    const onViolationDetected = jest.fn();
    const { result } = renderHook(() => useTranscriptionWorker({ onViolationDetected }));
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    const violation = { type: 'Miranda Rights', severity: 'high' };
    const transcriptionResult = {
      text: 'You are under arrest',
      timestamp: 500,
      potentialViolations: [violation]
    };
    
    act(() => {
      mockWorkerInstance.onmessage({
        data: {
          type: 'BATCH_PROCESSED',
          results: [transcriptionResult]
        }
      });
    });
    
    expect(onViolationDetected).toHaveBeenCalledWith(violation, transcriptionResult);
  });

  it('should handle immediate results', async () => {
    const onResult = jest.fn();
    const { result } = renderHook(() => useTranscriptionWorker({ onResult }));
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    act(() => {
      mockWorkerInstance.onmessage({
        data: {
          type: 'IMMEDIATE_RESULT',
          result: { text: 'Immediate', timestamp: 300, potentialViolations: [] }
        }
      });
    });
    
    expect(onResult).toHaveBeenCalledWith({
      text: 'Immediate',
      timestamp: 300,
      potentialViolations: []
    });
  });

  it('should update stats when received from worker', async () => {
    const { result } = renderHook(() => useTranscriptionWorker());
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    act(() => {
      mockWorkerInstance.onmessage({
        data: {
          type: 'STATS',
          stats: { queueSize: 5, isProcessing: true }
        }
      });
    });
    
    expect(result.current.stats).toEqual({ queueSize: 5, isProcessing: true });
  });

  it('should call onError when worker reports error', async () => {
    const onError = jest.fn();
    const { result } = renderHook(() => useTranscriptionWorker({ onError }));
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    act(() => {
      mockWorkerInstance.onmessage({
        data: {
          type: 'ERROR',
          error: 'Processing failed'
        }
      });
    });
    
    expect(onError).toHaveBeenCalledWith('Processing failed');
  });

  it('should request stats from worker', async () => {
    const { result } = renderHook(() => useTranscriptionWorker());
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    act(() => {
      result.current.getStats();
    });
    
    expect(mockWorkerInstance.postMessage).toHaveBeenCalledWith({ type: 'GET_STATS' });
  });

  it('should clear queue when requested', async () => {
    const { result } = renderHook(() => useTranscriptionWorker());
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    act(() => {
      result.current.clearQueue();
    });
    
    expect(mockWorkerInstance.postMessage).toHaveBeenCalledWith({ type: 'CLEAR_QUEUE' });
  });

  it('should terminate worker on unmount', async () => {
    const { unmount } = renderHook(() => useTranscriptionWorker());
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    unmount();
    
    expect(mockWorkerInstance.terminate).toHaveBeenCalled();
  });

  it('should handle worker fatal error', async () => {
    const onError = jest.fn();
    const { result } = renderHook(() => useTranscriptionWorker({ onError }));
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    act(() => {
      mockWorkerInstance.onerror({ message: 'Worker crashed' });
    });
    
    expect(result.current.isReady).toBe(false);
    expect(onError).toHaveBeenCalledWith('Worker crashed');
  });

  it('should not post messages when worker not ready', () => {
    // Don't wait for ready
    const { result } = renderHook(() => useTranscriptionWorker());
    
    // Immediately try to add transcription before ready
    act(() => {
      result.current.addTranscription('Test', 100, 0);
    });
    
    // Should not have posted the ADD_TRANSCRIPTION message
    expect(mockWorkerInstance.postMessage).not.toHaveBeenCalledWith(
      expect.objectContaining({ type: 'ADD_TRANSCRIPTION' })
    );
  });
});
