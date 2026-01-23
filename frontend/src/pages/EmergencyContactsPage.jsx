import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { Alert, AlertDescription } from '../components/ui/alert';
import { 
  Users, Plus, Phone, Mail, Edit2, Trash2, 
  GripVertical, AlertTriangle, Shield, Bell, 
  Heart, Scale, UserPlus, Send, CheckCircle, Loader2
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../lib/api';

const relationshipOptions = [
  { value: 'family', label: 'Family Member', icon: Heart },
  { value: 'friend', label: 'Friend', icon: Users },
  { value: 'attorney', label: 'Attorney', icon: Scale },
  { value: 'other', label: 'Other', icon: UserPlus },
];

const relationshipColors = {
  family: 'bg-pink-500/20 text-pink-400 border-pink-500/30',
  friend: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  attorney: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  other: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
};

export default function EmergencyContactsPage() {
  const navigate = useNavigate();
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [editingContact, setEditingContact] = useState(null);
  const [saving, setSaving] = useState(false);
  const [testingContact, setTestingContact] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    relationship: 'family',
    phone: '',
    email: '',
    notify_on_encounter: true,
    notify_on_sos: true,
    notify_on_dead_mans_switch: true,
    priority: 1
  });

  useEffect(() => {
    fetchContacts();
  }, []);

  const fetchContacts = async () => {
    try {
      const response = await api.get('/emergency-contacts');
      setContacts(response.data.contacts || []);
    } catch (error) {
      toast.error('Failed to load emergency contacts');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      relationship: 'family',
      phone: '',
      email: '',
      notify_on_encounter: true,
      notify_on_sos: true,
      notify_on_dead_mans_switch: true,
      priority: contacts.length + 1
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      toast.error('Name is required');
      return;
    }
    
    if (!formData.phone && !formData.email) {
      toast.error('At least phone or email is required');
      return;
    }

    setSaving(true);

    try {
      if (editingContact) {
        // Update existing contact
        await api.put(`/emergency-contacts/${editingContact.contact_id}`, formData);
        toast.success('Contact updated successfully');
      } else {
        // Create new contact
        await api.post('/emergency-contacts', formData);
        toast.success('Contact added successfully');
      }
      
      setShowAddDialog(false);
      setEditingContact(null);
      resetForm();
      fetchContacts();
    } catch (error) {
      if (error.response?.status === 400) {
        toast.error(error.response.data.detail || 'Maximum 10 contacts allowed');
      } else {
        toast.error('Failed to save contact');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (contact) => {
    setEditingContact(contact);
    setFormData({
      name: contact.name,
      relationship: contact.relationship,
      phone: contact.phone || '',
      email: contact.email || '',
      notify_on_encounter: contact.notify_on_encounter,
      notify_on_sos: contact.notify_on_sos,
      notify_on_dead_mans_switch: contact.notify_on_dead_mans_switch,
      priority: contact.priority
    });
    setShowAddDialog(true);
  };

  const handleDelete = async (contactId) => {
    if (!window.confirm('Are you sure you want to remove this emergency contact?')) {
      return;
    }

    try {
      await api.delete(`/emergency-contacts/${contactId}`);
      toast.success('Contact removed');
      fetchContacts();
    } catch (error) {
      toast.error('Failed to remove contact');
    }
  };

  const handleTest = async (contact) => {
    setTestingContact(contact.contact_id);
    
    try {
      await api.post(`/emergency-contacts/${contact.contact_id}/test`);
      toast.success(`Test alert sent to ${contact.name}`);
    } catch (error) {
      toast.error('Failed to send test alert');
    } finally {
      setTestingContact(null);
    }
  };

  const handleToggleActive = async (contact) => {
    try {
      await api.put(`/emergency-contacts/${contact.contact_id}`, {
        active: !contact.active
      });
      fetchContacts();
      toast.success(contact.active ? 'Contact deactivated' : 'Contact activated');
    } catch (error) {
      toast.error('Failed to update contact');
    }
  };

  const RelationshipIcon = ({ relationship }) => {
    const option = relationshipOptions.find(o => o.value === relationship);
    const Icon = option?.icon || Users;
    return <Icon className="h-4 w-4" />;
  };

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-6" data-testid="emergency-contacts-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Users className="h-6 w-6 text-red-500" />
              Emergency Contacts
            </h1>
            <p className="text-muted-foreground mt-1">
              People who will be notified during emergencies
            </p>
          </div>
          
          <Dialog open={showAddDialog} onOpenChange={(open) => {
            setShowAddDialog(open);
            if (!open) {
              setEditingContact(null);
              resetForm();
            }
          }}>
            <DialogTrigger asChild>
              <Button data-testid="add-contact-btn">
                <Plus className="h-4 w-4 mr-2" />
                Add Contact
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>
                  {editingContact ? 'Edit Emergency Contact' : 'Add Emergency Contact'}
                </DialogTitle>
                <DialogDescription>
                  This contact will be notified during emergencies based on your preferences.
                </DialogDescription>
              </DialogHeader>
              
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Name *</Label>
                  <Input
                    id="name"
                    placeholder="Contact name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    data-testid="contact-name-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="relationship">Relationship</Label>
                  <Select
                    value={formData.relationship}
                    onValueChange={(value) => setFormData({ ...formData, relationship: value })}
                  >
                    <SelectTrigger data-testid="relationship-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {relationshipOptions.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          <div className="flex items-center gap-2">
                            <opt.icon className="h-4 w-4" />
                            {opt.label}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="phone">Phone</Label>
                    <Input
                      id="phone"
                      type="tel"
                      placeholder="+1 (555) 123-4567"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      data-testid="contact-phone-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="email@example.com"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      data-testid="contact-email-input"
                    />
                  </div>
                </div>

                <div className="space-y-3 pt-2 border-t">
                  <Label className="text-sm text-muted-foreground">Notification Preferences</Label>
                  
                  <div className="flex items-center justify-between">
                    <Label htmlFor="notify_encounter" className="text-sm flex items-center gap-2">
                      <Shield className="h-4 w-4 text-blue-400" />
                      Notify on Encounter Start
                    </Label>
                    <Switch
                      id="notify_encounter"
                      checked={formData.notify_on_encounter}
                      onCheckedChange={(checked) => setFormData({ ...formData, notify_on_encounter: checked })}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <Label htmlFor="notify_sos" className="text-sm flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-red-400" />
                      Notify on SOS Alert
                    </Label>
                    <Switch
                      id="notify_sos"
                      checked={formData.notify_on_sos}
                      onCheckedChange={(checked) => setFormData({ ...formData, notify_on_sos: checked })}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <Label htmlFor="notify_switch" className="text-sm flex items-center gap-2">
                      <Bell className="h-4 w-4 text-orange-400" />
                      Notify on Dead Man's Switch
                    </Label>
                    <Switch
                      id="notify_switch"
                      checked={formData.notify_on_dead_mans_switch}
                      onCheckedChange={(checked) => setFormData({ ...formData, notify_on_dead_mans_switch: checked })}
                    />
                  </div>
                </div>

                <DialogFooter>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setShowAddDialog(false);
                      setEditingContact(null);
                      resetForm();
                    }}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" disabled={saving} data-testid="save-contact-btn">
                    {saving ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      editingContact ? 'Update Contact' : 'Add Contact'
                    )}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Info Alert */}
        <Alert className="border-blue-500/50 bg-blue-500/10">
          <Shield className="h-4 w-4 text-blue-500" />
          <AlertDescription className="text-sm">
            Emergency contacts will receive alerts via in-app notifications (if they're JUSTICE users) 
            and email/SMS (coming soon). You can add up to 10 contacts.
          </AlertDescription>
        </Alert>

        {/* Contacts List */}
        {loading ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-muted-foreground" />
              <p className="text-muted-foreground mt-2">Loading contacts...</p>
            </CardContent>
          </Card>
        ) : contacts.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Users className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
              <h3 className="text-lg font-medium mb-2">No Emergency Contacts</h3>
              <p className="text-muted-foreground mb-4">
                Add trusted contacts who will be notified during emergencies.
              </p>
              <Button onClick={() => setShowAddDialog(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Your First Contact
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {contacts.map((contact, index) => (
              <Card 
                key={contact.contact_id}
                className={`transition-all ${!contact.active ? 'opacity-60' : ''}`}
                data-testid={`contact-card-${contact.contact_id}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-start gap-4">
                    {/* Priority indicator */}
                    <div className="flex flex-col items-center gap-1">
                      <GripVertical className="h-5 w-5 text-muted-foreground/50 cursor-grab" />
                      <Badge variant="outline" className="text-xs">
                        #{contact.priority}
                      </Badge>
                    </div>

                    {/* Contact info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium truncate">{contact.name}</h3>
                        <Badge 
                          variant="outline" 
                          className={relationshipColors[contact.relationship]}
                        >
                          <RelationshipIcon relationship={contact.relationship} />
                          <span className="ml-1 capitalize">{contact.relationship}</span>
                        </Badge>
                        {contact.contact_user_id && (
                          <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            JUSTICE User
                          </Badge>
                        )}
                        {!contact.active && (
                          <Badge variant="secondary">Inactive</Badge>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                        {contact.phone && (
                          <span className="flex items-center gap-1">
                            <Phone className="h-3 w-3" />
                            {contact.phone}
                          </span>
                        )}
                        {contact.email && (
                          <span className="flex items-center gap-1">
                            <Mail className="h-3 w-3" />
                            {contact.email}
                          </span>
                        )}
                      </div>

                      {/* Notification badges */}
                      <div className="flex flex-wrap gap-2 mt-2">
                        {contact.notify_on_encounter && (
                          <Badge variant="outline" className="text-xs bg-blue-500/10 border-blue-500/30">
                            <Shield className="h-3 w-3 mr-1" />
                            Encounters
                          </Badge>
                        )}
                        {contact.notify_on_sos && (
                          <Badge variant="outline" className="text-xs bg-red-500/10 border-red-500/30">
                            <AlertTriangle className="h-3 w-3 mr-1" />
                            SOS
                          </Badge>
                        )}
                        {contact.notify_on_dead_mans_switch && (
                          <Badge variant="outline" className="text-xs bg-orange-500/10 border-orange-500/30">
                            <Bell className="h-3 w-3 mr-1" />
                            Dead Man's Switch
                          </Badge>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleTest(contact)}
                        disabled={testingContact === contact.contact_id}
                        data-testid={`test-contact-${contact.contact_id}`}
                      >
                        {testingContact === contact.contact_id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Send className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEdit(contact)}
                        data-testid={`edit-contact-${contact.contact_id}`}
                      >
                        <Edit2 className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDelete(contact.contact_id)}
                        className="text-red-500 hover:text-red-400 hover:border-red-500"
                        data-testid={`delete-contact-${contact.contact_id}`}
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

        {/* Usage Info */}
        <Card className="bg-muted/30">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">How Emergency Contacts Work</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <p>
              <strong className="text-blue-400">Encounter Alerts:</strong> Contacts are notified when you start recording a police encounter.
            </p>
            <p>
              <strong className="text-red-400">SOS Alerts:</strong> Immediate notification when you trigger the SOS button.
            </p>
            <p>
              <strong className="text-orange-400">Dead Man's Switch:</strong> If you become unresponsive during an encounter, contacts are automatically alerted.
            </p>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}
