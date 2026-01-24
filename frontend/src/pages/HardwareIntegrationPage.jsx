import React, { useState, useEffect } from 'react';
import { 
  Camera, Smartphone, Video, Wifi, WifiOff, Plus, Settings, Trash2,
  Eye, EyeOff, Volume2, VolumeX, Upload, Shield, Bluetooth, Radio,
  CheckCircle, XCircle, Loader2, ChevronRight, ExternalLink, Copy,
  Monitor, Tv, Play, Square, HelpCircle, RefreshCw
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Switch } from '../components/ui/switch';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Label } from '../components/ui/label';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '../components/ui/dialog';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../components/ui/accordion';
import { toast } from 'sonner';
import { hardwareAPI } from '../lib/api';

export default function HardwareIntegrationPage() {
  const [activeTab, setActiveTab] = useState('devices');
  const [loading, setLoading] = useState(true);
  const [devices, setDevices] = useState([]);
  const [stealthSettings, setStealthSettings] = useState(null);
  const [addDeviceOpen, setAddDeviceOpen] = useState(false);
  const [selectedDeviceType, setSelectedDeviceType] = useState('');
  const [newDeviceName, setNewDeviceName] = useState('');
  const [rtspUrl, setRtspUrl] = useState('');
  const [saving, setSaving] = useState(false);
  
  // Guides
  const [goProGuide, setGoProGuide] = useState(null);
  const [rtspGuide, setRtspGuide] = useState(null);
  const [dashcamGuide, setDashcamGuide] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [devicesRes, stealthRes] = await Promise.all([
        hardwareAPI.getDevices(),
        hardwareAPI.getStealthSettings()
      ]);
      setDevices(devicesRes.data.devices || []);
      setStealthSettings(stealthRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load hardware settings');
    } finally {
      setLoading(false);
    }
  };

  const handleAddDevice = async () => {
    if (!selectedDeviceType || !newDeviceName) {
      toast.error('Please select device type and enter a name');
      return;
    }

    setSaving(true);
    try {
      const connectionInfo = selectedDeviceType === 'rtsp_camera' ? { rtsp_url: rtspUrl } : null;
      await hardwareAPI.registerDevice(selectedDeviceType, newDeviceName, connectionInfo);
      toast.success('Device registered successfully!');
      setAddDeviceOpen(false);
      setSelectedDeviceType('');
      setNewDeviceName('');
      setRtspUrl('');
      fetchData();
    } catch (error) {
      toast.error('Failed to register device');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteDevice = async (deviceId) => {
    try {
      await hardwareAPI.deleteDevice(deviceId);
      toast.success('Device removed');
      fetchData();
    } catch (error) {
      toast.error('Failed to remove device');
    }
  };

  const handleStealthSettingChange = async (key, value) => {
    try {
      const updated = { ...stealthSettings, [key]: value };
      setStealthSettings(updated);
      await hardwareAPI.updateStealthSettings({ [key]: value });
      toast.success('Setting updated');
    } catch (error) {
      toast.error('Failed to update setting');
    }
  };

  const loadGuide = async (type) => {
    try {
      if (type === 'gopro' && !goProGuide) {
        const res = await hardwareAPI.getGoProPairingGuide();
        setGoProGuide(res.data);
      } else if (type === 'rtsp' && !rtspGuide) {
        const res = await hardwareAPI.getRtspSetupGuide();
        setRtspGuide(res.data);
      } else if (type === 'dashcam' && !dashcamGuide) {
        const res = await hardwareAPI.getDashcamSetupGuide();
        setDashcamGuide(res.data);
      }
    } catch (error) {
      toast.error('Failed to load guide');
    }
  };

  const getDeviceIcon = (type) => {
    switch (type) {
      case 'gopro': return <Video className="h-5 w-5" />;
      case 'dashcam': return <Monitor className="h-5 w-5" />;
      case 'rtsp_camera': return <Tv className="h-5 w-5" />;
      default: return <Camera className="h-5 w-5" />;
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'connected':
        return <Badge className="bg-green-500">Connected</Badge>;
      case 'streaming':
        return <Badge className="bg-blue-500">Streaming</Badge>;
      case 'connecting':
        return <Badge variant="outline" className="text-yellow-500 border-yellow-500">Connecting</Badge>;
      case 'error':
        return <Badge variant="destructive">Error</Badge>;
      default:
        return <Badge variant="secondary">Disconnected</Badge>;
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
    <div className="space-y-6 p-6" data-testid="hardware-integration-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Hardware Integration</h1>
          <p className="text-muted-foreground">
            Connect external cameras and configure recording settings
          </p>
        </div>
        <Button onClick={() => setAddDeviceOpen(true)} data-testid="add-device-btn">
          <Plus className="h-4 w-4 mr-2" />
          Add Device
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="devices">My Devices</TabsTrigger>
          <TabsTrigger value="stealth">Stealth Mode</TabsTrigger>
          <TabsTrigger value="guides">Setup Guides</TabsTrigger>
        </TabsList>

        {/* Devices Tab */}
        <TabsContent value="devices" className="space-y-4">
          {/* Smartphone Card (Always Present) */}
          <Card className="border-primary/50">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary/10">
                    <Smartphone className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">This Smartphone</CardTitle>
                    <CardDescription>Primary recording device</CardDescription>
                  </div>
                </div>
                <Badge className="bg-green-500">Active</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-4">
                <div className="flex items-center gap-2 p-3 rounded-lg bg-muted">
                  <Camera className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">Front &amp; Back Camera</span>
                </div>
                <div className="flex items-center gap-2 p-3 rounded-lg bg-muted">
                  <Volume2 className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">Microphone</span>
                </div>
                <div className="flex items-center gap-2 p-3 rounded-lg bg-muted">
                  <Upload className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">Auto Cloud Upload</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Connected Devices */}
          {devices.length > 0 ? (
            devices.map((device) => (
              <Card key={device.device_id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-muted">
                        {getDeviceIcon(device.device_type)}
                      </div>
                      <div>
                        <CardTitle className="text-lg">{device.device_name}</CardTitle>
                        <CardDescription className="capitalize">
                          {device.device_type.replace('_', ' ')}
                        </CardDescription>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {getStatusBadge(device.status)}
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDeleteDevice(device.device_id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-muted-foreground">
                      Stream Key: <code className="bg-muted px-2 py-1 rounded">{device.stream_key}</code>
                    </div>
                    <Button variant="outline" size="sm">
                      <Settings className="h-4 w-4 mr-2" />
                      Configure
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))
          ) : (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Camera className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">No External Devices</h3>
                <p className="text-muted-foreground text-center mb-4">
                  Add a GoPro, dash cam, or IP camera to enhance your recording setup
                </p>
                <Button onClick={() => setAddDeviceOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Your First Device
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Stealth Mode Tab */}
        <TabsContent value="stealth" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-purple-500/10">
                  <EyeOff className="h-6 w-6 text-purple-500" />
                </div>
                <div>
                  <CardTitle>Stealth Recording Mode</CardTitle>
                  <CardDescription>
                    Discreet recording settings for sensitive situations
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Master Toggle */}
              <div className="flex items-center justify-between p-4 rounded-lg border bg-muted/30">
                <div className="flex items-center gap-3">
                  <Shield className="h-5 w-5 text-purple-500" />
                  <div>
                    <Label className="text-base font-medium">Enable Stealth Mode</Label>
                    <p className="text-sm text-muted-foreground">
                      Activate all stealth features when recording
                    </p>
                  </div>
                </div>
                <Switch
                  checked={stealthSettings?.enabled}
                  onCheckedChange={(val) => handleStealthSettingChange('enabled', val)}
                  data-testid="stealth-enabled-toggle"
                />
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                {/* Black Screen */}
                <div className="flex items-center justify-between p-4 rounded-lg border">
                  <div className="flex items-center gap-3">
                    <Monitor className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <Label>Black Screen</Label>
                      <p className="text-xs text-muted-foreground">
                        Screen turns off while recording
                      </p>
                    </div>
                  </div>
                  <Switch
                    checked={stealthSettings?.black_screen}
                    onCheckedChange={(val) => handleStealthSettingChange('black_screen', val)}
                  />
                </div>

                {/* Disable Flash */}
                <div className="flex items-center justify-between p-4 rounded-lg border">
                  <div className="flex items-center gap-3">
                    <Eye className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <Label>Disable Flash</Label>
                      <p className="text-xs text-muted-foreground">
                        No flash or LED indicators
                      </p>
                    </div>
                  </div>
                  <Switch
                    checked={stealthSettings?.disable_flash}
                    onCheckedChange={(val) => handleStealthSettingChange('disable_flash', val)}
                  />
                </div>

                {/* Silent Shutter */}
                <div className="flex items-center justify-between p-4 rounded-lg border">
                  <div className="flex items-center gap-3">
                    <VolumeX className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <Label>Silent Mode</Label>
                      <p className="text-xs text-muted-foreground">
                        No sounds or vibrations
                      </p>
                    </div>
                  </div>
                  <Switch
                    checked={stealthSettings?.silent_shutter}
                    onCheckedChange={(val) => handleStealthSettingChange('silent_shutter', val)}
                  />
                </div>

                {/* Volume Button Trigger */}
                <div className="flex items-center justify-between p-4 rounded-lg border">
                  <div className="flex items-center gap-3">
                    <Volume2 className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <Label>Volume Button Trigger</Label>
                      <p className="text-xs text-muted-foreground">
                        Press volume to start recording
                      </p>
                    </div>
                  </div>
                  <Switch
                    checked={stealthSettings?.volume_button_trigger}
                    onCheckedChange={(val) => handleStealthSettingChange('volume_button_trigger', val)}
                  />
                </div>

                {/* Auto Upload */}
                <div className="flex items-center justify-between p-4 rounded-lg border">
                  <div className="flex items-center gap-3">
                    <Upload className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <Label>Auto Cloud Upload</Label>
                      <p className="text-xs text-muted-foreground">
                        Immediately backup to cloud
                      </p>
                    </div>
                  </div>
                  <Switch
                    checked={stealthSettings?.auto_upload}
                    onCheckedChange={(val) => handleStealthSettingChange('auto_upload', val)}
                  />
                </div>

                {/* Background Recording */}
                <div className="flex items-center justify-between p-4 rounded-lg border">
                  <div className="flex items-center gap-3">
                    <Radio className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <Label>Background Recording</Label>
                      <p className="text-xs text-muted-foreground">
                        Continue when app minimized
                      </p>
                    </div>
                  </div>
                  <Switch
                    checked={stealthSettings?.background_recording}
                    onCheckedChange={(val) => handleStealthSettingChange('background_recording', val)}
                  />
                </div>
              </div>

              {/* Quick Launch Gesture */}
              <div className="p-4 rounded-lg border">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <Play className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <Label>Quick Launch Gesture</Label>
                      <p className="text-sm text-muted-foreground">
                        Gesture to quickly start recording
                      </p>
                    </div>
                  </div>
                </div>
                <Select
                  value={stealthSettings?.quick_launch_gesture || 'triple_power'}
                  onValueChange={(val) => handleStealthSettingChange('quick_launch_gesture', val)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="triple_power">Triple Press Power Button</SelectItem>
                    <SelectItem value="double_volume">Double Press Volume Down</SelectItem>
                    <SelectItem value="shake">Shake Device</SelectItem>
                    <SelectItem value="none">Disabled</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Setup Guides Tab */}
        <TabsContent value="guides" className="space-y-4">
          <Accordion type="single" collapsible className="space-y-4">
            {/* GoPro Guide */}
            <AccordionItem value="gopro" className="border rounded-lg px-4">
              <AccordionTrigger 
                onClick={() => loadGuide('gopro')}
                className="hover:no-underline"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-blue-500/10">
                    <Video className="h-5 w-5 text-blue-500" />
                  </div>
                  <div className="text-left">
                    <h3 className="font-semibold">GoPro Integration</h3>
                    <p className="text-sm text-muted-foreground">Hero 9 and newer</p>
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent className="pt-4">
                {goProGuide ? (
                  <div className="space-y-4">
                    <div className="grid gap-3">
                      {goProGuide.steps.map((step) => (
                        <div key={step.step} className="flex gap-3 p-3 rounded-lg bg-muted/50">
                          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center font-bold">
                            {step.step}
                          </div>
                          <div>
                            <h4 className="font-medium">{step.title}</h4>
                            <p className="text-sm text-muted-foreground">{step.description}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="p-3 rounded-lg bg-blue-500/10">
                      <h4 className="font-medium mb-2">Supported Models</h4>
                      <div className="flex flex-wrap gap-2">
                        {goProGuide.supported_models.map((model) => (
                          <Badge key={model} variant="secondary">{model}</Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                  </div>
                )}
              </AccordionContent>
            </AccordionItem>

            {/* RTSP Camera Guide */}
            <AccordionItem value="rtsp" className="border rounded-lg px-4">
              <AccordionTrigger 
                onClick={() => loadGuide('rtsp')}
                className="hover:no-underline"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-green-500/10">
                    <Tv className="h-5 w-5 text-green-500" />
                  </div>
                  <div className="text-left">
                    <h3 className="font-semibold">IP/RTSP Camera</h3>
                    <p className="text-sm text-muted-foreground">Security cameras &amp; webcams</p>
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent className="pt-4">
                {rtspGuide ? (
                  <div className="space-y-4">
                    <h4 className="font-medium">Common URL Formats</h4>
                    <div className="space-y-2">
                      {rtspGuide.common_url_formats.map((format) => (
                        <div key={format.brand} className="p-3 rounded-lg bg-muted/50">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium">{format.brand}</span>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                navigator.clipboard.writeText(format.format);
                                toast.success('Copied to clipboard');
                              }}
                            >
                              <Copy className="h-3 w-3" />
                            </Button>
                          </div>
                          <code className="text-xs text-muted-foreground break-all">
                            {format.format}
                          </code>
                        </div>
                      ))}
                    </div>
                    <div className="p-3 rounded-lg bg-yellow-500/10">
                      <h4 className="font-medium mb-2">Troubleshooting</h4>
                      <ul className="text-sm space-y-1">
                        {rtspGuide.troubleshooting.map((tip, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <ChevronRight className="h-4 w-4 mt-0.5 flex-shrink-0" />
                            {tip}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                  </div>
                )}
              </AccordionContent>
            </AccordionItem>

            {/* Dash Cam Guide */}
            <AccordionItem value="dashcam" className="border rounded-lg px-4">
              <AccordionTrigger 
                onClick={() => loadGuide('dashcam')}
                className="hover:no-underline"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-orange-500/10">
                    <Monitor className="h-5 w-5 text-orange-500" />
                  </div>
                  <div className="text-left">
                    <h3 className="font-semibold">Dash Cam</h3>
                    <p className="text-sm text-muted-foreground">Vehicle cameras</p>
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent className="pt-4">
                {dashcamGuide ? (
                  <div className="space-y-4">
                    <div className="p-4 rounded-lg bg-muted/50">
                      <h4 className="font-medium mb-2">WiFi Dash Cams</h4>
                      <p className="text-sm text-muted-foreground mb-3">
                        {dashcamGuide.wifi_dashcams.description}
                      </p>
                      <ol className="text-sm space-y-2">
                        {dashcamGuide.wifi_dashcams.steps.map((step, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <span className="font-bold">{idx + 1}.</span>
                            {step}
                          </li>
                        ))}
                      </ol>
                    </div>
                    
                    <div className="p-4 rounded-lg bg-primary/5 border border-primary/20">
                      <h4 className="font-medium mb-2 flex items-center gap-2">
                        <Smartphone className="h-4 w-4" />
                        Recommended: Use Your Phone
                      </h4>
                      <p className="text-sm text-muted-foreground mb-3">
                        {dashcamGuide.smartphone_mount.description}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {dashcamGuide.smartphone_mount.benefits.map((benefit, idx) => (
                          <Badge key={idx} variant="secondary" className="text-xs">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            {benefit}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                  </div>
                )}
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </TabsContent>
      </Tabs>

      {/* Add Device Dialog */}
      <Dialog open={addDeviceOpen} onOpenChange={setAddDeviceOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add External Device</DialogTitle>
            <DialogDescription>
              Connect a GoPro, dash cam, or IP camera to enhance your recording setup
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Device Type</Label>
              <Select value={selectedDeviceType} onValueChange={setSelectedDeviceType}>
                <SelectTrigger data-testid="device-type-select">
                  <SelectValue placeholder="Select device type..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="gopro">
                    <div className="flex items-center gap-2">
                      <Video className="h-4 w-4" />
                      GoPro Camera
                    </div>
                  </SelectItem>
                  <SelectItem value="dashcam">
                    <div className="flex items-center gap-2">
                      <Monitor className="h-4 w-4" />
                      Dash Cam
                    </div>
                  </SelectItem>
                  <SelectItem value="rtsp_camera">
                    <div className="flex items-center gap-2">
                      <Tv className="h-4 w-4" />
                      IP/RTSP Camera
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Device Name</Label>
              <Input
                placeholder="e.g., My GoPro Hero 12"
                value={newDeviceName}
                onChange={(e) => setNewDeviceName(e.target.value)}
                data-testid="device-name-input"
              />
            </div>

            {selectedDeviceType === 'rtsp_camera' && (
              <div className="space-y-2">
                <Label>RTSP URL</Label>
                <Input
                  placeholder="rtsp://username:password@192.168.1.100:554/stream"
                  value={rtspUrl}
                  onChange={(e) => setRtspUrl(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Check the Setup Guides tab for URL formats
                </p>
              </div>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddDeviceOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddDevice} disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Plus className="h-4 w-4 mr-2" />}
              Add Device
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
