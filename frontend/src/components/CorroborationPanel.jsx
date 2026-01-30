import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Separator } from './ui/separator';
import { Alert, AlertDescription } from './ui/alert';
import { corroborationAPI } from '../lib/api';
import { 
  Users, Search, Shield, AlertTriangle, CheckCircle, 
  MapPin, Clock, Scale, Loader2, ChevronRight, FileText,
  UserX, TrendingUp, Eye
} from 'lucide-react';
import { toast } from 'sonner';

export default function CorroborationPanel({ encounterId }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await corroborationAPI.analyze(encounterId);
      setResult(response.data);
      toast.success('Corroboration analysis complete');
    } catch (err) {
      console.error('Corroboration error:', err);
      setError(err.response?.data?.detail || 'Failed to analyze corroboration');
      toast.error('Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-blue-600';
    if (score >= 40) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBg = (score) => {
    if (score >= 80) return 'bg-green-100';
    if (score >= 60) return 'bg-blue-100';
    if (score >= 40) return 'bg-yellow-100';
    return 'bg-red-100';
  };

  if (!result) {
    return (
      <Card data-testid="corroboration-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-purple-500" />
            AI Witness Corroboration
          </CardTitle>
          <CardDescription>
            Find corroborating evidence from other reports, officer history, and public data
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          
          <div className="text-center py-6">
            <Users className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground mb-4">
              Search for evidence that supports your account from multiple sources
            </p>
            <Button onClick={runAnalysis} disabled={loading} data-testid="run-corroboration-btn">
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4 mr-2" />
                  Find Corroborating Evidence
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="corroboration-results">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5 text-purple-500" />
              Corroboration Analysis
            </CardTitle>
            <CardDescription>
              Generated {new Date(result.generated_at).toLocaleString()}
            </CardDescription>
          </div>
          <div className={`p-3 rounded-lg ${getScoreBg(result.corroboration_score)}`}>
            <p className={`text-2xl font-bold ${getScoreColor(result.corroboration_score)}`}>
              {result.corroboration_score}
            </p>
            <p className="text-xs text-muted-foreground">Score</p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Score Interpretation */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Corroboration Strength</span>
            <span className={`text-sm ${getScoreColor(result.corroboration_score)}`}>
              {result.score_interpretation?.split(' - ')[0]}
            </span>
          </div>
          <Progress value={result.corroboration_score} className="h-2" />
          <p className="text-xs text-muted-foreground mt-1">
            {result.score_interpretation}
          </p>
        </div>

        <Separator />

        {/* Summary Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-muted/50 rounded-lg">
            <MapPin className="h-5 w-5 mx-auto mb-1 text-blue-500" />
            <p className="text-lg font-bold">{result.nearby_encounters?.count || 0}</p>
            <p className="text-xs text-muted-foreground">Nearby Encounters</p>
          </div>
          <div className="text-center p-3 bg-muted/50 rounded-lg">
            <Shield className="h-5 w-5 mx-auto mb-1 text-orange-500" />
            <p className="text-lg font-bold">{result.officer_history?.total_prior_complaints || 0}</p>
            <p className="text-xs text-muted-foreground">Officer Complaints</p>
          </div>
          <div className="text-center p-3 bg-muted/50 rounded-lg">
            <FileText className="h-5 w-5 mx-auto mb-1 text-purple-500" />
            <p className="text-lg font-bold">{result.area_incidents?.count || 0}</p>
            <p className="text-xs text-muted-foreground">Area Incidents</p>
          </div>
          <div className="text-center p-3 bg-muted/50 rounded-lg">
            <TrendingUp className="h-5 w-5 mx-auto mb-1 text-red-500" />
            <p className="text-lg font-bold">{result.similar_violations?.count || 0}</p>
            <p className="text-xs text-muted-foreground">Similar Patterns</p>
          </div>
        </div>

        {/* AI Analysis */}
        {result.ai_analysis && (
          <>
            <Separator />
            <div>
              <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                <Scale className="h-4 w-4" />
                AI Legal Analysis
              </h4>
              <p className="text-sm text-muted-foreground bg-muted/30 p-3 rounded-lg">
                {result.ai_analysis}
              </p>
            </div>
          </>
        )}

        {/* Officer History Details */}
        {result.officer_history?.officers?.length > 0 && (
          <>
            <Separator />
            <div>
              <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                <Shield className="h-4 w-4" />
                Officer History
              </h4>
              <div className="space-y-2">
                {result.officer_history.officers.map((officer, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                    <div>
                      <p className="font-medium">{officer.officer_name || 'Unknown Officer'}</p>
                      <p className="text-xs text-muted-foreground">
                        Badge: {officer.badge_number || 'N/A'} | {officer.department || 'Unknown Dept'}
                      </p>
                    </div>
                    <div className="text-right">
                      {officer.accountability_score !== null ? (
                        <Badge variant={officer.risk_level === 'high' ? 'destructive' : 
                                        officer.risk_level === 'medium' ? 'warning' : 'secondary'}>
                          Score: {officer.accountability_score}
                        </Badge>
                      ) : (
                        <Badge variant="outline">
                          <UserX className="h-3 w-3 mr-1" />
                          Not in database
                        </Badge>
                      )}
                      {officer.complaint_count > 0 && (
                        <p className="text-xs text-red-500 mt-1">
                          {officer.complaint_count} prior complaint(s)
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Nearby Encounters */}
        {result.nearby_encounters?.matches?.length > 0 && (
          <>
            <Separator />
            <div>
              <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                <MapPin className="h-4 w-4" />
                Nearby Encounters ({result.nearby_encounters.count})
              </h4>
              <div className="space-y-2">
                {result.nearby_encounters.matches.slice(0, 3).map((enc, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-muted/30 rounded-lg text-sm">
                    <div>
                      <Badge variant="outline" className="mb-1">{enc.encounter_type?.replace(/_/g, ' ')}</Badge>
                      <p className="text-xs text-muted-foreground">{enc.address || 'Address not recorded'}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-medium">{enc.distance_miles} mi away</p>
                      <Badge variant={enc.relevance === 'high' ? 'default' : 'secondary'} className="text-xs">
                        {enc.relevance} relevance
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Legal Value Assessment */}
        {result.legal_value && (
          <>
            <Separator />
            <div>
              <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                <Scale className="h-4 w-4" />
                Legal Value: <Badge variant={
                  result.legal_value.overall === 'high' ? 'default' :
                  result.legal_value.overall === 'medium' ? 'secondary' : 'outline'
                }>{result.legal_value.overall}</Badge>
              </h4>
              
              {result.legal_value.strengths?.length > 0 && (
                <div className="mb-3">
                  <p className="text-xs font-medium text-green-600 mb-1">Strengths:</p>
                  <ul className="text-xs text-muted-foreground space-y-1">
                    {result.legal_value.strengths.map((s, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <CheckCircle className="h-3 w-3 text-green-500 mt-0.5 flex-shrink-0" />
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {result.legal_value.recommendations?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-blue-600 mb-1">Recommendations:</p>
                  <ul className="text-xs text-muted-foreground space-y-1">
                    {result.legal_value.recommendations.map((r, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <ChevronRight className="h-3 w-3 text-blue-500 mt-0.5 flex-shrink-0" />
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </>
        )}

        {/* Re-run button */}
        <div className="pt-4">
          <Button variant="outline" onClick={runAnalysis} disabled={loading} className="w-full">
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Re-analyzing...
              </>
            ) : (
              <>
                <Search className="h-4 w-4 mr-2" />
                Run New Analysis
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
