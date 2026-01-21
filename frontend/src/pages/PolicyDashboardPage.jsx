import React, { useState, useEffect } from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { policyAPI } from '../lib/api';
import { 
  BarChart3, PieChart, TrendingUp, FileText, Download,
  Building, Users, AlertTriangle, Map, Scale, Megaphone,
  Newspaper, Landmark, Briefcase, ChevronRight, Loader2,
  CheckCircle, Target, Flag
} from 'lucide-react';
import { toast } from 'sonner';

const reportTypes = [
  { value: 'department_accountability', label: 'Department Accountability', icon: Building },
  { value: 'officer_pattern', label: 'Officer Pattern Analysis', icon: Users },
  { value: 'state_analysis', label: 'State Analysis', icon: Map },
  { value: 'violation_trend', label: 'Violation Trends', icon: TrendingUp }
];

const targetAudiences = [
  { value: 'city_council', label: 'City Council', icon: Landmark, desc: 'Local government oversight' },
  { value: 'media', label: 'Media Outlets', icon: Newspaper, desc: 'Investigative journalism' },
  { value: 'civil_rights_org', label: 'Civil Rights Organizations', icon: Scale, desc: 'Advocacy and legal action' },
  { value: 'legislators', label: 'Legislators', icon: Briefcase, desc: 'Policy reform proposals' }
];

