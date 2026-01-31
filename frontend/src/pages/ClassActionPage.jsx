/**
 * Class Action Finder Page
 * 
 * AI-powered pattern matching to identify potential class action opportunities
 * based on similar violations across users.
 * 
 * Features:
 * - Pattern analysis
 * - Similarity scoring
 * - User connection for collective action
 */

import React, { useState, useEffect, useCallback } from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Alert, AlertDescription } from '../components/ui/alert';
import { ScrollArea } from '../components/ui/scroll-area';
import { Progress } from '../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '../components/ui/dialog';
import { Textarea } from '../components/ui/textarea';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import api from '../lib/api';
import {
  Scale, Users, TrendingUp, Search, AlertTriangle,
  CheckCircle, ChevronRight, Loader2, Sparkles,
  Building, FileText, Handshake, Shield, ArrowRight,
  BarChart3, Target, Zap, RefreshCw
} from 'lucide-react';

// Class Action API
const classActionAPI = {
  analyze: (data) => api.post('/class-action/analyze', data),
  expressInterest: (data) => api.post('/class-action/express-interest', data),
  getPatterns: (params) => api.get('/class-action/patterns', { params }),
  getMyPatterns: () => api.get('/class-action/my-patterns'),
  getStats: () => api.get('/class-action/stats'),
  getPatternDetails: (id) => api.get(`/class-action/pattern/${id}`)
};

// Strength colors
const strengthColors = {
  very_strong: 'bg-green-500 text-white',
  strong: 'bg-blue-500 text-white',
  moderate: 'bg-yellow-500 text-black',
  weak: 'bg-orange-500 text-white',
  insufficient: 'bg-gray-500 text-white'
};

const strengthLabels = {
  very_strong: 'Very Strong',
  strong: 'Strong',
  moderate: 'Moderate',
  weak: 'Weak',
  insufficient: 'Insufficient'
};

