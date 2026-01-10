import React from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Separator } from '../components/ui/separator';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { getInitials } from '../lib/utils';
import { 
  User, Bell, Shield, Moon, Sun, Phone, Mail, 
  LogOut, Trash2, Save
} from 'lucide-react';
import { toast } from 'sonner';

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const handleSave = () => {
    toast.success('Settings saved successfully');
  };

  const handleLogout = async () => {
    await logout();
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
                <Input 
                  id="name" 
                  defaultValue={user?.name}
                  data-testid="settings-name-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input 
                    id="email" 
                    defaultValue={user?.email}
                    className="pl-10"
                    disabled
                    data-testid="settings-email-input"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="phone">Phone (for SOS alerts)</Label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input 
                    id="phone" 
                    placeholder="+1 (555) 123-4567"
                    defaultValue={user?.phone}
                    className="pl-10"
                    data-testid="settings-phone-input"
                  />
                </div>
              </div>
            </div>

            <Button onClick={handleSave} data-testid="save-profile-btn">
              <Save className="h-4 w-4 mr-2" />
              Save Changes
            </Button>
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
              <Switch 
                checked={theme === 'dark'} 
                onCheckedChange={toggleTheme}
                data-testid="theme-switch"
              />
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
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Attorney Messages</p>
                <p className="text-sm text-muted-foreground">Notifications for new messages</p>
              </div>
              <Switch defaultChecked data-testid="attorney-messages-switch" />
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
              <Button variant="outline" size="sm" data-testid="enable-2fa-btn">
                Enable
              </Button>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Change Password</p>
                <p className="text-sm text-muted-foreground">Update your account password</p>
              </div>
              <Button variant="outline" size="sm" data-testid="change-password-btn">
                Change
              </Button>
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
              <Button 
                variant="outline" 
                onClick={handleLogout}
                data-testid="settings-logout-btn"
              >
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
              <Button 
                variant="destructive"
                data-testid="delete-account-btn"
              >
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
