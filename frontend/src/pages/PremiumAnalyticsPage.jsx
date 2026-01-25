import React, { useState, useEffect } from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import { Progress } from '../components/ui/progress';
import { premiumAnalyticsAPI, accountabilityAPI } from '../lib/api';
import { 
  TrendingUp, TrendingDown, AlertTriangle, Shield, MapPin,
  Building2, FileText, Download, BarChart3, PieChart, 
  Activity, Target, Users, DollarSign, Loader2, RefreshCw,
  ChevronRight, Calendar, Clock, Flame
} from 'lucide-react';
import { toast } from 'sonner';

const riskColors = {
  critical: 'bg-red-500 text-white',
  elevated: 'bg-orange-500 text-white',
  moderate: 'bg-yellow-500 text-black',
  low: 'bg-green-500 text-white'
};

const trendIcons = {
  increasing: TrendingUp,
  decreasing: TrendingDown,
  stable: Activity
};

export default function PremiumAnalyticsPage() {
  const [loading, setLoading] = useState(true);
  const [departments, setDepartments] = useState([]);
  const [selectedDepartment, setSelectedDepartment] = useState(null);
  const [hotspots, setHotspots] = useState([]);
  const [trends, setTrends] = useState(null);
  const [riskPrediction, setRiskPrediction] = useState(null);
  const [auditReport, setAuditReport] = useState(null);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [deptRes, hotspotsRes, trendsRes] = await Promise.all([
        accountabilityAPI.getPublicDepartments(null, 'accountability_score', 50),
        premiumAnalyticsAPI.getHotspots(10),
        premiumAnalyticsAPI.getTrends(null, null, 12)
      ]);
      
      setDepartments(deptRes.data.departments || []);
      setHotspots(hotspotsRes.data.hotspots || []);
      setTrends(trendsRes.data);
    } catch (error) {
      toast.error('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  const loadDepartmentAnalytics = async (deptId) => {
    if (!deptId) return;
    
    setSelectedDepartment(deptId);
    
    try {
      const [riskRes, trendsRes] = await Promise.all([
        premiumAnalyticsAPI.getRiskPrediction(deptId),
        premiumAnalyticsAPI.getTrends(deptId, null, 12)
      ]);
      
      setRiskPrediction(riskRes.data);
      setTrends(trendsRes.data);
    } catch (error) {
      toast.error('Failed to load department analytics');
    }
  };

  const generateAuditReport = async () => {
    try {
      const response = await premiumAnalyticsAPI.generateAuditReport(
        selectedDepartment, 
        null, 
        true, 
        true
      );
      setAuditReport(response.data);
      toast.success('Audit report generated');
    } catch (error) {
      toast.error('Failed to generate audit report');
    }
  };

  const downloadPdfReport = async () => {
    setExportingPdf(true);
    try {
      const response = await premiumAnalyticsAPI.downloadAuditReportPDF(
        selectedDepartment,
        null,
        true,
        true
      );
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `JUSTICE_Audit_Report_${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('PDF report downloaded');
    } catch (error) {
      toast.error('Failed to download PDF report');
    } finally {
      setExportingPdf(false);
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="premium-analytics-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-serif text-3xl font-bold flex items-center gap-3">
              <BarChart3 className="h-8 w-8 text-primary" />
              Premium Analytics
            </h1>
            <p className="text-muted-foreground mt-1">
              Advanced predictive analytics and trend analysis for police accountability
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={loadInitialData} data-testid="refresh-btn">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
            <Button onClick={downloadPdfReport} disabled={exportingPdf} data-testid="export-pdf-btn">
              {exportingPdf ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Download className="h-4 w-4 mr-2" />
              )}
              Export PDF
            </Button>
          </div>
        </div>

        {/* Department Selector */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
              <div className="flex-1">
                <label className="text-sm font-medium mb-2 block">Select Department for Detailed Analysis</label>
                <Select 
                  value={selectedDepartment || ''} 
                  onValueChange={loadDepartmentAnalytics}
                >
                  <SelectTrigger className="w-full sm:w-80" data-testid="department-select">
                    <SelectValue placeholder="Select a department" />
                  </SelectTrigger>
                  <SelectContent>
                    {departments.map(dept => (
                      <SelectItem key={dept.department_id} value={dept.department_id}>
                        {dept.name} ({dept.state})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {selectedDepartment && (
                <Button variant="outline" onClick={generateAuditReport} data-testid="generate-audit-btn">
                  <FileText className="h-4 w-4 mr-2" />
                  Generate Audit Report
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="hotspots">Hotspots</TabsTrigger>
            <TabsTrigger value="trends">Trends</TabsTrigger>
            <TabsTrigger value="risk">Risk Analysis</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            <div className="grid md:grid-cols-3 gap-6">
              {/* Top Hotspots */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Flame className="h-5 w-5 text-orange-500" />
                    Top Violation Hotspots
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {hotspots.slice(0, 5).map((spot, idx) => (
                      <div 
                        key={spot.department_id}
                        className="flex items-center justify-between p-2 rounded bg-muted/50"
                        data-testid={`hotspot-${idx}`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-muted-foreground">#{idx + 1}</span>
                          <div>
                            <p className="font-medium text-sm">{spot.department_name}</p>
                            <p className="text-xs text-muted-foreground">{spot.state}</p>
                          </div>
                        </div>
                        <Badge variant="destructive" className="text-xs">
                          {spot.violations_per_officer?.toFixed(1)} per officer
                        </Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Trend Summary */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-blue-500" />
                    Trend Analysis
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {trends && (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Direction</span>
                        <Badge className={
                          trends.trend_direction === 'increasing' ? 'bg-red-500' :
                          trends.trend_direction === 'decreasing' ? 'bg-green-500' : 'bg-gray-500'
                        }>
                          {trends.trend_direction}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Total Violations</span>
                        <span className="font-bold">{trends.total_violations}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Avg Severity</span>
                        <span className="font-bold">{trends.average_severity?.toFixed(1)}/10</span>
                      </div>
                      <div className="pt-2 border-t">
                        <p className="text-sm text-muted-foreground">{trends.interpretation}</p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Quick Stats */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <PieChart className="h-5 w-5 text-purple-500" />
                    Quick Stats
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Departments</span>
                      <span className="font-bold">{departments.length}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">High Risk Depts</span>
                      <span className="font-bold text-red-500">
                        {departments.filter(d => d.accountability_score < 40).length}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Analysis Period</span>
                      <span className="font-medium">12 months</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Hotspots Tab */}
          <TabsContent value="hotspots">
            <Card>
              <CardHeader>
                <CardTitle>Violation Hotspots</CardTitle>
                <CardDescription>
                  Departments ranked by violations per officer ratio
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[500px]">
                  <div className="space-y-3">
                    {hotspots.map((spot, idx) => (
                      <div 
                        key={spot.department_id}
                        className="flex items-center justify-between p-4 rounded-lg border"
                        data-testid={`hotspot-detail-${idx}`}
                      >
                        <div className="flex items-center gap-4">
                          <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                            idx < 3 ? 'bg-red-500 text-white' :
                            idx < 6 ? 'bg-orange-500 text-white' : 'bg-yellow-500 text-black'
                          }`}>
                            {idx + 1}
                          </div>
                          <div>
                            <p className="font-medium">{spot.department_name}</p>
                            <p className="text-sm text-muted-foreground">
                              {spot.state} • {spot.officer_count} officers
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="font-bold text-lg">{spot.violations_per_officer?.toFixed(2)}</p>
                          <p className="text-xs text-muted-foreground">violations/officer</p>
                          <p className="text-sm mt-1">
                            {spot.total_violations} total violations
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Trends Tab */}
          <TabsContent value="trends">
            <Card>
              <CardHeader>
                <CardTitle>Violation Trends</CardTitle>
                <CardDescription>
                  Monthly breakdown of violations over the past 12 months
                </CardDescription>
              </CardHeader>
              <CardContent>
                {trends?.monthly_breakdown && (
                  <div className="space-y-4">
                    {/* Trend Indicator */}
                    <div className="flex items-center gap-4 p-4 rounded-lg bg-muted/50">
                      {(() => {
                        const TrendIcon = trendIcons[trends.trend_direction] || Activity;
                        return <TrendIcon className={`h-8 w-8 ${
                          trends.trend_direction === 'increasing' ? 'text-red-500' :
                          trends.trend_direction === 'decreasing' ? 'text-green-500' : 'text-gray-500'
                        }`} />;
                      })()}
                      <div>
                        <p className="font-semibold text-lg capitalize">{trends.trend_direction} Trend</p>
                        <p className="text-sm text-muted-foreground">{trends.interpretation}</p>
                      </div>
                    </div>

                    {/* Monthly Data */}
                    <ScrollArea className="h-[400px]">
                      <div className="space-y-2">
                        {trends.monthly_breakdown.map((month, idx) => (
                          <div 
                            key={month.month}
                            className="flex items-center justify-between p-3 rounded border"
                          >
                            <div className="flex items-center gap-3">
                              <Calendar className="h-4 w-4 text-muted-foreground" />
                              <span className="font-medium">{month.month}</span>
                            </div>
                            <div className="flex items-center gap-4">
                              <div className="text-right">
                                <span className="font-bold">{month.count}</span>
                                <span className="text-xs text-muted-foreground ml-1">violations</span>
                              </div>
                              <Progress 
                                value={(month.count / Math.max(...trends.monthly_breakdown.map(m => m.count))) * 100}
                                className="w-24"
                              />
                              <Badge variant="outline">
                                Avg: {month.avg_severity?.toFixed(1)}/10
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Risk Analysis Tab */}
          <TabsContent value="risk">
            <Card>
              <CardHeader>
                <CardTitle>Risk Prediction</CardTitle>
                <CardDescription>
                  {selectedDepartment 
                    ? 'Predictive risk analysis for selected department'
                    : 'Select a department above to view risk analysis'
                  }
                </CardDescription>
              </CardHeader>
              <CardContent>
                {!selectedDepartment ? (
                  <div className="text-center py-12">
                    <Target className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                    <p className="text-muted-foreground">
                      Select a department to view detailed risk prediction
                    </p>
                  </div>
                ) : riskPrediction ? (
                  <div className="space-y-6">
                    {/* Risk Level */}
                    <div className={`p-6 rounded-lg ${riskColors[riskPrediction.risk_level]}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm opacity-90">Risk Level</p>
                          <p className="text-3xl font-bold uppercase">{riskPrediction.risk_level}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm opacity-90">Risk Score</p>
                          <p className="text-3xl font-bold">{riskPrediction.risk_score}/100</p>
                        </div>
                      </div>
                    </div>

                    {/* Risk Factors */}
                    <div>
                      <h4 className="font-semibold mb-3">Risk Factors</h4>
                      <div className="space-y-3">
                        {riskPrediction.risk_factors?.map((factor, idx) => (
                          <div key={idx} className="flex items-start gap-3 p-3 rounded bg-muted/50">
                            <AlertTriangle className={`h-5 w-5 mt-0.5 ${
                              factor.weight > 0.3 ? 'text-red-500' :
                              factor.weight > 0.2 ? 'text-orange-500' : 'text-yellow-500'
                            }`} />
                            <div>
                              <p className="font-medium">{factor.factor}</p>
                              <p className="text-sm text-muted-foreground">{factor.description}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Recommendations */}
                    {riskPrediction.recommendations?.length > 0 && (
                      <div>
                        <h4 className="font-semibold mb-3">Recommendations</h4>
                        <div className="space-y-2">
                          {riskPrediction.recommendations.map((rec, idx) => (
                            <div key={idx} className="flex items-start gap-2 text-sm">
                              <ChevronRight className="h-4 w-4 text-primary mt-0.5" />
                              <span>{rec}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Audit Report Display */}
        {auditReport && (
          <Card className="border-primary/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" />
                Generated Audit Report
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Executive Summary */}
                <div className="p-4 rounded-lg bg-muted/50">
                  <h4 className="font-semibold mb-2">Executive Summary</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Total Departments</p>
                      <p className="text-xl font-bold">{auditReport.executive_summary?.total_departments}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Total Violations</p>
                      <p className="text-xl font-bold">{auditReport.executive_summary?.total_violations}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Avg Score</p>
                      <p className="text-xl font-bold">{auditReport.executive_summary?.average_accountability_score?.toFixed(1)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Settlement Exposure</p>
                      <p className="text-xl font-bold text-red-500">
                        ${(auditReport.executive_summary?.total_settlement_exposure / 1000000)?.toFixed(2)}M
                      </p>
                    </div>
                  </div>
                </div>

                {/* Recommendations */}
                {auditReport.recommendations?.length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-2">Automated Recommendations</h4>
                    <div className="space-y-2">
                      {auditReport.recommendations.map((rec, idx) => (
                        <div key={idx} className="flex items-start gap-2 p-2 rounded bg-muted/30">
                          <Badge variant={rec.priority === 'high' ? 'destructive' : 'secondary'} className="mt-0.5">
                            {rec.priority}
                          </Badge>
                          <span className="text-sm">{rec.recommendation}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </AppLayout>
  );
}
