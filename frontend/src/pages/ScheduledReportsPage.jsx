import React, { useState, useEffect } from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { schedulesAPI } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import {
  Calendar, Clock, Mail, Plus, Trash2, Edit2,
  Play, Pause, Send, RefreshCw, Loader2,
  CheckCircle, XCircle, AlertCircle, CalendarDays
} from 'lucide-react';

const DAYS_OF_WEEK = [
  { value: 0, label: 'Monday' },
  { value: 1, label: 'Tuesday' },
  { value: 2, label: 'Wednesday' },
  { value: 3, label: 'Thursday' },
  { value: 4, label: 'Friday' },
  { value: 5, label: 'Saturday' },
  { value: 6, label: 'Sunday' },
];

const HOURS = Array.from({ length: 24 }, (_, i) => ({
  value: i,
  label: `${i.toString().padStart(2, '0')}:00 UTC`
}));

const DATES_OF_MONTH = Array.from({ length: 28 }, (_, i) => ({
  value: i + 1,
  label: `${i + 1}${getOrdinalSuffix(i + 1)}`
}));

function getOrdinalSuffix(n) {
  const s = ['th', 'st', 'nd', 'rd'];
  const v = n % 100;
  return s[(v - 20) % 10] || s[v] || s[0];
}

export default function ScheduledReportsPage() {
  const { user } = useAuth();
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState(null);
  const [saving, setSaving] = useState(false);
  const [testingId, setTestingId] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    report_name: '',
    frequency: 'weekly',
    send_hour: 9,
    send_day: 0,
    send_date: 1,
    recipient_emails: ''
  });

  useEffect(() => {
    fetchSchedules();
  }, []);

  const fetchSchedules = async () => {
    try {
      const res = await schedulesAPI.getMySchedules();
      setSchedules(res.data.schedules || []);
    } catch (error) {
      console.error('Error fetching schedules:', error);
      toast.error('Failed to load schedules');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      report_name: '',
      frequency: 'weekly',
      send_hour: 9,
      send_day: 0,
      send_date: 1,
      recipient_emails: ''
    });
    setEditingSchedule(null);
  };

  const openCreateDialog = () => {
    resetForm();
    setShowCreateDialog(true);
  };

  const openEditDialog = (schedule) => {
    setFormData({
      report_name: schedule.report_name || '',
      frequency: schedule.frequency,
      send_hour: schedule.send_hour,
      send_day: schedule.send_day || 0,
      send_date: schedule.send_date || 1,
      recipient_emails: (schedule.recipient_emails || []).join('\n')
    });
    setEditingSchedule(schedule);
    setShowCreateDialog(true);
  };

  const closeDialog = () => {
    setShowCreateDialog(false);
    resetForm();
  };

  const handleSave = async () => {
    // Parse emails
    const emails = formData.recipient_emails
      .split(/[,\n]/)
      .map(e => e.trim())
      .filter(e => e.length > 0 && e.includes('@'));
    
    if (emails.length === 0) {
      toast.error('Please enter at least one valid email address');
      return;
    }
    
    if (emails.length > 10) {
      toast.error('Maximum 10 recipients allowed');
      return;
    }
    
    const data = {
      report_name: formData.report_name || null,
      frequency: formData.frequency,
      send_hour: parseInt(formData.send_hour),
      send_day: formData.frequency === 'weekly' ? parseInt(formData.send_day) : null,
      send_date: formData.frequency === 'monthly' ? parseInt(formData.send_date) : null,
      recipient_emails: emails
    };
    
    setSaving(true);
    try {
      if (editingSchedule) {
        await schedulesAPI.updateSchedule(editingSchedule.schedule_id, data);
        toast.success('Schedule updated!');
      } else {
        await schedulesAPI.createSchedule(data);
        toast.success('Schedule created!');
      }
      closeDialog();
      fetchSchedules();
    } catch (error) {
      console.error('Save error:', error);
      toast.error(error.response?.data?.detail || 'Failed to save schedule');
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (scheduleId) => {
    try {
      const res = await schedulesAPI.toggleSchedule(scheduleId);
      toast.success(`Schedule ${res.data.is_active ? 'activated' : 'paused'}`);
      fetchSchedules();
    } catch (error) {
      toast.error('Failed to toggle schedule');
    }
  };

  const handleDelete = async (scheduleId) => {
    if (!confirm('Are you sure you want to delete this schedule?')) return;
    
    try {
      await schedulesAPI.deleteSchedule(scheduleId);
      toast.success('Schedule deleted');
      fetchSchedules();
    } catch (error) {
      toast.error('Failed to delete schedule');
    }
  };

  const handleTest = async (scheduleId) => {
    setTestingId(scheduleId);
    try {
      toast.info('Sending test email...');
      const res = await schedulesAPI.testSchedule(scheduleId);
      toast.success(`Test email sent to ${res.data.recipients?.length || 0} recipient(s) with ${res.data.recording_count} recording(s)`);
    } catch (error) {
      console.error('Test error:', error);
      toast.error(error.response?.data?.detail || 'Failed to send test email');
    } finally {
      setTestingId(null);
    }
  };

  const getFrequencyLabel = (schedule) => {
    if (schedule.frequency === 'daily') {
      return `Daily at ${schedule.send_hour.toString().padStart(2, '0')}:00 UTC`;
    } else if (schedule.frequency === 'weekly') {
      const day = DAYS_OF_WEEK.find(d => d.value === schedule.send_day)?.label || 'Monday';
      return `Every ${day} at ${schedule.send_hour.toString().padStart(2, '0')}:00 UTC`;
    } else {
      return `Monthly on the ${schedule.send_date}${getOrdinalSuffix(schedule.send_date)} at ${schedule.send_hour.toString().padStart(2, '0')}:00 UTC`;
    }
  };

  const getStatusBadge = (schedule) => {
    if (!schedule.is_active) {
      return <Badge variant="secondary" className="bg-gray-100 text-gray-600"><Pause className="h-3 w-3 mr-1" />Paused</Badge>;
    }
    if (schedule.last_result === 'success') {
      return <Badge className="bg-green-100 text-green-700"><CheckCircle className="h-3 w-3 mr-1" />Active</Badge>;
    }
    if (schedule.last_result?.startsWith('failed')) {
      return <Badge className="bg-red-100 text-red-700"><XCircle className="h-3 w-3 mr-1" />Error</Badge>;
    }
    return <Badge className="bg-blue-100 text-blue-700"><Clock className="h-3 w-3 mr-1" />Pending</Badge>;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="scheduled-reports-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-serif text-3xl font-bold">Scheduled Reports</h1>
            <p className="text-muted-foreground mt-1">
              Automate your consultation summary reports
            </p>
          </div>
          <Button onClick={openCreateDialog} data-testid="create-schedule-btn">
            <Plus className="h-4 w-4 mr-2" />
            Create Schedule
          </Button>
        </div>

        {/* Info Card */}
        <Card className="bg-gradient-to-r from-purple-50 to-blue-50 border-purple-200">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <CalendarDays className="h-5 w-5 text-purple-600 mt-0.5" />
              <div>
                <p className="font-medium text-purple-900">How Scheduled Reports Work</p>
                <p className="text-sm text-purple-700 mt-1">
                  Set up automated email reports that summarize your call consultations. 
                  Reports are generated with AI summaries and sent as PDF attachments to your chosen recipients.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Schedules List */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : schedules.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Calendar className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
              <h3 className="font-medium text-lg mb-2">No Scheduled Reports</h3>
              <p className="text-muted-foreground mb-4">
                Create your first scheduled report to automate summary delivery.
              </p>
              <Button onClick={openCreateDialog}>
                <Plus className="h-4 w-4 mr-2" />
                Create Schedule
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {schedules.map((schedule) => (
              <Card key={schedule.schedule_id} data-testid={`schedule-card-${schedule.schedule_id}`}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="font-semibold text-lg">{schedule.report_name}</h3>
                        {getStatusBadge(schedule)}
                      </div>
                      
                      <div className="space-y-1 text-sm text-muted-foreground">
                        <div className="flex items-center gap-2">
                          <Clock className="h-4 w-4" />
                          <span>{getFrequencyLabel(schedule)}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Mail className="h-4 w-4" />
                          <span>{schedule.recipient_emails?.join(', ')}</span>
                        </div>
                        {schedule.last_sent && (
                          <div className="flex items-center gap-2 mt-2">
                            <RefreshCw className="h-4 w-4" />
                            <span>Last sent: {formatDate(schedule.last_sent)}</span>
                            {schedule.last_recording_count > 0 && (
                              <Badge variant="outline" className="text-xs">
                                {schedule.last_recording_count} recordings
                              </Badge>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={schedule.is_active}
                        onCheckedChange={() => handleToggle(schedule.schedule_id)}
                        data-testid={`toggle-schedule-${schedule.schedule_id}`}
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleTest(schedule.schedule_id)}
                        disabled={testingId === schedule.schedule_id}
                        data-testid={`test-schedule-${schedule.schedule_id}`}
                      >
                        {testingId === schedule.schedule_id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Send className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openEditDialog(schedule)}
                        data-testid={`edit-schedule-${schedule.schedule_id}`}
                      >
                        <Edit2 className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDelete(schedule.schedule_id)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        data-testid={`delete-schedule-${schedule.schedule_id}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Create/Edit Dialog */}
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogContent className="max-w-md" data-testid="schedule-dialog">
            <DialogHeader>
              <DialogTitle>
                {editingSchedule ? 'Edit Schedule' : 'Create Scheduled Report'}
              </DialogTitle>
              <DialogDescription>
                Configure when and where to send your automated summary reports.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="report_name">Report Name</Label>
                <Input
                  id="report_name"
                  placeholder="e.g., Weekly Client Summary"
                  value={formData.report_name}
                  onChange={(e) => setFormData({ ...formData, report_name: e.target.value })}
                  data-testid="schedule-name-input"
                />
              </div>
              
              <div className="space-y-2">
                <Label>Frequency</Label>
                <Select
                  value={formData.frequency}
                  onValueChange={(v) => setFormData({ ...formData, frequency: v })}
                >
                  <SelectTrigger data-testid="schedule-frequency-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="daily">Daily</SelectItem>
                    <SelectItem value="weekly">Weekly</SelectItem>
                    <SelectItem value="monthly">Monthly</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              {formData.frequency === 'weekly' && (
                <div className="space-y-2">
                  <Label>Day of Week</Label>
                  <Select
                    value={formData.send_day.toString()}
                    onValueChange={(v) => setFormData({ ...formData, send_day: parseInt(v) })}
                  >
                    <SelectTrigger data-testid="schedule-day-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {DAYS_OF_WEEK.map((day) => (
                        <SelectItem key={day.value} value={day.value.toString()}>
                          {day.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
              
              {formData.frequency === 'monthly' && (
                <div className="space-y-2">
                  <Label>Day of Month</Label>
                  <Select
                    value={formData.send_date.toString()}
                    onValueChange={(v) => setFormData({ ...formData, send_date: parseInt(v) })}
                  >
                    <SelectTrigger data-testid="schedule-date-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {DATES_OF_MONTH.map((date) => (
                        <SelectItem key={date.value} value={date.value.toString()}>
                          {date.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
              
              <div className="space-y-2">
                <Label>Time (UTC)</Label>
                <Select
                  value={formData.send_hour.toString()}
                  onValueChange={(v) => setFormData({ ...formData, send_hour: parseInt(v) })}
                >
                  <SelectTrigger data-testid="schedule-hour-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {HOURS.map((hour) => (
                      <SelectItem key={hour.value} value={hour.value.toString()}>
                        {hour.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="recipients">Recipient Emails *</Label>
                <Textarea
                  id="recipients"
                  placeholder="Enter email addresses (one per line or comma-separated)"
                  value={formData.recipient_emails}
                  onChange={(e) => setFormData({ ...formData, recipient_emails: e.target.value })}
                  className="min-h-[80px]"
                  data-testid="schedule-recipients-input"
                />
                <p className="text-xs text-muted-foreground">Maximum 10 recipients</p>
              </div>
            </div>
            
            <DialogFooter>
              <Button variant="outline" onClick={closeDialog} disabled={saving}>
                Cancel
              </Button>
              <Button onClick={handleSave} disabled={saving} data-testid="save-schedule-btn">
                {saving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  editingSchedule ? 'Update Schedule' : 'Create Schedule'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  );
}
