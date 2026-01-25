import React, { useState, useEffect } from 'react';
import { Search, Shield, AlertTriangle, TrendingDown, TrendingUp, Building2, User, BadgeAlert, DollarSign, Scale, ChevronRight, MapPin, Loader2, Plus, FileWarning, PieChart, BarChart3, Send } from 'lucide-react';
import { toast } from 'sonner';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Progress } from '../components/ui/progress';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogClose } from '../components/ui/dialog';
import { ScrollArea } from '../components/ui/scroll-area';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { useAuth } from '../contexts/AuthContext';
import api from '../lib/api';

const US_STATES = [
  "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
  "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
  "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
  "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
  "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
];

const VIOLATION_TYPES = [
  { value: "excessive_force", label: "Excessive Force", amendment: "4th" },
  { value: "unlawful_search", label: "Unlawful Search", amendment: "4th" },
  { value: "false_arrest", label: "False Arrest", amendment: "4th" },
  { value: "miranda_violation", label: "Miranda Violation", amendment: "5th" },
  { value: "recording_interference", label: "Recording Interference", amendment: "1st" },
  { value: "racial_profiling", label: "Racial Profiling", amendment: "14th" },
  { value: "due_process_violation", label: "Due Process Violation", amendment: "14th" },
  { value: "intimidation", label: "Intimidation", amendment: null },
  { value: "retaliation", label: "Retaliation", amendment: null },
  { value: "dishonesty", label: "Dishonesty", amendment: null },
  { value: "evidence_tampering", label: "Evidence Tampering", amendment: null },
  { value: "policy_violation", label: "Policy Violation", amendment: null },
];

const SEVERITY_LEVELS = [
  { value: "minor", label: "Minor (Warning-level)", color: "bg-yellow-500" },
  { value: "moderate", label: "Moderate (Suspension-level)", color: "bg-orange-500" },
  { value: "serious", label: "Serious (Termination-level)", color: "bg-red-500" },
  { value: "critical", label: "Critical (Criminal-level)", color: "bg-red-700" },
];

