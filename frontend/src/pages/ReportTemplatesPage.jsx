import React, { useState, useEffect } from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { ScrollArea } from '../components/ui/scroll-area';
import { templatesAPI } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import {
  FileText, Plus, Trash2, Edit2, Copy, Star,
  Palette, Layout, Type, Shield, Loader2, Eye,
  Check, X
} from 'lucide-react';

const DEFAULT_COLORS = {
  primary: '#4f46e5',
  secondary: '#7c3aed',
  accent: '#3b82f6'
};

const COLOR_PRESETS = [
  { name: 'Justice Purple', primary: '#4f46e5', secondary: '#7c3aed', accent: '#3b82f6' },
  { name: 'Professional Blue', primary: '#1e40af', secondary: '#3b82f6', accent: '#0ea5e9' },
  { name: 'Legal Green', primary: '#065f46', secondary: '#059669', accent: '#10b981' },
  { name: 'Classic Navy', primary: '#1e3a5f', secondary: '#2563eb', accent: '#3b82f6' },
  { name: 'Modern Gray', primary: '#374151', secondary: '#4b5563', accent: '#6b7280' },
  { name: 'Bold Red', primary: '#991b1b', secondary: '#dc2626', accent: '#ef4444' },
];

export default function ReportTemplatesPage() {
  const { user } = useAuth();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('branding');
  const [showPreview, setShowPreview] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState({
    template_name: '',
    description: '',
    branding: {
      firm_name: '',
      logo_url: '',
      primary_color: DEFAULT_COLORS.primary,
      secondary_color: DEFAULT_COLORS.secondary,
      accent_color: DEFAULT_COLORS.accent
    },
    sections: {
      show_overview: true,
      show_key_points: true,
      show_action_items: true,
      show_legal_concerns: true,
      show_recommendations: true,
      show_follow_up: true,
      show_call_info: true,
      show_timestamps: true
    },
    header_text: '',
    footer_text: '',
    intro_message: '',
    confidentiality_notice: '',
    is_default: false
  });

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const res = await templatesAPI.getMyTemplates();
      setTemplates(res.data.templates || []);
    } catch (error) {
      console.error('Error fetching templates:', error);
      toast.error('Failed to load templates');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      template_name: '',
      description: '',
      branding: {
        firm_name: '',
        logo_url: '',
        primary_color: DEFAULT_COLORS.primary,
        secondary_color: DEFAULT_COLORS.secondary,
        accent_color: DEFAULT_COLORS.accent
      },
      sections: {
        show_overview: true,
        show_key_points: true,
        show_action_items: true,
        show_legal_concerns: true,
        show_recommendations: true,
        show_follow_up: true,
        show_call_info: true,
        show_timestamps: true
      },
      header_text: '',
      footer_text: '',
      intro_message: '',
      confidentiality_notice: '',
      is_default: false
    });
    setEditingTemplate(null);
    setActiveTab('branding');
  };

  const openCreateDialog = () => {
    resetForm();
    setShowDialog(true);
  };

  const openEditDialog = (template) => {
    setFormData({
      template_name: template.template_name || '',
      description: template.description || '',
      branding: {
        firm_name: template.branding?.firm_name || '',
        logo_url: template.branding?.logo_url || '',
        primary_color: template.branding?.primary_color || DEFAULT_COLORS.primary,
        secondary_color: template.branding?.secondary_color || DEFAULT_COLORS.secondary,
        accent_color: template.branding?.accent_color || DEFAULT_COLORS.accent
      },
      sections: {
        show_overview: template.sections?.show_overview ?? true,
        show_key_points: template.sections?.show_key_points ?? true,
        show_action_items: template.sections?.show_action_items ?? true,
        show_legal_concerns: template.sections?.show_legal_concerns ?? true,
        show_recommendations: template.sections?.show_recommendations ?? true,
        show_follow_up: template.sections?.show_follow_up ?? true,
        show_call_info: template.sections?.show_call_info ?? true,
        show_timestamps: template.sections?.show_timestamps ?? true
      },
      header_text: template.header_text || '',
      footer_text: template.footer_text || '',
      intro_message: template.intro_message || '',
      confidentiality_notice: template.confidentiality_notice || '',
      is_default: template.is_default || false
    });
    setEditingTemplate(template);
    setShowDialog(true);
  };

  const closeDialog = () => {
    setShowDialog(false);
    resetForm();
  };

  const handleSave = async () => {
    if (!formData.template_name.trim()) {
      toast.error('Please enter a template name');
      return;
    }
    
    setSaving(true);
    try {
      const data = {
        template_name: formData.template_name,
        description: formData.description || null,
        branding: formData.branding,
        sections: formData.sections,
        header_text: formData.header_text || null,
        footer_text: formData.footer_text || null,
        intro_message: formData.intro_message || null,
        confidentiality_notice: formData.confidentiality_notice || null,
        is_default: formData.is_default
      };
      
      if (editingTemplate) {
        await templatesAPI.updateTemplate(editingTemplate.template_id, data);
        toast.success('Template updated!');
      } else {
        await templatesAPI.createTemplate(data);
        toast.success('Template created!');
      }
      closeDialog();
      fetchTemplates();
    } catch (error) {
      console.error('Save error:', error);
      toast.error(error.response?.data?.detail || 'Failed to save template');
    } finally {
      setSaving(false);
    }
  };

  const handleSetDefault = async (templateId) => {
    try {
      await templatesAPI.setDefault(templateId);
      toast.success('Default template updated');
      fetchTemplates();
    } catch (error) {
      toast.error('Failed to set default');
    }
  };

  const handleDuplicate = async (templateId) => {
    try {
      await templatesAPI.duplicateTemplate(templateId);
      toast.success('Template duplicated');
      fetchTemplates();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to duplicate');
    }
  };

  const handleDelete = async (templateId) => {
    if (!confirm('Are you sure you want to delete this template?')) return;
    
    try {
      await templatesAPI.deleteTemplate(templateId);
      toast.success('Template deleted');
      fetchTemplates();
    } catch (error) {
      toast.error('Failed to delete template');
    }
  };

  const applyColorPreset = (preset) => {
    setFormData({
      ...formData,
      branding: {
        ...formData.branding,
        primary_color: preset.primary,
        secondary_color: preset.secondary,
        accent_color: preset.accent
      }
    });
  };

  const updateBranding = (field, value) => {
    setFormData({
      ...formData,
      branding: { ...formData.branding, [field]: value }
    });
  };

  const updateSection = (field, value) => {
    setFormData({
      ...formData,
      sections: { ...formData.sections, [field]: value }
    });
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="report-templates-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-serif text-3xl font-bold">Report Templates</h1>
            <p className="text-muted-foreground mt-1">
              Customize your report branding and layout
            </p>
          </div>
          <Button onClick={openCreateDialog} data-testid="create-template-btn">
            <Plus className="h-4 w-4 mr-2" />
            Create Template
          </Button>
        </div>

        {/* Info Card */}
        <Card className="bg-gradient-to-r from-indigo-50 to-purple-50 border-indigo-200">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <Palette className="h-5 w-5 text-indigo-600 mt-0.5" />
              <div>
                <p className="font-medium text-indigo-900">Personalize Your Reports</p>
                <p className="text-sm text-indigo-700 mt-1">
                  Create custom templates with your firm's branding, choose which sections to include,
                  and add personalized messages. Templates can be used with scheduled reports.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Templates List */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : templates.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
              <h3 className="font-medium text-lg mb-2">No Templates Yet</h3>
              <p className="text-muted-foreground mb-4">
                Create your first custom report template with your firm branding.
              </p>
              <Button onClick={openCreateDialog}>
                <Plus className="h-4 w-4 mr-2" />
                Create Template
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map((template) => (
              <Card key={template.template_id} className="relative" data-testid={`template-card-${template.template_id}`}>
                {template.is_default && (
                  <Badge className="absolute top-2 right-2 bg-yellow-100 text-yellow-800">
                    <Star className="h-3 w-3 mr-1 fill-yellow-500" />
                    Default
                  </Badge>
                )}
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg">{template.template_name}</CardTitle>
                  {template.description && (
                    <CardDescription>{template.description}</CardDescription>
                  )}
                </CardHeader>
                <CardContent>
                  {/* Color Preview */}
                  <div className="flex gap-2 mb-4">
                    <div 
                      className="h-8 w-8 rounded-full border-2 border-white shadow" 
                      style={{ backgroundColor: template.branding?.primary_color || DEFAULT_COLORS.primary }}
                      title="Primary Color"
                    />
                    <div 
                      className="h-8 w-8 rounded-full border-2 border-white shadow" 
                      style={{ backgroundColor: template.branding?.secondary_color || DEFAULT_COLORS.secondary }}
                      title="Secondary Color"
                    />
                    <div 
                      className="h-8 w-8 rounded-full border-2 border-white shadow" 
                      style={{ backgroundColor: template.branding?.accent_color || DEFAULT_COLORS.accent }}
                      title="Accent Color"
                    />
                    {template.branding?.firm_name && (
                      <span className="ml-2 text-sm text-muted-foreground self-center truncate">
                        {template.branding.firm_name}
                      </span>
                    )}
                  </div>
                  
                  {/* Section toggles preview */}
                  <div className="flex flex-wrap gap-1 mb-4">
                    {template.sections?.show_overview && <Badge variant="outline" className="text-xs">Overview</Badge>}
                    {template.sections?.show_key_points && <Badge variant="outline" className="text-xs">Key Points</Badge>}
                    {template.sections?.show_action_items && <Badge variant="outline" className="text-xs">Actions</Badge>}
                    {template.sections?.show_legal_concerns && <Badge variant="outline" className="text-xs">Legal</Badge>}
                  </div>
                  
                  <p className="text-xs text-muted-foreground mb-4">
                    Created {formatDate(template.created_at)}
                  </p>
                  
                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    {!template.is_default && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleSetDefault(template.template_id)}
                        title="Set as default"
                      >
                        <Star className="h-4 w-4" />
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDuplicate(template.template_id)}
                      title="Duplicate"
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openEditDialog(template)}
                      title="Edit"
                    >
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(template.template_id)}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Create/Edit Dialog */}
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden" data-testid="template-dialog">
            <DialogHeader>
              <DialogTitle>
                {editingTemplate ? 'Edit Template' : 'Create Report Template'}
              </DialogTitle>
              <DialogDescription>
                Customize your report appearance and content
              </DialogDescription>
            </DialogHeader>
            
            <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-4">
              <TabsList className="grid grid-cols-4 w-full">
                <TabsTrigger value="branding">
                  <Palette className="h-4 w-4 mr-2" />
                  Branding
                </TabsTrigger>
                <TabsTrigger value="sections">
                  <Layout className="h-4 w-4 mr-2" />
                  Sections
                </TabsTrigger>
                <TabsTrigger value="content">
                  <Type className="h-4 w-4 mr-2" />
                  Content
                </TabsTrigger>
                <TabsTrigger value="settings">
                  <Shield className="h-4 w-4 mr-2" />
                  Settings
                </TabsTrigger>
              </TabsList>
              
              <ScrollArea className="h-[400px] mt-4 pr-4">
                {/* Branding Tab */}
                <TabsContent value="branding" className="space-y-4 m-0">
                  <div className="space-y-2">
                    <Label>Template Name *</Label>
                    <Input
                      placeholder="e.g., Smith & Associates Template"
                      value={formData.template_name}
                      onChange={(e) => setFormData({ ...formData, template_name: e.target.value })}
                      data-testid="template-name-input"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Description</Label>
                    <Input
                      placeholder="Brief description of this template"
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Firm Name</Label>
                    <Input
                      placeholder="Your firm or organization name"
                      value={formData.branding.firm_name}
                      onChange={(e) => updateBranding('firm_name', e.target.value)}
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Logo URL (optional)</Label>
                    <Input
                      placeholder="https://example.com/logo.png"
                      value={formData.branding.logo_url}
                      onChange={(e) => updateBranding('logo_url', e.target.value)}
                    />
                  </div>
                  
                  <div className="space-y-3">
                    <Label>Color Scheme</Label>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="space-y-2">
                        <Label className="text-xs text-muted-foreground">Primary</Label>
                        <div className="flex items-center gap-2">
                          <input
                            type="color"
                            value={formData.branding.primary_color}
                            onChange={(e) => updateBranding('primary_color', e.target.value)}
                            className="w-10 h-10 rounded cursor-pointer"
                          />
                          <Input
                            value={formData.branding.primary_color}
                            onChange={(e) => updateBranding('primary_color', e.target.value)}
                            className="flex-1 text-sm"
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label className="text-xs text-muted-foreground">Secondary</Label>
                        <div className="flex items-center gap-2">
                          <input
                            type="color"
                            value={formData.branding.secondary_color}
                            onChange={(e) => updateBranding('secondary_color', e.target.value)}
                            className="w-10 h-10 rounded cursor-pointer"
                          />
                          <Input
                            value={formData.branding.secondary_color}
                            onChange={(e) => updateBranding('secondary_color', e.target.value)}
                            className="flex-1 text-sm"
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label className="text-xs text-muted-foreground">Accent</Label>
                        <div className="flex items-center gap-2">
                          <input
                            type="color"
                            value={formData.branding.accent_color}
                            onChange={(e) => updateBranding('accent_color', e.target.value)}
                            className="w-10 h-10 rounded cursor-pointer"
                          />
                          <Input
                            value={formData.branding.accent_color}
                            onChange={(e) => updateBranding('accent_color', e.target.value)}
                            className="flex-1 text-sm"
                          />
                        </div>
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <Label className="text-xs text-muted-foreground">Presets</Label>
                      <div className="flex flex-wrap gap-2">
                        {COLOR_PRESETS.map((preset) => (
                          <button
                            key={preset.name}
                            onClick={() => applyColorPreset(preset)}
                            className="flex items-center gap-1 px-2 py-1 rounded border hover:bg-gray-50 text-xs"
                            title={preset.name}
                          >
                            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: preset.primary }} />
                            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: preset.secondary }} />
                            <span className="ml-1">{preset.name}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </TabsContent>
                
                {/* Sections Tab */}
                <TabsContent value="sections" className="space-y-4 m-0">
                  <p className="text-sm text-muted-foreground mb-4">
                    Choose which sections to include in your reports
                  </p>
                  
                  {[
                    { key: 'show_call_info', label: 'Call Information', desc: 'Date, duration, participants' },
                    { key: 'show_timestamps', label: 'Timestamps', desc: 'Time markers for transcript segments' },
                    { key: 'show_overview', label: 'Overview', desc: 'Summary of the consultation' },
                    { key: 'show_key_points', label: 'Key Discussion Points', desc: 'Main topics discussed' },
                    { key: 'show_action_items', label: 'Action Items', desc: 'Tasks and follow-ups' },
                    { key: 'show_legal_concerns', label: 'Legal Concerns', desc: 'Legal issues and risks' },
                    { key: 'show_recommendations', label: 'Recommendations', desc: 'Advice and suggestions' },
                    { key: 'show_follow_up', label: 'Follow-up Notes', desc: 'Items needing attention' },
                  ].map(({ key, label, desc }) => (
                    <div key={key} className="flex items-center justify-between py-2 border-b">
                      <div>
                        <Label className="font-medium">{label}</Label>
                        <p className="text-xs text-muted-foreground">{desc}</p>
                      </div>
                      <Switch
                        checked={formData.sections[key]}
                        onCheckedChange={(v) => updateSection(key, v)}
                      />
                    </div>
                  ))}
                </TabsContent>
                
                {/* Content Tab */}
                <TabsContent value="content" className="space-y-4 m-0">
                  <div className="space-y-2">
                    <Label>Header Text</Label>
                    <Input
                      placeholder="Text to display in the report header"
                      value={formData.header_text}
                      onChange={(e) => setFormData({ ...formData, header_text: e.target.value })}
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Introduction Message</Label>
                    <Textarea
                      placeholder="A personalized message to include at the beginning of reports..."
                      value={formData.intro_message}
                      onChange={(e) => setFormData({ ...formData, intro_message: e.target.value })}
                      className="min-h-[80px]"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Footer Text</Label>
                    <Input
                      placeholder="Text to display at the bottom of each page"
                      value={formData.footer_text}
                      onChange={(e) => setFormData({ ...formData, footer_text: e.target.value })}
                    />
                  </div>
                </TabsContent>
                
                {/* Settings Tab */}
                <TabsContent value="settings" className="space-y-4 m-0">
                  <div className="space-y-2">
                    <Label>Confidentiality Notice</Label>
                    <Textarea
                      placeholder="Custom confidentiality notice for the report..."
                      value={formData.confidentiality_notice}
                      onChange={(e) => setFormData({ ...formData, confidentiality_notice: e.target.value })}
                      className="min-h-[100px]"
                    />
                    <p className="text-xs text-muted-foreground">
                      Leave blank to use default confidentiality notice
                    </p>
                  </div>
                  
                  <div className="flex items-center justify-between py-4 border-t">
                    <div>
                      <Label className="font-medium">Set as Default</Label>
                      <p className="text-xs text-muted-foreground">
                        Use this template for all new scheduled reports
                      </p>
                    </div>
                    <Switch
                      checked={formData.is_default}
                      onCheckedChange={(v) => setFormData({ ...formData, is_default: v })}
                    />
                  </div>
                </TabsContent>
              </ScrollArea>
            </Tabs>
            
            <DialogFooter className="mt-4">
              <Button variant="outline" onClick={closeDialog} disabled={saving}>
                Cancel
              </Button>
              <Button onClick={handleSave} disabled={saving} data-testid="save-template-btn">
                {saving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  editingTemplate ? 'Update Template' : 'Create Template'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  );
}
