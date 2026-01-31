/**
 * Constants and configurations for the Encounter Mode
 */

export const encounterTypes = [
  { value: 'traffic_stop', label: 'Traffic Stop' },
  { value: 'pedestrian_stop', label: 'Pedestrian Stop' },
  { value: 'arrest', label: 'Arrest' },
  { value: 'search', label: 'Search/Seizure' },
  { value: 'other', label: 'Other' }
];

export const broadcastModes = [
  { value: 'save', label: 'Save Only', icon: 'FileText', desc: 'Record and save locally' },
  { value: 'share_contacts', label: 'Share with Contacts', icon: 'Users', desc: 'Notify emergency contacts' },
  { value: 'share_attorney', label: 'Share with Attorney', icon: 'Scale', desc: 'Alert your attorney' },
  { value: 'livestream', label: 'Livestream', icon: 'Radio', desc: 'Stream live publicly' },
  { value: 'all', label: 'All Options', icon: 'Share2', desc: 'Maximum protection' }
];

export const rightsReminders = [
  "You have the right to remain silent.",
  "You do not have to consent to a search.",
  "Ask: 'Am I being detained or am I free to go?'",
  "You have the right to an attorney.",
  "Do not physically resist, even if your rights are violated.",
  "Everything is being recorded for your protection."
];

export const voiceCommandsConfig = [
  { phrases: ['mark violation', 'flag violation', 'violation'], action: 'MARK_VIOLATION', feedback: 'Violation marked!' },
  { phrases: ['call attorney', 'contact attorney', 'lawyer'], action: 'CALL_ATTORNEY', feedback: 'Contacting attorney...' },
  { phrases: ['emergency', 'sos', 'help me', 'send help'], action: 'SOS', feedback: 'Sending SOS alert!' },
  { phrases: ['end recording', 'stop recording', 'stop'], action: 'END_RECORDING', feedback: 'Ending recording...' },
  { phrases: ['pause recording', 'pause'], action: 'PAUSE', feedback: 'Recording paused' },
  { phrases: ['resume recording', 'resume', 'continue'], action: 'RESUME', feedback: 'Recording resumed' },
  { phrases: ['share link', 'share stream', 'share'], action: 'SHARE', feedback: 'Sharing stream link...' },
];

export const riskLevelColors = {
  low: 'bg-green-500',
  medium: 'bg-yellow-500',
  high: 'bg-orange-500',
  critical: 'bg-red-500 animate-pulse'
};

export const riskLevelLabels = {
  low: 'Normal',
  medium: 'Caution',
  high: 'Alert',
  critical: 'CRITICAL'
};

export const toneColors = {
  professional: 'bg-green-500/20 text-green-400 border-green-500/30',
  calm: 'bg-green-500/20 text-green-400 border-green-500/30',
  assertive: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  anxious: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  defensive: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  compliant: 'bg-green-500/20 text-green-400 border-green-500/30',
  aggressive: 'bg-red-500/20 text-red-400 border-red-500/30',
  intimidating: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  hostile: 'bg-red-500/20 text-red-400 border-red-500/30 animate-pulse',
  neutral: 'bg-gray-500/20 text-gray-400 border-gray-500/30'
};

export const toneIcons = {
  professional: '✓',
  calm: '😌',
  assertive: '💪',
  anxious: '😰',
  defensive: '🛡️',
  compliant: '👍',
  aggressive: '⚠️',
  intimidating: '😠',
  hostile: '🚨',
  neutral: '•'
};

export const toneSeverityColors = {
  normal: 'bg-green-500',
  elevated: 'bg-yellow-500',
  concerning: 'bg-orange-500',
  critical: 'bg-red-500 animate-pulse'
};

export const highlightKeywords = {
  danger: ['search', 'arrest', 'detain', 'weapon', 'gun', 'resist', 'jail', 'prison'],
  rights: ['silent', 'attorney', 'lawyer', 'rights', 'consent', 'free to go', 'detained'],
  command: ['license', 'registration', 'step out', 'hands up', "don't move", 'stop']
};

export const qualityPresets = {
  maximum: { 
    label: 'Maximum (Court Quality)', 
    desc: '1080p, highest quality', 
    icon: '⚖️',
    video: { width: 1920, height: 1080 },
    videoBitrate: 2500000,
    audioBitrate: 192000,
    chunkInterval: 5000
  },
  balanced: { 
    label: 'Balanced (Recommended)', 
    desc: '720p, good quality', 
    icon: '✓',
    video: { width: 1280, height: 720 },
    videoBitrate: 1500000,
    audioBitrate: 128000,
    chunkInterval: 5000
  },
  performance: { 
    label: 'Performance Mode', 
    desc: '480p, smoothest recording', 
    icon: '⚡',
    video: { width: 854, height: 480 },
    videoBitrate: 800000,
    audioBitrate: 96000,
    chunkInterval: 5000
  }
};

/**
 * Helper to highlight keywords in transcription text
 */
export const highlightText = (text) => {
  if (!text) return text;
  
  let result = text;
  
  highlightKeywords.danger.forEach(word => {
    const regex = new RegExp(`\\b(${word})\\b`, 'gi');
    result = result.replace(regex, '<span class="text-red-400 font-medium">$1</span>');
  });
  
  highlightKeywords.rights.forEach(word => {
    const regex = new RegExp(`\\b(${word})\\b`, 'gi');
    result = result.replace(regex, '<span class="text-green-400 font-medium">$1</span>');
  });
  
  highlightKeywords.command.forEach(word => {
    const regex = new RegExp(`\\b(${word})\\b`, 'gi');
    result = result.replace(regex, '<span class="text-yellow-400 font-medium">$1</span>');
  });
  
  return result;
};

/**
 * Format duration in MM:SS or HH:MM:SS format
 */
export const formatDuration = (seconds) => {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};
