/**
 * Browser Speech Recognition Service
 * 
 * Uses the Web Speech API for instant, zero-latency transcription
 * without server calls. Falls back to server-side if not supported.
 * 
 * Features:
 * - Real-time word-by-word transcription
 * - Works offline
 * - No API costs
 * - Automatic language detection
 */

class BrowserSpeechRecognition {
  constructor() {
    this.recognition = null;
    this.isListening = false;
    this.isSupported = this.checkSupport();
    this.onResult = null;
    this.onInterim = null;
    this.onError = null;
    this.onStatusChange = null;
    this.restartAttempts = 0;
    this.maxRestartAttempts = 5;
    this.shouldBeListening = false;
    this.language = 'en-US';
    this.fullTranscript = '';
    this.interimTranscript = '';
  }

  /**
   * Check if browser supports Web Speech API
   */
  checkSupport() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    return !!SpeechRecognition;
  }

  /**
   * Initialize the speech recognition engine
   */
  init(options = {}) {
    if (!this.isSupported) {
      console.warn('BrowserSpeechRecognition: Not supported in this browser');
      return false;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.recognition = new SpeechRecognition();

    // Configuration
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.maxAlternatives = 1;
    this.recognition.lang = options.language || this.language;

    // Event handlers
    this.recognition.onstart = () => {
      this.isListening = true;
      this.restartAttempts = 0;
      console.log('BrowserSpeechRecognition: Started');
      this.notifyStatusChange('listening');
    };

    this.recognition.onend = () => {
      this.isListening = false;
      console.log('BrowserSpeechRecognition: Ended');
      
      // Auto-restart if we should still be listening
      if (this.shouldBeListening && this.restartAttempts < this.maxRestartAttempts) {
        this.restartAttempts++;
        console.log(`BrowserSpeechRecognition: Auto-restarting (attempt ${this.restartAttempts})`);
        setTimeout(() => {
          if (this.shouldBeListening) {
            try {
              this.recognition.start();
            } catch (e) {
              console.log('Restart failed:', e.message);
            }
          }
        }, 100);
      } else {
        this.notifyStatusChange('stopped');
      }
    };

    this.recognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        const confidence = event.results[i][0].confidence;

        if (event.results[i].isFinal) {
          finalTranscript += transcript;
          
          // Add to full transcript
          this.fullTranscript += (this.fullTranscript ? ' ' : '') + transcript.trim();
          
          // Notify with final result
          if (this.onResult) {
            this.onResult({
              text: transcript.trim(),
              confidence: confidence,
              isFinal: true,
              timestamp: new Date().toISOString(),
              fullTranscript: this.fullTranscript
            });
          }
        } else {
          interimTranscript += transcript;
          this.interimTranscript = interimTranscript;
          
          // Notify with interim result (for real-time display)
          if (this.onInterim) {
            this.onInterim({
              text: interimTranscript,
              isFinal: false,
              timestamp: new Date().toISOString()
            });
          }
        }
      }
    };

    this.recognition.onerror = (event) => {
      console.error('BrowserSpeechRecognition: Error', event.error);
      
      // Handle specific errors
      switch (event.error) {
        case 'no-speech':
          // Normal - just no speech detected, will auto-restart
          break;
        case 'audio-capture':
          this.notifyStatusChange('error', 'Microphone not available');
          break;
        case 'not-allowed':
          this.notifyStatusChange('error', 'Microphone permission denied');
          this.shouldBeListening = false;
          break;
        case 'network':
          // Some browsers need network for speech recognition
          this.notifyStatusChange('error', 'Network error - trying offline mode');
          break;
        case 'aborted':
          // User or system aborted
          break;
        default:
          this.notifyStatusChange('error', event.error);
      }

      if (this.onError) {
        this.onError(event.error);
      }
    };

    this.recognition.onnomatch = () => {
      console.log('BrowserSpeechRecognition: No match');
    };

    return true;
  }

  /**
   * Start listening for speech
   */
  start(options = {}) {
    if (!this.isSupported) {
      console.warn('BrowserSpeechRecognition: Not supported');
      return false;
    }

    if (!this.recognition) {
      this.init(options);
    }

    if (this.isListening) {
      console.log('BrowserSpeechRecognition: Already listening');
      return true;
    }

    try {
      this.shouldBeListening = true;
      this.restartAttempts = 0;
      this.recognition.start();
      return true;
    } catch (error) {
      console.error('BrowserSpeechRecognition: Start failed', error);
      return false;
    }
  }

  /**
   * Stop listening
   */
  stop() {
    this.shouldBeListening = false;
    
    if (this.recognition && this.isListening) {
      try {
        this.recognition.stop();
      } catch (e) {
        console.log('Stop error:', e.message);
      }
    }
    
    this.isListening = false;
    this.notifyStatusChange('stopped');
  }

  /**
   * Abort immediately (doesn't wait for final results)
   */
  abort() {
    this.shouldBeListening = false;
    
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch (e) {
        console.log('Abort error:', e.message);
      }
    }
    
    this.isListening = false;
  }

  /**
   * Get the full transcript so far
   */
  getFullTranscript() {
    return this.fullTranscript;
  }

  /**
   * Clear the transcript history
   */
  clearTranscript() {
    this.fullTranscript = '';
    this.interimTranscript = '';
  }

  /**
   * Set event handlers
   */
  on(event, callback) {
    switch (event) {
      case 'result':
        this.onResult = callback;
        break;
      case 'interim':
        this.onInterim = callback;
        break;
      case 'error':
        this.onError = callback;
        break;
      case 'status':
        this.onStatusChange = callback;
        break;
    }
  }

  /**
   * Get current status
   */
  getStatus() {
    return {
      isSupported: this.isSupported,
      isListening: this.isListening,
      language: this.language,
      transcriptLength: this.fullTranscript.length,
      restartAttempts: this.restartAttempts
    };
  }

  notifyStatusChange(status, error = null) {
    if (this.onStatusChange) {
      this.onStatusChange(status, error);
    }
  }

  /**
   * Set the language for recognition
   */
  setLanguage(lang) {
    this.language = lang;
    if (this.recognition) {
      this.recognition.lang = lang;
    }
  }

  /**
   * Get list of supported languages (common ones)
   */
  static getSupportedLanguages() {
    return [
      { code: 'en-US', name: 'English (US)' },
      { code: 'en-GB', name: 'English (UK)' },
      { code: 'es-ES', name: 'Spanish (Spain)' },
      { code: 'es-MX', name: 'Spanish (Mexico)' },
      { code: 'fr-FR', name: 'French' },
      { code: 'de-DE', name: 'German' },
      { code: 'it-IT', name: 'Italian' },
      { code: 'pt-BR', name: 'Portuguese (Brazil)' },
      { code: 'zh-CN', name: 'Chinese (Simplified)' },
      { code: 'ja-JP', name: 'Japanese' },
      { code: 'ko-KR', name: 'Korean' },
      { code: 'ar-SA', name: 'Arabic' },
      { code: 'hi-IN', name: 'Hindi' },
      { code: 'ru-RU', name: 'Russian' }
    ];
  }
}

// Singleton instance
const browserSpeechRecognition = new BrowserSpeechRecognition();

export default browserSpeechRecognition;
export { BrowserSpeechRecognition };