export default function AccountabilityPortalPage() {
  const { user, isAuthenticated } = useAuth();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [leaderboard, setLeaderboard] = useState({ best: [], worst: [] });
  const [officers, setOfficers] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [stateFilter, setStateFilter] = useState('all');
  const [selectedDepartment, setSelectedDepartment] = useState(null);
  const [selectedOfficer, setSelectedOfficer] = useState(null);
  const [officerViolations, setOfficerViolations] = useState([]);
  
  // Violation Report Form State
  const [reportDialogOpen, setReportDialogOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [reportForm, setReportForm] = useState({
    badge_number: '',
    department_name: '',
    department_city: '',
    department_state: '',
    violation_type: '',
    severity: '',
    description: '',
    incident_date: new Date().toISOString().split('T')[0]
  });

  useEffect(() => {
    loadData();
  }, [stateFilter]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsRes, deptsRes, leaderboardRes, officersRes] = await Promise.all([
        api.get('/accountability/public/stats'),
        api.get(`/accountability/public/departments?state=${stateFilter}&limit=50`),
        api.get(`/accountability/public/leaderboard?state=${stateFilter !== 'all' ? stateFilter : ''}`),
        api.get('/accountability/public/officers?min_violations=1&limit=20')
      ]);

      setStats(statsRes.data);
      setDepartments(deptsRes.data.departments || []);
      setLeaderboard({
        best: leaderboardRes.data.best_departments || [],
        worst: leaderboardRes.data.worst_departments || []
      });
      setOfficers(officersRes.data.officers || []);
    } catch (error) {
      console.error('Error loading data:', error);
      toast.error('Failed to load accountability data');
    } finally {
      setLoading(false);
    }
  };

  const loadOfficerDetails = async (officerId) => {
    try {
      const res = await api.get(`/accountability/public/officers/${officerId}`);
      setSelectedOfficer(res.data.officer);
      setOfficerViolations(res.data.violations || []);
    } catch (error) {
      toast.error('Failed to load officer details');
    }
  };

  const loadDepartmentDetails = async (departmentId) => {
    try {
      const res = await api.get(`/accountability/public/departments/${departmentId}`);
      setSelectedDepartment(res.data.department);
    } catch (error) {
      toast.error('Failed to load department details');
    }
  };

  const handleReportSubmit = async () => {
    if (!isAuthenticated) {
      toast.error('Please log in to report a violation');
      return;
    }

    if (!reportForm.badge_number || !reportForm.department_name || !reportForm.department_state || 
        !reportForm.violation_type || !reportForm.severity || !reportForm.description) {
      toast.error('Please fill in all required fields');
      return;
    }

    setSubmitting(true);
    try {
      const response = await api.post('/accountability/violations/report', reportForm);
      if (response.data.success) {
        toast.success('Violation reported successfully! Thank you for helping improve police accountability.');
        setReportDialogOpen(false);
        setReportForm({
          badge_number: '',
          department_name: '',
          department_city: '',
          department_state: '',
          violation_type: '',
          severity: '',
          description: '',
          incident_date: new Date().toISOString().split('T')[0]
        });
        // Refresh data
        loadData();
      }
    } catch (error) {
      console.error('Error reporting violation:', error);
      toast.error(error.response?.data?.detail || 'Failed to report violation');
    } finally {
      setSubmitting(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-500';
    if (score >= 60) return 'text-yellow-500';
    if (score >= 40) return 'text-orange-500';
    return 'text-red-500';
  };

  const getGradeColor = (grade) => {
    const colors = {
      'A': 'bg-green-500',
      'B': 'bg-blue-500',
      'C': 'bg-yellow-500',
      'D': 'bg-orange-500',
      'F': 'bg-red-500'
    };
    return colors[grade] || 'bg-gray-500';
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="accountability-portal">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
              <Scale className="w-8 h-8 text-primary" />
              Police Accountability Portal
            </h1>
            <p className="text-muted-foreground mt-1">
              Public transparency data on police departments and officers nationwide
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button 
              onClick={() => setReportDialogOpen(true)}
              className="bg-red-600 hover:bg-red-700"
              data-testid="report-violation-btn"
            >
              <FileWarning className="w-4 h-4 mr-2" />
              Report Violation
            </Button>
            <Select value={stateFilter} onValueChange={setStateFilter}>
              <SelectTrigger className="w-[180px]">
                <MapPin className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Filter by state" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All States</SelectItem>
              {US_STATES.map(state => (
                <SelectItem key={state} value={state}>{state}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          </div>
        </div>

        {/* Stats Overview */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Departments</p>
                    <p className="text-2xl font-bold">{stats.total_departments}</p>
                  </div>
                  <Building2 className="w-8 h-8 text-muted-foreground/50" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Officers Tracked</p>
                    <p className="text-2xl font-bold">{stats.total_officers_tracked}</p>
                  </div>
                  <User className="w-8 h-8 text-muted-foreground/50" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Violations</p>
                    <p className="text-2xl font-bold">{stats.total_violations}</p>
                  </div>
                  <BadgeAlert className="w-8 h-8 text-red-500/50" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Settlements</p>
                    <p className="text-2xl font-bold">{formatCurrency(stats.total_settlements || 0)}</p>
                  </div>
                  <DollarSign className="w-8 h-8 text-yellow-500/50" />
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        <Tabs defaultValue="departments" className="space-y-6">
          <TabsList>
            <TabsTrigger value="departments">Departments</TabsTrigger>
            <TabsTrigger value="officers">Officers</TabsTrigger>
            <TabsTrigger value="leaderboard">Rankings</TabsTrigger>
          </TabsList>

          {/* Departments Tab */}
          <TabsContent value="departments" className="space-y-4">
            <div className="flex gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Search departments..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {departments
                .filter(d => !searchQuery || d.name.toLowerCase().includes(searchQuery.toLowerCase()))
                .map(dept => (
                  <Card key={dept.department_id} className="hover:shadow-lg transition-shadow cursor-pointer" onClick={() => loadDepartmentDetails(dept.department_id)}>
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between">
                        <div>
                          <CardTitle className="text-base">{dept.name}</CardTitle>
                          <CardDescription>{dept.city}, {dept.state}</CardDescription>
                        </div>
                        <Badge className={`${getGradeColor(dept.transparency_grade)} text-white`}>
                          {dept.transparency_grade}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-muted-foreground">Accountability Score</span>
                          <span className={`text-lg font-bold ${getScoreColor(dept.accountability_score)}`}>
                            {dept.accountability_score}/100
                          </span>
                        </div>
                        <Progress value={dept.accountability_score} className="h-2" />
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div className="flex items-center gap-1">
                            <BadgeAlert className="w-3 h-3 text-red-500" />
                            <span>{dept.total_violations} violations</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <User className="w-3 h-3" />
                            <span>{dept.officers_with_violations} officers</span>
                          </div>
                        </div>
                        {dept.total_settlements > 0 && (
                          <div className="text-sm text-muted-foreground">
                            Settlements: {formatCurrency(dept.total_settlements)}
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
            </div>
          </TabsContent>

          {/* Officers Tab */}
          <TabsContent value="officers" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Officers with Reported Violations</CardTitle>
                <CardDescription>
                  Public records of officers with documented accountability issues
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {officers.map(officer => (
                    <div
                      key={officer.officer_id}
                      className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted/50 cursor-pointer transition-colors"
                      onClick={() => loadOfficerDetails(officer.officer_id)}
                    >
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center">
                          <User className="w-5 h-5" />
                        </div>
                        <div>
                          <p className="font-medium">{officer.full_name}</p>
                          <p className="text-sm text-muted-foreground">
                            Badge #{officer.badge_number} • {officer.department_name}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className={`font-bold ${getScoreColor(officer.accountability_score)}`}>
                            {officer.accountability_score}/100
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {officer.total_violations} violations
                          </p>
                        </div>
                        <ChevronRight className="w-5 h-5 text-muted-foreground" />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Leaderboard Tab */}
          <TabsContent value="leaderboard" className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Best Departments */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-green-600">
                    <TrendingUp className="w-5 h-5" />
                    Best Performing
                  </CardTitle>
                  <CardDescription>Departments with highest accountability scores</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {leaderboard.best.slice(0, 10).map((dept, i) => (
                      <div key={dept.department_id} className="flex items-center gap-3">
                        <span className="w-6 h-6 rounded-full bg-green-500/10 text-green-600 flex items-center justify-center text-sm font-bold">
                          {i + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">{dept.name}</p>
                          <p className="text-xs text-muted-foreground">{dept.city}, {dept.state}</p>
                        </div>
                        <Badge variant="outline" className="text-green-600 border-green-600">
                          {dept.accountability_score}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Worst Departments */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-red-600">
                    <TrendingDown className="w-5 h-5" />
                    Needs Improvement
                  </CardTitle>
                  <CardDescription>Departments with lowest accountability scores</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {leaderboard.worst.slice(0, 10).map((dept, i) => (
                      <div key={dept.department_id} className="flex items-center gap-3">
                        <span className="w-6 h-6 rounded-full bg-red-500/10 text-red-600 flex items-center justify-center text-sm font-bold">
                          {i + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">{dept.name}</p>
                          <p className="text-xs text-muted-foreground">{dept.city}, {dept.state}</p>
                        </div>
                        <Badge variant="outline" className="text-red-600 border-red-600">
                          {dept.accountability_score}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        {/* Officer Details Dialog */}
        <Dialog open={!!selectedOfficer} onOpenChange={(open) => !open && setSelectedOfficer(null)}>
          <DialogContent className="max-w-2xl">
            {selectedOfficer && (
              <>
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2">
                    <User className="w-5 h-5" />
                    {selectedOfficer.full_name}
                  </DialogTitle>
                  <DialogDescription>
                    Badge #{selectedOfficer.badge_number} • {selectedOfficer.department_name}
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <Card>
                      <CardContent className="pt-4 text-center">
                        <p className={`text-2xl font-bold ${getScoreColor(selectedOfficer.accountability_score)}`}>
                          {selectedOfficer.accountability_score}
                        </p>
                        <p className="text-xs text-muted-foreground">Accountability Score</p>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="pt-4 text-center">
                        <p className="text-2xl font-bold text-red-500">{selectedOfficer.total_violations}</p>
                        <p className="text-xs text-muted-foreground">Total Violations</p>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="pt-4 text-center">
                        <p className="text-2xl font-bold">{selectedOfficer.sustained_violations || 0}</p>
                        <p className="text-xs text-muted-foreground">Sustained</p>
                      </CardContent>
                    </Card>
                  </div>

                  <div>
                    <h4 className="font-semibold mb-2">Violation History</h4>
                    <ScrollArea className="h-[300px]">
                      <div className="space-y-2">
                        {officerViolations.map(v => (
                          <div key={v.violation_id} className="p-3 rounded-lg border">
                            <div className="flex items-center justify-between mb-1">
                              <Badge variant={v.outcome === 'sustained' ? 'destructive' : 'secondary'}>
                                {v.violation_type?.replace(/_/g, ' ')}
                              </Badge>
                              <span className="text-xs text-muted-foreground">{v.incident_date}</span>
                            </div>
                            <p className="text-sm">{v.description}</p>
                            <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                              <span>Severity: {v.severity}</span>
                              <span>Outcome: {v.outcome}</span>
                              {v.settlement_amount && (
                                <span className="text-yellow-600">Settlement: {formatCurrency(v.settlement_amount)}</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  </div>
                </div>
              </>
            )}
          </DialogContent>
        </Dialog>

        {/* Disclaimer */}
        <Card className="bg-blue-500/10 border-blue-500/20">
          <CardContent className="flex items-start gap-4 py-4">
            <Shield className="w-5 h-5 text-blue-500 mt-0.5" />
            <div>
              <h4 className="font-semibold text-blue-700 dark:text-blue-400">Data Transparency Notice</h4>
              <p className="text-sm text-blue-700/80 dark:text-blue-400/80">
                This data is compiled from public records, court filings, and citizen reports. 
                All officers are presumed innocent until proven otherwise. Pending violations 
                are under investigation and may not reflect final outcomes.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}
