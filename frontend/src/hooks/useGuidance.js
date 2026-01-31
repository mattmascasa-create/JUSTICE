/**
 * useGuidance Hook
 * Fetches and manages AI-driven guidance suggestions
 */

import { useState, useEffect, useCallback } from 'react';
import api from '../lib/api';

export function useGuidance(currentPage = null) {
  const [suggestions, setSuggestions] = useState([]);
  const [allSuggestions, setAllSuggestions] = useState([]);
  const [completionScore, setCompletionScore] = useState(0);
  const [userStats, setUserStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchGuidance = useCallback(async () => {
    try {
      setLoading(true);
      const params = currentPage ? { current_page: currentPage } : {};
      const response = await api.get('/guidance/suggestions', { params });
      
      if (response.data.success) {
        const data = response.data.data;
        setSuggestions(data.suggestions || []);
        setAllSuggestions(data.all_suggestions || []);
        setCompletionScore(data.completion_score || 0);
        setUserStats(data.user_stats || null);
      }
      setError(null);
    } catch (err) {
      console.error('Failed to fetch guidance:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [currentPage]);

  useEffect(() => {
    fetchGuidance();
  }, [fetchGuidance]);

  const dismissSuggestion = useCallback(async (suggestionId) => {
    try {
      await api.post(`/api/guidance/dismiss/${suggestionId}`);
      setSuggestions(prev => prev.filter(s => s.id !== suggestionId));
      setAllSuggestions(prev => prev.filter(s => s.id !== suggestionId));
    } catch (err) {
      console.error('Failed to dismiss suggestion:', err);
    }
  }, []);

  const completeSuggestion = useCallback(async (suggestionId) => {
    try {
      await api.post(`/api/guidance/complete/${suggestionId}`);
      setSuggestions(prev => prev.filter(s => s.id !== suggestionId));
      setAllSuggestions(prev => prev.filter(s => s.id !== suggestionId));
      // Refresh to get updated completion score
      fetchGuidance();
    } catch (err) {
      console.error('Failed to complete suggestion:', err);
    }
  }, [fetchGuidance]);

  const refresh = useCallback(() => {
    fetchGuidance();
  }, [fetchGuidance]);

  return {
    suggestions,
    allSuggestions,
    completionScore,
    userStats,
    loading,
    error,
    dismissSuggestion,
    completeSuggestion,
    refresh,
    topSuggestion: suggestions[0] || null,
    hasCritical: suggestions.some(s => s.priority === 'critical'),
    hasHigh: suggestions.some(s => s.priority === 'high')
  };
}

export default useGuidance;
