import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from '../ui/dialog';
import { attorneyCollabAPI } from '../../lib/api';
import { toast } from 'sonner';
import { 
  Scale, UserPlus, CheckCircle, XCircle, 
  Mail, Building, Shield, Trash2,
  Copy, ExternalLink, AlertTriangle
} from 'lucide-react';

export default function InviteAttorneyDialog({ encounterId, onInviteSent }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    email: '',
    message: ''
  });
  const [sending, setSending] = useState(false);
  const [inviteResult, setInviteResult] = useState(null);

  const handleSend = async () => {
    if (!form.email.trim()) {
      toast.error('Email is required');
      return;
    }
    
    // Basic email validation
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      toast.error('Please enter a valid email');
      return;
    }

    setSending(true);
    try {
      const res = await attorneyCollabAPI.inviteAttorney(
        form.email,
        encounterId,
        form.message
      );
      
      setInviteResult(res.data);
      toast.success('Invitation sent!');
      onInviteSent?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send invitation');
    } finally {
      setSending(false);
    }
  };

  const copyInviteLink = () => {
    if (inviteResult?.invite_url) {
      const fullUrl = `${window.location.origin}${inviteResult.invite_url}`;
      navigator.clipboard.writeText(fullUrl);
      toast.success('Link copied to clipboard!');
    }
  };

  const resetDialog = () => {
    setForm({ email: '', message: '' });
    setInviteResult(null);
  };

  const handleOpenChange = (newOpen) => {
    setOpen(newOpen);
    if (!newOpen) {
      resetDialog();
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" data-testid="invite-attorney-btn">
          <UserPlus className="h-4 w-4 mr-2" />
          Invite Attorney
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Scale className="h-5 w-5" />
            Invite Attorney to Collaborate
          </DialogTitle>
          <DialogDescription>
            Send an invitation to an attorney to review and collaborate on this encounter.
          </DialogDescription>
        </DialogHeader>

        {!inviteResult ? (
          <>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="attorney-email">Attorney's Email *</Label>
                <Input
                  id="attorney-email"
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="attorney@lawfirm.com"
                  data-testid="attorney-email-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="invite-message">Personal Message (Optional)</Label>
                <Textarea
                  id="invite-message"
                  value={form.message}
                  onChange={(e) => setForm({ ...form, message: e.target.value })}
                  placeholder="Add a personal message for the attorney..."
                  rows={3}
                  data-testid="invite-message-input"
                />
              </div>
              <div className="bg-muted p-3 rounded-lg text-sm">
                <p className="text-muted-foreground">
                  <Shield className="h-4 w-4 inline mr-1" />
                  The attorney will receive a secure link valid for 48 hours. 
                  They can view your encounter details, transcripts, and evidence highlights.
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleSend} disabled={sending} data-testid="send-invite-btn">
                {sending ? 'Sending...' : 'Send Invitation'}
              </Button>
            </DialogFooter>
          </>
        ) : (
          <div className="py-4 space-y-4">
            <div className="text-center">
              <div className="h-16 w-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="h-8 w-8 text-green-600" />
              </div>
              <h3 className="font-semibold text-lg">Invitation Sent!</h3>
              <p className="text-muted-foreground text-sm mt-2">
                An invitation has been sent to <strong>{inviteResult.email}</strong>
              </p>
            </div>

            <div className="bg-muted p-4 rounded-lg space-y-2">
              <p className="text-sm text-muted-foreground">
                Expires: {new Date(inviteResult.expires_at).toLocaleString()}
              </p>
              <div className="flex items-center gap-2">
                <Input 
                  value={`${window.location.origin}${inviteResult.invite_url}`}
                  readOnly
                  className="text-xs"
                />
                <Button variant="outline" size="icon" onClick={copyInviteLink}>
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <p className="text-xs text-muted-foreground text-center">
              You can also share this link directly with the attorney.
            </p>

            <DialogFooter>
              <Button onClick={() => setOpen(false)} className="w-full">
                Done
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// Component to show list of attorneys with access
export function MyAttorneysList({ onAccessRevoked }) {
  const [attorneys, setAttorneys] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAttorneys();
  }, []);

  const fetchAttorneys = async () => {
    try {
      const res = await attorneyCollabAPI.getMyAttorneys();
      setAttorneys(res.data.attorneys || []);
    } catch (error) {
      console.error('Error fetching attorneys:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeAccess = async (encounterId) => {
    if (!window.confirm('Revoke attorney access to this encounter? This cannot be undone.')) {
      return;
    }

    try {
      await attorneyCollabAPI.revokeAccess(encounterId);
      toast.success('Access revoked');
      fetchAttorneys();
      onAccessRevoked?.();
    } catch (error) {
      toast.error('Failed to revoke access');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (attorneys.length === 0) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <Scale className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="font-semibold">No Attorneys Yet</h3>
          <p className="text-muted-foreground text-sm mt-2">
            You haven't invited any attorneys to collaborate on your encounters.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {attorneys.map((attorney, index) => (
        <Card key={attorney.attorney_id} data-testid={`attorney-card-${index}`}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                  <Scale className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="font-semibold">{attorney.name || 'Attorney'}</h4>
                    {attorney.verified && (
                      <Badge variant="secondary" className="text-green-600 bg-green-100">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Verified
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">{attorney.email}</p>
                  {attorney.firm_name && (
                    <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                      <Building className="h-3 w-3" />
                      {attorney.firm_name}
                    </p>
                  )}
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium">{attorney.encounter_count} encounter(s)</p>
                {attorney.encounters?.length > 0 && (
                  <div className="mt-2 space-x-1">
                    {attorney.encounters.map((encId) => (
                      <Button
                        key={encId}
                        variant="ghost"
                        size="sm"
                        className="text-xs text-red-500 hover:text-red-700"
                        onClick={() => handleRevokeAccess(encId)}
                        data-testid={`revoke-${encId}`}
                      >
                        <XCircle className="h-3 w-3 mr-1" />
                        Revoke
                      </Button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
