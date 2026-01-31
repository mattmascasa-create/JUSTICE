/**
 * SmartGuidancePanel Component
 * 
 * AI-driven wizard that shows personalized next-step suggestions
 * Can be displayed as a floating panel, sidebar widget, or inline card
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { ScrollArea } from './ui/scroll-area';
import {
  Sparkles, ChevronRight, X, Clock, Users, Scale, Shield,
  FileText, CloudUpload, GraduationCap, FolderOpen, Tag,
  Share, AlertTriangle, Mail, FolderPlus, FileSearch,
  CheckCircle, ChevronDown, ChevronUp, Lightbulb
} from 'lucide-react';
import { useGuidance } from '../hooks/useGuidance';

// Icon mapping
const iconMap = {
  'users': Users,
  'scale': Scale,
  'shield': Shield,
  'file-text': FileText,
  'cloud-upload': CloudUpload,
  'graduation-cap': GraduationCap,
  'folder-open': FolderOpen,
  'folder-plus': FolderPlus,
  'tag': Tag,
  'share': Share,
  'alert-triangle': AlertTriangle,
  'mail': Mail,
  'file-search': FileSearch,
  'check-circle': CheckCircle,
};

// Priority styling
const priorityStyles = {
  critical: {
    badge: 'bg-red-500 text-white',
    border: 'border-red-500/50',
    bg: 'bg-red-500/5',
    icon: 'text-red-500'
  },
  high: {
    badge: 'bg-orange-500 text-white',
    border: 'border-orange-500/50',
    bg: 'bg-orange-500/5',
    icon: 'text-orange-500'
  },
  medium: {
    badge: 'bg-blue-500 text-white',
    border: 'border-blue-500/50',
    bg: 'bg-blue-500/5',
    icon: 'text-blue-500'
  },
  low: {
    badge: 'bg-gray-500 text-white',
    border: 'border-gray-500/30',
    bg: 'bg-gray-500/5',
    icon: 'text-gray-500'
  }
};

// Category labels
const categoryLabels = {
  setup: 'Setup',
  safety: 'Safety',
  legal: 'Legal',
  evidence: 'Evidence',
  action: 'Action Required'
};

/**
 * Single Suggestion Card
 */
