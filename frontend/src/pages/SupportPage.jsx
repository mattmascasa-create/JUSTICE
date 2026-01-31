/**
 * Support Page - User-facing ticket submission
 * 
 * Allows users to:
 * - Submit support tickets
 * - View their ticket history
 * - Track ticket status
 */

import React, { useState, useEffect, useCallback } from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Label } from '../components/ui/label';
import { adminAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  HelpCircle, Send, Ticket, Clock, CheckCircle,
  MessageSquare, Calendar, ChevronRight, Loader2,
  AlertTriangle, Info
} from 'lucide-react';

// Priority colors
const priorityColors = {
  urgent: 'bg-red-500 text-white',
  high: 'bg-orange-500 text-white',
  medium: 'bg-yellow-500 text-black',
  low: 'bg-green-500 text-white'
};

// Status colors and labels
const statusConfig = {
  open: { color: 'bg-blue-500', label: 'Open', icon: Clock },
  in_progress: { color: 'bg-yellow-500', label: 'In Progress', icon: Loader2 },
  resolved: { color: 'bg-green-500', label: 'Resolved', icon: CheckCircle },
  closed: { color: 'bg-gray-500', label: 'Closed', icon: CheckCircle }
};

export default function SupportPage() {
  const [activeTab, setActiveTab] = useState('submit');
  
  // Ticket submission state
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('general');
  const [priority, setPriority] = useState('medium');
  const [submitting, setSubmitting] = useState(false);
  
  // Tickets list state
  const [tickets, setTickets] = useState([]);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [ticketDialogOpen, setTicketDialogOpen] = useState(false);

  // Load user's tickets
  const loadTickets = useCallback(async () => {
    try {
      setTicketsLoading(true);
      const response = await adminAPI.getMyTickets();
      setTickets(response.data.tickets || []);
    } catch (error) {
      console.error('Failed to load tickets:', error);
    } finally {
      setTicketsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'history') {
      loadTickets();
    }
  }, [activeTab, loadTickets]);

  // Submit new ticket
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!subject.trim() || !description.trim()) {
      toast.error('Please fill in all required fields');
      return;
    }
    
    try {
      setSubmitting(true);
      const response = await adminAPI.createTicket({
        subject: subject.trim(),
        description: description.trim(),
        category,
        priority
      });
      
      toast.success(`Ticket #${response.data.ticket_id} created successfully!`);
      
      // Reset form
      setSubject('');
      setDescription('');
      setCategory('general');
      setPriority('medium');
      
      // Switch to history tab
      setActiveTab('history');
      loadTickets();
    } catch (error) {
      toast.error('Failed to submit ticket. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  // View ticket details
  const viewTicket = async (ticketId) => {
    try {
      const response = await adminAPI.getTicket(ticketId);
      setSelectedTicket(response.data);
      setTicketDialogOpen(true);
    } catch (error) {
      toast.error('Failed to load ticket details');
    }
  };

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-6" data-testid="support-page">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center p-3 rounded-full bg-primary/10">
            <HelpCircle className="h-10 w-10 text-primary" />
          </div>
          <h1 className="text-3xl font-bold">Support Center</h1>
          <p className="text-muted-foreground">
            Need help? Submit a ticket and our team will respond within 24 hours.
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="submit" data-testid="tab-submit">
              <Send className="h-4 w-4 mr-2" />
              Submit Ticket
            </TabsTrigger>
            <TabsTrigger value="history" data-testid="tab-history">
              <Ticket className="h-4 w-4 mr-2" />
              My Tickets
            </TabsTrigger>
          </TabsList>

          {/* Submit Ticket Tab */}
          <TabsContent value="submit">
            <Card>
              <CardHeader>
                <CardTitle>New Support Request</CardTitle>
                <CardDescription>
                  Describe your issue in detail and we'll help you as soon as possible.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                  {/* Subject */}
                  <div className="space-y-2">
                    <Label htmlFor="subject">Subject *</Label>
                    <Input
                      id="subject"
                      placeholder="Brief summary of your issue"
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                      maxLength={100}
                      data-testid="ticket-subject"
                    />
                  </div>

                  {/* Category & Priority */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Category</Label>
                      <Select value={category} onValueChange={setCategory}>
                        <SelectTrigger data-testid="ticket-category">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="general">General Question</SelectItem>
                          <SelectItem value="technical">Technical Issue</SelectItem>
                          <SelectItem value="billing">Billing</SelectItem>
                          <SelectItem value="feature_request">Feature Request</SelectItem>
                          <SelectItem value="bug_report">Bug Report</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Priority</Label>
                      <Select value={priority} onValueChange={setPriority}>
                        <SelectTrigger data-testid="ticket-priority">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="low">Low - General inquiry</SelectItem>
                          <SelectItem value="medium">Medium - Need help soon</SelectItem>
                          <SelectItem value="high">High - Affecting my work</SelectItem>
                          <SelectItem value="urgent">Urgent - Critical issue</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {/* Description */}
                  <div className="space-y-2">
                    <Label htmlFor="description">Description *</Label>
                    <Textarea
                      id="description"
                      placeholder="Please describe your issue in detail. Include any error messages, steps to reproduce, and what you expected to happen."
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      className="min-h-[150px]"
                      data-testid="ticket-description"
                    />
                    <p className="text-xs text-muted-foreground text-right">
                      {description.length} / 2000 characters
                    </p>
                  </div>

                  {/* Tips */}
                  <Alert>
                    <Info className="h-4 w-4" />
                    <AlertDescription>
                      <strong>Tips for faster resolution:</strong>
                      <ul className="list-disc list-inside mt-1 text-sm">
                        <li>Include specific error messages if any</li>
                        <li>Mention what browser/device you're using</li>
                        <li>Describe steps to reproduce the issue</li>
                      </ul>
                    </AlertDescription>
                  </Alert>

                  {/* Submit Button */}
                  <Button
                    type="submit"
                    className="w-full"
                    disabled={submitting || !subject.trim() || !description.trim()}
                    data-testid="submit-ticket-btn"
                  >
                    {submitting ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <Send className="h-4 w-4 mr-2" />
                    )}
                    {submitting ? 'Submitting...' : 'Submit Ticket'}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tickets History Tab */}
          <TabsContent value="history">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>My Support Tickets</CardTitle>
                    <CardDescription>View and track your submitted tickets</CardDescription>
                  </div>
                  <Button variant="outline" size="sm" onClick={loadTickets} disabled={ticketsLoading}>
                    {ticketsLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      'Refresh'
                    )}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[400px]">
                  {tickets.length > 0 ? (
                    <div className="space-y-3">
                      {tickets.map((ticket) => {
                        const StatusIcon = statusConfig[ticket.status]?.icon || Clock;
                        return (
                          <div
                            key={ticket.ticket_id}
                            className="p-4 rounded-lg border hover:bg-muted/50 cursor-pointer transition-colors"
                            onClick={() => viewTicket(ticket.ticket_id)}
                            data-testid={`ticket-${ticket.ticket_id}`}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  <Badge className={priorityColors[ticket.priority]} variant="secondary">
                                    {ticket.priority}
                                  </Badge>
                                  <Badge variant="outline" className="flex items-center gap-1">
                                    <StatusIcon className={`h-3 w-3 ${ticket.status === 'in_progress' ? 'animate-spin' : ''}`} />
                                    {statusConfig[ticket.status]?.label || ticket.status}
                                  </Badge>
                                </div>
                                <p className="font-medium">{ticket.subject}</p>
                                <p className="text-sm text-muted-foreground line-clamp-1">{ticket.description}</p>
                                <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                                  <span className="flex items-center gap-1">
                                    <Calendar className="h-3 w-3" />
                                    {new Date(ticket.created_at).toLocaleDateString()}
                                  </span>
                                  {ticket.responses?.length > 0 && (
                                    <span className="flex items-center gap-1 text-blue-500">
                                      <MessageSquare className="h-3 w-3" />
                                      {ticket.responses.length} response(s)
                                    </span>
                                  )}
                                </div>
                              </div>
                              <ChevronRight className="h-5 w-5 text-muted-foreground flex-shrink-0" />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-12">
                      <Ticket className="h-12 w-12 text-muted-foreground mb-4" />
                      <p className="text-lg font-medium">No tickets yet</p>
                      <p className="text-muted-foreground">Submit a ticket to get help from our team</p>
                      <Button
                        variant="outline"
                        className="mt-4"
                        onClick={() => setActiveTab('submit')}
                      >
                        <Send className="h-4 w-4 mr-2" />
                        Submit Your First Ticket
                      </Button>
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Ticket Detail Dialog */}
        <Dialog open={ticketDialogOpen} onOpenChange={setTicketDialogOpen}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            {selectedTicket && (
              <>
                <DialogHeader>
                  <div className="flex items-center gap-2 mb-2">
                    <Badge className={priorityColors[selectedTicket.priority]}>
                      {selectedTicket.priority}
                    </Badge>
                    <Badge variant="outline">
                      {statusConfig[selectedTicket.status]?.label || selectedTicket.status}
                    </Badge>
                    <Badge variant="secondary">{selectedTicket.category}</Badge>
                  </div>
                  <DialogTitle>{selectedTicket.subject}</DialogTitle>
                  <p className="text-sm text-muted-foreground">
                    Ticket #{selectedTicket.ticket_id} • Created {new Date(selectedTicket.created_at).toLocaleString()}
                  </p>
                </DialogHeader>

                <div className="space-y-4 mt-4">
                  {/* Original Description */}
                  <div>
                    <h4 className="font-medium text-sm text-muted-foreground mb-2">Your Message</h4>
                    <p className="bg-muted p-3 rounded-lg whitespace-pre-wrap text-sm">
                      {selectedTicket.description}
                    </p>
                  </div>

                  {/* Responses */}
                  {selectedTicket.responses?.length > 0 && (
                    <div>
                      <h4 className="font-medium text-sm text-muted-foreground mb-2">
                        Responses ({selectedTicket.responses.length})
                      </h4>
                      <div className="space-y-3">
                        {selectedTicket.responses.map((response, i) => (
                          <div key={i} className="bg-blue-500/10 border border-blue-500/20 p-3 rounded-lg">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium text-sm text-blue-400">
                                {response.responder_name}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {new Date(response.created_at).toLocaleString()}
                              </span>
                            </div>
                            <p className="text-sm whitespace-pre-wrap">{response.text}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Resolution */}
                  {selectedTicket.resolution && (
                    <Alert className="bg-green-500/10 border-green-500/30">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <AlertDescription>
                        <strong>Resolution:</strong> {selectedTicket.resolution}
                      </AlertDescription>
                    </Alert>
                  )}

                  {/* Status-specific messages */}
                  {selectedTicket.status === 'open' && (
                    <Alert>
                      <Clock className="h-4 w-4" />
                      <AlertDescription>
                        Your ticket is in the queue. We typically respond within 24 hours.
                      </AlertDescription>
                    </Alert>
                  )}

                  {selectedTicket.status === 'in_progress' && (
                    <Alert className="bg-yellow-500/10 border-yellow-500/30">
                      <Loader2 className="h-4 w-4 text-yellow-500 animate-spin" />
                      <AlertDescription>
                        Our team is actively working on your request.
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              </>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  );
}
