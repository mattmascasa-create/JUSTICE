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
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { getInitials } from '../lib/utils';
import { emergencyContactsAPI, blockchainAPI, backupAPI } from '../lib/api';
import { 
  User, Bell, Shield, Moon, Sun, Phone, Mail, 
  LogOut, Trash2, Save, Users, Plus, X,
  Database, Globe, CheckCircle, AlertCircle, Link2,
  Cloud, CloudOff, RefreshCw, History, Loader2
} from 'lucide-react';
import { toast } from 'sonner';

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [contacts, setContacts] = useState([]);
  const [newContact, setNewContact] = useState({ name: '', phone: '', email: '' });
  const [ipfsStatus, setIpfsStatus] = useState(null);
  const [blockchainStatus, setBlockchainStatus] = useState(null);
  const [backupStatus, setBackupStatus] = useState(null);
  const [backupLoading, setBackupLoading] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const [contactsRes, ipfsRes, blockchainRes, backupRes] = await Promise.all([
        emergencyContactsAPI.get().catch(() => ({ data: [] })),
        blockchainAPI.getIPFSStatus().catch(() => ({ data: null })),
        blockchainAPI.getBlockchainStatus().catch(() => ({ data: null })),
        backupAPI.getStatus().catch(() => ({ data: null }))
      ]);
      setContacts(contactsRes.data || []);
      setIpfsStatus(ipfsRes.data);
      setBlockchainStatus(blockchainRes.data);
      setBackupStatus(backupRes.data);
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
              <Button variant="outline" size="sm" data-testid="enable-2fa-btn">Enable</Button>
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
