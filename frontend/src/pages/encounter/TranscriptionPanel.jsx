/**
 * TranscriptionPanel Component
 * Displays real-time transcription with highlighted keywords
 */

import React, { useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { ScrollArea } from '../../components/ui/scroll-area';
import { FileText, Mic, User, AlertTriangle } from 'lucide-react';
import { highlightText, toneColors, toneIcons } from './constants';

export function TranscriptionPanel({
  transcriptions = [],
  maxHeight = '200px',
  showToneIndicators = true,
  compact = false
}) {
  const scrollRef = useRef(null);

  // Auto-scroll to bottom when new transcriptions arrive
  useEffect(() => {
    if (scrollRef.current) {
      const scrollElement = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollElement) {
        scrollElement.scrollTop = scrollElement.scrollHeight;
      }
    }
  }, [transcriptions]);

  if (transcriptions.length === 0) {
    return (
      <Card className={compact ? 'border-muted' : ''}>
        <CardContent className="p-4">
          <div className="flex items-center justify-center gap-2 text-muted-foreground py-4">
            <Mic className="h-5 w-5 animate-pulse" />
            <span>Listening for speech...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (compact) {
    return (
      <Card className="border-muted">
        <CardContent className="p-3">
          <ScrollArea className="h-[120px]" ref={scrollRef}>
            <div className="space-y-2">
              {transcriptions.slice(-5).map((t, idx) => (
                <div key={idx} className="text-sm">
                  <span 
                    className="text-foreground"
                    dangerouslySetInnerHTML={{ __html: highlightText(t.text) }}
                  />
                </div>
              ))}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Live Transcription
          <Badge variant="outline" className="ml-auto">
            {transcriptions.length} segments
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className={`pr-4`} style={{ height: maxHeight }} ref={scrollRef}>
          <div className="space-y-3">
            {transcriptions.map((t, idx) => (
              <TranscriptionEntry 
                key={idx} 
                entry={t} 
                showTone={showToneIndicators}
              />
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

/**
 * Individual transcription entry
 */
function TranscriptionEntry({ entry, showTone = true }) {
  const { text, speaker, tone, timestamp, violations_detected } = entry;
  const hasViolations = violations_detected && violations_detected.length > 0;
  
  // Determine speaker icon and color
  const isOfficer = speaker === 'officer' || speaker === 'Officer';
  const speakerColor = isOfficer ? 'text-blue-400' : 'text-green-400';
  const speakerLabel = isOfficer ? 'Officer' : 'You';
  
  // Get tone styling
  const toneClass = tone ? (toneColors[tone.toLowerCase()] || toneColors.neutral) : '';
  const toneIcon = tone ? (toneIcons[tone.toLowerCase()] || '•') : '';

  return (
    <div className={`p-3 rounded-lg border ${hasViolations ? 'border-red-500/30 bg-red-500/5' : 'border-border bg-muted/30'}`}>
      {/* Header with speaker and tone */}
      <div className="flex items-center gap-2 mb-1">
        <User className={`h-4 w-4 ${speakerColor}`} />
        <span className={`text-xs font-medium ${speakerColor}`}>
          {speakerLabel}
        </span>
        
        {showTone && tone && (
          <Badge 
            variant="outline" 
            className={`text-xs ml-auto ${toneClass}`}
          >
            {toneIcon} {tone}
          </Badge>
        )}
        
        {timestamp && (
          <span className="text-xs text-muted-foreground">
            {formatTimestamp(timestamp)}
          </span>
        )}
      </div>
      
      {/* Transcription text with highlighted keywords */}
      <p 
        className="text-sm text-foreground leading-relaxed"
        dangerouslySetInnerHTML={{ __html: highlightText(text) }}
      />
      
      {/* Violation warnings */}
      {hasViolations && (
        <div className="mt-2 pt-2 border-t border-red-500/20">
          <div className="flex items-center gap-1 text-red-400 text-xs">
            <AlertTriangle className="h-3 w-3" />
            <span>Potential violation: {violations_detected.join(', ')}</span>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Format timestamp for display
 */
function formatTimestamp(ts) {
  if (!ts) return '';
  
  // If it's a number (seconds), format as MM:SS
  if (typeof ts === 'number') {
    const mins = Math.floor(ts / 60);
    const secs = Math.floor(ts % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }
  
  // If it's an ISO string, show time only
  try {
    const date = new Date(ts);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return '';
  }
}

export default TranscriptionPanel;
