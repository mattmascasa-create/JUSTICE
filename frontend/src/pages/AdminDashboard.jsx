/**
 * Admin Dashboard Page
 * 
 * Main admin control panel with:
 * - Platform statistics
 * - User management
 * - Support ticket queue
 * - AI-assisted ticket resolution
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Alert, AlertDescription } from '../components/ui/alert';
import { adminAPI } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import {
  Shield, Users, Ticket, BarChart3, Search,
  AlertTriangle, Clock, CheckCircle, XCircle,
  MessageSquare, Sparkles, RefreshCw, ChevronRight,
  User, Mail, Calendar, Activity, Loader2
} from 'lucide-react';

// Priority colors
const priorityColors = {
  urgent: 'bg-red-500 text-white',
  high: 'bg-orange-500 text-white',
  medium: 'bg-yellow-500 text-black',
  low: 'bg-green-500 text-white'
};

// Status colors
const statusColors = {
  open: 'bg-blue-500',
  in_progress: 'bg-yellow-500',
  resolved: 'bg-green-500',
  closed: 'bg-gray-500'
};

export default function AdminDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  
  // Dashboard state
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  
  // Tickets state
  const [tickets, setTickets] = useState([]);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [ticketFilter, setTicketFilter] = useState({ status: '', priority: '' });
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [ticketDialogOpen, setTicketDialogOpen] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [responseText, setResponseText] = useState('');
  const [responding, setResponding] = useState(false);
  
  // Users state
  const [users, setUsers] = useState([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [userSearch, setUserSearch] = useState('');
  const [userRoleFilter, setUserRoleFilter] = useState('');
  
  // Check admin access
  useEffect(() => {
    if (user && user.role !== 'admin') {
      toast.error('Admin access required');
      navigate('/dashboard');
    }
  }, [user, navigate]);

  // Load dashboard data
  const loadDashboard = useCallback(async () => {
    try {
      setLoading(true);
      const response = await adminAPI.getDashboard();
      setStats(response.data);
    } catch (error) {
      console.error('Failed to load dashboard:', error);
      if (error.response?.status === 403) {
        toast.error('Admin access required');
        navigate('/dashboard');
      }
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  // Load tickets
  const loadTickets = useCallback(async () => {
    try {
      setTicketsLoading(true);
      const params = {};
      if (ticketFilter.status) params.status = ticketFilter.status;
      if (ticketFilter.priority) params.priority = ticketFilter.priority;
      
      const response = await adminAPI.getTickets(params);
      setTickets(response.data.tickets || []);
    } catch (error) {
      console.error('Failed to load tickets:', error);
    } finally {
      setTicketsLoading(false);
    }
  }, [ticketFilter]);

  // Load users
  const loadUsers = useCallback(async () => {
    try {
      setUsersLoading(true);
      const params = {};
      if (userSearch) params.search = userSearch;
      if (userRoleFilter) params.role = userRoleFilter;
      
      const response = await adminAPI.getUsers(params);
      setUsers(response.data.users || []);
    } catch (error) {
      console.error('Failed to load users:', error);
    } finally {
      setUsersLoading(false);
    }
  }, [userSearch, userRoleFilter]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    if (activeTab === 'tickets') {
      loadTickets();
    } else if (activeTab === 'users') {
      loadUsers();
    }
  }, [activeTab, loadTickets, loadUsers]);

  // Get AI suggestion for ticket
  const getAiSuggestion = async (ticketId) => {
    try {
      setAiLoading(true);
      const response = await adminAPI.getAiSuggestion(ticketId);
      setAiSuggestion(response.data.suggestion);
      setResponseText(response.data.suggestion);
    } catch (error) {
      toast.error('Failed to get AI suggestion');
    } finally {
      setAiLoading(false);
    }
  };

  // Respond to ticket
  const handleRespondToTicket = async () => {
    if (!selectedTicket || !responseText.trim()) return;
    
    try {
      setResponding(true);
      await adminAPI.respondToTicket(selectedTicket.ticket_id, {
        subject: selectedTicket.subject,
        description: selectedTicket.description,
        response_text: responseText,
        is_public: true
      });
      toast.success('Response sent successfully');
      setTicketDialogOpen(false);
      setResponseText('');
      setAiSuggestion('');
      loadTickets();
    } catch (error) {
      toast.error('Failed to send response');
    } finally {
      setResponding(false);
    }
  };

  // Update ticket status
  const updateTicketStatus = async (ticketId, status) => {
    try {
      await adminAPI.updateTicket(ticketId, { status });
      toast.success(`Ticket marked as ${status}`);
      loadTickets();
    } catch (error) {
      toast.error('Failed to update ticket');
    }
  };

  // Update user role
  const updateUserRole = async (userId, role) => {
    try {
      await adminAPI.updateUser(userId, { role });
      toast.success('User role updated');
      loadUsers();
    } catch (error) {
      toast.error('Failed to update user');
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="admin-dashboard">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <Shield className="h-8 w-8 text-primary" />
              Admin Dashboard
            </h1>
            <p className="text-muted-foreground mt-1">
              Manage users, support tickets, and platform settings
            </p>
          </div>
          <Button variant="outline" onClick={loadDashboard}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Users</p>
                  <p className="text-2xl font-bold">{stats?.users?.total || 0}</p>
                </div>
                <Users className="h-8 w-8 text-blue-500 opacity-50" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Open Tickets</p>
                  <p className="text-2xl font-bold">{stats?.tickets?.open || 0}</p>
                </div>
                <Ticket className="h-8 w-8 text-yellow-500 opacity-50" />
              </div>
            </CardContent>
          </Card>
          
          <Card className={stats?.tickets?.urgent > 0 ? 'border-red-500/50 bg-red-500/5' : ''}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Urgent Tickets</p>
                  <p className="text-2xl font-bold text-red-500">{stats?.tickets?.urgent || 0}</p>
                </div>
                <AlertTriangle className="h-8 w-8 text-red-500 opacity-50" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Encounters</p>
                  <p className="text-2xl font-bold">{stats?.platform?.total_encounters || 0}</p>
                </div>
                <Activity className="h-8 w-8 text-green-500 opacity-50" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="overview" data-testid="tab-overview">
              <BarChart3 className="h-4 w-4 mr-2" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="tickets" data-testid="tab-tickets">
              <Ticket className="h-4 w-4 mr-2" />
              Tickets {stats?.tickets?.open > 0 && <Badge className="ml-2 bg-red-500">{stats.tickets.open}</Badge>}
            </TabsTrigger>
            <TabsTrigger value="users" data-testid="tab-users">
              <Users className="h-4 w-4 mr-2" />
              Users
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              {/* Recent Tickets */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Recent Tickets</CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[300px]">
                    {stats?.tickets?.recent?.length > 0 ? (
                      <div className="space-y-3">
                        {stats.tickets.recent.map((ticket) => (
                          <div
                            key={ticket.ticket_id}
                            className="p-3 rounded-lg border hover:bg-muted/50 cursor-pointer transition-colors"
                            onClick={() => {
                              setSelectedTicket(ticket);
                              setActiveTab('tickets');
                            }}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex-1 min-w-0">
                                <p className="font-medium truncate">{ticket.subject}</p>
                                <p className="text-sm text-muted-foreground">
                                  {ticket.user_name} • {new Date(ticket.created_at).toLocaleDateString()}
                                </p>
                              </div>
                              <Badge className={priorityColors[ticket.priority]}>
                                {ticket.priority}
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-center text-muted-foreground py-8">No recent tickets</p>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>

              {/* User Stats */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">User Breakdown</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 rounded-lg bg-blue-500/10">
                      <div className="flex items-center gap-3">
                        <User className="h-5 w-5 text-blue-500" />
                        <span>Citizens</span>
                      </div>
                      <span className="font-bold">{stats?.users?.by_role?.citizens || 0}</span>
                    </div>
                    <div className="flex items-center justify-between p-3 rounded-lg bg-purple-500/10">
                      <div className="flex items-center gap-3">
                        <User className="h-5 w-5 text-purple-500" />
                        <span>Attorneys</span>
                      </div>
                      <span className="font-bold">{stats?.users?.by_role?.attorneys || 0}</span>
                    </div>
                    <div className="flex items-center justify-between p-3 rounded-lg bg-amber-500/10">
                      <div className="flex items-center gap-3">
                        <Shield className="h-5 w-5 text-amber-500" />
                        <span>Admins</span>
                      </div>
                      <span className="font-bold">{stats?.users?.by_role?.admins || 0}</span>
                    </div>
                  </div>
                  
                  <div className="pt-4 border-t">
                    <p className="text-sm text-muted-foreground mb-2">Active Today</p>
                    <p className="text-3xl font-bold">{stats?.users?.active_today || 0}</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Tickets Tab */}
          <TabsContent value="tickets" className="space-y-4">
            {/* Filters */}
            <div className="flex gap-4 flex-wrap">
              <Select value={ticketFilter.status || 'all'} onValueChange={(v) => setTicketFilter(p => ({ ...p, status: v === 'all' ? '' : v }))}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="All Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="open">Open</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="resolved">Resolved</SelectItem>
                  <SelectItem value="closed">Closed</SelectItem>
                </SelectContent>
              </Select>
              
              <Select value={ticketFilter.priority || 'all'} onValueChange={(v) => setTicketFilter(p => ({ ...p, priority: v === 'all' ? '' : v }))}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="All Priority" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Priority</SelectItem>
                  <SelectItem value="urgent">Urgent</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
              
              <Button variant="outline" onClick={loadTickets} disabled={ticketsLoading}>
                <RefreshCw className={`h-4 w-4 mr-2 ${ticketsLoading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>

            {/* Tickets List */}
            <Card>
              <CardContent className="p-0">
                <ScrollArea className="h-[500px]">
                  {tickets.length > 0 ? (
                    <div className="divide-y">
                      {tickets.map((ticket) => (
                        <div
                          key={ticket.ticket_id}
                          className="p-4 hover:bg-muted/50 cursor-pointer transition-colors"
                          onClick={() => {
                            setSelectedTicket(ticket);
                            setTicketDialogOpen(true);
                          }}
                        >
                          <div className="flex items-start gap-4">
                            <div className={`w-2 h-2 mt-2 rounded-full ${statusColors[ticket.status]}`} />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <p className="font-medium">{ticket.subject}</p>
                                <Badge className={priorityColors[ticket.priority]} variant="secondary">
                                  {ticket.priority}
                                </Badge>
                                <Badge variant="outline">{ticket.category}</Badge>
                              </div>
                              <p className="text-sm text-muted-foreground line-clamp-2">{ticket.description}</p>
                              <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                                <span className="flex items-center gap-1">
                                  <User className="h-3 w-3" />
                                  {ticket.user_name}
                                </span>
                                <span className="flex items-center gap-1">
                                  <Mail className="h-3 w-3" />
                                  {ticket.user_email}
                                </span>
                                <span className="flex items-center gap-1">
                                  <Calendar className="h-3 w-3" />
                                  {new Date(ticket.created_at).toLocaleString()}
                                </span>
                              </div>
                            </div>
                            <ChevronRight className="h-5 w-5 text-muted-foreground" />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-12">
                      <CheckCircle className="h-12 w-12 text-green-500 mb-4" />
                      <p className="text-lg font-medium">All caught up!</p>
                      <p className="text-muted-foreground">No tickets match your filters</p>
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Users Tab */}
          <TabsContent value="users" className="space-y-4">
            {/* Search & Filters */}
            <div className="flex gap-4 flex-wrap">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by name or email..."
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
              
              <Select value={userRoleFilter} onValueChange={setUserRoleFilter}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="All Roles" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Roles</SelectItem>
                  <SelectItem value="citizen">Citizens</SelectItem>
                  <SelectItem value="attorney">Attorneys</SelectItem>
                  <SelectItem value="admin">Admins</SelectItem>
                </SelectContent>
              </Select>
              
              <Button variant="outline" onClick={loadUsers} disabled={usersLoading}>
                <RefreshCw className={`h-4 w-4 mr-2 ${usersLoading ? 'animate-spin' : ''}`} />
                Search
              </Button>
            </div>

            {/* Users List */}
            <Card>
              <CardContent className="p-0">
                <ScrollArea className="h-[500px]">
                  {users.length > 0 ? (
                    <div className="divide-y">
                      {users.map((u) => (
                        <div key={u.user_id} className="p-4 flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                              <User className="h-5 w-5 text-primary" />
                            </div>
                            <div>
                              <p className="font-medium">{u.name}</p>
                              <p className="text-sm text-muted-foreground">{u.email}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            <Select
                              value={u.role}
                              onValueChange={(role) => updateUserRole(u.user_id, role)}
                            >
                              <SelectTrigger className="w-[120px]">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="citizen">Citizen</SelectItem>
                                <SelectItem value="attorney">Attorney</SelectItem>
                                <SelectItem value="admin">Admin</SelectItem>
                              </SelectContent>
                            </Select>
                            <span className="text-xs text-muted-foreground">
                              {new Date(u.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-12">
                      <Users className="h-12 w-12 text-muted-foreground mb-4" />
                      <p className="text-lg font-medium">No users found</p>
                      <p className="text-muted-foreground">Try adjusting your search</p>
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Ticket Detail Dialog */}
        <Dialog open={ticketDialogOpen} onOpenChange={setTicketDialogOpen}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            {selectedTicket && (
              <>
                <DialogHeader>
                  <div className="flex items-center gap-2">
                    <Badge className={priorityColors[selectedTicket.priority]}>
                      {selectedTicket.priority}
                    </Badge>
                    <Badge variant="outline">{selectedTicket.status}</Badge>
                  </div>
                  <DialogTitle className="text-xl mt-2">{selectedTicket.subject}</DialogTitle>
                  <p className="text-sm text-muted-foreground">
                    From: {selectedTicket.user_name} ({selectedTicket.user_email}) • 
                    {new Date(selectedTicket.created_at).toLocaleString()}
                  </p>
                </DialogHeader>

                <div className="space-y-4">
                  {/* Description */}
                  <div>
                    <h4 className="font-medium mb-2">Description</h4>
                    <p className="text-sm bg-muted p-3 rounded-lg whitespace-pre-wrap">
                      {selectedTicket.description}
                    </p>
                  </div>

                  {/* Previous Responses */}
                  {selectedTicket.responses?.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-2">Previous Responses</h4>
                      <div className="space-y-2">
                        {selectedTicket.responses.map((r, i) => (
                          <div key={i} className="bg-blue-500/10 p-3 rounded-lg">
                            <p className="text-xs text-muted-foreground mb-1">
                              {r.responder_name} • {new Date(r.created_at).toLocaleString()}
                            </p>
                            <p className="text-sm">{r.text}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* AI Suggestion */}
                  <div className="border-t pt-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-purple-500" />
                        AI-Assisted Response
                      </h4>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => getAiSuggestion(selectedTicket.ticket_id)}
                        disabled={aiLoading}
                      >
                        {aiLoading ? (
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        ) : (
                          <Sparkles className="h-4 w-4 mr-2" />
                        )}
                        Generate Suggestion
                      </Button>
                    </div>
                    
                    <Textarea
                      placeholder="Type your response or click 'Generate Suggestion' for AI help..."
                      value={responseText}
                      onChange={(e) => setResponseText(e.target.value)}
                      className="min-h-[150px]"
                    />
                  </div>

                  {/* Quick Actions */}
                  <div className="flex gap-2 flex-wrap">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => updateTicketStatus(selectedTicket.ticket_id, 'in_progress')}
                    >
                      <Clock className="h-4 w-4 mr-1" />
                      Mark In Progress
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => updateTicketStatus(selectedTicket.ticket_id, 'resolved')}
                      className="text-green-600 border-green-600"
                    >
                      <CheckCircle className="h-4 w-4 mr-1" />
                      Mark Resolved
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => updateTicketStatus(selectedTicket.ticket_id, 'closed')}
                    >
                      <XCircle className="h-4 w-4 mr-1" />
                      Close
                    </Button>
                  </div>
                </div>

                <DialogFooter>
                  <Button variant="outline" onClick={() => setTicketDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button
                    onClick={handleRespondToTicket}
                    disabled={!responseText.trim() || responding}
                  >
                    {responding ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <MessageSquare className="h-4 w-4 mr-2" />
                    )}
                    Send Response
                  </Button>
                </DialogFooter>
              </>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  );
}