function SuggestionCard({ suggestion, onAction, onDismiss, compact = false }) {
  const navigate = useNavigate();
  const IconComponent = iconMap[suggestion.icon] || Lightbulb;
  const style = priorityStyles[suggestion.priority] || priorityStyles.medium;

  const handleAction = () => {
    if (suggestion.action_url) {
      navigate(suggestion.action_url);
    }
    if (onAction) onAction(suggestion);
  };

  if (compact) {
    return (
      <div 
        className={`p-3 rounded-lg border ${style.border} ${style.bg} cursor-pointer hover:bg-opacity-20 transition-all group`}
        onClick={handleAction}
        data-testid={`suggestion-${suggestion.id}`}
      >
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg bg-background ${style.icon}`}>
            <IconComponent className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-sm truncate">{suggestion.title}</p>
            {suggestion.estimated_time && (
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock className="h-3 w-3" /> {suggestion.estimated_time}
              </p>
            )}
          </div>
          <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:translate-x-1 transition-transform" />
        </div>
      </div>
    );
  }

  return (
    <div 
      className={`p-4 rounded-lg border-2 ${style.border} ${style.bg} transition-all`}
      data-testid={`suggestion-${suggestion.id}`}
    >
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-lg bg-background ${style.icon}`}>
          <IconComponent className="h-5 w-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-semibold">{suggestion.title}</h4>
            {suggestion.priority === 'critical' && (
              <Badge className={style.badge}>Critical</Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground mb-3">{suggestion.description}</p>
          
          {suggestion.progress !== undefined && (
            <div className="mb-3">
              <Progress value={suggestion.progress} className="h-2" />
              <p className="text-xs text-muted-foreground mt-1">{Math.round(suggestion.progress)}% complete</p>
            </div>
          )}
          
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {suggestion.estimated_time && (
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" /> {suggestion.estimated_time}
                </span>
              )}
              {suggestion.category && (
                <Badge variant="outline" className="text-xs">
                  {categoryLabels[suggestion.category] || suggestion.category}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2">
              {onDismiss && (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={(e) => { e.stopPropagation(); onDismiss(suggestion.id); }}
                  className="h-8 px-2 text-muted-foreground hover:text-foreground"
                >
                  Dismiss
                </Button>
              )}
              <Button size="sm" onClick={handleAction} className="h-8">
                {suggestion.action_label || 'Do This'}
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Main Smart Guidance Panel
 */
export function SmartGuidancePanel({ 
  currentPage = null,
  variant = 'card', // 'card', 'floating', 'minimal', 'inline'
  maxSuggestions = 3,
  showProgress = true,
  collapsible = true,
  className = ''
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [showAll, setShowAll] = useState(false);
  
  const {
    suggestions,
    allSuggestions,
    completionScore,
    userStats,
    loading,
    dismissSuggestion,
    refresh,
    hasCritical,
    hasHigh
  } = useGuidance(currentPage);

  if (loading) {
    return (
      <Card className={`animate-pulse ${className}`}>
        <CardContent className="p-4">
          <div className="h-4 bg-muted rounded w-3/4 mb-2" />
          <div className="h-3 bg-muted rounded w-1/2" />
        </CardContent>
      </Card>
    );
  }

  if (suggestions.length === 0) {
    return null; // Don't show if no suggestions
  }

  const displaySuggestions = showAll ? allSuggestions : suggestions.slice(0, maxSuggestions);

  // Minimal inline variant
  if (variant === 'minimal') {
    const topSuggestion = suggestions[0];
    if (!topSuggestion) return null;
    
    return (
      <SuggestionCard 
        suggestion={topSuggestion} 
        compact 
        onDismiss={dismissSuggestion}
      />
    );
  }

  // Inline variant - just the suggestions
  if (variant === 'inline') {
    return (
      <div className={`space-y-3 ${className}`}>
        {displaySuggestions.map(suggestion => (
          <SuggestionCard
            key={suggestion.id}
            suggestion={suggestion}
            onDismiss={dismissSuggestion}
            compact
          />
        ))}
      </div>
    );
  }

  // Card and floating variants
  return (
    <Card className={`${hasCritical ? 'border-red-500/50' : hasHigh ? 'border-orange-500/30' : ''} ${className}`}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-purple-500" />
            Smart Guide
            {hasCritical && (
              <Badge className="bg-red-500 text-white animate-pulse">Action Needed</Badge>
            )}
          </CardTitle>
          <div className="flex items-center gap-2">
            {collapsible && (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => setIsExpanded(!isExpanded)}
                className="h-8 w-8 p-0"
              >
                {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            )}
          </div>
        </div>
        
        {showProgress && isExpanded && (
          <div className="mt-2">
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-muted-foreground">Profile Completion</span>
              <span className="font-medium">{completionScore}%</span>
            </div>
            <Progress value={completionScore} className="h-2" />
          </div>
        )}
      </CardHeader>
      
      {isExpanded && (
        <CardContent className="pt-2">
          <ScrollArea className={displaySuggestions.length > 3 ? 'h-[400px] pr-4' : ''}>
            <div className="space-y-3">
              {displaySuggestions.map(suggestion => (
                <SuggestionCard
                  key={suggestion.id}
                  suggestion={suggestion}
                  onDismiss={dismissSuggestion}
                />
              ))}
            </div>
          </ScrollArea>
          
          {allSuggestions.length > maxSuggestions && (
            <Button
              variant="ghost"
              className="w-full mt-3"
              onClick={() => setShowAll(!showAll)}
            >
              {showAll ? 'Show Less' : `Show ${allSuggestions.length - maxSuggestions} More`}
              {showAll ? <ChevronUp className="h-4 w-4 ml-1" /> : <ChevronDown className="h-4 w-4 ml-1" />}
            </Button>
          )}
          
          {userStats && (
            <div className="mt-4 pt-4 border-t grid grid-cols-4 gap-2 text-center">
              <div>
                <p className="text-lg font-bold">{userStats.encounters_count}</p>
                <p className="text-xs text-muted-foreground">Encounters</p>
              </div>
              <div>
                <p className="text-lg font-bold">{userStats.cases_count}</p>
                <p className="text-xs text-muted-foreground">Cases</p>
              </div>
              <div>
                <p className="text-lg font-bold">{userStats.contacts_count}</p>
                <p className="text-xs text-muted-foreground">Contacts</p>
              </div>
              <div>
                <p className="text-lg font-bold">{userStats.has_attorney ? '✓' : '—'}</p>
                <p className="text-xs text-muted-foreground">Attorney</p>
              </div>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}

/**
 * Floating Guidance Button - Opens a panel
 */
export function FloatingGuidanceButton({ currentPage = null }) {
  const [isOpen, setIsOpen] = useState(false);
  const { suggestions, hasCritical, hasHigh } = useGuidance(currentPage);

  if (suggestions.length === 0) return null;

  return (
    <>
      {/* Floating Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`fixed bottom-20 right-4 z-40 p-3 rounded-full shadow-lg transition-all ${
          hasCritical 
            ? 'bg-red-500 hover:bg-red-600 animate-pulse' 
            : hasHigh 
              ? 'bg-orange-500 hover:bg-orange-600'
              : 'bg-purple-500 hover:bg-purple-600'
        }`}
        data-testid="guidance-floating-btn"
      >
        <Sparkles className="h-6 w-6 text-white" />
        {suggestions.length > 0 && (
          <span className="absolute -top-1 -right-1 bg-white text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center text-purple-600">
            {suggestions.length}
          </span>
        )}
      </button>

      {/* Panel */}
      {isOpen && (
        <div className="fixed bottom-36 right-4 z-50 w-96 max-w-[calc(100vw-2rem)]">
          <div className="relative">
            <Button
              variant="ghost"
              size="sm"
              className="absolute -top-2 -right-2 z-10 h-8 w-8 p-0 rounded-full bg-background shadow"
              onClick={() => setIsOpen(false)}
            >
              <X className="h-4 w-4" />
            </Button>
            <SmartGuidancePanel 
              currentPage={currentPage}
              variant="floating"
              collapsible={false}
            />
          </div>
        </div>
      )}
    </>
  );
}

/**
 * Contextual Tip - Shows a single relevant tip based on page
 */
export function ContextualTip({ currentPage }) {
  const { topSuggestion, loading } = useGuidance(currentPage);
  const navigate = useNavigate();

  if (loading || !topSuggestion || !topSuggestion.contextual) return null;

  const style = priorityStyles[topSuggestion.priority] || priorityStyles.medium;
  const IconComponent = iconMap[topSuggestion.icon] || Lightbulb;

  return (
    <div 
      className={`p-3 rounded-lg border ${style.border} ${style.bg} flex items-center gap-3 cursor-pointer hover:opacity-90 transition-opacity`}
      onClick={() => navigate(topSuggestion.action_url)}
      data-testid="contextual-tip"
    >
      <IconComponent className={`h-5 w-5 ${style.icon}`} />
      <div className="flex-1">
        <p className="font-medium text-sm">{topSuggestion.title}</p>
        <p className="text-xs text-muted-foreground">{topSuggestion.description}</p>
      </div>
      <Button size="sm" variant="outline">
        {topSuggestion.action_label || 'Do This'}
      </Button>
    </div>
  );
}

export default SmartGuidancePanel;
