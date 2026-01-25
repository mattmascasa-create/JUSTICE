import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { LocationAlertPanel } from '../components/LocationAlertPanel';
import { analyticsAPI, casesAPI } from '../lib/api';
import { formatDate, getStatusColor, getSeverityColor } from '../lib/utils';
import { 
  FolderOpen, FileBox, Siren, Bot, Plus, 
  TrendingUp, AlertTriangle, CheckCircle, Clock,
  ArrowRight, Shield, Scale
} from 'lucide-react';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [recentCases, setRecentCases] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, casesRes] = await Promise.all([
          analyticsAPI.getDashboard(),
          casesAPI.list()
        ]);
        setStats(statsRes.data);
        setRecentCases(casesRes.data.slice(0, 5));
      } catch (error) {
        console.error('Dashboard fetch error:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const quickActions = [
    { icon: Plus, label: 'New Case', path: '/cases/new', color: 'bg-blue-500' },
    { icon: Bot, label: 'AI Attorney', path: '/ai-attorney', color: 'bg-purple-500' },
    { icon: Siren, label: 'SOS', path: '/sos', color: 'bg-red-500' },
    { icon: Scale, label: 'Find Attorney', path: '/attorneys', color: 'bg-green-500' },
  ];

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
      <div className="space-y-8" data-testid="dashboard">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-serif text-3xl font-bold">Dashboard</h1>
            <p className="text-muted-foreground mt-1">Your rights protection overview</p>
          </div>
          <Link to="/cases/new">
            <Button data-testid="new-case-btn">
              <Plus className="h-4 w-4 mr-2" />
              Report Incident
            </Button>
          </Link>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {quickActions.map((action, index) => (
            <Link key={index} to={action.path}>
              <Card 
                className="hover:shadow-md transition-shadow cursor-pointer group"
                data-testid={`quick-action-${action.label.toLowerCase().replace(/\s+/g, '-')}`}
              >
                <CardContent className="p-4 flex items-center gap-3">
                  <div className={`p-3 rounded-lg ${action.color} text-white`}>
                    <action.icon className="h-5 w-5" />
                  </div>
                  <span className="font-medium group-hover:text-primary transition-colors">
                    {action.label}
                  </span>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>

        {/* Stats Grid */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card data-testid="stat-total-cases">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Cases</p>
                  <p className="text-3xl font-bold mt-1">{stats?.total_cases || 0}</p>
                </div>
                <div className="p-3 rounded-full bg-blue-500/10">
                  <FolderOpen className="h-6 w-6 text-blue-500" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="stat-open-cases">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Open Cases</p>
                  <p className="text-3xl font-bold mt-1">{stats?.open_cases || 0}</p>
                </div>
                <div className="p-3 rounded-full bg-yellow-500/10">
                  <Clock className="h-6 w-6 text-yellow-500" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="stat-resolved-cases">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Resolved</p>
                  <p className="text-3xl font-bold mt-1">{stats?.resolved_cases || 0}</p>
                </div>
                <div className="p-3 rounded-full bg-green-500/10">
                  <CheckCircle className="h-6 w-6 text-green-500" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="stat-total-evidence">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Evidence Files</p>
                  <p className="text-3xl font-bold mt-1">{stats?.total_evidence || 0}</p>
                </div>
                <div className="p-3 rounded-full bg-purple-500/10">
                  <FileBox className="h-6 w-6 text-purple-500" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Grid */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Recent Cases */}
          <Card className="lg:col-span-2" data-testid="recent-cases-section">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="font-serif">Recent Cases</CardTitle>
              <Link to="/cases">
                <Button variant="ghost" size="sm">
                  View all <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {recentCases.length === 0 ? (
                <div className="text-center py-8">
                  <Shield className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                  <p className="text-muted-foreground">No cases yet</p>
                  <Link to="/cases/new">
                    <Button variant="outline" size="sm" className="mt-4">
                      Report your first incident
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-3">
                  {recentCases.map((caseItem) => (
                    <Link                      key={caseItem.case_id} 
                      to={`/cases/${caseItem.case_id}`}
                      className="block"
                    >
                      <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50 hover:bg-muted transition-colors">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">{caseItem.title}</p>
                          <p className="text-sm text-muted-foreground">
                            {formatDate(caseItem.incident_date)} • {caseItem.location}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 ml-4">
                          <Badge className={getSeverityColor(caseItem.severity)}>
                            {caseItem.severity}
                          </Badge>
                          <Badge className={getStatusColor(caseItem.status)}>
                            {caseItem.status}
                          </Badge>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Violations by Type */}
          <Card data-testid="violations-by-type">
            <CardHeader>
              <CardTitle className="font-serif">Violations by Type</CardTitle>
            </CardHeader>
            <CardContent>
              {stats?.violations_by_type?.length > 0 ? (
                <div className="space-y-4">
                  {stats.violations_by_type.map((violation, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <AlertTriangle className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">{violation.type || 'Unknown'}</span>
                      </div>
                      <Badge variant="secondary">{violation.count}</Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No violations recorded yet
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Emergency SOS Banner */}
        <Card className="bg-gradient-to-r from-red-600 to-red-700 text-white border-0">
          <CardContent className="p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-full bg-white/20 animate-pulse">
                <Siren className="h-8 w-8" />
              </div>
              <div>
                <h3 className="text-xl font-bold">Emergency SOS</h3>
                <p className="text-white/80">One-tap activation for immediate help</p>
              </div>
            </div>
            <Link to="/sos">
              <Button 
                size="lg" 
                className="bg-white text-red-600 hover:bg-white/90"
                data-testid="dashboard-sos-btn"
              >
                Activate SOS
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}