export default function PolicyDashboardPage() {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [showGenerateDialog, setShowGenerateDialog] = useState(false);
  const [reportForm, setReportForm] = useState({
    report_type: 'department_accountability',
    target_audience: 'city_council',
    department: '',
    state: ''
  });
  const [generatedReport, setGeneratedReport] = useState(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const response = await policyAPI.getDashboardData();
      setDashboardData(response.data);
    } catch (error) {
      console.error('Error loading dashboard:', error);
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    setGenerating(true);
    try {
      const response = await policyAPI.generateReport(
        reportForm.report_type,
        reportForm.target_audience,
        reportForm.department || null,
        reportForm.state || null,
        null
      );
      setGeneratedReport(response.data);
      toast.success('Report generated successfully!');
    } catch (error) {
      console.error('Error generating report:', error);
      toast.error('Failed to generate report');
    } finally {
      setGenerating(false);
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'text-red-500 bg-red-500/10';
      case 'high': return 'text-orange-500 bg-orange-500/10';
      case 'medium': return 'text-yellow-500 bg-yellow-500/10';
      case 'low': return 'text-green-500 bg-green-500/10';
      default: return 'text-muted-foreground bg-muted';
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="policy-dashboard-page">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="font-serif text-3xl font-bold flex items-center gap-3">
              <Megaphone className="h-8 w-8 text-primary" />
              Policy Impact Dashboard
            </h1>
            <p className="text-muted-foreground mt-1">
              Transform community data into actionable reports for systemic change
            </p>
          </div>
          
          <Dialog open={showGenerateDialog} onOpenChange={setShowGenerateDialog}>
            <DialogTrigger asChild>
              <Button className="gap-2" data-testid="generate-report-btn">
                <FileText className="h-4 w-4" />
                Generate Report
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>Generate Policy Report</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Report Type</label>
                  <Select 
                    value={reportForm.report_type} 
                    onValueChange={(v) => setReportForm(prev => ({ ...prev, report_type: v }))}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {reportTypes.map(t => (
                        <SelectItem key={t.value} value={t.value}>
                          <div className="flex items-center gap-2">
                            <t.icon className="h-4 w-4" />
                            {t.label}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Target Audience</label>
                  <div className="grid grid-cols-2 gap-2">
                    {targetAudiences.map(a => (
                      <button
                        key={a.value}
                        onClick={() => setReportForm(prev => ({ ...prev, target_audience: a.value }))}
                        className={`p-3 rounded-lg border text-left transition-all ${
                          reportForm.target_audience === a.value 
                            ? 'border-primary bg-primary/10' 
                            : 'border-border hover:bg-muted'
                        }`}
                      >
                        <a.icon className="h-5 w-5 mb-1" />
                        <p className="font-medium text-sm">{a.label}</p>
                        <p className="text-xs text-muted-foreground">{a.desc}</p>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Department (optional)</label>
                    <Input 
                      placeholder="e.g., LAPD"
                      value={reportForm.department}
                      onChange={(e) => setReportForm(prev => ({ ...prev, department: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">State (optional)</label>
                    <Input 
                      placeholder="e.g., California"
                      value={reportForm.state}
                      onChange={(e) => setReportForm(prev => ({ ...prev, state: e.target.value }))}
                    />
                  </div>
                </div>

                <Button 
                  onClick={handleGenerateReport} 
                  className="w-full"
                  disabled={generating}
                >
                  {generating ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <FileText className="h-4 w-4 mr-2" />
                      Generate Report
                    </>
                  )}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* Overview Stats */}
        {dashboardData?.overview && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-blue-500/10">
                    <FileText className="h-5 w-5 text-blue-500" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{dashboardData.overview.total_submissions}</p>
                    <p className="text-sm text-muted-foreground">Total Reports</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-orange-500/10">
                    <Building className="h-5 w-5 text-orange-500" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{dashboardData.overview.total_departments}</p>
                    <p className="text-sm text-muted-foreground">Departments</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-purple-500/10">
                    <Users className="h-5 w-5 text-purple-500" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{dashboardData.overview.total_officers}</p>
                    <p className="text-sm text-muted-foreground">Officers Tracked</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-red-500/10">
                    <AlertTriangle className="h-5 w-5 text-red-500" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{dashboardData.overview.repeat_offenders}</p>
                    <p className="text-sm text-muted-foreground">Repeat Offenders</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Main Content */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left Column - Charts */}
          <div className="lg:col-span-2 space-y-6">
            <Tabs defaultValue="violations">
              <TabsList>
                <TabsTrigger value="violations">Violations</TabsTrigger>
                <TabsTrigger value="departments">Departments</TabsTrigger>
                <TabsTrigger value="states">States</TabsTrigger>
              </TabsList>

              <TabsContent value="violations">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <BarChart3 className="h-5 w-5" />
                      Violations by Type
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {dashboardData?.violations_breakdown?.map((v, i) => (
                        <div key={i} className="flex items-center gap-3">
                          <div className="flex-1">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-sm font-medium capitalize">
                                {v.type?.replace(/_/g, ' ')}
                              </span>
                              <span className="text-sm text-muted-foreground">{v.count}</span>
                            </div>
                            <div className="h-2 bg-muted rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-primary rounded-full"
                                style={{ 
                                  width: `${Math.min((v.count / (dashboardData.overview?.total_submissions || 1)) * 100 * 2, 100)}%` 
                                }}
                              />
                            </div>
                          </div>
                        </div>
                      ))}
                      {(!dashboardData?.violations_breakdown || dashboardData.violations_breakdown.length === 0) && (
                        <p className="text-center text-muted-foreground py-4">No violation data yet</p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="departments">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Building className="h-5 w-5" />
                      Top Departments by Incidents
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {dashboardData?.top_departments?.map((d, i) => (
                        <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                          <div>
                            <p className="font-medium">{d.department}</p>
                            <p className="text-sm text-muted-foreground">{d.state}</p>
                          </div>
                          <Badge variant="destructive">{d.total_incidents} incidents</Badge>
                        </div>
                      ))}
                      {(!dashboardData?.top_departments || dashboardData.top_departments.length === 0) && (
                        <p className="text-center text-muted-foreground py-4">No department data yet</p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="states">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Map className="h-5 w-5" />
                      Incidents by State
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {dashboardData?.state_breakdown?.map((s, i) => (
                        <div key={i} className="flex items-center gap-3">
                          <div className="flex-1">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-sm font-medium">{s.state}</span>
                              <span className="text-sm text-muted-foreground">{s.count} incidents</span>
                            </div>
                            <div className="h-2 bg-muted rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-orange-500 rounded-full"
                                style={{ 
                                  width: `${Math.min((s.count / (dashboardData.overview?.total_submissions || 1)) * 100 * 2, 100)}%` 
                                }}
                              />
                            </div>
                          </div>
                        </div>
                      ))}
                      {(!dashboardData?.state_breakdown || dashboardData.state_breakdown.length === 0) && (
                        <p className="text-center text-muted-foreground py-4">No state data yet</p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>

          {/* Right Column - Reports & Officers */}
          <div className="space-y-6">
            {/* Repeat Offenders */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-red-500">
                  <Flag className="h-5 w-5" />
                  Repeat Offenders
                </CardTitle>
                <CardDescription>Officers with 2+ reported incidents</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {dashboardData?.repeat_officers?.map((o, i) => (
                    <div key={i} className="flex items-center justify-between p-2 rounded bg-red-500/5 border border-red-500/20">
                      <div>
                        <p className="font-medium">Badge #{o.badge_number}</p>
                        <p className="text-xs text-muted-foreground">{o.department}</p>
                      </div>
                      <Badge variant="destructive">{o.total_incidents}</Badge>
                    </div>
                  ))}
                  {(!dashboardData?.repeat_officers || dashboardData.repeat_officers.length === 0) && (
                    <p className="text-center text-muted-foreground py-4 text-sm">No repeat offenders identified</p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Recent Reports */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Recent Reports
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {dashboardData?.recent_reports?.map((r, i) => (
                    <div key={i} className="p-2 rounded border hover:bg-muted/50 cursor-pointer">
                      <p className="font-medium text-sm truncate">{r.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(r.generated_at).toLocaleDateString()}
                      </p>
                    </div>
                  ))}
                  {(!dashboardData?.recent_reports || dashboardData.recent_reports.length === 0) && (
                    <p className="text-center text-muted-foreground py-4 text-sm">No reports generated yet</p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Severity Distribution */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <PieChart className="h-5 w-5" />
                  Severity Distribution
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {dashboardData?.severity_breakdown?.map((s, i) => (
                    <div key={i} className="flex items-center justify-between">
                      <Badge className={getSeverityColor(s.severity)}>{s.severity}</Badge>
                      <span className="font-medium">{s.count}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Generated Report Display */}
        {generatedReport && (
          <Card className="border-primary">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle className="h-5 w-5 text-green-500" />
                    {generatedReport.title}
                  </CardTitle>
                  <CardDescription>
                    Generated for {generatedReport.target_audience.replace(/_/g, ' ')} • {new Date(generatedReport.generated_at).toLocaleString()}
                  </CardDescription>
                </div>
                <Button variant="outline" size="sm">
                  <Download className="h-4 w-4 mr-1" />
                  Export
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h3 className="font-medium mb-2">Executive Summary</h3>
                <p className="text-muted-foreground">{generatedReport.executive_summary}</p>
              </div>

              <div>
                <h3 className="font-medium mb-2">Key Findings</h3>
                <div className="space-y-2">
                  {generatedReport.key_findings?.map((f, i) => (
                    <div key={i} className={`p-3 rounded-lg border ${getSeverityColor(f.severity)}`}>
                      <div className="flex items-start gap-2">
                        <Target className="h-4 w-4 mt-0.5" />
                        <p className="text-sm">{f.finding}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="font-medium mb-2">Recommendations</h3>
                <ul className="space-y-2">
                  {generatedReport.recommendations?.map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <ChevronRight className="h-4 w-4 mt-0.5 text-primary" />
                      {r}
                    </li>
                  ))}
                </ul>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </AppLayout>
  );
}
