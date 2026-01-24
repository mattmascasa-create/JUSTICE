import React, { useState, useEffect } from 'react';
import { 
  Shield, Smartphone, Mail, Key, CheckCircle, XCircle, Loader2,
  Copy, Eye, EyeOff, AlertTriangle, QrCode, RefreshCw, Lock
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Switch } from '../components/ui/switch';
import { Badge } from '../components/ui/badge';
import { Label } from '../components/ui/label';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Alert, AlertDescription } from '../components/ui/alert';
import { InputOTP, InputOTPGroup, InputOTPSlot } from '../components/ui/input-otp';
import { toast } from 'sonner';
import { twoFactorAPI } from '../lib/api';

export default function TwoFactorSettingsPage() {
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState(null);
  
  // Setup dialogs
  const [totpSetupOpen, setTotpSetupOpen] = useState(false);
  const [smsSetupOpen, setSmsSetupOpen] = useState(false);
  const [emailSetupOpen, setEmailSetupOpen] = useState(false);
  const [disableDialogOpen, setDisableDialogOpen] = useState(false);
  const [backupCodesDialogOpen, setBackupCodesDialogOpen] = useState(false);
  
  // Setup state
  const [qrCode, setQrCode] = useState('');
  const [manualKey, setManualKey] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [password, setPassword] = useState('');
  const [backupCodes, setBackupCodes] = useState([]);
  const [showBackupCodes, setShowBackupCodes] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [setupStep, setSetupStep] = useState(1);

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await twoFactorAPI.getStatus();
      setStatus(res.data);
    } catch (error) {
      console.error('Error fetching 2FA status:', error);
      toast.error('Failed to load 2FA settings');
    } finally {
      setLoading(false);
    }
  };

  // ============== TOTP Setup ==============
  const startTotpSetup = async () => {
    setProcessing(true);
    try {
      const res = await twoFactorAPI.setupTOTP();
      setQrCode(res.data.qr_code);
      setManualKey(res.data.manual_entry_key);
      setSetupStep(1);
      setVerificationCode('');
      setTotpSetupOpen(true);
    } catch (error) {
      toast.error('Failed to start authenticator setup');
    } finally {
      setProcessing(false);
    }
  };

  const verifyTotpSetup = async () => {
    if (verificationCode.length !== 6) {
      toast.error('Please enter a 6-digit code');
      return;
    }
    
    setProcessing(true);
    try {
      const res = await twoFactorAPI.verifyTOTP(verificationCode);
      setBackupCodes(res.data.backup_codes || []);
      setSetupStep(2);
      toast.success('Authenticator app enabled!');
      fetchStatus();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Invalid code');
    } finally {
      setProcessing(false);
    }
  };

  // ============== SMS Setup ==============
  const startSmsSetup = async () => {
    if (!phoneNumber || phoneNumber.length < 10) {
      toast.error('Please enter a valid phone number');
      return;
    }
    
    setProcessing(true);
    try {
      await twoFactorAPI.setupSMS(phoneNumber);
      setSetupStep(1);
      setVerificationCode('');
      toast.success('Verification code sent!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send SMS');
    } finally {
      setProcessing(false);
    }
  };

  const verifySmsSetup = async () => {
    if (verificationCode.length !== 6) {
      toast.error('Please enter a 6-digit code');
      return;
    }
    
    setProcessing(true);
    try {
      const res = await twoFactorAPI.verifySMS(verificationCode);
      if (res.data.backup_codes) {
        setBackupCodes(res.data.backup_codes);
        setSetupStep(2);
      } else {
        setSmsSetupOpen(false);
      }
      toast.success('SMS 2FA enabled!');
      fetchStatus();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Invalid code');
    } finally {
      setProcessing(false);
    }
  };

  // ============== Email Setup ==============
  const startEmailSetup = async () => {
    setProcessing(true);
    try {
      await twoFactorAPI.setupEmail();
      setSetupStep(1);
      setVerificationCode('');
      setEmailSetupOpen(true);
      toast.success('Verification code sent to your email!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send email');
    } finally {
      setProcessing(false);
    }
  };

  const verifyEmailSetup = async () => {
    if (verificationCode.length !== 6) {
      toast.error('Please enter a 6-digit code');
      return;
    }
    
    setProcessing(true);
    try {
      const res = await twoFactorAPI.verifyEmail(verificationCode);
      if (res.data.backup_codes) {
        setBackupCodes(res.data.backup_codes);
        setSetupStep(2);
      } else {
        setEmailSetupOpen(false);
      }
      toast.success('Email 2FA enabled!');
      fetchStatus();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Invalid code');
    } finally {
      setProcessing(false);
    }
  };

  // ============== Disable 2FA ==============
  const handleDisable2FA = async () => {
    if (!password) {
      toast.error('Please enter your password');
      return;
    }
    
    setProcessing(true);
    try {
      await twoFactorAPI.disable(password);
      toast.success('Two-factor authentication disabled');
      setDisableDialogOpen(false);
      setPassword('');
      fetchStatus();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Invalid password');
    } finally {
      setProcessing(false);
    }
  };

  // ============== Backup Codes ==============
  const regenerateBackupCodes = async () => {
    setProcessing(true);
    try {
      const res = await twoFactorAPI.regenerateBackupCodes();
      setBackupCodes(res.data.backup_codes);
      setShowBackupCodes(true);
      setBackupCodesDialogOpen(true);
      toast.success('New backup codes generated');
      fetchStatus();
    } catch (error) {
      toast.error('Failed to generate backup codes');
    } finally {
      setProcessing(false);
    }
  };

  const copyBackupCodes = () => {
    navigator.clipboard.writeText(backupCodes.join('\n'));
    toast.success('Backup codes copied to clipboard');
  };

  // ============== Set Primary Method ==============
  const setPrimaryMethod = async (method) => {
    try {
      await twoFactorAPI.setPrimaryMethod(method);
      toast.success(`Primary method set to ${method}`);
      fetchStatus();
    } catch (error) {
      toast.error('Failed to update primary method');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6" data-testid="two-factor-settings-page">
      <div>
        <h1 className="text-3xl font-bold">Two-Factor Authentication</h1>
        <p className="text-muted-foreground">
          Add an extra layer of security to your account
        </p>
      </div>

      {/* Status Card */}
      <Card className={status?.enabled ? 'border-green-500/50' : 'border-yellow-500/50'}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${status?.enabled ? 'bg-green-500/10' : 'bg-yellow-500/10'}`}>
                <Shield className={`h-6 w-6 ${status?.enabled ? 'text-green-500' : 'text-yellow-500'}`} />
              </div>
              <div>
                <CardTitle>Account Security</CardTitle>
                <CardDescription>
                  {status?.enabled 
                    ? `Protected with ${status.methods?.length || 0} authentication method(s)`
                    : 'Two-factor authentication is not enabled'
                  }
                </CardDescription>
              </div>
            </div>
            <Badge className={status?.enabled ? 'bg-green-500' : 'bg-yellow-500'}>
              {status?.enabled ? 'Enabled' : 'Not Enabled'}
            </Badge>
          </div>
        </CardHeader>
        {status?.enabled && (
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {status.methods?.map((method) => (
                <Badge 
                  key={method} 
                  variant={method === status.primary_method ? 'default' : 'secondary'}
                  className="capitalize"
                >
                  {method === 'totp' ? 'Authenticator App' : method}
                  {method === status.primary_method && ' (Primary)'}
                </Badge>
              ))}
            </div>
          </CardContent>
        )}
      </Card>

      {/* Authentication Methods */}
      <div className="grid gap-4">
        {/* Authenticator App */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/10">
                  <QrCode className="h-5 w-5 text-blue-500" />
                </div>
                <div>
                  <CardTitle className="text-lg">Authenticator App</CardTitle>
                  <CardDescription>
                    Use Google Authenticator, Authy, or similar apps
                  </CardDescription>
                </div>
              </div>
              {status?.methods?.includes('totp') ? (
                <div className="flex items-center gap-2">
                  <Badge className="bg-green-500">
                    <CheckCircle className="h-3 w-3 mr-1" />
                    Enabled
                  </Badge>
                  {status.primary_method !== 'totp' && (
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => setPrimaryMethod('totp')}
                    >
                      Set Primary
                    </Button>
                  )}
                </div>
              ) : (
                <Button onClick={startTotpSetup} disabled={processing}>
                  {processing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                  Setup
                </Button>
              )}
            </div>
          </CardHeader>
        </Card>

        {/* SMS */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-green-500/10">
                  <Smartphone className="h-5 w-5 text-green-500" />
                </div>
                <div>
                  <CardTitle className="text-lg">SMS Authentication</CardTitle>
                  <CardDescription>
                    Receive codes via text message
                    {status?.phone_last_4 && ` (***${status.phone_last_4})`}
                  </CardDescription>
                </div>
              </div>
              {status?.methods?.includes('sms') ? (
                <div className="flex items-center gap-2">
                  <Badge className="bg-green-500">
                    <CheckCircle className="h-3 w-3 mr-1" />
                    Enabled
                  </Badge>
                  {status.primary_method !== 'sms' && (
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => setPrimaryMethod('sms')}
                    >
                      Set Primary
                    </Button>
                  )}
                </div>
              ) : (
                <Button onClick={() => setSmsSetupOpen(true)} disabled={processing}>
                  Setup
                </Button>
              )}
            </div>
          </CardHeader>
        </Card>

        {/* Email */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-purple-500/10">
                  <Mail className="h-5 w-5 text-purple-500" />
                </div>
                <div>
                  <CardTitle className="text-lg">Email Authentication</CardTitle>
                  <CardDescription>
                    Receive codes via email
                  </CardDescription>
                </div>
              </div>
              {status?.methods?.includes('email') ? (
                <div className="flex items-center gap-2">
                  <Badge className="bg-green-500">
                    <CheckCircle className="h-3 w-3 mr-1" />
                    Enabled
                  </Badge>
                  {status.primary_method !== 'email' && (
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => setPrimaryMethod('email')}
                    >
                      Set Primary
                    </Button>
                  )}
                </div>
              ) : (
                <Button onClick={startEmailSetup} disabled={processing}>
                  {processing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                  Setup
                </Button>
              )}
            </div>
          </CardHeader>
        </Card>
      </div>

      {/* Backup Codes & Disable */}
      {status?.enabled && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-orange-500/10">
                <Key className="h-5 w-5 text-orange-500" />
              </div>
              <div>
                <CardTitle className="text-lg">Backup Codes</CardTitle>
                <CardDescription>
                  {status.backup_codes_remaining} backup codes remaining
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="flex gap-3">
            <Button variant="outline" onClick={regenerateBackupCodes} disabled={processing}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Generate New Codes
            </Button>
            <Button 
              variant="destructive" 
              onClick={() => setDisableDialogOpen(true)}
            >
              <XCircle className="h-4 w-4 mr-2" />
              Disable 2FA
            </Button>
          </CardContent>
        </Card>
      )}

      {/* TOTP Setup Dialog */}
      <Dialog open={totpSetupOpen} onOpenChange={setTotpSetupOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Setup Authenticator App</DialogTitle>
            <DialogDescription>
              {setupStep === 1 
                ? 'Scan the QR code with your authenticator app'
                : 'Save your backup codes'
              }
            </DialogDescription>
          </DialogHeader>
          
          {setupStep === 1 ? (
            <div className="space-y-4">
              {qrCode && (
                <div className="flex justify-center">
                  <img src={qrCode} alt="QR Code" className="w-48 h-48" />
                </div>
              )}
              
              <div className="text-center">
                <p className="text-sm text-muted-foreground mb-2">Or enter this key manually:</p>
                <code className="bg-muted px-3 py-1 rounded text-sm">{manualKey}</code>
              </div>
              
              <div className="space-y-2">
                <Label>Enter verification code</Label>
                <div className="flex justify-center">
                  <InputOTP 
                    maxLength={6} 
                    value={verificationCode}
                    onChange={setVerificationCode}
                  >
                    <InputOTPGroup>
                      <InputOTPSlot index={0} />
                      <InputOTPSlot index={1} />
                      <InputOTPSlot index={2} />
                      <InputOTPSlot index={3} />
                      <InputOTPSlot index={4} />
                      <InputOTPSlot index={5} />
                    </InputOTPGroup>
                  </InputOTP>
                </div>
              </div>
              
              <Button 
                className="w-full" 
                onClick={verifyTotpSetup}
                disabled={processing || verificationCode.length !== 6}
              >
                {processing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                Verify &amp; Enable
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  Save these backup codes in a safe place. You won&apos;t see them again!
                </AlertDescription>
              </Alert>
              
              <div className="grid grid-cols-2 gap-2 p-4 bg-muted rounded-lg font-mono text-sm">
                {backupCodes.map((code, idx) => (
                  <div key={idx} className="text-center">{code}</div>
                ))}
              </div>
              
              <Button variant="outline" className="w-full" onClick={copyBackupCodes}>
                <Copy className="h-4 w-4 mr-2" />
                Copy Codes
              </Button>
              
              <Button className="w-full" onClick={() => setTotpSetupOpen(false)}>
                Done
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* SMS Setup Dialog */}
      <Dialog open={smsSetupOpen} onOpenChange={setSmsSetupOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Setup SMS Authentication</DialogTitle>
            <DialogDescription>
              {setupStep === 0 
                ? 'Enter your phone number to receive verification codes'
                : setupStep === 1 
                  ? 'Enter the code sent to your phone'
                  : 'Save your backup codes'
              }
            </DialogDescription>
          </DialogHeader>
          
          {setupStep === 0 || !verificationCode ? (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Phone Number</Label>
                <Input
                  type="tel"
                  placeholder="+1 (555) 123-4567"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Include country code (e.g., +1 for US)
                </p>
              </div>
              
              <Button 
                className="w-full" 
                onClick={startSmsSetup}
                disabled={processing || !phoneNumber}
              >
                {processing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                Send Code
              </Button>
            </div>
          ) : setupStep === 1 ? (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Verification Code</Label>
                <div className="flex justify-center">
                  <InputOTP 
                    maxLength={6} 
                    value={verificationCode}
                    onChange={setVerificationCode}
                  >
                    <InputOTPGroup>
                      <InputOTPSlot index={0} />
                      <InputOTPSlot index={1} />
                      <InputOTPSlot index={2} />
                      <InputOTPSlot index={3} />
                      <InputOTPSlot index={4} />
                      <InputOTPSlot index={5} />
                    </InputOTPGroup>
                  </InputOTP>
                </div>
              </div>
              
              <Button 
                className="w-full" 
                onClick={verifySmsSetup}
                disabled={processing || verificationCode.length !== 6}
              >
                {processing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                Verify
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  Save these backup codes in a safe place!
                </AlertDescription>
              </Alert>
              
              <div className="grid grid-cols-2 gap-2 p-4 bg-muted rounded-lg font-mono text-sm">
                {backupCodes.map((code, idx) => (
                  <div key={idx} className="text-center">{code}</div>
                ))}
              </div>
              
              <Button variant="outline" className="w-full" onClick={copyBackupCodes}>
                <Copy className="h-4 w-4 mr-2" />
                Copy Codes
              </Button>
              
              <Button className="w-full" onClick={() => setSmsSetupOpen(false)}>
                Done
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Email Setup Dialog */}
      <Dialog open={emailSetupOpen} onOpenChange={setEmailSetupOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Setup Email Authentication</DialogTitle>
            <DialogDescription>
              {setupStep === 1 
                ? 'Enter the code sent to your email'
                : 'Save your backup codes'
              }
            </DialogDescription>
          </DialogHeader>
          
          {setupStep === 1 ? (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Verification Code</Label>
                <div className="flex justify-center">
                  <InputOTP 
                    maxLength={6} 
                    value={verificationCode}
                    onChange={setVerificationCode}
                  >
                    <InputOTPGroup>
                      <InputOTPSlot index={0} />
                      <InputOTPSlot index={1} />
                      <InputOTPSlot index={2} />
                      <InputOTPSlot index={3} />
                      <InputOTPSlot index={4} />
                      <InputOTPSlot index={5} />
                    </InputOTPGroup>
                  </InputOTP>
                </div>
              </div>
              
              <Button 
                className="w-full" 
                onClick={verifyEmailSetup}
                disabled={processing || verificationCode.length !== 6}
              >
                {processing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                Verify
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  Save these backup codes in a safe place!
                </AlertDescription>
              </Alert>
              
              <div className="grid grid-cols-2 gap-2 p-4 bg-muted rounded-lg font-mono text-sm">
                {backupCodes.map((code, idx) => (
                  <div key={idx} className="text-center">{code}</div>
                ))}
              </div>
              
              <Button variant="outline" className="w-full" onClick={copyBackupCodes}>
                <Copy className="h-4 w-4 mr-2" />
                Copy Codes
              </Button>
              
              <Button className="w-full" onClick={() => setEmailSetupOpen(false)}>
                Done
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Disable 2FA Dialog */}
      <Dialog open={disableDialogOpen} onOpenChange={setDisableDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Disable Two-Factor Authentication</DialogTitle>
            <DialogDescription>
              This will remove all 2FA methods from your account. Enter your password to confirm.
            </DialogDescription>
          </DialogHeader>
          
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Warning: Disabling 2FA will make your account less secure.
            </AlertDescription>
          </Alert>
          
          <div className="space-y-2">
            <Label>Password</Label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
            />
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setDisableDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleDisable2FA}
              disabled={processing || !password}
            >
              {processing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              Disable 2FA
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Backup Codes Dialog */}
      <Dialog open={backupCodesDialogOpen} onOpenChange={setBackupCodesDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Backup Codes</DialogTitle>
            <DialogDescription>
              Your old backup codes are no longer valid.
            </DialogDescription>
          </DialogHeader>
          
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Save these codes in a safe place. You won&apos;t see them again!
            </AlertDescription>
          </Alert>
          
          <div className="grid grid-cols-2 gap-2 p-4 bg-muted rounded-lg font-mono text-sm">
            {backupCodes.map((code, idx) => (
              <div key={idx} className="text-center">{code}</div>
            ))}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={copyBackupCodes}>
              <Copy className="h-4 w-4 mr-2" />
              Copy
            </Button>
            <Button onClick={() => setBackupCodesDialogOpen(false)}>
              Done
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
