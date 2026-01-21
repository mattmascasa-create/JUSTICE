import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Textarea } from '../components/ui/textarea';
import { communityAPI } from '../lib/api';
import { 
  Users, Shield, AlertTriangle, MapPin, Building, 
  TrendingUp, Search, ThumbsUp, Filter, ChevronRight,
  Calendar, FileText, Scale, Eye, Plus, Database,
  BarChart3, PieChart, Award
} from 'lucide-react';
import { toast } from 'sonner';

const US_STATES = [
  'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut',
  'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa',
  'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan',
  'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire',
  'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio',
  'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
  'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia',
  'Wisconsin', 'Wyoming'
];

const violationTypes = [
  '4th_amendment_violation', 'unlawful_search', 'unlawful_detention',
  'excessive_force', 'racial_profiling', 'intimidation', 'coercion',
  'miranda_violation', '5th_amendment_violation', 'false_arrest'
];

const severityOptions = ['low', 'medium', 'high', 'critical'];

const encounterTypes = [
  { value: 'traffic_stop', label: 'Traffic Stop' },
  { value: 'pedestrian_stop', label: 'Pedestrian Stop' },
  { value: 'arrest', label: 'Arrest' },
  { value: 'search', label: 'Search/Seizure' },
  { value: 'other', label: 'Other' }
];

