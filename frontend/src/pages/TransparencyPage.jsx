import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Progress } from '../components/ui/progress';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { departmentsAPI, analyticsAPI } from '../lib/api';
import { 
  Building, Search, MapPin, AlertTriangle, Shield, Users, 
  TrendingUp, TrendingDown, Eye, DollarSign, Camera, Scale,
  BarChart3, Info
} from 'lucide-react';
import { toast } from 'sonner';

export default function TransparencyPage() {
  const [departments, setDepartments] = useState([]);
  const [publicStats, setPublicStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [stateFilter, setStateFilter] = useState('all');
  const [sortBy, setSortBy] = useState('risk_score');
  const [selectedDepartment, setSelectedDepartment] = useState(null);

  useEffect(() => {
    fetchData();
  }, [sortBy, stateFilter]);

  const fetchData = async () => {
    try {
      const params = { sort_by: sortBy };
      if (stateFilter !== 'all') params.state = stateFilter;
      
      const [deptRes, statsRes] = await Promise.all([
        departmentsAPI.list(params),
        analyticsAPI.getPublic()
      ]);
      setDepartments(deptRes.data);
      setPublicStats(statsRes.data);
    } catch (error) {
      toast.error('Failed to load transparency data');
    } finally {
      setLoading(false);
    }
  };

  const filteredDepartments = departments.filter(d =>
    d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    d.city.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getRiskColor = (score) => {
    if (score >= 8) return 'text-red-500 bg-red-500/10';
    if (score >= 6) return 'text-orange-500 bg-orange-500/10';
    if (score >= 4) return 'text-yellow-500 bg-yellow-500/10';
    return 'text-green-500 bg-green-500/10';
  };

  const getTransparencyColor = (score) => {
    if (score >= 8) return 'text-green-500';
    if (score >= 6) return 'text-yellow-500';
    if (score >= 4) return 'text-orange-500';
    return 'text-red-500';
  };

  const formatBudget = (budget) => {
    if (budget >= 1000000000) return `$${(budget / 1000000000).toFixed(1)}B`;
    if (budget >= 1000000) return `$${(budget / 1000000).toFixed(0)}M`;
    return `$${budget.toLocaleString()}`;
  };

  const states = [...new Set(departments.map(d => d.state))].sort();

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
      <div className="space-y-6" data-testid="transparency-page">
        {/* Header */}
        <div>
          <h1 className="font-serif text-3xl font-bold">Transparency Portal</h1>
          <p className="text-muted-foreground mt-1">Public police department accountability data</p>
        </div>

        {/* Stats Overview */}
        {publicStats && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Departments Tracked</p>
                    <p className="text-3xl font-bold">{publicStats.total_departments || departments.length}</p>
                  </div>
                  <Building className="h-8 w-8 text-blue-500" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Cases</p>
                    <p className="text-3xl font-bold">{publicStats.total_cases}</p>
                  </div>
                  <Scale className="h-8 w-8 text-purple-500" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Resolution Rate</p>
                    <p className="text-3xl font-bold">{publicStats.success_rate}%</p>
                  </div>
                  <TrendingUp className="h-8 w-8 text-green-500" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Active Users</p>
                    <p className="text-3xl font-bold">{publicStats.total_users}</p>
                  </div>
                  <Users className="h-8 w-8 text-cyan-500" />
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search departments..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
              data-testid="dept-search"
            />
          </div>
          <Select value={stateFilter} onValueChange={setStateFilter}>
            <SelectTrigger className="w-full lg:w-48" data-testid="state-filter">
              <MapPin className="h-4 w-4 mr-2" />
              <SelectValue placeholder="State" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All States</SelectItem>
              {states.map(state => (
                <SelectItem key={state} value={state}>{state}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="w-full lg:w-48" data-testid="sort-by">
              <BarChart3 className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="risk_score">Risk Score (High to Low)</SelectItem>
              <SelectItem value="transparency_score">Transparency (High to Low)</SelectItem>
              <SelectItem value="complaint_rate">Complaint Rate</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Info Banner */}
        <Card className="bg-blue-500/10 border-blue-500/20">
          <CardContent className="p-4 flex items-start gap-4">
            <Info className="h-6 w-6 text-blue-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-blue-600 dark:text-blue-400">About This Data</p>
              <p className="text-sm text-muted-foreground">
                Risk scores are calculated based on complaint rates, use of force incidents, body cam adoption, 
                and transparency metrics. Higher scores indicate more accountability concerns.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Department Cards */}
        <div className="grid gap-4">
          {filteredDepartments.map((dept) => (
            <Card key={dept.department_id} data-testid={`dept-card-${dept.department_id}`}>
              <CardContent className="p-6">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-start gap-4">
                      <div className={`p-3 rounded-lg ${getRiskColor(dept.risk_score)}`}>
                        <Building className="h-6 w-6" />
                      </div>
                      <div>
                        <h3 className="font-serif text-xl font-bold">{dept.name}</h3>
                        <p className="text-sm text-muted-foreground flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {dept.city}, {dept.state}
                        </p>
                        {dept.chief_name && (
                          <p className="text-sm text-muted-foreground mt-1">
                            Chief: {dept.chief_name}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4">
                      <div>
                        <p className="text-xs text-muted-foreground">Officers</p>
                        <p className="font-bold flex items-center gap-1">
                          <Users className="h-4 w-4 text-muted-foreground" />
                          {dept.officer_count.toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Budget</p>
                        <p className="font-bold flex items-center gap-1">
                          <DollarSign className="h-4 w-4 text-muted-foreground" />
                          {formatBudget(dept.budget)}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Body Cams</p>
                        <p className="font-bold flex items-center gap-1">
                          <Camera className="h-4 w-4 text-muted-foreground" />
                          {dept.body_cam_adoption}%
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Incidents</p>
                        <p className="font-bold">
                          {dept.resolved_incidents}/{dept.total_incidents}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row lg:flex-col items-start sm:items-center lg:items-end gap-4">
                    {/* Risk Score */}
                    <div className="text-center lg:text-right">
                      <p className="text-xs text-muted-foreground mb-1">Risk Score</p>
                      <Badge className={`text-lg px-3 py-1 ${getRiskColor(dept.risk_score)}`}>
                        {dept.risk_score.toFixed(1)}
                      </Badge>
                    </div>

                    {/* Metrics */}
                    <div className="space-y-2 w-48">
                      <div>
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span>Complaint Rate</span>
                          <span>{dept.complaint_rate}%</span>
                        </div>
                        <Progress value={dept.complaint_rate} className="h-1.5" />
                      </div>
                      <div>
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span>Use of Force</span>
                          <span>{dept.use_of_force_rate}%</span>
                        </div>
                        <Progress value={dept.use_of_force_rate} className="h-1.5" />
                      </div>
                      <div>
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span>Transparency</span>
                          <span className={getTransparencyColor(dept.transparency_score)}>
                            {dept.transparency_score}/10
                          </span>
                        </div>
                        <Progress value={dept.transparency_score * 10} className="h-1.5" />
                      </div>
                    </div>

                    <Dialog>
                      <DialogTrigger asChild>
                        <Button variant="outline" size="sm" onClick={() => setSelectedDepartment(dept)}>
                          <Eye className="h-4 w-4 mr-2" />
                          View Details
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="max-w-2xl">
                        <DialogHeader>
                          <DialogTitle className="font-serif">{dept.name}</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-6">
                          <div className="grid grid-cols-2 gap-4">
                            <div className="p-4 rounded-lg bg-muted">
                              <p className="text-sm text-muted-foreground">Risk Score</p>
                              <p className="text-3xl font-bold">{dept.risk_score.toFixed(1)}/10</p>
                            </div>
                            <div className="p-4 rounded-lg bg-muted">
                              <p className="text-sm text-muted-foreground">Transparency Score</p>
                              <p className="text-3xl font-bold">{dept.transparency_score.toFixed(1)}/10</p>
                            </div>
                          </div>

                          <div>
                            <h4 className="font-bold mb-3">Key Metrics</h4>
                            <div className="space-y-3">
                              <div>
                                <div className="flex justify-between text-sm mb-1">
                                  <span>Complaint Rate</span>
                                  <span className="font-mono">{dept.complaint_rate}%</span>
                                </div>
                                <Progress value={dept.complaint_rate} />
                              </div>
                              <div>
                                <div className="flex justify-between text-sm mb-1">
                                  <span>Use of Force Rate</span>
                                  <span className="font-mono">{dept.use_of_force_rate}%</span>
                                </div>
                                <Progress value={dept.use_of_force_rate} />
                              </div>
                              <div>
                                <div className="flex justify-between text-sm mb-1">
                                  <span>Body Camera Adoption</span>
                                  <span className="font-mono">{dept.body_cam_adoption}%</span>
                                </div>
                                <Progress value={dept.body_cam_adoption} />
                              </div>
                            </div>
                          </div>

                          <div className="grid grid-cols-3 gap-4 text-center">
                            <div className="p-3 rounded-lg bg-muted">
                              <p className="text-2xl font-bold">{dept.officer_count.toLocaleString()}</p>
                              <p className="text-xs text-muted-foreground">Officers</p>
                            </div>
                            <div className="p-3 rounded-lg bg-muted">
                              <p className="text-2xl font-bold">{formatBudget(dept.budget)}</p>
                              <p className="text-xs text-muted-foreground">Budget</p>
                            </div>
                            <div className="p-3 rounded-lg bg-muted">
                              <p className="text-2xl font-bold">{dept.total_incidents}</p>
                              <p className="text-xs text-muted-foreground">Total Incidents</p>
                            </div>
                          </div>
                        </div>
                      </DialogContent>
                    </Dialog>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {filteredDepartments.length === 0 && (
          <Card>
            <CardContent className="py-12 text-center">
              <Building className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">No departments found</h3>
              <p className="text-muted-foreground">Try adjusting your search or filters</p>
            </CardContent>
          </Card>
        )}
      </div>
    </AppLayout>
  );
}
