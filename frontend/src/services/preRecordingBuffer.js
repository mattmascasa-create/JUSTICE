/**
 * Pre-Recording Buffer Service
 * 
 * Maintains a circular buffer of the last 30 seconds of audio/video
 * so users never miss the start of an encounter.
 * 
 * Usage:
 *   preRecordingBuffer.start() - Start silent background recording
 *   preRecordingBuffer.getBuffer() - Get last 30 seconds as Blob
 *   preRecordingBuffer.stop() - Stop and cleanup
 */

const BUFFER_DURATION_MS = 30000; // 30 seconds
const CHUNK_INTERVAL_MS = 1000;   // 1 second chunks for smooth buffer

class PreRecordingBuffer {
  constructor() {
    this.isActive = false;
    this.stream = null;
    this.mediaRecorder = null;
    this.chunks = [];
    this.maxChunks = Math.ceil(BUFFER_DURATION_MS / CHUNK_INTERVAL_MS);
    this.hasPermission = false;
    this.enableVideo = false;
    this.onStatusChange = null;
  }

  /**
   * Request permissions and start background recording
   */
  async start(options = {}) {
    if (this.isActive) {
      console.log('PreRecordingBuffer: Already active');
      return true;
    }

    this.enableVideo = options.video || false;

    try {
      // Request media permissions
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        },
        video: this.enableVideo ? {
          facingMode: { ideal: 'environment' },
          width: { ideal: 640 },  // Lower resolution for buffer
          height: { ideal: 480 }
        } : false
      });

      this.hasPermission = true;

      // Determine mime type
      const mimeType = this.enableVideo
        ? (MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus') ? 'video/webm;codecs=vp8,opus' : 'video/webm')
        : (MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm');

      this.mediaRecorder = new MediaRecorder(this.stream, { 
        mimeType,
        videoBitsPerSecond: this.enableVideo ? 500000 : undefined, // Low bitrate for buffer
        audioBitsPerSecond: 64000
      });

      this.chunks = [];

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.chunks.push({
            data: event.data,
            timestamp: Date.now()
          });
          
          // Keep only last N chunks (circular buffer)
          while (this.chunks.length > this.maxChunks) {
            this.chunks.shift();
          }
        }
      };

      this.mediaRecorder.onerror = (error) => {
        console.error('PreRecordingBuffer: MediaRecorder error', error);
        this.stop();
      };

      this.mediaRecorder.start(CHUNK_INTERVAL_MS);
      this.isActive = true;
      
      console.log(`PreRecordingBuffer: Started (${this.enableVideo ? 'video+audio' : 'audio only'})`);
      this.notifyStatusChange('active');
      
      return true;
    } catch (error) {
      console.error('PreRecordingBuffer: Failed to start', error);
      this.hasPermission = false;
      this.notifyStatusChange('error', error.message);
      return false;
    }
  }

  /**
   * Get the buffered media as a single Blob
   */
  async getBuffer() {
    if (this.chunks.length === 0) {
      return null;
    }

    // Combine all chunks into single blob
    const blobs = this.chunks.map(c => c.data);
    const mimeType = this.chunks[0].data.type;
    const combinedBlob = new Blob(blobs, { type: mimeType });

    // Calculate actual duration
    const oldestTimestamp = this.chunks[0].timestamp;
    const newestTimestamp = this.chunks[this.chunks.length - 1].timestamp;
    const durationMs = newestTimestamp - oldestTimestamp;

    return {
      blob: combinedBlob,
      duration: durationMs,
      chunkCount: this.chunks.length,
      mimeType,
      startTime: new Date(oldestTimestamp).toISOString(),
      endTime: new Date(newestTimestamp).toISOString()
    };
  }

  /**
   * Get buffer and clear it (for starting actual recording)
   */
  async getBufferAndClear() {
    const buffer = await this.getBuffer();
    this.chunks = []; // Clear after getting
    return buffer;
  }

  /**
   * Stop the background recording
   */
  stop() {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }

    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }

    this.mediaRecorder = null;
    this.chunks = [];
    this.isActive = false;
    
    console.log('PreRecordingBuffer: Stopped');
    this.notifyStatusChange('inactive');
  }

  /**
   * Pause the buffer (keeps stream but stops recording)
   */
  pause() {
    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
      this.mediaRecorder.pause();
      this.notifyStatusChange('paused');
    }
  }

  /**
   * Resume the buffer
   */
  resume() {
    if (this.mediaRecorder && this.mediaRecorder.state === 'paused') {
      this.mediaRecorder.resume();
      this.notifyStatusChange('active');
    }
  }

  /**
   * Get the current stream (for preview or to hand off to main recorder)
   */
  getStream() {
    return this.stream;
  }

  /**
   * Get buffer statistics
   */
  getStats() {
    const totalSize = this.chunks.reduce((sum, c) => sum + c.data.size, 0);
    const durationSec = this.chunks.length > 1
      ? (this.chunks[this.chunks.length - 1].timestamp - this.chunks[0].timestamp) / 1000
      : 0;

    return {
      isActive: this.isActive,
      hasPermission: this.hasPermission,
      chunkCount: this.chunks.length,
      totalSizeBytes: totalSize,
      totalSizeMB: (totalSize / (1024 * 1024)).toFixed(2),
      durationSeconds: Math.round(durationSec),
      maxDurationSeconds: BUFFER_DURATION_MS / 1000,
      enableVideo: this.enableVideo
    };
  }

  /**
   * Subscribe to status changes
   */
  onStatus(callback) {
    this.onStatusChange = callback;
  }

  notifyStatusChange(status, error = null) {
    if (this.onStatusChange) {
      this.onStatusChange(status, error, this.getStats());
    }
  }

  /**
   * Check if browser supports required features
   */
  static isSupported() {
    return !!(
      navigator.mediaDevices &&
      navigator.mediaDevices.getUserMedia &&
      window.MediaRecorder
    );
  }
}

// Singleton instance
const preRecordingBuffer = new PreRecordingBuffer();

export default preRecordingBuffer;
export { PreRecordingBuffer, BUFFER_DURATION_MS };
