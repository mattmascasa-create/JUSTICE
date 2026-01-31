/**
 * IndexedDB Storage Service for Encounter Evidence
 * Provides persistent local storage for recordings that survives crashes
 */

const DB_NAME = 'JusticeEvidenceDB';
const DB_VERSION = 1;
const STORES = {
  CHUNKS: 'media_chunks',
  ENCOUNTERS: 'encounters',
  UPLOAD_QUEUE: 'upload_queue'
};

class EvidenceStorageService {
  constructor() {
    this.db = null;
    this.isReady = false;
    this.readyPromise = this.initDB();
  }

  async initDB() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => {
        console.error('IndexedDB error:', request.error);
        reject(request.error);
      };

      request.onsuccess = () => {
        this.db = request.result;
        this.isReady = true;
        console.log('EvidenceStorage: IndexedDB ready');
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // Store for media chunks (audio/video blobs)
        if (!db.objectStoreNames.contains(STORES.CHUNKS)) {
          const chunksStore = db.createObjectStore(STORES.CHUNKS, { keyPath: 'id', autoIncrement: true });
          chunksStore.createIndex('encounterId', 'encounterId', { unique: false });
          chunksStore.createIndex('type', 'type', { unique: false });
          chunksStore.createIndex('timestamp', 'timestamp', { unique: false });
          chunksStore.createIndex('uploaded', 'uploaded', { unique: false });
        }

        // Store for encounter metadata
        if (!db.objectStoreNames.contains(STORES.ENCOUNTERS)) {
          const encountersStore = db.createObjectStore(STORES.ENCOUNTERS, { keyPath: 'encounterId' });
          encountersStore.createIndex('status', 'status', { unique: false });
          encountersStore.createIndex('createdAt', 'createdAt', { unique: false });
        }

        // Store for upload queue
        if (!db.objectStoreNames.contains(STORES.UPLOAD_QUEUE)) {
          const queueStore = db.createObjectStore(STORES.UPLOAD_QUEUE, { keyPath: 'id', autoIncrement: true });
          queueStore.createIndex('encounterId', 'encounterId', { unique: false });
          queueStore.createIndex('status', 'status', { unique: false });
          queueStore.createIndex('priority', 'priority', { unique: false });
        }

        console.log('EvidenceStorage: Database schema created');
      };
    });
  }

  async waitForReady() {
    if (this.isReady) return this.db;
    return this.readyPromise;
  }

  // ============== Cryptographic Hashing ==============

  /**
   * Generate SHA-256 hash of a blob for evidence integrity
   * @param {Blob} blob - The media blob to hash
   * @returns {Promise<string>} - Hex string of the SHA-256 hash
   */
  async generateHash(blob) {
    try {
      const arrayBuffer = await blob.arrayBuffer();
      const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
      return hashHex;
    } catch (error) {
      console.error('EvidenceStorage: Failed to generate hash', error);
      // Fallback: use timestamp + size as pseudo-hash if crypto API unavailable
      return `fallback_${Date.now()}_${blob.size}`;
    }
  }

  /**
   * Generate a chain hash that links this chunk to the previous one
   * This creates an immutable chain of evidence
   */
  async generateChainHash(currentHash, previousHash, metadata) {
    const chainData = `${previousHash || 'GENESIS'}|${currentHash}|${metadata.timestamp}|${metadata.chunkIndex}`;
    const encoder = new TextEncoder();
    const data = encoder.encode(chainData);
    
    try {
      const hashBuffer = await crypto.subtle.digest('SHA-256', data);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    } catch (error) {
      return `chain_${Date.now()}`;
    }
  }

  // ============== Chunk Storage ==============

  async saveChunk(encounterId, blob, type, chunkIndex, metadata = {}) {
    await this.waitForReady();
    
    // Generate SHA-256 hash for evidence integrity
    const contentHash = await this.generateHash(blob);
    
    // Get the previous chunk's hash for chain integrity
    const previousChunks = await this.getChunksForEncounter(encounterId, type);
    const previousChunk = previousChunks.find(c => c.chunkIndex === chunkIndex - 1);
    const previousHash = previousChunk?.chainHash || null;
    
    // Generate chain hash linking to previous chunk
    const timestamp = Date.now();
    const chainHash = await this.generateChainHash(contentHash, previousHash, {
      timestamp,
      chunkIndex,
      type,
      encounterId
    });
    
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([STORES.CHUNKS], 'readwrite');
      const store = transaction.objectStore(STORES.CHUNKS);

      const chunk = {
        encounterId,
        type, // 'audio' or 'video'
        chunkIndex,
        blob,
        size: blob.size,
        mimeType: blob.type,
        timestamp,
        uploaded: false,
        uploadAttempts: 0,
        // Integrity verification fields
        contentHash,      // SHA-256 of the blob content
        previousHash,     // Hash of the previous chunk (creates chain)
        chainHash,        // Combined hash linking this chunk in the chain
        hashAlgorithm: 'SHA-256',
        hashGeneratedAt: new Date().toISOString(),
        ...metadata
      };

      const request = store.add(chunk);

      request.onsuccess = () => {
        console.log(`EvidenceStorage: Saved ${type} chunk ${chunkIndex} (${(blob.size / 1024).toFixed(1)}KB) - Hash: ${contentHash.substring(0, 16)}...`);
        resolve(request.result); // Returns the auto-generated ID
      };

      request.onerror = () => {
        console.error('EvidenceStorage: Failed to save chunk', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Verify the integrity of a chunk by recalculating its hash
   */
  async verifyChunkIntegrity(chunkId) {
    await this.waitForReady();
    
    const chunk = await new Promise((resolve, reject) => {
      const transaction = this.db.transaction([STORES.CHUNKS], 'readonly');
      const store = transaction.objectStore(STORES.CHUNKS);
      const request = store.get(chunkId);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    
    if (!chunk) return { valid: false, error: 'Chunk not found' };
    
    const currentHash = await this.generateHash(chunk.blob);
    const isValid = currentHash === chunk.contentHash;
    
    return {
      valid: isValid,
      chunkId,
      storedHash: chunk.contentHash,
      calculatedHash: currentHash,
      timestamp: chunk.timestamp,
      chainHash: chunk.chainHash
    };
  }

  /**
   * Verify the entire chain of evidence for an encounter
   */
  async verifyEncounterIntegrity(encounterId) {
    await this.waitForReady();
    
    const chunks = await this.getChunksForEncounter(encounterId);
    const results = {
      encounterId,
      totalChunks: chunks.length,
      verifiedAt: new Date().toISOString(),
      chainIntact: true,
      chunkResults: []
    };
    
    // Sort by type and index
    const audioChunks = chunks.filter(c => c.type === 'audio').sort((a, b) => a.chunkIndex - b.chunkIndex);
    const videoChunks = chunks.filter(c => c.type === 'video').sort((a, b) => a.chunkIndex - b.chunkIndex);
    
    // Verify each chain
    for (const chainChunks of [audioChunks, videoChunks]) {
      let previousHash = null;
      
      for (const chunk of chainChunks) {
        const verification = await this.verifyChunkIntegrity(chunk.id);
        
        // Verify chain link
        const chainValid = chunk.previousHash === previousHash;
        
        results.chunkResults.push({
          ...verification,
          type: chunk.type,
          chunkIndex: chunk.chunkIndex,
          chainLinkValid: chainValid
        });
        
        if (!verification.valid || !chainValid) {
          results.chainIntact = false;
        }
        
        previousHash = chunk.chainHash;
      }
    }
    
    return results;
  }

  /**
   * Generate a court-ready integrity report
   */
  async generateIntegrityReport(encounterId) {
    const verification = await this.verifyEncounterIntegrity(encounterId);
    const encounter = await this.getEncounter(encounterId);
    
    return {
      reportType: 'EVIDENCE_INTEGRITY_VERIFICATION',
      generatedAt: new Date().toISOString(),
      encounterId,
      encounterStarted: encounter?.createdAt ? new Date(encounter.createdAt).toISOString() : null,
      hashAlgorithm: 'SHA-256',
      verification: {
        status: verification.chainIntact ? 'VERIFIED' : 'INTEGRITY_COMPROMISED',
        totalChunks: verification.totalChunks,
        audioChunks: verification.chunkResults.filter(c => c.type === 'audio').length,
        videoChunks: verification.chunkResults.filter(c => c.type === 'video').length,
        allHashesValid: verification.chunkResults.every(c => c.valid),
        chainIntact: verification.chainIntact
      },
      chunks: verification.chunkResults.map(c => ({
        type: c.type,
        index: c.chunkIndex,
        hash: c.storedHash,
        verified: c.valid,
        chainLinkValid: c.chainLinkValid
      })),
      signature: `JUSTICE_INTEGRITY_${encounterId}_${Date.now()}`
    };
  }

  async getChunksForEncounter(encounterId, type = null) {
    await this.waitForReady();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([STORES.CHUNKS], 'readonly');
      const store = transaction.objectStore(STORES.CHUNKS);
      const index = store.index('encounterId');
      const request = index.getAll(encounterId);

      request.onsuccess = () => {
        let chunks = request.result;
        if (type) {
          chunks = chunks.filter(c => c.type === type);
        }
        chunks.sort((a, b) => a.chunkIndex - b.chunkIndex);
        resolve(chunks);
      };

      request.onerror = () => reject(request.error);
    });
  }

  async getPendingChunks(encounterId = null) {
    await this.waitForReady();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([STORES.CHUNKS], 'readonly');
      const store = transaction.objectStore(STORES.CHUNKS);
      const index = store.index('uploaded');
      const request = index.getAll(false);

      request.onsuccess = () => {
        let chunks = request.result;
        if (encounterId) {
          chunks = chunks.filter(c => c.encounterId === encounterId);
        }
        chunks.sort((a, b) => a.timestamp - b.timestamp);
        resolve(chunks);
      };

      request.onerror = () => reject(request.error);
    });
  }

  async markChunkUploaded(chunkId) {
    await this.waitForReady();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([STORES.CHUNKS], 'readwrite');
      const store = transaction.objectStore(STORES.CHUNKS);
      const getRequest = store.get(chunkId);

      getRequest.onsuccess = () => {
        const chunk = getRequest.result;
        if (chunk) {
          chunk.uploaded = true;
          chunk.uploadedAt = Date.now();
          const updateRequest = store.put(chunk);
          updateRequest.onsuccess = () => resolve(true);
          updateRequest.onerror = () => reject(updateRequest.error);
        } else {
          resolve(false);
        }
      };

      getRequest.onerror = () => reject(getRequest.error);
    });
  }

  async incrementUploadAttempts(chunkId) {
    await this.waitForReady();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([STORES.CHUNKS], 'readwrite');
      const store = transaction.objectStore(STORES.CHUNKS);
      const getRequest = store.get(chunkId);

      getRequest.onsuccess = () => {
        const chunk = getRequest.result;
        if (chunk) {
          chunk.uploadAttempts = (chunk.uploadAttempts || 0) + 1;
          chunk.lastAttempt = Date.now();
          const updateRequest = store.put(chunk);
          updateRequest.onsuccess = () => resolve(chunk.uploadAttempts);
          updateRequest.onerror = () => reject(updateRequest.error);
        } else {
          resolve(0);
        }
      };

      getRequest.onerror = () => reject(getRequest.error);
    });
  }

  // ============== Encounter Metadata ==============

  async saveEncounter(encounterId, metadata) {
    await this.waitForReady();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([STORES.ENCOUNTERS], 'readwrite');
      const store = transaction.objectStore(STORES.ENCOUNTERS);

      const encounter = {
        encounterId,
        status: 'recording',
        createdAt: Date.now(),
        ...metadata
      };

      const request = store.put(encounter);
      request.onsuccess = () => resolve(encounter);
      request.onerror = () => reject(request.error);
    });
  }

  async updateEncounterStatus(encounterId, status) {
    await this.waitForReady();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([STORES.ENCOUNTERS], 'readwrite');
      const store = transaction.objectStore(STORES.ENCOUNTERS);
      const getRequest = store.get(encounterId);

      getRequest.onsuccess = () => {
        const encounter = getRequest.result;
        if (encounter) {
          encounter.status = status;
          encounter.updatedAt = Date.now();
          if (status === 'completed') {
            encounter.completedAt = Date.now();
          }
          const updateRequest = store.put(encounter);
          updateRequest.onsuccess = () => resolve(encounter);
          updateRequest.onerror = () => reject(updateRequest.error);
        } else {
          resolve(null);
        }
      };

      getRequest.onerror = () => reject(getRequest.error);
    });
  }

  async getEncounter(encounterId) {
    await this.waitForReady();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([STORES.ENCOUNTERS], 'readonly');
      const store = transaction.objectStore(STORES.ENCOUNTERS);
      const request = store.get(encounterId);

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async getActiveEncounters() {
    await this.waitForReady();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([STORES.ENCOUNTERS], 'readonly');
      const store = transaction.objectStore(STORES.ENCOUNTERS);
      const index = store.index('status');
      const request = index.getAll('recording');

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  // ============== Cleanup ==============

  async deleteUploadedChunks(encounterId, olderThanMs = 24 * 60 * 60 * 1000) {
    await this.waitForReady();
    const cutoff = Date.now() - olderThanMs;

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([STORES.CHUNKS], 'readwrite');
      const store = transaction.objectStore(STORES.CHUNKS);
      const index = store.index('encounterId');
      const request = index.openCursor(encounterId);

      let deletedCount = 0;

      request.onsuccess = (event) => {
        const cursor = event.target.result;
        if (cursor) {
          const chunk = cursor.value;
          if (chunk.uploaded && chunk.timestamp < cutoff) {
            cursor.delete();
            deletedCount++;
          }
          cursor.continue();
        } else {
          console.log(`EvidenceStorage: Cleaned up ${deletedCount} old chunks`);
          resolve(deletedCount);
        }
      };

      request.onerror = () => reject(request.error);
    });
  }

  async getStorageStats() {
    await this.waitForReady();

    const stats = {
      totalChunks: 0,
      pendingChunks: 0,
      uploadedChunks: 0,
      totalSize: 0,
      encounters: 0
    };

    // Count chunks
    const chunks = await new Promise((resolve, reject) => {
      const transaction = this.db.transaction([STORES.CHUNKS], 'readonly');
      const store = transaction.objectStore(STORES.CHUNKS);
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });

    stats.totalChunks = chunks.length;
    stats.pendingChunks = chunks.filter(c => !c.uploaded).length;
    stats.uploadedChunks = chunks.filter(c => c.uploaded).length;
    stats.totalSize = chunks.reduce((sum, c) => sum + (c.size || 0), 0);

    // Count encounters
    const encounters = await new Promise((resolve, reject) => {
      const transaction = this.db.transaction([STORES.ENCOUNTERS], 'readonly');
      const store = transaction.objectStore(STORES.ENCOUNTERS);
      const request = store.count();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });

    stats.encounters = encounters;

    return stats;
  }
}

// Export singleton instance
const evidenceStorage = new EvidenceStorageService();
export default evidenceStorage;
export { EvidenceStorageService };
