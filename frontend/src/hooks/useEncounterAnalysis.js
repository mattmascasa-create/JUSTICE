/**
 * useEncounterAnalysis Hook
 * Handles AI analysis and real-time coaching during encounters
 */

import { useState, useRef, useCallback } from 'react';
import { toast } from 'sonner';

export function useEncounterAnalysis({
  encounter,
  encounterType,
  encounterAPI,
  encounterCoachAPI,
  enabled = true,
  coachingEnabled = true
}) {
  // AI Analysis State
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [riskLevel, setRiskLevel] = useState('low');
  const [detectedViolations, setDetectedViolations] = useState([]);
  const [biasIndicators, setBiasIndicators] = useState([]);
  const [proceduralIssues, setProceduralIssues] = useState([]);
  const [immediateAlert, setImmediateAlert] = useState(null);
  const [fullTranscript, setFullTranscript] = useState('');
  
  // Coaching State
  const [coachingMessages, setCoachingMessages] = useState([]);
  const [lastCoachingTime, setLastCoachingTime] = useState(0);
  
  // Refs for throttling
  const analysisQueueRef = useRef([]);
  const lastAnalysisRef = useRef(0);

  /**
   * Perform real-time AI analysis on transcription text (NON-BLOCKING)
   */
  const performAnalysis = useCallback((text) => {
    if (!encounter || !text || text.length < 30 || !enabled) return;
    
    // Throttle analysis to every 15 seconds
    const now = Date.now();
    if (now - lastAnalysisRef.current < 15000) {
      analysisQueueRef.current.push(text);
      return;
    }
    lastAnalysisRef.current = now;
    
    // Combine queued text
    const combinedText = [...analysisQueueRef.current, text].join(' ');
    analysisQueueRef.current = [];
    
    // Update full transcript
    setFullTranscript(prev => prev + ' ' + combinedText);
    
    // Fire and forget - don't block UI
    encounterAPI.analyzeRealtime(encounter.encounter_id, fullTranscript + ' ' + combinedText)
      .then(response => {
        const analysis = response.data?.analysis;
        if (!analysis) return;
        
        setAiAnalysis(analysis);
        
        // Update risk level
        if (analysis.risk_level) {
          setRiskLevel(analysis.risk_level);
          
          if (analysis.risk_level === 'critical' || analysis.risk_level === 'high') {
            toast.error(`⚠️ ${analysis.risk_level.toUpperCase()} RISK: Potential violation detected!`, {
              duration: 10000
            });
          }
        }
        
        // Update violations
        if (analysis.violations?.length > 0) {
          setDetectedViolations(prev => {
            const newViolations = analysis.violations.filter(
              v => !prev.some(pv => pv.type === v.type && pv.quote === v.quote)
            );
            return [...prev, ...newViolations];
          });
        }
        
        // Update bias indicators
        if (analysis.bias_indicators?.length > 0) {
          setBiasIndicators(prev => [...prev, ...analysis.bias_indicators]);
        }
        
        // Update procedural issues
        if (analysis.procedural_issues?.length > 0) {
          setProceduralIssues(prev => [...prev, ...analysis.procedural_issues]);
        }
        
        // Show immediate alert if present
        if (analysis.immediate_alert) {
          setImmediateAlert(analysis.immediate_alert);
          toast.warning(analysis.immediate_alert, { duration: 15000 });
        }
      })
      .catch(error => {
        console.error('AI analysis error:', error);
      });
  }, [encounter, fullTranscript, enabled, encounterAPI]);

  /**
   * Perform real-time coaching based on transcription
   */
  const performCoaching = useCallback(async (text) => {
    if (!encounter || !text || text.length < 10 || !coachingEnabled) return;
    
    // Throttle coaching to every 3 seconds
    const now = Date.now();
    if (now - lastCoachingTime < 3000) return;
    setLastCoachingTime(now);
    
    try {
      const response = await encounterCoachAPI.analyze(
        text,
        encounterType,
        encounter.encounter_id
      );
      
      if (response.data.coaching?.length > 0) {
        setCoachingMessages(prev => {
          const newMessages = response.data.coaching.map(msg => ({
            ...msg,
            id: `${msg.coaching_id}_${Date.now()}`,
            isNew: true
          }));
          
          // Keep only last 10 messages
          const combined = [...newMessages, ...prev].slice(0, 10);
          
          // Announce urgent messages
          const urgent = newMessages.find(m => m.tone === 'urgent');
          if (urgent) {
            toast.warning(urgent.message, { 
              duration: 8000,
              icon: '🛡️'
            });
          }
          
          return combined;
        });
        
        // Clear "new" status after animation
        setTimeout(() => {
          setCoachingMessages(prev => 
            prev.map(m => ({ ...m, isNew: false }))
          );
        }, 2000);
      }
    } catch (error) {
      console.error('Coaching error:', error);
    }
  }, [encounter, encounterType, coachingEnabled, lastCoachingTime, encounterCoachAPI]);

  /**
   * Process new transcription text through both analysis and coaching
   */
  const processTranscription = useCallback((text) => {
    if (enabled) {
      performAnalysis(text);
    }
    if (coachingEnabled) {
      performCoaching(text);
    }
  }, [enabled, coachingEnabled, performAnalysis, performCoaching]);

  /**
   * Clear immediate alert
   */
  const clearAlert = useCallback(() => {
    setImmediateAlert(null);
  }, []);

  /**
   * Get total violation count
   */
  const getTotalViolationCount = useCallback(() => {
    return detectedViolations.length + biasIndicators.length + proceduralIssues.length;
  }, [detectedViolations, biasIndicators, proceduralIssues]);

  /**
   * Reset all analysis state
   */
  const reset = useCallback(() => {
    setAiAnalysis(null);
    setRiskLevel('low');
    setDetectedViolations([]);
    setBiasIndicators([]);
    setProceduralIssues([]);
    setImmediateAlert(null);
    setFullTranscript('');
    setCoachingMessages([]);
    analysisQueueRef.current = [];
    lastAnalysisRef.current = 0;
  }, []);

  return {
    // Analysis state
    aiAnalysis,
    riskLevel,
    detectedViolations,
    biasIndicators,
    proceduralIssues,
    immediateAlert,
    fullTranscript,
    
    // Coaching state
    coachingMessages,
    
    // Actions
    processTranscription,
    performAnalysis,
    performCoaching,
    clearAlert,
    reset,
    
    // Computed
    getTotalViolationCount,
    hasViolations: getTotalViolationCount() > 0
  };
}

export default useEncounterAnalysis;
