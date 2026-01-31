/**
 * ViolationsPanel Component
 * Displays detected violations, bias indicators, and procedural issues
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { ScrollArea } from '../../components/ui/scroll-area';
import { Button } from '../../components/ui/button';
import { AlertTriangle, Scale, Eye, ChevronRight, X } from 'lucide-react';
import { riskLevelColors, riskLevelLabels } from './constants';

export function ViolationsPanel({
  isOpen,
  onClose,
  riskLevel = 'low',
  detectedViolations = [],
  biasIndicators = [],
  proceduralIssues = [],
  manualMarks = []
}) {
  const totalCount = detectedViolations.length + biasIndicators.length + proceduralIssues.length + manualMarks.length;

  if (!isOpen) {
    return null;
  }

  return (
    <Card className="border-red-500/30 bg-red-500/5">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            Detected Issues ({totalCount})
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        
        {/* Risk Level Indicator */}
        <div className="flex items-center gap-2 mt-2">
          <span className="text-sm text-muted-foreground">Risk Level:</span>
          <Badge className={`${riskLevelColors[riskLevel]} text-white`}>
            {riskLevelLabels[riskLevel]}
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent>
        <ScrollArea className="h-[300px] pr-4">
          <div className="space-y-4">
            {/* Rights Violations */}
            {detectedViolations.length > 0 && (
              <div>
                <h4 className="font-medium text-red-500 flex items-center gap-2 mb-2">
                  <Scale className="h-4 w-4" />
                  Rights Violations ({detectedViolations.length})
                </h4>
                <div className="space-y-2">
                  {detectedViolations.map((violation, idx) => (
                    <div 
                      key={idx} 
                      className="p-3 rounded-lg bg-red-500/10 border border-red-500/20"
                    >
                      <p className="font-medium text-sm">{violation.type || violation}</p>
                      {violation.quote && (
                        <p className="text-xs text-muted-foreground mt-1 italic">
                          &ldquo;{violation.quote}&rdquo;
                        </p>
                      )}
                      {violation.severity && (
                        <Badge 
                          variant="outline" 
                          className="mt-2 text-xs"
                        >
                          Severity: {violation.severity}
                        </Badge>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Bias Indicators */}
            {biasIndicators.length > 0 && (
              <div>
                <h4 className="font-medium text-orange-500 flex items-center gap-2 mb-2">
                  <Eye className="h-4 w-4" />
                  Bias Indicators ({biasIndicators.length})
                </h4>
                <div className="space-y-2">
                  {biasIndicators.map((indicator, idx) => (
                    <div 
                      key={idx} 
                      className="p-3 rounded-lg bg-orange-500/10 border border-orange-500/20"
                    >
                      <p className="text-sm">{indicator}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Procedural Issues */}
            {proceduralIssues.length > 0 && (
              <div>
                <h4 className="font-medium text-yellow-500 flex items-center gap-2 mb-2">
                  <ChevronRight className="h-4 w-4" />
                  Procedural Issues ({proceduralIssues.length})
                </h4>
                <div className="space-y-2">
                  {proceduralIssues.map((issue, idx) => (
                    <div 
                      key={idx} 
                      className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20"
                    >
                      <p className="text-sm">{issue}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Manual Marks */}
            {manualMarks.length > 0 && (
              <div>
                <h4 className="font-medium text-purple-500 flex items-center gap-2 mb-2">
                  <AlertTriangle className="h-4 w-4" />
                  Manual Marks ({manualMarks.length})
                </h4>
                <div className="space-y-2">
                  {manualMarks.map((mark, idx) => (
                    <div 
                      key={idx} 
                      className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/20"
                    >
                      <p className="text-sm font-medium">
                        Marked at {formatTime(mark.timestamp)}
                      </p>
                      {mark.note && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {mark.note}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {totalCount === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <Scale className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No issues detected so far.</p>
                <p className="text-sm mt-1">AI is actively monitoring the encounter.</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

// Helper to format timestamp
function formatTime(seconds) {
  if (typeof seconds !== 'number') return '--:--';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export default ViolationsPanel;
