/**
 * Notification Sound Service
 * Generates and plays notification sounds using Web Audio API
 */

// Audio context singleton
let audioContext = null;

const getAudioContext = () => {
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }
  return audioContext;
};

// Sound definitions with frequencies and patterns
const SOUND_PRESETS = {
  // Gentle sounds
  gentle_chime: {
    name: 'Gentle Chime',
    category: 'gentle',
    frequencies: [523.25, 659.25, 783.99], // C5, E5, G5
    duration: 0.15,
    type: 'sine',
    volume: 0.3
  },
  soft_bell: {
    name: 'Soft Bell',
    category: 'gentle',
    frequencies: [440, 554.37], // A4, C#5
    duration: 0.3,
    type: 'sine',
    volume: 0.25
  },
  whisper: {
    name: 'Whisper',
    category: 'gentle',
    frequencies: [880],
    duration: 0.1,
    type: 'sine',
    volume: 0.2
  },
  
  // Standard sounds
  default_ping: {
    name: 'Default Ping',
    category: 'standard',
    frequencies: [880, 1108.73], // A5, C#6
    duration: 0.12,
    type: 'sine',
    volume: 0.4
  },
  notification: {
    name: 'Notification',
    category: 'standard',
    frequencies: [587.33, 880], // D5, A5
    duration: 0.15,
    type: 'triangle',
    volume: 0.35
  },
  pop: {
    name: 'Pop',
    category: 'standard',
    frequencies: [1000, 800],
    duration: 0.08,
    type: 'sine',
    volume: 0.4
  },
  
  // Alert sounds
  alert_high: {
    name: 'High Alert',
    category: 'alert',
    frequencies: [1200, 1400, 1200],
    duration: 0.1,
    type: 'square',
    volume: 0.5
  },
  urgent: {
    name: 'Urgent',
    category: 'alert',
    frequencies: [800, 1000, 800, 1000],
    duration: 0.12,
    type: 'sawtooth',
    volume: 0.5
  },
  warning_beep: {
    name: 'Warning Beep',
    category: 'alert',
    frequencies: [440, 880],
    duration: 0.2,
    type: 'square',
    volume: 0.45
  },
  
  // Emergency sounds
  sos_alarm: {
    name: 'SOS Alarm',
    category: 'emergency',
    frequencies: [1500, 1000, 1500, 1000, 1500],
    duration: 0.15,
    type: 'square',
    volume: 0.7
  },
  critical: {
    name: 'Critical Alert',
    category: 'emergency',
    frequencies: [880, 1760, 880, 1760],
    duration: 0.1,
    type: 'sawtooth',
    volume: 0.6
  },
  
  // Special sounds
  success: {
    name: 'Success',
    category: 'special',
    frequencies: [523.25, 659.25, 783.99, 1046.5], // C5 major arpeggio
    duration: 0.12,
    type: 'sine',
    volume: 0.35
  },
  message: {
    name: 'Message',
    category: 'special',
    frequencies: [659.25, 783.99], // E5, G5
    duration: 0.1,
    type: 'triangle',
    volume: 0.3
  },
  
  // Silent option
  none: {
    name: 'Silent',
    category: 'silent',
    frequencies: [],
    duration: 0,
    type: 'sine',
    volume: 0
  }
};

// Get all sound options grouped by category
export const getSoundOptions = () => {
  const categories = {
    silent: { label: 'Silent', sounds: [] },
    gentle: { label: 'Gentle', sounds: [] },
    standard: { label: 'Standard', sounds: [] },
    alert: { label: 'Alert', sounds: [] },
    emergency: { label: 'Emergency', sounds: [] },
    special: { label: 'Special', sounds: [] }
  };
  
  Object.entries(SOUND_PRESETS).forEach(([key, sound]) => {
    if (categories[sound.category]) {
      categories[sound.category].sounds.push({
        id: key,
        name: sound.name
      });
    }
  });
  
  return categories;
};

// Play a sound by preset ID
export const playSound = async (presetId, volumeMultiplier = 1) => {
  const preset = SOUND_PRESETS[presetId];
  if (!preset || preset.frequencies.length === 0) return;
  
  try {
    const ctx = getAudioContext();
    
    // Resume context if suspended (browser autoplay policy)
    if (ctx.state === 'suspended') {
      await ctx.resume();
    }
    
    const masterGain = ctx.createGain();
    masterGain.connect(ctx.destination);
    masterGain.gain.value = preset.volume * volumeMultiplier;
    
    let time = ctx.currentTime;
    
    preset.frequencies.forEach((freq, index) => {
      const oscillator = ctx.createOscillator();
      const gainNode = ctx.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(masterGain);
      
      oscillator.type = preset.type;
      oscillator.frequency.value = freq;
      
      // Envelope
      gainNode.gain.setValueAtTime(0, time);
      gainNode.gain.linearRampToValueAtTime(1, time + 0.01);
      gainNode.gain.exponentialRampToValueAtTime(0.01, time + preset.duration);
      
      oscillator.start(time);
      oscillator.stop(time + preset.duration + 0.05);
      
      time += preset.duration * 0.8; // Slight overlap
    });
    
  } catch (error) {
    console.error('Error playing sound:', error);
  }
};

// Preview a sound (used in settings)
export const previewSound = (presetId) => {
  playSound(presetId, 1);
};

// Default sounds for each notification type
export const DEFAULT_NOTIFICATION_SOUNDS = {
  message: 'message',
  case_update: 'notification',
  attorney_response: 'default_ping',
  sos_alert: 'sos_alarm',
  warning: 'warning_beep',
  system: 'soft_bell'
};

// Get sound name by ID
export const getSoundName = (presetId) => {
  return SOUND_PRESETS[presetId]?.name || 'Unknown';
};
