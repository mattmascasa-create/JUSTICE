import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { attorneyCollabAPI } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import { Shield, Scale, Clock, UserPlus, LogIn, AlertTriangle } from 'lucide-react';

export default function AttorneyAcceptInvitePage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setToken, setUser } = useAuth();
  
  const token = searchParams.get('token');
  
  const [inviteDetails, setInviteDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  
  // New user registration form
  const [newUserForm, setNewUserForm] = useState({
    name: '',
    password: '',
    confirmPassword: ''
  });
  
  // Existing user login form
  const [existingUserForm, setExistingUserForm] = useState({
    email: '',
    password: ''
  });

  useEffect(() => {
    if (token) {
      fetchInviteDetails();
    } else {
      setError('No invitation token provided');
      setLoading(false);
    }
  }, [token]);

  const fetchInviteDetails = async () => {
    try {
      const res = await attorneyCollabAPI.getInviteDetails(token);
      setInviteDetails(res.data);
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Invalid or expired invitation';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleNewUserAccept = async (e) => {
    e.preventDefault();
    
    if (!newUserForm.name.trim()) {
      toast.error('Name is required');
      return;
    }
    
    if (newUserForm.password.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }
    
    if (newUserForm.password !== newUserForm.confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    
    setSubmitting(true);
    try {
      const res = await attorneyCollabAPI.acceptInvite(
        token,
        newUserForm.name,
        newUserForm.password
      );
      
      // Store token and redirect
      if (res.data.access_token) {
        localStorage.setItem('justice-token', res.data.access_token);
        setToken(res.data.access_token);
        toast.success('Invitation accepted! Welcome to JUSTICE.');
        navigate('/attorney-dashboard');
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to accept invitation');
    } finally {
      setSubmitting(false);
    }
  };

  const handleExistingUserAccept = async (e) => {
    e.preventDefault();
    
    if (!existingUserForm.email || !existingUserForm.password) {
      toast.error('Email and password required');
      return;
    }
    
    setSubmitting(true);
    try {
      const res = await attorneyCollabAPI.acceptInviteExisting(
        token,
        existingUserForm.email,
        existingUserForm.password
      );
      
      // Store token and redirect
      if (res.data.access_token) {
        localStorage.setItem('justice-token', res.data.access_token);
        setToken(res.data.access_token);
        toast.success('Access granted! Welcome back.');
        navigate('/attorney-dashboard');
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to accept invitation');
    } finally {
      setSubmitting(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading invitation details...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="p-8 text-center">
            <AlertTriangle className="h-16 w-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-2xl font-bold mb-2">Invalid Invitation</h2>
            <p className="text-muted-foreground mb-6">{error}</p>
            <Link to="/">
              <Button>Return to Home</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <Shield className="h-10 w-10 text-blue-500" />
          <span className="font-serif text-3xl font-bold">JUSTICE</span>
        </div>

        <Card data-testid="accept-invite-card">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 h-16 w-16 rounded-full bg-blue-100 flex items-center justify-center">
              <Scale className="h-8 w-8 text-blue-600" />
            </div>
            <CardTitle className="text-2xl">Attorney Invitation</CardTitle>
            <CardDescription>
              {inviteDetails?.client_name 
                ? `${inviteDetails.client_name} has invited you to collaborate on their encounter.`
                : 'You have been invited to collaborate as an attorney.'}
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Invitation Message */}
            {inviteDetails?.message && (
              <div className="bg-muted p-4 rounded-lg">
                <p className="text-sm font-medium mb-1">Message from client:</p>
                <p className="text-muted-foreground italic">"{inviteDetails.message}"</p>
              </div>
            )}

            {/* Expiration Notice */}
            <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span>
                Expires: {new Date(inviteDetails?.expires_at).toLocaleString()}
              </span>
            </div>

            {/* Tabs for New / Existing User */}
            <Tabs defaultValue="new" className="mt-6">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="new" data-testid="tab-new-user">
                  <UserPlus className="h-4 w-4 mr-2" />
                  New User
                </TabsTrigger>
                <TabsTrigger value="existing" data-testid="tab-existing-user">
                  <LogIn className="h-4 w-4 mr-2" />
                  I Have an Account
                </TabsTrigger>
              </TabsList>

              {/* New User Registration */}
              <TabsContent value="new">
                <form onSubmit={handleNewUserAccept} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="new-name">Full Name *</Label>
                    <Input
                      id="new-name"
                      value={newUserForm.name}
                      onChange={(e) => setNewUserForm({ ...newUserForm, name: e.target.value })}
                      placeholder="Your full name"
                      data-testid="new-user-name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="new-password">Password *</Label>
                    <Input
                      id="new-password"
                      type="password"
                      value={newUserForm.password}
                      onChange={(e) => setNewUserForm({ ...newUserForm, password: e.target.value })}
                      placeholder="Create a password"
                      data-testid="new-user-password"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="new-confirm">Confirm Password *</Label>
                    <Input
                      id="new-confirm"
                      type="password"
                      value={newUserForm.confirmPassword}
                      onChange={(e) => setNewUserForm({ ...newUserForm, confirmPassword: e.target.value })}
                      placeholder="Confirm password"
                      data-testid="new-user-confirm"
                    />
                  </div>
                  <Button 
                    type="submit" 
                    className="w-full" 
                    disabled={submitting}
                    data-testid="accept-new-btn"
                  >
                    {submitting ? 'Creating Account...' : 'Create Account & Accept'}
                  </Button>
                </form>
              </TabsContent>

              {/* Existing User Login */}
              <TabsContent value="existing">
                <form onSubmit={handleExistingUserAccept} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="existing-email">Email *</Label>
                    <Input
                      id="existing-email"
                      type="email"
                      value={existingUserForm.email}
                      onChange={(e) => setExistingUserForm({ ...existingUserForm, email: e.target.value })}
                      placeholder="Your email address"
                      data-testid="existing-user-email"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="existing-password">Password *</Label>
                    <Input
                      id="existing-password"
                      type="password"
                      value={existingUserForm.password}
                      onChange={(e) => setExistingUserForm({ ...existingUserForm, password: e.target.value })}
                      placeholder="Your password"
                      data-testid="existing-user-password"
                    />
                  </div>
                  <Button 
                    type="submit" 
                    className="w-full" 
                    disabled={submitting}
                    data-testid="accept-existing-btn"
                  >
                    {submitting ? 'Logging In...' : 'Login & Accept Invitation'}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>

            {/* Legal Notice */}
            <p className="text-xs text-muted-foreground text-center mt-6">
              By accepting this invitation, you agree to maintain client confidentiality 
              and comply with all applicable legal and ethical standards.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
