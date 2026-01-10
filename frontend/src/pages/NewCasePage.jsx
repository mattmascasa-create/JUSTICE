import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Calendar } from '../components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { casesAPI } from '../lib/api';
import { cn } from '../lib/utils';
import { format } from 'date-fns';
import { ArrowLeft, Calendar as CalendarIcon, MapPin, Building, User, BadgeIcon, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

const violationTypes = [
  "4th Amendment - Unlawful Search/Seizure",
  "5th Amendment - Self-Incrimination",
  "1st Amendment - Free Speech",
  "6th Amendment - Right to Counsel",
  "8th Amendment - Excessive Force",
  "14th Amendment - Equal Protection",
  "False Arrest",
  "Racial Profiling",
  "Police Misconduct",
  "Other"
];

export default function NewCasePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [incidentDate, setIncidentDate] = useState(new Date());
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    location: '',
    department: '',
    officer_name: '',
    officer_badge: '',
    violation_type: '',
    severity: 'medium'
  });

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.title || !formData.description || !formData.location || !formData.violation_type) {
      toast.error('Please fill in all required fields');
      return;
    }

    setLoading(true);
    try {
      const response = await casesAPI.create({
        ...formData,
        incident_date: incidentDate.toISOString()
      });
      toast.success('Case created successfully');
      navigate(`/cases/${response.data.case_id}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create case');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout>
      <div className="max-w-3xl mx-auto space-y-6" data-testid="new-case-page">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/cases')} data-testid="back-btn">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="font-serif text-2xl font-bold">Report New Incident</h1>
            <p className="text-muted-foreground">Document a civil rights incident</p>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <Card>
            <CardHeader>
              <CardTitle className="font-serif">Incident Information</CardTitle>
              <CardDescription>
                Provide as much detail as possible. This information is confidential and encrypted.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Title */}
              <div className="space-y-2">
                <Label htmlFor="title">Case Title *</Label>
                <Input
                  id="title"
                  placeholder="Brief description of the incident"
                  value={formData.title}
                  onChange={(e) => handleChange('title', e.target.value)}
                  required
                  data-testid="case-title-input"
                />
              </div>

              {/* Description */}
              <div className="space-y-2">
                <Label htmlFor="description">Detailed Description *</Label>
                <Textarea
                  id="description"
                  placeholder="Describe what happened in detail. Include timeline, actions taken, and any witnesses present."
                  value={formData.description}
                  onChange={(e) => handleChange('description', e.target.value)}
                  className="min-h-[150px]"
                  required
                  data-testid="case-description-input"
                />
              </div>

              {/* Date & Location Row */}
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Incident Date *</Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        className={cn(
                          "w-full justify-start text-left font-normal",
                          !incidentDate && "text-muted-foreground"
                        )}
                        data-testid="date-picker-btn"
                      >
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {incidentDate ? format(incidentDate, "PPP") : "Select date"}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <Calendar
                        mode="single"
                        selected={incidentDate}
                        onSelect={(date) => date && setIncidentDate(date)}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="location">Location *</Label>
                  <div className="relative">
                    <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="location"
                      placeholder="Address or intersection"
                      value={formData.location}
                      onChange={(e) => handleChange('location', e.target.value)}
                      className="pl-10"
                      required
                      data-testid="case-location-input"
                    />
                  </div>
                </div>
              </div>

              {/* Violation & Severity Row */}
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Violation Type *</Label>
                  <Select 
                    value={formData.violation_type} 
                    onValueChange={(value) => handleChange('violation_type', value)}
                  >
                    <SelectTrigger data-testid="violation-type-select">
                      <SelectValue placeholder="Select violation type" />
                    </SelectTrigger>
                    <SelectContent>
                      {violationTypes.map((type) => (
                        <SelectItem key={type} value={type}>{type}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Severity Level</Label>
                  <Select 
                    value={formData.severity} 
                    onValueChange={(value) => handleChange('severity', value)}
                  >
                    <SelectTrigger data-testid="severity-select">
                      <AlertTriangle className="h-4 w-4 mr-2" />
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="critical">Critical</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Officer Information */}
              <div className="border-t border-border pt-6">
                <h3 className="font-medium mb-4">Officer Information (if known)</h3>
                <div className="grid sm:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="department">Department</Label>
                    <div className="relative">
                      <Building className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="department"
                        placeholder="Police department"
                        value={formData.department}
                        onChange={(e) => handleChange('department', e.target.value)}
                        className="pl-10"
                        data-testid="department-input"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="officer_name">Officer Name</Label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="officer_name"
                        placeholder="Officer's name"
                        value={formData.officer_name}
                        onChange={(e) => handleChange('officer_name', e.target.value)}
                        className="pl-10"
                        data-testid="officer-name-input"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="officer_badge">Badge Number</Label>
                    <div className="relative">
                      <BadgeIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="officer_badge"
                        placeholder="Badge #"
                        value={formData.officer_badge}
                        onChange={(e) => handleChange('officer_badge', e.target.value)}
                        className="pl-10"
                        data-testid="badge-input"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Submit */}
              <div className="flex justify-end gap-4 pt-4">
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => navigate('/cases')}
                  data-testid="cancel-btn"
                >
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  disabled={loading}
                  data-testid="submit-case-btn"
                >
                  {loading ? 'Creating...' : 'Create Case'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </form>
      </div>
    </AppLayout>
  );
}
