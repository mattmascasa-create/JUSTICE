import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { 
  BarChart3, TrendingUp, TrendingDown, MapPin, Clock, 
  AlertTriangle, Shield, Activity, Users, Calendar,
  Gauge, Target, Eye, FileText, ChevronRight, RefreshCw,
  ThermometerSun, Flame, AlertCircle, CheckCircle
} from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Helper to make API calls
const fetchAPI = async (endpoint, token) => {
  const response = await fetch(`${API_URL}${endpoint}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!response.ok) throw new Error('API Error');
  return response.json();
};

// Tone color mapping
const toneColors = {
  professional: 'bg-green-500',
  calm: 'bg-green-400',
  assertive: 'bg-blue-500',
  anxious: 'bg-yellow-500',
  defensive: 'bg-yellow-400',
  compliant: 'bg-green-300',
  aggressive: 'bg-red-500',
  intimidating: 'bg-orange-500',
  hostile: 'bg-red-600',
  neutral: 'bg-gray-500'
};

// Day abbreviations
const dayAbbrev = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function EncounterAnalytics() {
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [patterns, setPatterns] = useState(null);
  const [hotspots, setHotspots] = useState(null);
  const [trends, setTrends] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  const fetchAllData = async () => {
    const token = localStorage.getItem('justice-token');
    if (!token) {
      toast.error('Please login to view analytics');
      return;
    }

    setLoading(true);
    try {
      const [summaryData, patternsData, hotspotsData, trendsData] = await Promise.all([
        fetchAPI('/api/analytics/encounters/summary', token),
        fetchAPI('/api/analytics/encounters/patterns', token),
        fetchAPI('/api/analytics/encounters/hotspots', token),
        fetchAPI('/api/analytics/encounters/trends?days=30', token)
      ]);
      
      setSummary(summaryData);
      setPatterns(patternsData);
      setHotspots(hotspotsData);
      setTrends(trendsData);
    } catch (error) {
      console.error('Analytics fetch error:', error);
      toast.error('Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading analytics...</p>
          </div>
        </div>
      </AppLayout>
    );
  }

  const getRiskColor = (score) => {
    if (score >= 70) return 'text-red-500';
    if (score >= 40) return 'text-orange-500';
    if (score >= 20) return 'text-yellow-500';
    return 'text-green-500';
  };

  const getRiskLabel = (score) => {
    if (score >= 70) return 'High Risk';
    if (score >= 40) return 'Elevated';
    if (score >= 20) return 'Moderate';
    return 'Low Risk';
  };

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="encounter-analytics">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-serif text-3xl font-bold flex items-center gap-3">
              <BarChart3 className="h-8 w-8 text-primary" />
              Encounter Analytics
            </h1>
            <p className="text-muted-foreground mt-1">
              Insights from your police encounter recordings
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchAllData} data-testid="refresh-analytics">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
            <Link to="/encounter">
              <Button data-testid="new-encounter-btn">
                <Shield className="h-4 w-4 mr-2" />
                Start Encounter
              </Button>
            </Link>
          </div>
        </div>

        {/* Risk Score Banner */}
        {summary && (
          <Card className={`border-2 ${summary.risk_score >= 50 ? 'border-red-500/50 bg-red-500/5' : 'border-green-500/50 bg-green-500/5'}`}>
            <CardContent className="py-6">
              <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                <div className="flex items-center gap-4">
                  <div className={`p-4 rounded-full ${summary.risk_score >= 50 ? 'bg-red-500/20' : 'bg-green-500/20'}`}>
                    <Gauge className={`h-10 w-10 ${getRiskColor(summary.risk_score)}`} />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Overall Risk Score</p>
                    <p className={`text-4xl font-bold ${getRiskColor(summary.risk_score)}`}>
                      {summary.risk_score}/100
                    </p>
                    <Badge variant={summary.risk_score >= 50 ? 'destructive' : 'secondary'}>
                      {getRiskLabel(summary.risk_score)}
                    </Badge>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-6 text-center">
                  <div>
                    <p className="text-2xl font-bold">{summary.total_encounters}</p>
                    <p className="text-xs text-muted-foreground">Total Encounters</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-orange-500">{summary.officer_demeanor?.avg_aggression || 0}%</p>
                    <p className="text-xs text-muted-foreground">Avg Aggression</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-green-500">{summary.officer_demeanor?.avg_professionalism || 0}%</p>
                    <p className="text-xs text-muted-foreground">Avg Professionalism</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Tabs Navigation */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid grid-cols-4 w-full max-w-lg">
            <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
            <TabsTrigger value="patterns" data-testid="tab-patterns">Patterns</TabsTrigger>
            <TabsTrigger value="violations" data-testid="tab-violations">Violations</TabsTrigger>
            <TabsTrigger value="locations" data-testid="tab-locations">Locations</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Total Encounters</p>
                      <p className="text-3xl font-bold">{summary?.total_encounters || 0}</p>
                    </div>
                    <FileText className="h-8 w-8 text-muted-foreground/50" />
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Active</p>
                      <p className="text-3xl font-bold text-green-500">{summary?.active_encounters || 0}</p>
                    </div>
                    <Activity className="h-8 w-8 text-green-500/50" />
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Max Aggression</p>
                      <p className="text-3xl font-bold text-red-500">{summary?.officer_demeanor?.max_aggression || 0}%</p>
                    </div>
                    <Flame className="h-8 w-8 text-red-500/50" />
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Violations</p>
                      <p className="text-3xl font-bold text-orange-500">
                        {summary?.violations_by_type?.reduce((a, v) => a + v.count, 0) || 0}
                      </p>
                    </div>
                    <AlertTriangle className="h-8 w-8 text-orange-500/50" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Officer Demeanor Analysis */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  Officer Demeanor Analysis
                </CardTitle>
                <CardDescription>Average metrics across all your encounters</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Professionalism</span>
                    <span className="text-sm font-medium text-green-500">
                      {summary?.officer_demeanor?.avg_professionalism || 0}%
                    </span>
                  </div>
                  <Progress 
                    value={summary?.officer_demeanor?.avg_professionalism || 0} 
                    className="h-2 bg-muted"
                  />
                </div>
                
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Aggression Level</span>
                    <span className="text-sm font-medium text-red-500">
                      {summary?.officer_demeanor?.avg_aggression || 0}%
                    </span>
                  </div>
                  <Progress 
                    value={summary?.officer_demeanor?.avg_aggression || 0} 
                    className="h-2 bg-muted [&>div]:bg-red-500"
                  />
                </div>
                
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Intimidation Level</span>
                    <span className="text-sm font-medium text-orange-500">
                      {summary?.officer_demeanor?.avg_intimidation || 0}%
                    </span>
                  </div>
                  <Progress 
                    value={summary?.officer_demeanor?.avg_intimidation || 0} 
                    className="h-2 bg-muted [&>div]:bg-orange-500"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Tone Distribution */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ThermometerSun className="h-5 w-5" />
                  Tone Distribution
                </CardTitle>
                <CardDescription>Detected emotional tones across transcriptions</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  {summary?.tone_distribution?.slice(0, 10).map((tone, i) => (
                    <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-muted/30">
                      <div className={`w-3 h-3 rounded-full ${toneColors[tone.tone] || 'bg-gray-500'}`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate capitalize">{tone.tone}</p>
                        <p className="text-xs text-muted-foreground">{tone.count} times</p>
                      </div>
                    </div>
                  )) || <p className="text-muted-foreground col-span-5 text-center py-4">No tone data yet</p>}
                </div>
              </CardContent>
            </Card>

            {/* Escalation Stats */}
            {summary?.escalation_stats?.length > 0 && (
              <Card className="border-orange-500/30">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-orange-500">
                    <TrendingUp className="h-5 w-5" />
                    Escalation Events
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex gap-4">
                    {summary.escalation_stats.map((es, i) => (
                      <Badge key={i} variant="outline" className="text-sm py-1 px-3">
                        {es.direction === 'escalating' ? '📈' : es.direction === 'de-escalating' ? '📉' : '➡️'}
                        {' '}{es.direction}: {es.count}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Patterns Tab */}
          <TabsContent value="patterns" className="space-y-6">
            {/* Time of Day */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  Time of Day Distribution
                </CardTitle>
                <CardDescription>
                  Peak hour: {patterns?.peak_hour !== null ? `${patterns.peak_hour}:00` : 'N/A'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-end gap-1 h-32">
                  {patterns?.by_hour?.map((h, i) => (
                    <div 
                      key={i} 
                      className="flex-1 bg-primary/20 hover:bg-primary/40 transition-colors rounded-t relative group"
                      style={{ height: `${Math.max(4, (h.count / Math.max(...patterns.by_hour.map(x => x.count), 1)) * 100)}%` }}
                    >
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Badge variant="secondary" className="text-xs whitespace-nowrap">
                          {h.hour}:00 - {h.count}
                        </Badge>
                      </div>
                    </div>
                  )) || <p className="text-muted-foreground w-full text-center py-8">No time data</p>}
                </div>
                <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                  <span>12am</span>
                  <span>6am</span>
                  <span>12pm</span>
                  <span>6pm</span>
                  <span>12am</span>
                </div>
              </CardContent>
            </Card>

            {/* Day of Week */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5" />
                  Day of Week Distribution
                </CardTitle>
                <CardDescription>
                  Peak day: {patterns?.peak_day || 'N/A'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-7 gap-2">
                  {patterns?.by_day?.map((d, i) => (
                    <div key={i} className="text-center">
                      <div 
                        className="h-20 bg-primary/20 rounded-t flex items-end justify-center mb-1 relative"
                      >
                        <div 
                          className="w-full bg-primary rounded-t transition-all"
                          style={{ height: `${Math.max(8, (d.count / Math.max(...patterns.by_day.map(x => x.count), 1)) * 100)}%` }}
                        />
                      </div>
                      <p className="text-xs font-medium">{dayAbbrev[d.day_index]}</p>
                      <p className="text-xs text-muted-foreground">{d.count}</p>
                    </div>
                  )) || <p className="text-muted-foreground col-span-7 text-center py-8">No day data</p>}
                </div>
              </CardContent>
            </Card>

            {/* Encounter Types */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="h-5 w-5" />
                  Encounter Types
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {patterns?.by_type?.map((t, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="flex-1">
                        <div className="flex justify-between mb-1">
                          <span className="text-sm capitalize">{t.type.replace(/_/g, ' ')}</span>
                          <span className="text-sm text-muted-foreground">{t.count}</span>
                        </div>
                        <Progress 
                          value={(t.count / Math.max(...patterns.by_type.map(x => x.count), 1)) * 100} 
                          className="h-2"
                        />
                      </div>
                    </div>
                  )) || <p className="text-muted-foreground text-center py-4">No type data</p>}
                </div>
              </CardContent>
            </Card>

            {/* 30-Day Trend */}
            {trends && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5" />
                    30-Day Trend
                  </CardTitle>
                  <CardDescription>
                    {trends.total_encounters} encounters ({trends.avg_encounters_per_day}/day average)
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-end gap-0.5 h-24">
                    {trends.daily_data?.slice(-30).map((d, i) => (
                      <div 
                        key={i}
                        className="flex-1 bg-primary/30 hover:bg-primary/50 rounded-t transition-colors relative group"
                        style={{ 
                          height: `${Math.max(4, (d.encounters / Math.max(...trends.daily_data.map(x => x.encounters), 1)) * 100)}%`,
                          backgroundColor: d.avg_aggression > 50 ? `rgba(239, 68, 68, ${d.avg_aggression / 100})` : undefined
                        }}
                      >
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                          <Badge variant="secondary" className="text-xs whitespace-nowrap">
                            {d.date.slice(5)}: {d.encounters}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Violations Tab */}
          <TabsContent value="violations" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-orange-500" />
                  Detected Violations
                </CardTitle>
                <CardDescription>
                  Rights violations identified by AI analysis
                </CardDescription>
              </CardHeader>
              <CardContent>
                {summary?.violations_by_type?.length > 0 ? (
                  <div className="space-y-3">
                    {summary.violations_by_type.map((v, i) => (
                      <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
                        <div className={`p-2 rounded-full ${
                          v.type.includes('unlawful') ? 'bg-red-500/20 text-red-500' :
                          v.type.includes('intimidation') || v.type.includes('coercion') ? 'bg-orange-500/20 text-orange-500' :
                          'bg-yellow-500/20 text-yellow-500'
                        }`}>
                          <AlertCircle className="h-5 w-5" />
                        </div>
                        <div className="flex-1">
                          <p className="font-medium capitalize">{v.type.replace(/_/g, ' ')}</p>
                          <p className="text-sm text-muted-foreground">{v.count} occurrence{v.count !== 1 ? 's' : ''}</p>
                        </div>
                        <Badge variant="outline">{v.count}</Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <CheckCircle className="h-12 w-12 mx-auto text-green-500 mb-3" />
                    <p className="text-muted-foreground">No violations detected yet</p>
                    <p className="text-sm text-muted-foreground mt-1">Violations will appear here when detected during encounters</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Locations Tab */}
          <TabsContent value="locations" className="space-y-6">
            {/* Hotspots */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MapPin className="h-5 w-5 text-red-500" />
                  Geographic Hotspots
                </CardTitle>
                <CardDescription>
                  {hotspots?.total_mapped || 0} encounters mapped
                </CardDescription>
              </CardHeader>
              <CardContent>
                {hotspots?.hotspots?.length > 0 ? (
                  <div className="space-y-3">
                    {hotspots.hotspots.slice(0, 10).map((h, i) => (
                      <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-muted/30">
                        <div className="p-2 rounded-full bg-red-500/20">
                          <MapPin className="h-5 w-5 text-red-500" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">
                            {h.addresses[0] || `${h.latitude}, ${h.longitude}`}
                          </p>
                          <div className="flex gap-2 mt-1">
                            {h.types.slice(0, 3).map((t, j) => (
                              <Badge key={j} variant="outline" className="text-xs capitalize">
                                {t.replace(/_/g, ' ')}
                              </Badge>
                            ))}
                          </div>
                        </div>
                        <Badge variant={h.count >= 3 ? 'destructive' : 'secondary'}>
                          {h.count} encounter{h.count !== 1 ? 's' : ''}
                        </Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <MapPin className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
                    <p className="text-muted-foreground">No location data yet</p>
                    <p className="text-sm text-muted-foreground mt-1">Enable location during encounters to see hotspots</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* All Locations List */}
            {hotspots?.all_locations?.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Eye className="h-5 w-5" />
                    All Encounter Locations
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="max-h-64 overflow-y-auto space-y-2">
                    {hotspots.all_locations.slice(0, 20).map((loc, i) => (
                      <Link 
                        key={i} 
                        to={`/encounters/${loc.encounter_id}`}
                        className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 transition-colors group"
                      >
                        <MapPin className="h-4 w-4 text-muted-foreground" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm truncate">{loc.address || `${loc.latitude}, ${loc.longitude}`}</p>
                          <p className="text-xs text-muted-foreground capitalize">{loc.type?.replace(/_/g, ' ')}</p>
                        </div>
                        <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                      </Link>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  );
}
