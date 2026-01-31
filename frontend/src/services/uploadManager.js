/**
 * Upload Manager Service
 * Manages background uploads with retry logic and queue management
 * Runs uploads without blocking the UI
 */

import evidenceStorage from './evidenceStorage';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || '';

class UploadManager {
  constructor() {
    this.isProcessing = false;
    this.uploadQueue = [];
    this.listeners = new Set();
    this.maxRetries = 5;
    this.retryDelayMs = 2000;
    this.concurrentUploads = 2; // Process 2 uploads at a time
    this.activeUploads = 0;
    this.stats = {
      uploaded: 0,
      failed: 0,
      pending: 0,
      totalBytes: 0
    };
    
    // Start processing loop
    this.startProcessing();
    
    // Listen for online/offline
    window.addEventListener('online', () => this.onOnline());
    window.addEventListener('offline', () => this.onOffline());
  }

  // ============== Event Listeners ==============

  subscribe(callback) {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  notify(event, data) {
    this.listeners.forEach(cb => {
      try {
        cb(event, data);
      } catch (e) {
        console.error('UploadManager listener error:', e);
      }
    });
  }

  // ============== Queue Management ==============

  async queueUpload(encounterId, chunkId, type, priority = 'normal') {
    const item = {
      encounterId,
      chunkId,
      type,
      priority: priority === 'high' ? 1 : 2,
      queuedAt: Date.now()
    };
    
    this.uploadQueue.push(item);
    this.uploadQueue.sort((a, b) => a.priority - b.priority || a.queuedAt - b.queuedAt);
    
    this.stats.pending = this.uploadQueue.length;
    this.notify('queued', { chunkId, queueLength: this.uploadQueue.length });
    
    // Trigger processing
    this.processQueue();
  }

  async processQueue() {
    if (!navigator.onLine) {
      console.log('UploadManager: Offline, pausing uploads');
      return;
    }

    // Check if we can start more uploads
    while (this.activeUploads < this.concurrentUploads && this.uploadQueue.length > 0) {
      const item = this.uploadQueue.shift();
      this.activeUploads++;
      this.processUpload(item).finally(() => {
        this.activeUploads--;
        this.stats.pending = this.uploadQueue.length;
        this.notify('progress', this.stats);
        // Continue processing
        if (this.uploadQueue.length > 0) {
          this.processQueue();
        }
      });
    }
  }

  async processUpload(item) {
    const { encounterId, chunkId, type } = item;
    
    try {
      // Get chunk from IndexedDB
      const chunks = await evidenceStorage.getChunksForEncounter(encounterId);
      const chunk = chunks.find(c => c.id === chunkId);
      
      if (!chunk) {
        console.warn('UploadManager: Chunk not found in storage', chunkId);
        return;
      }
      
      if (chunk.uploaded) {
        console.log('UploadManager: Chunk already uploaded', chunkId);
        return;
      }
      
      // Increment attempt counter
      const attempts = await evidenceStorage.incrementUploadAttempts(chunkId);
      
      if (attempts > this.maxRetries) {
        console.error('UploadManager: Max retries exceeded for chunk', chunkId);
        this.stats.failed++;
        this.notify('failed', { chunkId, reason: 'max_retries' });
        return;
      }
      
      this.notify('uploading', { chunkId, type, attempt: attempts });
      
      // Perform upload
      const success = await this.uploadChunk(encounterId, chunk);
      
      if (success) {
        await evidenceStorage.markChunkUploaded(chunkId);
        this.stats.uploaded++;
        this.stats.totalBytes += chunk.size;
        this.notify('uploaded', { chunkId, type, size: chunk.size });
      } else {
        // Re-queue with delay
        setTimeout(() => {
          this.uploadQueue.push({ ...item, queuedAt: Date.now() });
          this.processQueue();
        }, this.retryDelayMs * attempts);
      }
      
    } catch (error) {
      console.error('UploadManager: Upload error', error);
      // Re-queue for retry
      setTimeout(() => {
        this.uploadQueue.push({ ...item, queuedAt: Date.now() });
        this.processQueue();
      }, this.retryDelayMs);
    }
  }

  async uploadChunk(encounterId, chunk) {
    const { type, blob, chunkIndex } = chunk;
    const token = localStorage.getItem('token');
    
    const formData = new FormData();
    const filename = type === 'video' 
      ? `video_chunk_${chunkIndex}.webm`
      : `audio_chunk_${chunkIndex}.webm`;
    
    formData.append('file', blob, filename);
    formData.append('chunk_index', chunkIndex.toString());
    
    const endpoint = type === 'video'
      ? `${API_BASE_URL}/api/encounters/${encounterId}/video`
      : `${API_BASE_URL}/api/encounters/${encounterId}/audio`;
    
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });
      
      if (!response.ok) {
        console.error('Upload failed:', response.status, await response.text());
        return false;
      }
      
      const result = await response.json();
      
      // Return transcription data if available (for audio)
      if (type === 'audio' && result.transcription) {
        this.notify('transcription', { 
          encounterId, 
          transcription: result.transcription 
        });
      }
      
      return true;
    } catch (error) {
      console.error('Upload fetch error:', error);
      return false;
    }
  }

  // ============== Background Processing ==============

  startProcessing() {
    // Check for pending uploads every 5 seconds
    setInterval(async () => {
      if (!navigator.onLine || this.activeUploads >= this.concurrentUploads) return;
      
      try {
        const pending = await evidenceStorage.getPendingChunks();
        
        for (const chunk of pending) {
          // Check if already in queue
          const inQueue = this.uploadQueue.some(q => q.chunkId === chunk.id);
          if (!inQueue && !chunk.uploaded) {
            await this.queueUpload(chunk.encounterId, chunk.id, chunk.type);
          }
        }
      } catch (e) {
        console.error('Background processing error:', e);
      }
    }, 5000);
  }

  // ============== Online/Offline Handling ==============

  onOnline() {
    console.log('UploadManager: Back online, resuming uploads');
    this.notify('online', {});
    this.processQueue();
  }

  onOffline() {
    console.log('UploadManager: Offline, pausing uploads');
    this.notify('offline', {});
  }

  // ============== Stats ==============

  getStats() {
    return {
      ...this.stats,
      queueLength: this.uploadQueue.length,
      activeUploads: this.activeUploads,
      isOnline: navigator.onLine
    };
  }

  async getFullStats() {
    const storageStats = await evidenceStorage.getStorageStats();
    return {
      ...this.getStats(),
      storage: storageStats
    };
  }
}

// Export singleton
const uploadManager = new UploadManager();
export default uploadManager;
export { UploadManager };
