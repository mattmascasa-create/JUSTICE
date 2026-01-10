import React, { useState, useEffect } from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { attorneysAPI } from '../lib/api';
import { getInitials } from '../lib/utils';
import { 
  Search, MapPin, Star, Award, Clock, Phone, Mail, 
  Scale, Filter, CheckCircle, Siren, MessageCircle
} from 'lucide-react';
import { toast } from 'sonner';

const states = [
  "All States", "California", "New York", "Texas", "Illinois", "Georgia", 
  "Florida", "Pennsylvania", "Ohio", "Michigan", "North Carolina"
];

const specializations = [
  "All Specializations", "Civil Rights", "Police Misconduct", "4th Amendment",
  "Constitutional Law", "1st Amendment", "Excessive Force", "False Arrest",
  "Racial Profiling", "5th Amendment", "14th Amendment"
];

export default function AttorneysPage() {
  const [attorneys, setAttorneys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [stateFilter, setStateFilter] = useState('All States');
  const [specFilter, setSpecFilter] = useState('All Specializations');
  const [emergencyOnly, setEmergencyOnly] = useState(false);
  const [selectedAttorney, setSelectedAttorney] = useState(null);

  useEffect(() => {
    fetchAttorneys();
  }, [stateFilter, specFilter, emergencyOnly]);

  const fetchAttorneys = async () => {
    try {
      const params = {};
      if (stateFilter !== 'All States') params.state = stateFilter;
      if (specFilter !== 'All Specializations') params.specialization = specFilter;
      if (emergencyOnly) params.available_emergency = true;
      
      const response = await attorneysAPI.list(params);
      setAttorneys(response.data);
    } catch (error) {
      toast.error('Failed to load attorneys');
    } finally {
      setLoading(false);
    }
  };

  const filteredAttorneys = attorneys.filter(a =>
    a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.bio?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="attorneys-page">
        {/* Header */}
        <div>
          <h1 className="font-serif text-3xl font-bold">Attorney Directory</h1>
          <p className="text-muted-foreground mt-1">Find verified civil rights attorneys</p>
        </div>

        {/* Filters */}
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search attorneys..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
              data-testid="attorney-search"
            />
          </div>
          <Select value={stateFilter} onValueChange={setStateFilter}>
            <SelectTrigger className="w-full lg:w-48" data-testid="state-filter">
              <MapPin className="h-4 w-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {states.map((state) => (
                <SelectItem key={state} value={state}>{state}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={specFilter} onValueChange={setSpecFilter}>
            <SelectTrigger className="w-full lg:w-56" data-testid="specialization-filter">
              <Scale className="h-4 w-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {specializations.map((spec) => (
                <SelectItem key={spec} value={spec}>{spec}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant={emergencyOnly ? "default" : "outline"}
            onClick={() => setEmergencyOnly(!emergencyOnly)}
            className="whitespace-nowrap"
            data-testid="emergency-filter"
          >
            <Siren className="h-4 w-4 mr-2" />
            Emergency Available
          </Button>
        </div>

        {/* Results Count */}
        <p className="text-sm text-muted-foreground">
          Showing {filteredAttorneys.length} attorneys
        </p>

        {/* Attorney Grid */}
        {filteredAttorneys.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Scale className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">No attorneys found</h3>
              <p className="text-muted-foreground">Try adjusting your filters</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {filteredAttorneys.map((attorney) => (
              <Card 
                key={attorney.attorney_id} 
                className="hover:shadow-md transition-shadow"
                data-testid={`attorney-card-${attorney.attorney_id}`}
              >
                <CardContent className="p-6">
                  <div className="flex items-start gap-4">
                    <Avatar className="h-16 w-16">
                      <AvatarImage src={attorney.picture} alt={attorney.name} />
                      <AvatarFallback className="text-lg bg-primary text-primary-foreground">
                        {getInitials(attorney.name)}
                      </AvatarFallback>
                    </Avatar>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <h3 className="font-serif font-bold text-lg">{attorney.name}</h3>
                          <p className="text-sm text-muted-foreground flex items-center gap-1">
                            <MapPin className="h-3 w-3" />
                            {attorney.state}
                          </p>
                        </div>
                        {attorney.verified && (
                          <Badge className="bg-green-500/10 text-green-500 border-green-500/20">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Verified
                          </Badge>
                        )}
                      </div>

                      <div className="flex flex-wrap gap-2 mt-3">
                        {attorney.specializations?.slice(0, 3).map((spec, i) => (
                          <Badge key={i} variant="secondary" className="text-xs">
                            {spec}
                          </Badge>
                        ))}
                      </div>

                      <div className="grid grid-cols-3 gap-4 mt-4 text-center">
                        <div>
                          <div className="flex items-center justify-center gap-1 text-yellow-500">
                            <Star className="h-4 w-4 fill-current" />
                            <span className="font-bold">{attorney.rating}</span>
                          </div>
                          <p className="text-xs text-muted-foreground">Rating</p>
                        </div>
                        <div>
                          <div className="flex items-center justify-center gap-1 text-green-500">
                            <Award className="h-4 w-4" />
                            <span className="font-bold">{attorney.success_rate}%</span>
                          </div>
                          <p className="text-xs text-muted-foreground">Success</p>
                        </div>
                        <div>
                          <div className="flex items-center justify-center gap-1">
                            <Clock className="h-4 w-4" />
                            <span className="font-bold">{attorney.years_experience}</span>
                          </div>
                          <p className="text-xs text-muted-foreground">Years</p>
                        </div>
                      </div>

                      {attorney.available_for_emergency && (
                        <div className="mt-3 flex items-center gap-2 text-sm text-red-500">
                          <Siren className="h-4 w-4" />
                          <span>Available for emergencies</span>
                        </div>
                      )}

                      <div className="flex gap-2 mt-4">
                        <Dialog>
                          <DialogTrigger asChild>
                            <Button 
                              variant="outline" 
                              size="sm" 
                              className="flex-1"
                              onClick={() => setSelectedAttorney(attorney)}
                            >
                              View Profile
                            </Button>
                          </DialogTrigger>
                          <DialogContent className="max-w-lg">
                            <DialogHeader>
                              <DialogTitle className="font-serif">{attorney.name}</DialogTitle>
                            </DialogHeader>
                            <div className="space-y-4">
                              <div className="flex items-center gap-4">
                                <Avatar className="h-20 w-20">
                                  <AvatarImage src={attorney.picture} alt={attorney.name} />
                                  <AvatarFallback className="text-xl bg-primary text-primary-foreground">
                                    {getInitials(attorney.name)}
                                  </AvatarFallback>
                                </Avatar>
                                <div>
                                  <p className="text-muted-foreground">{attorney.state}</p>
                                  <p className="text-sm">Bar #: {attorney.bar_number}</p>
                                  {attorney.hourly_rate && (
                                    <p className="text-sm font-medium">${attorney.hourly_rate}/hr</p>
                                  )}
                                </div>
                              </div>

                              {attorney.bio && (
                                <p className="text-sm text-muted-foreground">{attorney.bio}</p>
                              )}

                              <div className="flex flex-wrap gap-2">
                                {attorney.specializations?.map((spec, i) => (
                                  <Badge key={i} variant="secondary">{spec}</Badge>
                                ))}
                              </div>

                              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                                <div>
                                  <p className="text-2xl font-bold">{attorney.cases_won}</p>
                                  <p className="text-sm text-muted-foreground">Cases Won</p>
                                </div>
                                <div>
                                  <p className="text-2xl font-bold">{attorney.total_cases}</p>
                                  <p className="text-sm text-muted-foreground">Total Cases</p>
                                </div>
                              </div>

                              <div className="flex gap-2 pt-4">
                                <Button className="flex-1">
                                  <MessageCircle className="h-4 w-4 mr-2" />
                                  Contact
                                </Button>
                                <Button variant="outline">
                                  <Phone className="h-4 w-4 mr-2" />
                                  Call
                                </Button>
                              </div>
                            </div>
                          </DialogContent>
                        </Dialog>
                        <Button size="sm" className="flex-1">
                          <MessageCircle className="h-4 w-4 mr-2" />
                          Contact
                        </Button>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
