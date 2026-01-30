import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Separator } from '../components/ui/separator';
import api from '../lib/api';
import { 
  Shield, CheckCircle, XCircle, Clock, AlertTriangle, 
  Trash2, Eye, MapPin, Calendar, MessageSquare, Users,
  BarChart3, RefreshCw, Loader2, Search, ChevronLeft, ChevronRight,
  ThumbsUp, ShieldCheck
} from 'lucide-react';
import { toast } from 'sonner';

export default function ModerationDashboardPage() {
  const [reports, setReports] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('pending');
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  // Dialog states
  const [rejectDialog, setRejectDialog] = useState({ open: false, reportId: null });
  const [rejectReason, setRejectReason] = useState('');
  const [viewDialog, setViewDialog] = useState({ open: false, report: null });
  const [processing, setProcessing] = useState(null);

  // Load reports
  const loadReports = useCallback(async () => {
    setLoading(true);
    try {
      const [reportsRes, statsRes] = await Promise.all([
        api.get('/community-map/admin/reports', {
          params: { status: activeTab, limit: pageSize, skip: page * pageSize }
        }),
        api.get('/community-map/admin/stats')
      ]);
      
      setReports(reportsRes.data.reports || []);
      setTotal(reportsRes.data.total || 0);
      setStats(statsRes.data.stats || null);
    } catch (err) {
      console.error('Error loading reports:', err);
      if (err.response?.status === 403) {
        toast.error('Access denied. Admin or moderator role required.');
      } else {
        toast.error('Failed to load reports');
      }
    } finally {
      setLoading(false);
    }
  }, [activeTab, page]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  // Actions
  const handleApprove = async (reportId) => {
    setProcessing(reportId);
    try {
      await api.put(`/community-map/admin/reports/${reportId}/approve`);
      toast.success('Report approved!');
      loadReports();
    } catch (err) {
      toast.error('Failed to approve report');
    } finally {
      setProcessing(null);
    }
  };

  const handleReject = async () => {
    if (!rejectReason || rejectReason.length < 5) {
      toast.error('Please provide a reason (at least 5 characters)');
      return;
    }
    
    setProcessing(rejectDialog.reportId);
    try {
      await api.put(`/community-map/admin/reports/${rejectDialog.reportId}/reject`, null, {
        params: { reason: rejectReason }
      });
      toast.success('Report rejected');
      setRejectDialog({ open: false, reportId: null });
      setRejectReason('');
      loadReports();
    } catch (err) {
      toast.error('Failed to reject report');
    } finally {
      setProcessing(null);
    }
  };

  const handleVerify = async (reportId) => {
    setProcessing(reportId);
    try {
      await api.put(`/community-map/admin/reports/${reportId}/verify`);
      toast.success('Report marked as verified!');
      loadReports();
    } catch (err) {
      toast.error('Failed to verify report');
    } finally {
      setProcessing(null);
    }
  };

  const handleDelete = async (reportId) => {
    if (!confirm('Permanently delete this report? This cannot be undone.')) return;
    
    setProcessing(reportId);
    try {
      await api.delete(`/community-map/admin/reports/${reportId}`);
      toast.success('Report deleted');
      loadReports();
    } catch (err) {
      if (err.response?.status === 403) {
        toast.error('Only admins can delete reports');
      } else {
        toast.error('Failed to delete report');
      }
    } finally {
      setProcessing(null);
    }
  };

  const getReportTypeLabel = (type) => {
    const labels = {
      safety_tip: 'Safety Tip',
      incident: 'Incident Report',
      concern: 'Area Concern',
      positive: 'Positive Interaction'
    };
    return labels[type] || type;
  };

  const getReportTypeBadge = (type) => {
    const styles = {
      safety_tip: 'bg-green-500/10 text-green-600 border-green-500/20',
      incident: 'bg-red-500/10 text-red-600 border-red-500/20',
      concern: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20',
      positive: 'bg-blue-500/10 text-blue-600 border-blue-500/20'
    };
    return styles[type] || '';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown';
    return new Date(dateStr).toLocaleString();
  };

  const filteredReports = reports.filter(r => 
    searchTerm === '' || 
    r.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    r.location?.address?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-background p-6" data-testid="moderation-dashboard">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Shield className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Report Moderation</h1>
            <p className="text-muted-foreground text-sm">Review and manage community reports</p>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <Card className="bg-yellow-500/10 border-yellow-500/20">
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-yellow-600" />
                <div>
                  <p className="text-2xl font-bold text-yellow-600">{stats.pending}</p>
                  <p className="text-xs text-muted-foreground">Pending</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-green-500/10 border-green-500/20">
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-600" />
                <div>
                  <p className="text-2xl font-bold text-green-600">{stats.approved}</p>
                  <p className="text-xs text-muted-foreground">Approved</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-red-500/10 border-red-500/20">
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <XCircle className="h-5 w-5 text-red-600" />
                <div>
                  <p className="text-2xl font-bold text-red-600">{stats.rejected}</p>
                  <p className="text-xs text-muted-foreground">Rejected</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-blue-500/10 border-blue-500/20">
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-blue-600" />
                <div>
                  <p className="text-2xl font-bold text-blue-600">{stats.verified}</p>
                  <p className="text-xs text-muted-foreground">Verified</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-purple-500/10 border-purple-500/20">
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-purple-600" />
                <div>
                  <p className="text-2xl font-bold text-purple-600">{stats.last_7_days}</p>
                  <p className="text-xs text-muted-foreground">Last 7 Days</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Community Reports
            </CardTitle>
            <Button variant="outline" size="sm" onClick={loadReports} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
          
          {/* Search */}
          <div className="relative mt-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search reports..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9"
            />
          </div>
        </CardHeader>
        
        <CardContent>
          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={(v) => { setActiveTab(v); setPage(0); }}>
            <TabsList className="mb-4">
              <TabsTrigger value="pending" className="gap-2">
                <Clock className="h-4 w-4" />
                Pending {stats?.pending > 0 && <Badge variant="secondary">{stats.pending}</Badge>}
              </TabsTrigger>
              <TabsTrigger value="approved" className="gap-2">
                <CheckCircle className="h-4 w-4" />
                Approved
              </TabsTrigger>
              <TabsTrigger value="rejected" className="gap-2">
                <XCircle className="h-4 w-4" />
                Rejected
              </TabsTrigger>
              <TabsTrigger value="all" className="gap-2">
                <Users className="h-4 w-4" />
                All
              </TabsTrigger>
            </TabsList>

            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : filteredReports.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No reports found</p>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredReports.map((report) => (
                  <div
                    key={report.report_id}
                    className="p-4 border rounded-lg hover:bg-muted/30 transition-colors"
                    data-testid={`report-${report.report_id}`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2 flex-wrap">
                          <Badge className={getReportTypeBadge(report.report_type)}>
                            {getReportTypeLabel(report.report_type)}
                          </Badge>
                          {report.verified && (
                            <Badge className="bg-blue-500 text-white">
                              <ShieldCheck className="h-3 w-3 mr-1" />
                              Verified
                            </Badge>
                          )}
                          {report.anonymous && (
                            <Badge variant="outline">Anonymous</Badge>
                          )}
                          {report.votes > 0 && (
                            <Badge variant="secondary">
                              <ThumbsUp className="h-3 w-3 mr-1" />
                              {report.votes}
                            </Badge>
                          )}
                        </div>
                        
                        <p className="text-sm mb-2 line-clamp-2">{report.description}</p>
                        
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          {report.location?.address && (
                            <span className="flex items-center gap-1">
                              <MapPin className="h-3 w-3" />
                              {report.location.address}
                            </span>
                          )}
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {formatDate(report.created_at)}
                          </span>
                        </div>
                      </div>
                      
                      {/* Actions */}
                      <div className="flex items-center gap-2 shrink-0">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setViewDialog({ open: true, report })}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        
                        {report.status === 'pending' && (
                          <>
                            <Button
                              variant="default"
                              size="sm"
                              className="bg-green-600 hover:bg-green-700"
                              onClick={() => handleApprove(report.report_id)}
                              disabled={processing === report.report_id}
                              data-testid={`approve-${report.report_id}`}
                            >
                              {processing === report.report_id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <CheckCircle className="h-4 w-4" />
                              )}
                            </Button>
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => setRejectDialog({ open: true, reportId: report.report_id })}
                              disabled={processing === report.report_id}
                              data-testid={`reject-${report.report_id}`}
                            >
                              <XCircle className="h-4 w-4" />
                            </Button>
                          </>
                        )}
                        
                        {report.status === 'approved' && !report.verified && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleVerify(report.report_id)}
                            disabled={processing === report.report_id}
                          >
                            <ShieldCheck className="h-4 w-4 mr-1" />
                            Verify
                          </Button>
                        )}
                        
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-500 hover:text-red-600 hover:bg-red-500/10"
                          onClick={() => handleDelete(report.report_id)}
                          disabled={processing === report.report_id}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Pagination */}
            {total > pageSize && (
              <div className="flex items-center justify-between mt-4 pt-4 border-t">
                <p className="text-sm text-muted-foreground">
                  Showing {page * pageSize + 1} - {Math.min((page + 1) * pageSize, total)} of {total}
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(p => Math.max(0, p - 1))}
                    disabled={page === 0}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(p => p + 1)}
                    disabled={(page + 1) * pageSize >= total}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </Tabs>
        </CardContent>
      </Card>

      {/* Reject Dialog */}
      <Dialog open={rejectDialog.open} onOpenChange={(open) => setRejectDialog({ open, reportId: open ? rejectDialog.reportId : null })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <XCircle className="h-5 w-5" />
              Reject Report
            </DialogTitle>
            <DialogDescription>
              Please provide a reason for rejecting this report.
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4">
            <Label>Rejection Reason *</Label>
            <Textarea
              placeholder="Enter the reason for rejection..."
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              rows={3}
              className="mt-2"
            />
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectDialog({ open: false, reportId: null })}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleReject} disabled={processing}>
              {processing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Reject Report
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Dialog */}
      <Dialog open={viewDialog.open} onOpenChange={(open) => setViewDialog({ open, report: open ? viewDialog.report : null })}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              Report Details
            </DialogTitle>
          </DialogHeader>
          
          {viewDialog.report && (
            <div className="space-y-4 py-4">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge className={getReportTypeBadge(viewDialog.report.report_type)}>
                  {getReportTypeLabel(viewDialog.report.report_type)}
                </Badge>
                <Badge variant="outline" className="capitalize">
                  {viewDialog.report.status}
                </Badge>
                {viewDialog.report.verified && (
                  <Badge className="bg-blue-500 text-white">Verified</Badge>
                )}
              </div>
              
              <Separator />
              
              <div>
                <Label className="text-xs text-muted-foreground">Description</Label>
                <p className="mt-1">{viewDialog.report.description}</p>
              </div>
              
              {viewDialog.report.location?.address && (
                <div>
                  <Label className="text-xs text-muted-foreground">Location</Label>
                  <p className="mt-1 flex items-center gap-1">
                    <MapPin className="h-4 w-4" />
                    {viewDialog.report.location.address}
                  </p>
                  {viewDialog.report.location.latitude && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Coordinates: {viewDialog.report.location.latitude}, {viewDialog.report.location.longitude}
                    </p>
                  )}
                </div>
              )}
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs text-muted-foreground">Created</Label>
                  <p className="mt-1 text-sm">{formatDate(viewDialog.report.created_at)}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Votes</Label>
                  <p className="mt-1 text-sm flex items-center gap-1">
                    <ThumbsUp className="h-4 w-4" />
                    {viewDialog.report.votes || 0}
                  </p>
                </div>
              </div>
              
              {!viewDialog.report.anonymous && viewDialog.report.contact_email && (
                <div>
                  <Label className="text-xs text-muted-foreground">Contact Email</Label>
                  <p className="mt-1 text-sm">{viewDialog.report.contact_email}</p>
                </div>
              )}
              
              {viewDialog.report.moderated_at && (
                <div className="pt-2 border-t">
                  <Label className="text-xs text-muted-foreground">Moderation</Label>
                  <p className="mt-1 text-sm">
                    {viewDialog.report.status === 'approved' ? 'Approved' : 'Rejected'} on {formatDate(viewDialog.report.moderated_at)}
                  </p>
                  {viewDialog.report.moderation_notes && (
                    <p className="mt-1 text-sm text-muted-foreground">{viewDialog.report.moderation_notes}</p>
                  )}
                </div>
              )}
            </div>
          )}
          
          <DialogFooter>
            <Button onClick={() => setViewDialog({ open: false, report: null })}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
