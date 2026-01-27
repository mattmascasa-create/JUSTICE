import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { attorneyCollabAPI, attorneyStreamAPI } from '../lib/api';
import { toast } from 'sonner';
import { useAuth } from '../contexts/AuthContext';
import { 
  Briefcase, Users, FileText, MessageCircle, 
  Clock, CheckCircle, Shield, Award, 
  AlertTriangle, ArrowRight, Mail, Building,
  BarChart3, UserCheck, XCircle, Video,
  Radio, MapPin, Bell, Eye, RefreshCw, ExternalLink
} from 'lucide-react';

export default function AttorneyDashboardPage() {
  const { user } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showVerifyDialog, setShowVerifyDialog] = useState(false);
  const [verifyForm, setVerifyForm] = useState({
    barNumber: '',
    firmName: '',
    specialization: ''
  });
  const [verifying, setVerifying] = useState(false);
  
  // New state for live streams and alerts
  const [activeStreams, setActiveStreams] = useState([]);
  const [recentAlerts, setRecentAlerts] = useState([]);
  const [streamHistory, setStreamHistory] = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  const fetchDashboard = useCallback(async () => {
    try {
      const res = await attorneyCollabAPI.getDashboard();
      setDashboard(res.data);
    } catch (error) {
      console.error('Error fetching dashboard:', error);
      if (error.response?.status === 403) {
        toast.error('Attorney access required');
      } else {
        toast.error('Failed to load dashboard');
      }
    } finally {
      setLoading(false);
    }
  }, []);
  
  const fetchStreamHistory = useCallback(async () => {
    try {
      const res = await attorneyStreamAPI.getHistory(20);
      const streams = res.data.streams || [];
      
      // Separate active vs ended streams
      const active = streams.filter(s => s.status === 'active' || s.status === 'pending');
      const recent = streams.filter(s => s.status === 'ended').slice(0, 5);
      
      setActiveStreams(active);
      setStreamHistory(recent);
      
      // Create alerts from active streams
      const alerts = active.map(s => ({
        id: s.session_id,
        type: 'live_stream',
        message: `Client is streaming live from ${s.location || 'unknown location'}`,
        timestamp: s.created_at,
        stream_code: s.stream_code,
        encounter_id: s.encounter_id,
        urgent: true
      }));
      setRecentAlerts(alerts);
    } catch (error) {
      console.error('Error fetching stream history:', error);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
    fetchStreamHistory();
    
    // Poll for active streams every 30 seconds
    const pollInterval = setInterval(fetchStreamHistory, 30000);
    return () => clearInterval(pollInterval);
  }, [fetchDashboard, fetchStreamHistory]);
  
  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([fetchDashboard(), fetchStreamHistory()]);
    setRefreshing(false);
    toast.success('Dashboard refreshed');
  };

  const handleVerify = async () => {
    if (!verifyForm.barNumber) {
      toast.error('Bar number is required');
      return;
    }
    
    setVerifying(true);
    try {
      await attorneyCollabAPI.verify(
        verifyForm.barNumber,
        verifyForm.firmName,
        verifyForm.specialization
      );
      toast.success('Verification successful!');
      setShowVerifyDialog(false);
      fetchDashboard();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Verification failed');
    } finally {
      setVerifying(false);
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

  // Check if user is an attorney
  if (user?.role !== 'attorney') {
    return (
      <AppLayout>
        <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
          <Shield className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-2xl font-bold">Attorney Access Required</h2>
          <p className="text-muted-foreground text-center max-w-md">
            This dashboard is only available to verified attorneys. 
            If you received an invitation, please use the link provided to accept it.
          </p>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-8" data-testid="attorney-dashboard">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-serif text-3xl font-bold">Attorney Dashboard</h1>
            <p className="text-muted-foreground mt-1">
              Welcome back, {dashboard?.attorney_name || user?.name}
            </p>
          </div>
          
          {/* Verification Badge / Button */}
          {dashboard?.verified ? (
            <Badge variant="secondary" className="flex items-center gap-2 text-green-600 bg-green-100">
              <CheckCircle className="h-4 w-4" />
              Verified Attorney
            </Badge>
          ) : (
            <Dialog open={showVerifyDialog} onOpenChange={setShowVerifyDialog}>
              <DialogTrigger asChild>
                <Button variant="outline" data-testid="verify-btn">
                  <Award className="h-4 w-4 mr-2" />
                  Verify Credentials
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Attorney Verification</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label htmlFor="bar-number">Bar Number *</Label>
                    <Input
                      id="bar-number"
                      value={verifyForm.barNumber}
                      onChange={(e) => setVerifyForm({ ...verifyForm, barNumber: e.target.value })}
                      placeholder="e.g., CA123456"
                      data-testid="bar-number-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="firm-name">Law Firm (Optional)</Label>
                    <Input
                      id="firm-name"
                      value={verifyForm.firmName}
                      onChange={(e) => setVerifyForm({ ...verifyForm, firmName: e.target.value })}
                      placeholder="Your law firm"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="specialization">Specialization (Optional)</Label>
                    <Input
                      id="specialization"
                      value={verifyForm.specialization}
                      onChange={(e) => setVerifyForm({ ...verifyForm, specialization: e.target.value })}
                      placeholder="e.g., Civil Rights, Criminal Defense"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowVerifyDialog(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleVerify} disabled={verifying} data-testid="submit-verify-btn">
                    {verifying ? 'Verifying...' : 'Submit Verification'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          )}
        </div>

        {/* Stats Grid */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card data-testid="stat-clients">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Clients</p>
                  <p className="text-3xl font-bold">{dashboard?.stats?.total_clients || 0}</p>
                </div>
                <Users className="h-10 w-10 text-blue-500 opacity-50" />
              </div>
            </CardContent>
          </Card>

          <Card data-testid="stat-encounters">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Active Encounters</p>
                  <p className="text-3xl font-bold">{dashboard?.stats?.total_encounters || 0}</p>
                </div>
                <FileText className="h-10 w-10 text-purple-500 opacity-50" />
              </div>
            </CardContent>
          </Card>

          <Card data-testid="stat-reviews">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Pending Reviews</p>
                  <p className="text-3xl font-bold">{dashboard?.stats?.pending_reviews || 0}</p>
                </div>
                <AlertTriangle className="h-10 w-10 text-yellow-500 opacity-50" />
              </div>
            </CardContent>
          </Card>

          <Card data-testid="stat-messages">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Unread Messages</p>
                  <p className="text-3xl font-bold">{dashboard?.stats?.unread_messages || 0}</p>
                </div>
                <MessageCircle className="h-10 w-10 text-green-500 opacity-50" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs for Clients & Encounters */}
        <Tabs defaultValue="clients" className="space-y-4">
          <TabsList>
            <TabsTrigger value="clients" data-testid="tab-clients">
              <Users className="h-4 w-4 mr-2" />
              My Clients
            </TabsTrigger>
            <TabsTrigger value="encounters" data-testid="tab-encounters">
              <FileText className="h-4 w-4 mr-2" />
              Shared Encounters
            </TabsTrigger>
          </TabsList>

          <TabsContent value="clients" className="space-y-4">
            {dashboard?.clients?.length > 0 ? (
              <div className="grid gap-4">
                {dashboard.clients.map((client, index) => (
                  <Card key={client.client_id || index} data-testid={`client-card-${index}`}>
                    <CardContent className="p-6">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                            <Users className="h-6 w-6 text-primary" />
                          </div>
                          <div>
                            <h3 className="font-semibold">{client.client_name || 'Unknown Client'}</h3>
                            <p className="text-sm text-muted-foreground">{client.client_email}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <p className="text-sm font-medium">{client.encounter_count} encounter(s)</p>
                            {client.last_activity && (
                              <p className="text-xs text-muted-foreground">
                                Last activity: {new Date(client.last_activity).toLocaleDateString()}
                              </p>
                            )}
                          </div>
                          <Link to={`/attorney/workspace/${client.client_id}`}>
                            <Button variant="outline" size="sm">
                              View <ArrowRight className="h-4 w-4 ml-2" />
                            </Button>
                          </Link>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <Card>
                <CardContent className="p-12 text-center">
                  <Users className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="font-semibold text-lg">No Clients Yet</h3>
                  <p className="text-muted-foreground mt-2">
                    When clients invite you to collaborate on their encounters, they'll appear here.
                  </p>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="encounters" className="space-y-4">
            <EncountersList encounterIds={dashboard?.encounter_ids || []} />
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  );
}

// Sub-component for encounters list
function EncountersList({ encounterIds }) {
  const [encounters, setEncounters] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchEncounters();
  }, []);

  const fetchEncounters = async () => {
    try {
      const res = await attorneyCollabAPI.getEncounters();
      setEncounters(res.data.encounters || []);
    } catch (error) {
      console.error('Error fetching encounters:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (encounters.length === 0) {
    return (
      <Card>
        <CardContent className="p-12 text-center">
          <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="font-semibold text-lg">No Shared Encounters</h3>
          <p className="text-muted-foreground mt-2">
            When clients share encounters with you, they'll appear here for review.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4">
      {encounters.map((enc, index) => (
        <Card key={enc.encounter_id} data-testid={`encounter-card-${index}`}>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`h-12 w-12 rounded-full flex items-center justify-center ${
                  enc.status === 'active' ? 'bg-green-100' : 'bg-gray-100'
                }`}>
                  <FileText className={`h-6 w-6 ${
                    enc.status === 'active' ? 'text-green-600' : 'text-gray-600'
                  }`} />
                </div>
                <div>
                  <h3 className="font-semibold">{enc.encounter_type?.replace(/_/g, ' ')}</h3>
                  <p className="text-sm text-muted-foreground">
                    Client: {enc.client_name} • {enc.address || 'Unknown location'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <Badge variant={enc.status === 'active' ? 'default' : 'secondary'}>
                    {enc.status}
                  </Badge>
                  {enc.highlights_count > 0 && (
                    <p className="text-xs text-yellow-600 mt-1">
                      {enc.highlights_count} highlight(s)
                    </p>
                  )}
                </div>
                <Link to={`/attorney/encounter/${enc.encounter_id}`}>
                  <Button variant="outline" size="sm">
                    Review <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </Link>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Started: {new Date(enc.started_at).toLocaleString()}
              </span>
              <span className="flex items-center gap-1">
                <UserCheck className="h-3 w-3" />
                Access granted: {new Date(enc.access_granted_at).toLocaleDateString()}
              </span>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
