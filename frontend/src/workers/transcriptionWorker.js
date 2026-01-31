/**
 * Transcription Processing Web Worker
 * 
 * Moves heavy transcription processing off the main UI thread
 * to prevent lag and freezing during recording.
 */

// Queue for processing
let processingQueue = [];
let isProcessing = false;

// Configuration
const config = {
  batchSize: 3,          // Process multiple items at once
  processingDelay: 100,  // ms between batches
  maxQueueSize: 50       // Prevent memory issues
};

/**
 * Process transcription data without blocking UI
 */
function processTranscription(data) {
  const { text, timestamp, chunkIndex } = data;
  
  // Analyze transcription for keywords and violations
  const analysis = {
    timestamp,
    chunkIndex,
    text: text || '',
    wordCount: (text || '').split(/\s+/).filter(w => w).length,
    keywords: extractKeywords(text),
    potentialViolations: detectViolations(text),
    sentiment: analyzeSentiment(text),
    processedAt: new Date().toISOString()
  };
  
  return analysis;
}

/**
 * Extract important keywords from transcription
 */
function extractKeywords(text) {
  if (!text) return { danger: [], rights: [], commands: [] };
  
  const lowerText = text.toLowerCase();
  
  const dangerWords = ['search', 'arrest', 'detain', 'weapon', 'gun', 'resist', 'jail', 'prison', 'taser', 'force'];
  const rightsWords = ['silent', 'attorney', 'lawyer', 'rights', 'consent', 'free to go', 'detained', 'miranda'];
  const commandWords = ['license', 'registration', 'step out', 'hands up', "don't move", 'stop', 'exit vehicle'];
  
  return {
    danger: dangerWords.filter(w => lowerText.includes(w)),
    rights: rightsWords.filter(w => lowerText.includes(w)),
    commands: commandWords.filter(w => lowerText.includes(w))
  };
}

/**
 * Simple pattern-based violation detection
 * (Heavy AI analysis is deferred to server)
 */
function detectViolations(text) {
  if (!text) return [];
  
  const lowerText = text.toLowerCase();
  const violations = [];
  
  // Pattern-based quick detection
  const patterns = [
    { pattern: /search (your|the) (car|vehicle|bag|person)/i, type: 'POTENTIAL_SEARCH', severity: 'medium' },
    { pattern: /you('re| are) (under arrest|being detained)/i, type: 'ARREST_DETENTION', severity: 'high' },
    { pattern: /(stop|put down|drop).*(recording|phone|camera)/i, type: 'RECORDING_INTERFERENCE', severity: 'high' },
    { pattern: /you (don't|do not) have (the )?right/i, type: 'RIGHTS_DENIAL', severity: 'critical' },
    { pattern: /(get|step) out (of )?(the )?(car|vehicle)/i, type: 'EXIT_COMMAND', severity: 'medium' },
    { pattern: /consent to (a )?search/i, type: 'CONSENT_REQUEST', severity: 'medium' }
  ];
  
  patterns.forEach(({ pattern, type, severity }) => {
    if (pattern.test(lowerText)) {
      violations.push({ type, severity, detectedAt: new Date().toISOString() });
    }
  });
  
  return violations;
}

/**
 * Basic sentiment analysis
 */
function analyzeSentiment(text) {
  if (!text) return { tone: 'neutral', score: 0 };
  
  const lowerText = text.toLowerCase();
  
  const aggressiveWords = ['now', 'immediately', 'stop', 'don\'t', 'shut', 'move'];
  const calmWords = ['please', 'thank', 'sir', 'ma\'am', 'understand', 'okay'];
  
  let score = 0;
  aggressiveWords.forEach(w => { if (lowerText.includes(w)) score -= 1; });
  calmWords.forEach(w => { if (lowerText.includes(w)) score += 1; });
  
  let tone = 'neutral';
  if (score <= -3) tone = 'aggressive';
  else if (score <= -1) tone = 'tense';
  else if (score >= 3) tone = 'calm';
  else if (score >= 1) tone = 'polite';
  
  return { tone, score };
}

/**
 * Process queue in batches
 */
async function processQueue() {
  if (isProcessing || processingQueue.length === 0) return;
  
  isProcessing = true;
  
  try {
    // Process a batch
    const batch = processingQueue.splice(0, config.batchSize);
    const results = batch.map(item => processTranscription(item));
    
    // Send results back to main thread
    self.postMessage({
      type: 'BATCH_PROCESSED',
      results,
      queueRemaining: processingQueue.length
    });
    
    // Continue processing if more in queue
    if (processingQueue.length > 0) {
      setTimeout(processQueue, config.processingDelay);
    }
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      error: error.message
    });
  } finally {
    isProcessing = false;
  }
}

/**
 * Message handler
 */
self.onmessage = function(e) {
  const { type, data } = e.data;
  
  switch (type) {
    case 'ADD_TRANSCRIPTION':
      // Add to queue, trim if too large
      if (processingQueue.length < config.maxQueueSize) {
        processingQueue.push(data);
        processQueue();
      } else {
        // Queue full - process immediately and drop oldest
        processingQueue.shift();
        processingQueue.push(data);
      }
      break;
      
    case 'PROCESS_IMMEDIATE':
      // Bypass queue for critical processing
      const result = processTranscription(data);
      self.postMessage({ type: 'IMMEDIATE_RESULT', result });
      break;
      
    case 'GET_STATS':
      self.postMessage({
        type: 'STATS',
        stats: {
          queueSize: processingQueue.length,
          isProcessing,
          maxQueueSize: config.maxQueueSize
        }
      });
      break;
      
    case 'CLEAR_QUEUE':
      processingQueue = [];
      self.postMessage({ type: 'QUEUE_CLEARED' });
      break;
      
    case 'UPDATE_CONFIG':
      Object.assign(config, data);
      self.postMessage({ type: 'CONFIG_UPDATED', config });
      break;
      
    default:
      console.log('Unknown message type:', type);
  }
};

// Notify main thread that worker is ready
self.postMessage({ type: 'WORKER_READY' });