export default function CommunityVaultPage() {
  const [stats, setStats] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [officers, setOfficers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ state: '', department: '', violation: '', severity: '' });
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [showSubmitDialog, setShowSubmitDialog] = useState(false);
  const [submitForm, setSubmitForm] = useState({
    encounter_type: 'traffic_stop',
    location_city: '',
    location_state: '',
    incident_date: new Date().toISOString().split('T')[0],
    violations: [],
    department: '',
    officer_badge: '',
    severity: 'medium',
    outcome: '',
    summary: ''
  });

  useEffect(() => {
    loadData();
  }, [filters, page]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsRes, subsRes, deptsRes, offRes] = await Promise.all([
        communityAPI.getStats(),
        communityAPI.getSubmissions({ ...filters, page }),
        communityAPI.getDepartments(filters.state),
        communityAPI.getOfficers()
      ]);
      
      setStats(statsRes.data);
      setSubmissions(subsRes.data.submissions);
      setTotalPages(subsRes.data.pages);
      setDepartments(deptsRes.data.departments || []);
      setOfficers(offRes.data.officers || []);
    } catch (error) {
      console.error('Error loading community data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!submitForm.location_city || !submitForm.location_state || !submitForm.summary) {
      toast.error('Please fill in required fields');
      return;
    }
    
    try {
      await communityAPI.submit({
        ...submitForm,
        incident_date: new Date(submitForm.incident_date).toISOString()
      });
      toast.success('Thank you for contributing to the community vault');
      setShowSubmitDialog(false);
      setSubmitForm({
        encounter_type: 'traffic_stop',
        location_city: '',
        location_state: '',
        incident_date: new Date().toISOString().split('T')[0],
        violations: [],
        department: '',
        officer_badge: '',
        severity: 'medium',
        outcome: '',
        summary: ''
      });
      loadData();
    } catch (error) {
      toast.error('Failed to submit: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleUpvote = async (submissionId) => {
    try {
      await communityAPI.upvote(submissionId);
      toast.success('Upvoted!');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upvote');
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'high': return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
      case 'medium': return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      case 'low': return 'bg-green-500/10 text-green-500 border-green-500/20';
      default: return 'bg-muted text-muted-foreground';
    }
  };

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="community-vault-page">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="font-serif text-3xl font-bold flex items-center gap-3">
              <Database className="h-8 w-8 text-primary" />
              Community Evidence Vault
            </h1>
            <p className="text-muted-foreground mt-1">
              Anonymized database of police encounters - together we build accountability
            </p>
          </div>
          
          <Dialog open={showSubmitDialog} onOpenChange={setShowSubmitDialog}>
            <DialogTrigger asChild>
              <Button className="gap-2" data-testid="submit-incident-btn">
                <Plus className="h-4 w-4" />
                Report Incident
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Submit to Community Vault</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">City *</label>
                    <Input 
                      placeholder="City"
                      value={submitForm.location_city}
                      onChange={(e) => setSubmitForm(prev => ({ ...prev, location_city: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">State *</label>
                    <Select value={submitForm.location_state} onValueChange={(v) => setSubmitForm(prev => ({ ...prev, location_state: v }))}>
                      <SelectTrigger><SelectValue placeholder="Select state" /></SelectTrigger>
                      <SelectContent>
                        {US_STATES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Incident Date</label>
                    <Input 
                      type="date"
                      value={submitForm.incident_date}
                      onChange={(e) => setSubmitForm(prev => ({ ...prev, incident_date: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Encounter Type</label>
                    <Select value={submitForm.encounter_type} onValueChange={(v) => setSubmitForm(prev => ({ ...prev, encounter_type: v }))}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {encounterTypes.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Department</label>
                    <Input 
                      placeholder="Police department"
                      value={submitForm.department}
                      onChange={(e) => setSubmitForm(prev => ({ ...prev, department: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Officer Badge #</label>
                    <Input 
                      placeholder="Badge number"
                      value={submitForm.officer_badge}
                      onChange={(e) => setSubmitForm(prev => ({ ...prev, officer_badge: e.target.value }))}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Severity</label>
                  <Select value={submitForm.severity} onValueChange={(v) => setSubmitForm(prev => ({ ...prev, severity: v }))}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {severityOptions.map(s => <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Violations</label>
                  <div className="flex flex-wrap gap-2">
                    {violationTypes.map(v => (
                      <Badge 
                        key={v}
                        variant={submitForm.violations.includes(v) ? "default" : "outline"}
                        className="cursor-pointer"
                        onClick={() => {
                          setSubmitForm(prev => ({
                            ...prev,
                            violations: prev.violations.includes(v) 
                              ? prev.violations.filter(x => x !== v)
                              : [...prev.violations, v]
                          }));
                        }}
                      >
                        {v.replace(/_/g, ' ')}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Summary *</label>
                  <Textarea 
                    placeholder="Describe what happened (this will be anonymized)"
                    value={submitForm.summary}
                    onChange={(e) => setSubmitForm(prev => ({ ...prev, summary: e.target.value }))}
                    rows={4}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Outcome</label>
                  <Input 
                    placeholder="What was the outcome? (dismissed, charged, settled, etc.)"
                    value={submitForm.outcome}
                    onChange={(e) => setSubmitForm(prev => ({ ...prev, outcome: e.target.value }))}
                  />
                </div>

                <Button onClick={handleSubmit} className="w-full">
                  Submit to Community Vault
                </Button>
                <p className="text-xs text-muted-foreground text-center">
                  Your submission is anonymized. No personal data is stored.
                </p>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* Stats Overview */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-blue-500/10">
                    <FileText className="h-5 w-5 text-blue-500" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{stats.total_submissions}</p>
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
                    <p className="text-2xl font-bold">{stats.total_departments_tracked}</p>
                    <p className="text-sm text-muted-foreground">Departments Tracked</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-red-500/10">
                    <Users className="h-5 w-5 text-red-500" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{stats.total_officers_tracked}</p>
                    <p className="text-sm text-muted-foreground">Officers Tracked</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-purple-500/10">
                    <TrendingUp className="h-5 w-5 text-purple-500" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{stats.top_violations?.[0]?.type?.replace(/_/g, ' ') || 'N/A'}</p>
                    <p className="text-sm text-muted-foreground">Top Violation</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Main Content Tabs */}
        <Tabs defaultValue="submissions">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="submissions">Recent Submissions</TabsTrigger>
            <TabsTrigger value="departments">Departments</TabsTrigger>
            <TabsTrigger value="officers">Officers</TabsTrigger>
          </TabsList>

          {/* Filters */}
          <Card className="mt-4">
            <CardContent className="p-4">
              <div className="flex flex-wrap items-center gap-3">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <Select value={filters.state} onValueChange={(v) => setFilters(prev => ({ ...prev, state: v }))}>
                  <SelectTrigger className="w-[150px]"><SelectValue placeholder="State" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All States</SelectItem>
                    {US_STATES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                  </SelectContent>
                </Select>
                <Input 
                  placeholder="Department..." 
                  className="w-[180px]"
                  value={filters.department}
                  onChange={(e) => setFilters(prev => ({ ...prev, department: e.target.value }))}
                />
                <Select value={filters.violation} onValueChange={(v) => setFilters(prev => ({ ...prev, violation: v }))}>
                  <SelectTrigger className="w-[180px]"><SelectValue placeholder="Violation Type" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All Violations</SelectItem>
                    {violationTypes.map(v => <SelectItem key={v} value={v}>{v.replace(/_/g, ' ')}</SelectItem>)}
                  </SelectContent>
                </Select>
                <Select value={filters.severity} onValueChange={(v) => setFilters(prev => ({ ...prev, severity: v }))}>
                  <SelectTrigger className="w-[120px]"><SelectValue placeholder="Severity" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All</SelectItem>
                    {severityOptions.map(s => <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>)}
                  </SelectContent>
                </Select>
                <Button variant="outline" size="sm" onClick={() => setFilters({ state: '', department: '', violation: '', severity: '' })}>
                  Clear
                </Button>
              </div>
            </CardContent>
          </Card>

          <TabsContent value="submissions" className="mt-4">
            <div className="space-y-4">
              {loading ? (
                <div className="text-center py-8">Loading submissions...</div>
              ) : submissions.length === 0 ? (
                <Card>
                  <CardContent className="text-center py-12">
                    <Shield className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                    <p className="text-lg font-medium">No submissions yet</p>
                    <p className="text-muted-foreground">Be the first to contribute to the community vault</p>
                  </CardContent>
                </Card>
              ) : (
                submissions.map((sub) => (
                  <Card key={sub.submission_id} data-testid={`submission-${sub.submission_id}`}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 space-y-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge className={getSeverityColor(sub.severity)}>{sub.severity}</Badge>
                            <Badge variant="outline">{sub.encounter_type?.replace(/_/g, ' ')}</Badge>
                            <span className="text-sm text-muted-foreground flex items-center gap-1">
                              <MapPin className="h-3 w-3" />
                              {sub.location_city}, {sub.location_state}
                            </span>
                            {sub.department && (
                              <span className="text-sm text-muted-foreground flex items-center gap-1">
                                <Building className="h-3 w-3" />
                                {sub.department}
                              </span>
                            )}
                          </div>
                          <p className="text-sm">{sub.summary}</p>
                          <div className="flex flex-wrap gap-1">
                            {sub.violations?.map((v, i) => (
                              <Badge key={i} variant="secondary" className="text-xs">
                                {v.replace(/_/g, ' ')}
                              </Badge>
                            ))}
                          </div>
                          <div className="flex items-center gap-4 text-xs text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {new Date(sub.incident_date).toLocaleDateString()}
                            </span>
                            {sub.outcome && <span>Outcome: {sub.outcome}</span>}
                          </div>
                        </div>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="flex-col gap-1"
                          onClick={() => handleUpvote(sub.submission_id)}
                        >
                          <ThumbsUp className="h-4 w-4" />
                          <span className="text-xs">{sub.upvotes || 0}</span>
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
              
              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex justify-center gap-2">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    Previous
                  </Button>
                  <span className="py-2 px-3 text-sm">Page {page} of {totalPages}</span>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                  >
                    Next
                  </Button>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="departments" className="mt-4">
            <div className="space-y-3">
              {departments.length === 0 ? (
                <Card>
                  <CardContent className="text-center py-12">
                    <Building className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                    <p className="text-muted-foreground">No department data yet</p>
                  </CardContent>
                </Card>
              ) : (
                departments.map((dept, i) => (
                  <Card key={i}>
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{dept.department}</p>
                          <p className="text-sm text-muted-foreground">{dept.state}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-2xl font-bold text-orange-500">{dept.total_incidents}</p>
                          <p className="text-xs text-muted-foreground">incidents</p>
                        </div>
                        <div className="text-right">
                          <p className="font-medium">{dept.officers_with_incidents}</p>
                          <p className="text-xs text-muted-foreground">officers</p>
                        </div>
                        <Button variant="ghost" size="sm">
                          <Eye className="h-4 w-4 mr-1" /> View
                        </Button>
                      </div>
                      {dept.violations_by_type && Object.keys(dept.violations_by_type).length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1">
                          {Object.entries(dept.violations_by_type).slice(0, 5).map(([type, count]) => (
                            <Badge key={type} variant="secondary" className="text-xs">
                              {type.replace(/_/g, ' ')}: {count}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>

          <TabsContent value="officers" className="mt-4">
            <div className="space-y-3">
              {officers.length === 0 ? (
                <Card>
                  <CardContent className="text-center py-12">
                    <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                    <p className="text-muted-foreground">No officer data yet</p>
                  </CardContent>
                </Card>
              ) : (
                officers.map((officer, i) => (
                  <Card key={i}>
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">Badge #{officer.badge_number}</p>
                          <p className="text-sm text-muted-foreground">{officer.department}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-2xl font-bold text-red-500">{officer.total_incidents}</p>
                          <p className="text-xs text-muted-foreground">incidents</p>
                        </div>
                        <Button variant="ghost" size="sm">
                          <Eye className="h-4 w-4 mr-1" /> Profile
                        </Button>
                      </div>
                      {officer.violations_by_type && Object.keys(officer.violations_by_type).length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1">
                          {Object.entries(officer.violations_by_type).slice(0, 5).map(([type, count]) => (
                            <Badge key={type} variant="secondary" className="text-xs">
                              {type.replace(/_/g, ' ')}: {count}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  );
}
