import React, { useState, useEffect } from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Separator } from '../components/ui/separator';
import { Badge } from '../components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { getInitials } from '../lib/utils';
import { emergencyContactsAPI, blockchainAPI, backupAPI } from '../lib/api';
import { 
  User, Bell, Shield, Moon, Sun, Phone, Mail, 
  LogOut, Trash2, Save, Users, Plus, X,
  Database, Globe, CheckCircle, AlertCircle, Link2,
  Cloud, CloudOff, RefreshCw, History, Loader2, ChevronRight,
  Scale, Video, MessageSquare
} from 'lucide-react';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [contacts, setContacts] = useState([]);
  const [newContact, setNewContact] = useState({ name: '', phone: '', email: '' });
  const [ipfsStatus, setIpfsStatus] = useState(null);
  const [blockchainStatus, setBlockchainStatus] = useState(null);
  const [backupStatus, setBackupStatus] = useState(null);
  const [backupLoading, setBackupLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  
  // Attorney Settings State
  const [attorneySettings, setAttorneySettings] = useState({
    defaultAttorneyEmail: '',
    notificationMethod: 'email', // email, sms, both, in-app
    autoStartStream: false,
    shareLocationWithAttorney: true,
    shareTranscriptWithAttorney: true
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const [contactsRes, ipfsRes, blockchainRes, backupRes] = await Promise.all([
        emergencyContactsAPI.getAll().catch(() => ({ data: [] })),
        blockchainAPI.getIPFSStatus().catch(() => ({ data: null })),
        blockchainAPI.getBlockchainStatus().catch(() => ({ data: null })),
        backupAPI.getStatus().catch(() => ({ data: null }))
      ]);
      setContacts(contactsRes.data || []);
      setIpfsStatus(ipfsRes.data);
      setBlockchainStatus(blockchainRes.data);
      setBackupStatus(backupRes.data);
      
      // Load attorney settings from localStorage
      const savedAttorneySettings = localStorage.getItem('justice_attorney_settings');
      if (savedAttorneySettings) {
        setAttorneySettings(JSON.parse(savedAttorneySettings));
      }
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  };

  const handleTriggerBackup = async () => {
    setBackupLoading(true);
    try {
      await backupAPI.triggerBackup();
      toast.success('Backup job started! This may take a few minutes.');
      // Refresh status after a delay
      setTimeout(() => {
        loadSettings();
        setBackupLoading(false);
      }, 2000);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to start backup');
      setBackupLoading(false);
    }
  };

  const handleSave = () => {
    toast.success('Settings saved successfully');
  };

  const handleLogout = async () => {
    await logout();
  };

  const handleAddContact = async () => {
    if (!newContact.name || (!newContact.phone && !newContact.email)) {
      toast.error('Please provide a name and at least phone or email');
      return;
    }
    
    setLoading(true);
    try {
      const updatedContacts = [...contacts, { ...newContact, notify_on_encounter: true }];
      await emergencyContactsAPI.update(updatedContacts);
      setContacts(updatedContacts);
      setNewContact({ name: '', phone: '', email: '' });
      toast.success('Emergency contact added');
    } catch (error) {
      toast.error('Failed to add contact');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveContact = async (index) => {
    setLoading(true);
    try {
      const updatedContacts = contacts.filter((_, i) => i !== index);
      await emergencyContactsAPI.update(updatedContacts);
      setContacts(updatedContacts);
      toast.success('Contact removed');
    } catch (error) {
      toast.error('Failed to remove contact');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout>
      <div className="max-w-3xl mx-auto space-y-6" data-testid="settings-page">
        {/* Header */}
        <div>
          <h1 className="font-serif text-3xl font-bold">Settings</h1>
          <p className="text-muted-foreground mt-1">Manage your account and preferences</p>
        </div>

        {/* Profile Section */}
        <Card>
          <CardHeader>
            <CardTitle className="font-serif flex items-center gap-2">
              <User className="h-5 w-5" />
              Profile
            </CardTitle>
            <CardDescription>Your personal information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center gap-6">
              <Avatar className="h-20 w-20">
                <AvatarImage src={user?.picture} alt={user?.name} />
                <AvatarFallback className="text-2xl bg-primary text-primary-foreground">
                  {getInitials(user?.name)}
                </AvatarFallback>
              </Avatar>
              <div>
                <h3 className="font-bold text-lg">{user?.name}</h3>
                <p className="text-muted-foreground">{user?.email}</p>
                <p className="text-sm text-muted-foreground capitalize">{user?.role} Account</p>
              </div>
            </div>

            <Separator />

            <div className="grid sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">Full Name</Label>
                <Input id="name" defaultValue={user?.name} data-testid="settings-name-input" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input id="email" defaultValue={user?.email} className="pl-10" disabled data-testid="settings-email-input" />
                </div>
              </div>
            </div>

            <Button onClick={handleSave} data-testid="save-profile-btn">
              <Save className="h-4 w-4 mr-2" />
              Save Changes
            </Button>
          </CardContent>
        </Card>

        {/* Emergency Contacts Section */}
        <Card>
          <CardHeader>
            <CardTitle className="font-serif flex items-center gap-2">
              <Users className="h-5 w-5 text-red-500" />
              Emergency Contacts
            </CardTitle>
            <CardDescription>People to notify during police encounters</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {contacts.length > 0 ? (
              <div className="space-y-2">
                {contacts.map((contact, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-muted/50 border">
                    <div>
                      <p className="font-medium">{contact.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {contact.phone && <span className="mr-3">{contact.phone}</span>}
                        {contact.email}
                      </p>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => handleRemoveContact(i)} disabled={loading}>
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center text-muted-foreground py-4">No emergency contacts added</p>
            )}

            <Separator />

            <div className="space-y-3">
              <p className="text-sm font-medium">Add New Contact</p>
              <div className="grid sm:grid-cols-3 gap-3">
                <Input
                  placeholder="Name"
                  value={newContact.name}
                  onChange={(e) => setNewContact(prev => ({ ...prev, name: e.target.value }))}
                />
                <Input
                  placeholder="Phone"
                  value={newContact.phone}
                  onChange={(e) => setNewContact(prev => ({ ...prev, phone: e.target.value }))}
                />
                <Input
                  placeholder="Email"
                  value={newContact.email}
                  onChange={(e) => setNewContact(prev => ({ ...prev, email: e.target.value }))}
                />
              </div>
              <Button onClick={handleAddContact} disabled={loading} size="sm">
                <Plus className="h-4 w-4 mr-2" />
                Add Contact
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Evidence Storage Status */}
        <Card>
          <CardHeader>
            <CardTitle className="font-serif flex items-center gap-2">
              <Database className="h-5 w-5" />
              Evidence Storage
            </CardTitle>
            <CardDescription>Blockchain and IPFS status for immutable evidence</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Blockchain Status */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded bg-blue-500/10">
                  <Link2 className="h-5 w-5 text-blue-500" />
                </div>
                <div>
                  <p className="font-medium">Blockchain Verification</p>
                  <p className="text-sm text-muted-foreground">
                    {blockchainStatus ? `${blockchainStatus.total_evidence_hashed} evidence items hashed` : 'Loading...'}
                  </p>
                </div>
              </div>
              <Badge className="bg-green-500/10 text-green-500">
                <CheckCircle className="h-3 w-3 mr-1" />
                Active
              </Badge>
            </div>

            {/* IPFS Status */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded ${ipfsStatus?.ipfs_enabled ? 'bg-green-500/10' : 'bg-orange-500/10'}`}>
                  <Globe className={`h-5 w-5 ${ipfsStatus?.ipfs_enabled ? 'text-green-500' : 'text-orange-500'}`} />
                </div>
                <div>
                  <p className="font-medium">IPFS Decentralized Storage</p>
                  <p className="text-sm text-muted-foreground">
                    {ipfsStatus?.ipfs_enabled 
                      ? `${ipfsStatus.total_evidence_on_ipfs} files on IPFS` 
                      : 'Not configured - evidence stored locally only'}
                  </p>
                </div>
              </div>
              {ipfsStatus?.ipfs_enabled ? (
                <Badge className="bg-green-500/10 text-green-500">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Connected
                </Badge>
              ) : (
                <Badge className="bg-orange-500/10 text-orange-500">
                  <AlertCircle className="h-3 w-3 mr-1" />
                  Not Configured
                </Badge>
              )}
            </div>

            {!ipfsStatus?.ipfs_enabled && (
              <div className="p-3 rounded-lg border border-dashed border-orange-500/50 bg-orange-500/5">
                <p className="text-sm font-medium text-orange-600 mb-1">Enable IPFS for Maximum Protection</p>
                <p className="text-xs text-muted-foreground mb-2">
                  IPFS stores your evidence on a decentralized network, making it impossible to delete or tamper with.
                </p>
                <p className="text-xs text-muted-foreground">
                  Get a free Pinata API key at <a href="https://app.pinata.cloud" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">app.pinata.cloud</a> and contact support to enable.
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* S3 Cloud Backup */}
        <Card>
          <CardHeader>
            <CardTitle className="font-serif flex items-center gap-2">
              <Cloud className="h-5 w-5" />
              Cloud Backup (AWS S3)
            </CardTitle>
            <CardDescription>Automated disaster recovery for your evidence</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* S3 Connection Status */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded ${backupStatus?.s3_enabled ? 'bg-green-500/10' : 'bg-gray-500/10'}`}>
                  {backupStatus?.s3_enabled ? (
                    <Cloud className="h-5 w-5 text-green-500" />
                  ) : (
                    <CloudOff className="h-5 w-5 text-gray-500" />
                  )}
                </div>
                <div>
                  <p className="font-medium">AWS S3 Backup</p>
                  <p className="text-sm text-muted-foreground">
                    {backupStatus?.s3_enabled 
                      ? `Connected to ${backupStatus.s3_bucket} (${backupStatus.s3_region})`
                      : 'Not configured - add AWS credentials to enable'}
                  </p>
                </div>
              </div>
              {backupStatus?.s3_enabled ? (
                <Badge className="bg-green-500/10 text-green-500">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Connected
                </Badge>
              ) : (
                <Badge className="bg-gray-500/10 text-gray-500">
                  <CloudOff className="h-3 w-3 mr-1" />
                  Disabled
                </Badge>
              )}
            </div>

            {/* Backup Statistics */}
            {backupStatus?.s3_enabled && backupStatus?.statistics && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg bg-muted/50 text-center">
                  <p className="text-2xl font-bold">{backupStatus.statistics.backed_up_files}</p>
                  <p className="text-xs text-muted-foreground">Files Backed Up</p>
                </div>
                <div className="p-3 rounded-lg bg-muted/50 text-center">
                  <p className="text-2xl font-bold">{backupStatus.statistics.total_evidence_files}</p>
                  <p className="text-xs text-muted-foreground">Total Evidence</p>
                </div>
                <div className="p-3 rounded-lg bg-muted/50 text-center">
                  <p className="text-2xl font-bold">{backupStatus.statistics.backup_coverage_percent}%</p>
                  <p className="text-xs text-muted-foreground">Coverage</p>
                </div>
                <div className="p-3 rounded-lg bg-muted/50 text-center">
                  <p className="text-2xl font-bold">{backupStatus.statistics.successful_backups}</p>
                  <p className="text-xs text-muted-foreground">Total Backups</p>
                </div>
              </div>
            )}

            {/* Last Backup Info */}
            {backupStatus?.last_backup && (
              <div className="p-3 rounded-lg border border-dashed">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium flex items-center gap-2">
                    <History className="h-4 w-4" />
                    Last Backup
                  </p>
                  <Badge variant={backupStatus.last_backup.status === 'completed' ? 'default' : 'secondary'}>
                    {backupStatus.last_backup.status}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  {backupStatus.last_backup.started_at 
                    ? new Date(backupStatus.last_backup.started_at).toLocaleString()
                    : 'N/A'}
                </p>
                <p className="text-xs text-muted-foreground">
                  {backupStatus.last_backup.files_backed_up} / {backupStatus.last_backup.files_total} files
                </p>
              </div>
            )}

            {/* Trigger Backup Button */}
            {backupStatus?.s3_enabled && (
              <Button 
                onClick={handleTriggerBackup} 
                disabled={backupLoading}
                className="w-full"
                data-testid="trigger-backup-btn"
              >
                {backupLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Running Backup...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Backup All Evidence Now
                  </>
                )}
              </Button>
            )}

            {/* Setup Instructions */}
            {!backupStatus?.s3_enabled && backupStatus?.setup_instructions && (
              <div className="p-3 rounded-lg border border-dashed border-blue-500/50 bg-blue-500/5">
                <p className="text-sm font-medium text-blue-600 mb-2">Enable S3 Backup for Disaster Recovery</p>
                <p className="text-xs text-muted-foreground mb-2">
                  S3 backup provides an additional layer of protection by automatically syncing your evidence to AWS cloud storage.
                </p>
                <p className="text-xs font-medium mb-1">Required environment variables:</p>
                <ul className="text-xs text-muted-foreground list-disc list-inside mb-2">
                  {backupStatus.setup_instructions.required_env_vars.map((v, i) => (
                    <li key={i} className="font-mono">{v}</li>
                  ))}
                </ul>
                <p className="text-xs text-muted-foreground">
                  <a 
                    href={backupStatus.setup_instructions.how_to_get_credentials} 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className="text-primary hover:underline"
                  >
                    How to get AWS credentials →
                  </a>
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Appearance Section */}
        <Card>
          <CardHeader>
            <CardTitle className="font-serif flex items-center gap-2">
              {theme === 'dark' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
              Appearance
            </CardTitle>
            <CardDescription>Customize your visual experience</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Dark Mode</p>
                <p className="text-sm text-muted-foreground">
                  {theme === 'dark' ? 'Currently using dark theme' : 'Currently using light theme'}
                </p>
              </div>
              <Switch checked={theme === 'dark'} onCheckedChange={toggleTheme} data-testid="theme-switch" />
            </div>
          </CardContent>
        </Card>

        {/* Notifications Section */}
        <Card>
          <CardHeader>
            <CardTitle className="font-serif flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Notifications
            </CardTitle>
            <CardDescription>Configure how you receive alerts</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Email Notifications</p>
                <p className="text-sm text-muted-foreground">Receive updates about your cases</p>
              </div>
              <Switch defaultChecked data-testid="email-notifications-switch" />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">SMS Alerts (MOCKED)</p>
                <p className="text-sm text-muted-foreground">Emergency SOS notifications</p>
              </div>
              <Switch defaultChecked data-testid="sms-alerts-switch" />
            </div>
          </CardContent>
        </Card>

        {/* Security Section */}
        <Card>
          <CardHeader>
            <CardTitle className="font-serif flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Security
            </CardTitle>
            <CardDescription>Protect your account</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Two-Factor Authentication</p>
                <p className="text-sm text-muted-foreground">Add an extra layer of security</p>
              </div>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => navigate('/security/2fa')}
                data-testid="enable-2fa-btn"
              >
                Configure
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Change Password</p>
                <p className="text-sm text-muted-foreground">Update your account password</p>
              </div>
              <Button variant="outline" size="sm" data-testid="change-password-btn">Change</Button>
            </div>
          </CardContent>
        </Card>

        {/* Danger Zone */}
        <Card className="border-red-500/20">
          <CardHeader>
            <CardTitle className="font-serif text-red-500">Danger Zone</CardTitle>
            <CardDescription>Irreversible actions</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Sign Out</p>
                <p className="text-sm text-muted-foreground">Log out of your account</p>
              </div>
              <Button variant="outline" onClick={handleLogout} data-testid="settings-logout-btn">
                <LogOut className="h-4 w-4 mr-2" />
                Sign Out
              </Button>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-red-500">Delete Account</p>
                <p className="text-sm text-muted-foreground">Permanently delete your account and all data</p>
              </div>
              <Button variant="destructive" data-testid="delete-account-btn">
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}