export default function ClassActionPage() {
  const [activeTab, setActiveTab] = useState('analyze');
  
  // Analysis state
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  
  // Patterns state
  const [patterns, setPatterns] = useState([]);
  const [myPatterns, setMyPatterns] = useState({ analyzed: [], interested: [] });
  const [patternsLoading, setPatternsLoading] = useState(false);
  
  // Stats state
  const [stats, setStats] = useState(null);
  
  // Interest dialog state
  const [showInterestDialog, setShowInterestDialog] = useState(false);
  const [selectedPattern, setSelectedPattern] = useState(null);
  const [interestNotes, setInterestNotes] = useState('');
  const [contactConsent, setContactConsent] = useState(true);
  const [submittingInterest, setSubmittingInterest] = useState(false);

  // Load data
  const loadStats = useCallback(async () => {
    try {
      const res = await classActionAPI.getStats();
      setStats(res.data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  }, []);

  const loadPatterns = useCallback(async () => {
    try {
      setPatternsLoading(true);
      const [patternsRes, myPatternsRes] = await Promise.all([
        classActionAPI.getPatterns({ min_strength: 'moderate' }),
        classActionAPI.getMyPatterns()
      ]);
      setPatterns(patternsRes.data.patterns || []);
      setMyPatterns({
        analyzed: myPatternsRes.data.analyzed_patterns || [],
        interested: myPatternsRes.data.interested_patterns || []
      });
    } catch (error) {
      console.error('Failed to load patterns:', error);
    } finally {
      setPatternsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
    loadPatterns();
  }, [loadStats, loadPatterns]);

  // Run analysis
  const runAnalysis = async () => {
    try {
      setAnalyzing(true);
      const res = await classActionAPI.analyze({
        date_range_days: 365
      });
      setAnalysisResult(res.data);
      
      if (res.data.class_action_viable) {
        toast.success('Strong pattern found! Review the analysis below.');
      } else {
        toast.info('Analysis complete. Review results below.');
      }
    } catch (error) {
      toast.error('Analysis failed. Make sure you have reported violations.');
    } finally {
      setAnalyzing(false);
    }
  };

  // Express interest
  const handleExpressInterest = async () => {
    if (!selectedPattern) return;

    try {
      setSubmittingInterest(true);
      const res = await classActionAPI.expressInterest({
        pattern_id: selectedPattern.pattern_id,
        contact_consent: contactConsent,
        notes: interestNotes
      });
      
      toast.success('Your interest has been recorded');
      setShowInterestDialog(false);
      setInterestNotes('');
      loadPatterns();
    } catch (error) {
      toast.error('Failed to register interest');
    } finally {
      setSubmittingInterest(false);
    }
  };

  return (
    <AppLayout>
      <div className="max-w-5xl mx-auto space-y-6" data-testid="class-action-page">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center p-4 rounded-full bg-purple-500/20">
            <Scale className="h-12 w-12 text-purple-500" />
          </div>
          <h1 className="text-3xl font-bold">Class Action Finder</h1>
          <p className="text-muted-foreground max-w-lg mx-auto">
            AI-powered analysis finds others with similar violations.
            <strong> Strength in numbers.</strong>
          </p>
        </div>

        {/* Quick Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-3xl font-bold text-purple-500">{stats.total_patterns_analyzed || 0}</p>
                <p className="text-sm text-muted-foreground">Patterns Analyzed</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-3xl font-bold text-green-500">{stats.viable_class_actions || 0}</p>
                <p className="text-sm text-muted-foreground">Viable Class Actions</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-3xl font-bold text-blue-500">{stats.total_interested_users || 0}</p>
                <p className="text-sm text-muted-foreground">Users Interested</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-3xl font-bold text-orange-500">
                  {stats.most_common_violations?.[0]?.count || 0}
                </p>
                <p className="text-sm text-muted-foreground truncate">
                  {stats.most_common_violations?.[0]?.type?.replace(/_/g, ' ') || 'Top Violation'}
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Main Content */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="analyze">
              <Search className="h-4 w-4 mr-2" />
              Analyze My Case
            </TabsTrigger>
            <TabsTrigger value="patterns">
              <TrendingUp className="h-4 w-4 mr-2" />
              Active Patterns
            </TabsTrigger>
            <TabsTrigger value="my-activity">
              <FileText className="h-4 w-4 mr-2" />
              My Activity
            </TabsTrigger>
          </TabsList>

          {/* Analyze Tab */}
          <TabsContent value="analyze" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-purple-500" />
                  AI Pattern Analysis
                </CardTitle>
                <CardDescription>
                  Scan your violations against our database to find similar cases
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Alert>
                  <Target className="h-4 w-4" />
                  <AlertDescription>
                    This analysis compares your reported violations with others in our system
                    to identify patterns that could support a class action lawsuit.
                  </AlertDescription>
                </Alert>

                <Button
                  onClick={runAnalysis}
                  disabled={analyzing}
                  className="w-full"
                  size="lg"
                >
                  {analyzing ? (
                    <>
                      <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                      Analyzing patterns...
                    </>
                  ) : (
                    <>
                      <Search className="h-5 w-5 mr-2" />
                      Run Pattern Analysis
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>

            {/* Analysis Results */}
            {analysisResult && (
              <Card className={analysisResult.class_action_viable 
                ? 'border-2 border-green-500/50 bg-green-500/5' 
                : ''
              }>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>Analysis Results</CardTitle>
                    <Badge className={strengthColors[analysisResult.pattern_strength?.strength]}>
                      {strengthLabels[analysisResult.pattern_strength?.strength] || 'Unknown'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Summary */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center p-3 rounded-lg bg-muted/50">
                      <p className="text-2xl font-bold">{analysisResult.similar_cases_found || 0}</p>
                      <p className="text-xs text-muted-foreground">Similar Cases</p>
                    </div>
                    <div className="text-center p-3 rounded-lg bg-muted/50">
                      <p className="text-2xl font-bold">
                        {analysisResult.pattern_strength?.factors?.users_affected || 0}
                      </p>
                      <p className="text-xs text-muted-foreground">Users Affected</p>
                    </div>
                    <div className="text-center p-3 rounded-lg bg-muted/50">
                      <p className="text-2xl font-bold">
                        {analysisResult.departments_with_pattern?.length || 0}
                      </p>
                      <p className="text-xs text-muted-foreground">Departments</p>
                    </div>
                    <div className="text-center p-3 rounded-lg bg-muted/50">
                      <p className="text-2xl font-bold">
                        {analysisResult.pattern_strength?.score || 0}
                      </p>
                      <p className="text-xs text-muted-foreground">Pattern Score</p>
                    </div>
                  </div>

                  {/* Violation Breakdown */}
                  {analysisResult.breakdown_by_type?.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-3">Violation Breakdown</h4>
                      <div className="space-y-2">
                        {analysisResult.breakdown_by_type.slice(0, 5).map((item, i) => (
                          <div key={i} className="flex items-center justify-between p-2 rounded bg-muted/30">
                            <span className="text-sm capitalize">
                              {item.violation_type?.replace(/_/g, ' ')}
                            </span>
                            <div className="flex items-center gap-2">
                              <Badge variant="outline">{item.count} cases</Badge>
                              <Badge variant="secondary">{item.users_affected} users</Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* AI Analysis */}
                  {analysisResult.ai_analysis && (
                    <div>
                      <h4 className="font-medium mb-3 flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-purple-500" />
                        AI Legal Analysis
                      </h4>
                      <div className="p-4 rounded-lg bg-purple-500/10 border border-purple-500/20">
                        <p className="text-sm whitespace-pre-wrap">{analysisResult.ai_analysis}</p>
                      </div>
                    </div>
                  )}

                  {/* Next Steps */}
                  {analysisResult.next_steps?.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-3">Recommended Next Steps</h4>
                      <div className="space-y-2">
                        {analysisResult.next_steps.map((step, i) => (
                          <div key={i} className="flex items-start gap-2">
                            <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                            <span className="text-sm">{step}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Action */}
                  {analysisResult.class_action_viable && (
                    <Alert className="bg-green-500/10 border-green-500/30">
                      <Handshake className="h-4 w-4 text-green-500" />
                      <AlertDescription>
                        <strong>Strong Pattern Detected!</strong> Consider connecting with other
                        affected users and consulting a civil rights attorney about collective action.
                      </AlertDescription>
                    </Alert>
                  )}
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Active Patterns Tab */}
          <TabsContent value="patterns" className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Showing patterns with moderate or stronger viability
              </p>
              <Button variant="outline" size="sm" onClick={loadPatterns} disabled={patternsLoading}>
                <RefreshCw className={`h-4 w-4 mr-2 ${patternsLoading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>

            <ScrollArea className="h-[500px]">
              {patterns.length > 0 ? (
                <div className="space-y-3">
                  {patterns.map((pattern) => (
                    <Card key={pattern.pattern_id} className="hover:bg-muted/50 transition-colors">
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between">
                          <div className="space-y-1 flex-1">
                            <div className="flex items-center gap-2">
                              <Badge className={strengthColors[pattern.strength?.strength]}>
                                {strengthLabels[pattern.strength?.strength]}
                              </Badge>
                              <Badge variant="outline">
                                {pattern.similar_count} similar cases
                              </Badge>
                              {pattern.interested_users > 0 && (
                                <Badge variant="secondary">
                                  <Users className="h-3 w-3 mr-1" />
                                  {pattern.interested_users} interested
                                </Badge>
                              )}
                            </div>
                            <p className="text-sm">
                              <strong>Violations:</strong>{' '}
                              {pattern.violation_types?.slice(0, 3).map(v => 
                                v.replace(/_/g, ' ')
                              ).join(', ')}
                              {pattern.violation_types?.length > 3 && 
                                ` +${pattern.violation_types.length - 3} more`
                              }
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {pattern.strength?.factors?.users_affected} users affected • 
                              Score: {pattern.strength?.score}
                            </p>
                          </div>
                          <Button
                            size="sm"
                            onClick={() => {
                              setSelectedPattern(pattern);
                              setShowInterestDialog(true);
                            }}
                          >
                            Express Interest
                            <ChevronRight className="h-4 w-4 ml-1" />
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Scale className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="font-medium">No Strong Patterns Yet</p>
                  <p className="text-sm text-muted-foreground">
                    Run an analysis to discover patterns in the data
                  </p>
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          {/* My Activity Tab */}
          <TabsContent value="my-activity" className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              {/* My Analyses */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">My Analyses</CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[300px]">
                    {myPatterns.analyzed.length > 0 ? (
                      <div className="space-y-2">
                        {myPatterns.analyzed.map((pattern) => (
                          <div
                            key={pattern.pattern_id}
                            className="p-3 rounded-lg border"
                          >
                            <div className="flex items-center justify-between mb-1">
                              <Badge className={strengthColors[pattern.strength?.strength]} variant="secondary">
                                {strengthLabels[pattern.strength?.strength]}
                              </Badge>
                              <span className="text-xs text-muted-foreground">
                                {new Date(pattern.created_at).toLocaleDateString()}
                              </span>
                            </div>
                            <p className="text-sm">{pattern.similar_count} similar cases found</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-center text-muted-foreground py-8">
                        No analyses yet. Run your first analysis above.
                      </p>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>

              {/* My Interests */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Patterns I'm Following</CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[300px]">
                    {myPatterns.interested.length > 0 ? (
                      <div className="space-y-2">
                        {myPatterns.interested.map((pattern) => (
                          <div
                            key={pattern.pattern_id}
                            className="p-3 rounded-lg border"
                          >
                            <div className="flex items-center gap-2 mb-1">
                              <Badge className={strengthColors[pattern.strength?.strength]} variant="secondary">
                                {strengthLabels[pattern.strength?.strength]}
                              </Badge>
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            </div>
                            <p className="text-sm">{pattern.similar_count} similar cases</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-center text-muted-foreground py-8">
                        You haven't expressed interest in any patterns yet.
                      </p>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        {/* Interest Dialog */}
        <Dialog open={showInterestDialog} onOpenChange={setShowInterestDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Express Interest in Class Action</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              {selectedPattern && (
                <Alert>
                  <Scale className="h-4 w-4" />
                  <AlertDescription>
                    This pattern has {selectedPattern.similar_count} similar cases with a{' '}
                    <strong>{strengthLabels[selectedPattern.strength?.strength]}</strong> strength rating.
                  </AlertDescription>
                </Alert>
              )}

              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div>
                  <p className="font-medium">Share my contact info</p>
                  <p className="text-xs text-muted-foreground">
                    Allow attorneys and other affected users to contact you
                  </p>
                </div>
                <Switch
                  checked={contactConsent}
                  onCheckedChange={setContactConsent}
                />
              </div>

              <div className="space-y-2">
                <Label>Additional Notes (optional)</Label>
                <Textarea
                  placeholder="Any additional information about your case..."
                  value={interestNotes}
                  onChange={(e) => setInterestNotes(e.target.value)}
                />
              </div>

              <div className="text-sm text-muted-foreground">
                <p><strong>What happens next:</strong></p>
                <ul className="list-disc list-inside mt-1 space-y-1">
                  <li>You'll be notified when a class action is formally initiated</li>
                  <li>Attorneys monitoring this pattern will see aggregated interest</li>
                  <li>Your info is only shared if you consented above</li>
                </ul>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowInterestDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleExpressInterest} disabled={submittingInterest}>
                {submittingInterest ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Handshake className="h-4 w-4 mr-2" />
                )}
                Express Interest
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  );
}
