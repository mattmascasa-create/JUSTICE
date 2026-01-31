/**
 * Tests for usePreRecordingBuffer Hook
 * 
 * This hook manages the pre-recording buffer that captures
 * the last 30 seconds of audio/video before the user starts recording.
 */

import { renderHook, act, waitFor } from '@testing-library/react';

// Mock the preRecordingBuffer service
const mockPreRecordingBuffer = {
  start: jest.fn().mockResolvedValue(true),
  stop: jest.fn(),
  getBuffer: jest.fn().mockResolvedValue({ audio: [], video: [] }),
  getBufferAndClear: jest.fn().mockResolvedValue({ audio: [], video: [] }),
  getStream: jest.fn().mockReturnValue(null),
  getStats: jest.fn().mockReturnValue({
    bufferDuration: 0,
    chunkCount: 0,
    isCapturing: false
  }),
  onStatus: jest.fn(),
  isActive: false,
  hasPermission: false,
  constructor: {
    isSupported: jest.fn().mockReturnValue(true)
  }
};

jest.mock('../../services/preRecordingBuffer', () => mockPreRecordingBuffer);

// Import after mocking
import { usePreRecordingBuffer } from '../../hooks/usePreRecordingBuffer';

describe('usePreRecordingBuffer', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockPreRecordingBuffer.isActive = false;
    mockPreRecordingBuffer.hasPermission = false;
  });

  it('should initialize with inactive state', () => {
    const { result } = renderHook(() => usePreRecordingBuffer());
    
    expect(result.current.isActive).toBe(false);
    expect(result.current.hasPermission).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should check if pre-recording is supported', () => {
    const { result } = renderHook(() => usePreRecordingBuffer());
    
    expect(result.current.isSupported).toBe(true);
  });

  it('should start the buffer successfully', async () => {
    const { result } = renderHook(() => usePreRecordingBuffer());
    
    let success;
    await act(async () => {
      success = await result.current.start();
    });
    
    expect(success).toBe(true);
    expect(mockPreRecordingBuffer.start).toHaveBeenCalled();
  });

  it('should handle start failure', async () => {
    mockPreRecordingBuffer.start.mockResolvedValueOnce(false);
    
    const { result } = renderHook(() => usePreRecordingBuffer());
    
    await act(async () => {
      await result.current.start();
    });
    
    expect(result.current.error).toBe('Failed to start pre-recording buffer');
  });

  it('should stop the buffer', () => {
    const { result } = renderHook(() => usePreRecordingBuffer());
    
    act(() => {
      result.current.stop();
    });
    
    expect(mockPreRecordingBuffer.stop).toHaveBeenCalled();
  });

  it('should get buffer contents', async () => {
    const mockBufferData = {
      audio: [new Blob(['audio data'])],
      video: [new Blob(['video data'])]
    };
    mockPreRecordingBuffer.getBuffer.mockResolvedValueOnce(mockBufferData);
    
    const { result } = renderHook(() => usePreRecordingBuffer());
    
    let buffer;
    await act(async () => {
      buffer = await result.current.getBuffer();
    });
    
    expect(buffer).toEqual(mockBufferData);
    expect(mockPreRecordingBuffer.getBuffer).toHaveBeenCalled();
  });

  it('should get buffer and clear', async () => {
    const mockBufferData = {
      audio: [new Blob(['audio'])],
      video: []
    };
    mockPreRecordingBuffer.getBufferAndClear.mockResolvedValueOnce(mockBufferData);
    
    const { result } = renderHook(() => usePreRecordingBuffer());
    
    let buffer;
    await act(async () => {
      buffer = await result.current.getBufferAndClear();
    });
    
    expect(buffer).toEqual(mockBufferData);
    expect(mockPreRecordingBuffer.getBufferAndClear).toHaveBeenCalled();
  });

  it('should get the media stream', () => {
    const mockStream = { id: 'test-stream' };
    mockPreRecordingBuffer.getStream.mockReturnValue(mockStream);
    
    const { result } = renderHook(() => usePreRecordingBuffer());
    
    const stream = result.current.getStream();
    
    expect(stream).toEqual(mockStream);
  });

  it('should auto-start when autoStart is true', () => {
    mockPreRecordingBuffer.isActive = false;
    
    renderHook(() => usePreRecordingBuffer(true));
    
    // Start should be called due to autoStart
    expect(mockPreRecordingBuffer.start).toHaveBeenCalled();
  });

  it('should subscribe to status changes', () => {
    renderHook(() => usePreRecordingBuffer());
    
    expect(mockPreRecordingBuffer.onStatus).toHaveBeenCalled();
  });

  it('should pass options to start', async () => {
    const options = { bufferDuration: 60000, captureVideo: true };
    
    const { result } = renderHook(() => usePreRecordingBuffer(false, options));
    
    await act(async () => {
      await result.current.start({ quality: 'high' });
    });
    
    expect(mockPreRecordingBuffer.start).toHaveBeenCalledWith({
      bufferDuration: 60000,
      captureVideo: true,
      quality: 'high'
    });
  });
});
