import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Alert, AlertDescription } from './ui/alert';
import { 
  Scale, Shield, AlertTriangle, ChevronDown, ChevronUp, 
  Loader2, Lightbulb, MessageSquare, Info
} from 'lucide-react';
import api from '../lib/api';

const severityColors = {
  1: 'bg-green-500/20 text-green-400 border-green-500/30',
  2: 'bg-green-500/20 text-green-400 border-green-500/30',
  3: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  4: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  5: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  6: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  7: 'bg-red-500/20 text-red-400 border-red-500/30',
  8: 'bg-red-500/20 text-red-400 border-red-500/30',
  9: 'bg-red-500/20 text-red-400 border-red-500/30 animate-pulse',
  10: 'bg-red-500/20 text-red-400 border-red-500/30 animate-pulse',
};

export default function RightsCoachPanel({ 
  encounterType = 'general',
  fullTranscript = '',
  isRecording = false,
  isPaused = false,
  onGuidanceReceived
}) {
  const [guidance, setGuidance] = useState(null);
  const [guidanceHistory, setGuidanceHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastAnalyzedLength, setLastAnalyzedLength] = useState(0);
  const [error, setError] = useState(null);

  // Fetch AI guidance when transcript changes significantly
  const fetchGuidance = useCallback(async () => {
    if (!fullTranscript || fullTranscript.length < 20) return;
    if (isLoading) return;
    
    // Only analyze if transcript has grown significantly (50+ chars)
    if (fullTranscript.length - lastAnalyzedLength < 50) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.post('/advanced/rights-coach/guidance', {
        transcript: fullTranscript,
        encounter_type: encounterType,
        context: { auto_refresh: true }
      });

      const newGuidance = response.data;
      setGuidance(newGuidance);
      setLastAnalyzedLength(fullTranscript.length);

      // Add to history if it's different from the last entry
      setGuidanceHistory(prev => {
        const last = prev[prev.length - 1];
        if (!last || last.immediate_guidance !== newGuidance.immediate_guidance) {
          return [...prev.slice(-9), newGuidance]; // Keep last 10
        }
        return prev;
      });

      // Notify parent component
      if (onGuidanceReceived) {
        onGuidanceReceived(newGuidance);
      }
    } catch (err) {
      console.error('Rights Coach error:', err);
      setError('Unable to get AI guidance. Using basic mode.');
    } finally {
      setIsLoading(false);
    }
  }, [fullTranscript, encounterType, lastAnalyzedLength, isLoading, onGuidanceReceived]);

  // Auto-refresh guidance when transcript updates
  useEffect(() => {
    if (!isRecording || isPaused || !autoRefresh) return;

    const timer = setTimeout(() => {
      fetchGuidance();
    }, 3000); // Debounce 3 seconds

    return () => clearTimeout(timer);
  }, [fullTranscript, isRecording, isPaused, autoRefresh, fetchGuidance]);

  // Get quick guidance (instant, no AI)
  const getQuickGuidance = async (phrase) => {
    try {
      const response = await api.post(`/advanced/rights-coach/quick?phrase=${encodeURIComponent(phrase)}&encounter_type=${encounterType}`);
      return response.data.guidance;
    } catch {
      return null;
    }
  };

  if (!isRecording) {
    return null;
  }

  return (
    <Card 
      className={`border-2 transition-all ${
        guidance?.potential_violation 
          ? 'border-red-500/50 bg-red-500/5' 
          : guidance?.safety_warning
            ? 'border-orange-500/50 bg-orange-500/5'
            : 'border-purple-500/50 bg-purple-500/5'
      }`}
      data-testid="rights-coach-panel"
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Scale className="h-5 w-5 text-purple-400" />
            AI Rights Coach
            {isLoading && <Loader2 className="h-4 w-4 animate-spin text-purple-400" />}
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge 
              variant="outline" 
              className={autoRefresh ? 'bg-purple-500/20 text-purple-400' : 'bg-gray-500/20'}
            >
              {autoRefresh ? 'Auto' : 'Manual'}
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
              className="h-8 w-8 p-0"
            >
              {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-4">
          {/* Error State */}
          {error && (
            <Alert className="border-yellow-500/50 bg-yellow-500/10">
              <AlertTriangle className="h-4 w-4 text-yellow-500" />
              <AlertDescription className="text-yellow-400 text-sm">
                {error}
              </AlertDescription>
            </Alert>
          )}

          {/* Main Guidance */}
          {guidance ? (
            <div className="space-y-3">
              {/* Immediate Guidance */}
              <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/30">
                <div className="flex items-start gap-2">
                  <Lightbulb className="h-5 w-5 text-purple-400 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-purple-300">
                      {guidance.immediate_guidance}
                    </p>
                  </div>
                </div>
              </div>

              {/* Suggested Response */}
              {guidance.suggested_response && (
                <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/30">
                  <div className="flex items-start gap-2">
                    <MessageSquare className="h-5 w-5 text-blue-400 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-xs text-blue-400/70 mb-1">Say this:</p>
                      <p className="text-sm font-medium text-blue-300 italic">
                        "{guidance.suggested_response}"
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Applicable Rights */}
              {guidance.rights_applicable?.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {guidance.rights_applicable.map((right, idx) => (
                    <Badge 
                      key={idx} 
                      variant="outline"
                      className="bg-green-500/10 text-green-400 border-green-500/30"
                    >
                      <Shield className="h-3 w-3 mr-1" />
                      {right}
                    </Badge>
                  ))}
                </div>
              )}

              {/* Potential Violation Alert */}
              {guidance.potential_violation && (
                <Alert className="border-red-500/50 bg-red-500/10">
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                  <AlertDescription>
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-red-400">
                        Potential {guidance.potential_violation.type}
                      </span>
                      <Badge 
                        className={severityColors[guidance.potential_violation.severity] || severityColors[5]}
                      >
                        Severity: {guidance.potential_violation.severity}/10
                      </Badge>
                    </div>
                    <p className="text-sm text-red-300">
                      {guidance.potential_violation.explanation}
                    </p>
                  </AlertDescription>
                </Alert>
              )}

              {/* Safety Warning */}
              {guidance.safety_warning && (
                <Alert className="border-orange-500/50 bg-orange-500/10">
                  <Shield className="h-4 w-4 text-orange-500" />
                  <AlertDescription className="text-orange-400">
                    <span className="font-bold">Safety:</span> {guidance.safety_warning}
                  </AlertDescription>
                </Alert>
              )}

              {/* What NOT to do */}
              {guidance.do_not && (
                <div className="p-2 rounded bg-gray-500/10 border border-gray-500/30">
                  <p className="text-xs text-gray-400">
                    <span className="font-bold text-red-400">Don't:</span> {guidance.do_not}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-4">
              <Info className="h-8 w-8 mx-auto text-muted-foreground/50 mb-2" />
              <p className="text-sm text-muted-foreground">
                AI guidance will appear as the conversation develops
              </p>
              <p className="text-xs text-muted-foreground/70 mt-1">
                Real-time analysis of your rights and suggested responses
              </p>
            </div>
          )}

          {/* Guidance History (collapsible) */}
          {guidanceHistory.length > 1 && (
            <details className="text-sm">
              <summary className="cursor-pointer text-muted-foreground hover:text-foreground text-xs">
                View guidance history ({guidanceHistory.length} entries)
              </summary>
              <ScrollArea className="h-32 mt-2">
                <div className="space-y-2">
                  {guidanceHistory.slice().reverse().map((g, idx) => (
                    <div 
                      key={idx}
                      className="p-2 rounded bg-muted/30 text-xs"
                    >
                      <p className="text-muted-foreground">{g.immediate_guidance}</p>
                      {g.timestamp && (
                        <p className="text-muted-foreground/50 text-[10px] mt-1">
                          {new Date(g.timestamp).toLocaleTimeString()}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </details>
          )}

          {/* Controls */}
          <div className="flex items-center justify-between pt-2 border-t border-border/50">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className="text-xs"
            >
              {autoRefresh ? 'Disable Auto' : 'Enable Auto'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchGuidance}
              disabled={isLoading || !fullTranscript}
              className="text-xs"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                  Analyzing...
                </>
              ) : (
                'Get Guidance Now'
              )}
            </Button>
          </div>
        </CardContent>
      )}
    </Card>
  );
}
