import React, { useState } from 'react';
import { Search, Shield, AlertTriangle, AlertCircle, CheckCircle, User, BadgeAlert, Loader2, X, ExternalLink } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from './ui/dialog';
import { Progress } from './ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { ScrollArea } from './ui/scroll-area';
import { accountabilityAPI } from '../lib/api';
import { toast } from 'sonner';

const US_STATES = [
  "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
  "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
  "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
  "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
  "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
];

const WARNING_COLORS = {
  low: { bg: 'bg-green-500/10', border: 'border-green-500/20', text: 'text-green-600', icon: CheckCircle },
  medium: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/20', text: 'text-yellow-600', icon: AlertCircle },
  elevated: { bg: 'bg-orange-500/10', border: 'border-orange-500/20', text: 'text-orange-600', icon: AlertTriangle },
  high: { bg: 'bg-red-500/10', border: 'border-red-500/20', text: 'text-red-600', icon: AlertTriangle }
};

export function QuickOfficerLookup({ variant = 'button', className = '', onOfficerFound = null }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [badge, setBadge] = useState('');
  const [state, setState] = useState('');
  const [results, setResults] = useState(null);
  const [searched, setSearched] = useState(false);

  const handleSearch = async () => {
    if (!badge.trim()) {
      toast.error('Please enter a badge number');
      return;
    }

    setLoading(true);
    setSearched(true);
    try {
      const response = await accountabilityAPI.quickLookup(badge.trim(), state || null);
      setResults(response.data);
      
      if (response.data.found && onOfficerFound) {
        onOfficerFound(response.data.officers[0]);
      }
    } catch (error) {
      console.error('Lookup failed:', error);
      toast.error('Failed to look up officer');
      setResults({ found: false, officers: [] });
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setBadge('');
    setState('');
    setResults(null);
    setSearched(false);
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-500';
    if (score >= 60) return 'text-yellow-500';
    if (score >= 40) return 'text-orange-500';
    return 'text-red-500';
  };

  const LookupContent = () => (
    <div className="space-y-4">
      {/* Search Form */}
      <div className="flex gap-2">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Enter badge number..."
            value={badge}
            onChange={(e) => setBadge(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            className="pl-10"
            data-testid="badge-lookup-input"
          />
        </div>
        <Select value={state} onValueChange={setState}>
          <SelectTrigger className="w-[100px]">
            <SelectValue placeholder="State" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Any</SelectItem>
            {US_STATES.map(s => (
              <SelectItem key={s} value={s}>{s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button 
          onClick={handleSearch} 
          disabled={loading}
          data-testid="lookup-search-btn"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Search'}
        </Button>
      </div>

      {/* Results */}
      {searched && (
        <div className="space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          ) : !results?.found ? (
            <Card className="bg-muted/50">
              <CardContent className="py-8 text-center">
                <User className="w-12 h-12 mx-auto text-muted-foreground mb-3" />
                <p className="font-medium">No officer found</p>
                <p className="text-sm text-muted-foreground">
                  Badge #{badge} {state && `in ${state}`} not in our database
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  This may be a new officer or one not yet reported
                </p>
              </CardContent>
            </Card>
          ) : (
            <ScrollArea className="max-h-[400px]">
              <div className="space-y-4">
                {results.officers.map((officer) => {
                  const warning = WARNING_COLORS[officer.warning_level?.level] || WARNING_COLORS.low;
                  const WarningIcon = warning.icon;
                  
                  return (
                    <Card 
                      key={officer.officer_id} 
                      className={`${warning.bg} ${warning.border} border-2`}
                      data-testid="officer-result-card"
                    >
                      <CardHeader className="pb-2">
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-3">
                            <div className={`w-12 h-12 rounded-full ${warning.bg} flex items-center justify-center`}>
                              <WarningIcon className={`w-6 h-6 ${warning.text}`} />
                            </div>
                            <div>
                              <CardTitle className="text-lg">{officer.full_name}</CardTitle>
                              <CardDescription>
                                Badge #{officer.badge_number} • {officer.rank}
                              </CardDescription>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className={`text-2xl font-bold ${getScoreColor(officer.accountability_score)}`}>
                              {officer.accountability_score}
                            </p>
                            <p className="text-xs text-muted-foreground">Score</p>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {/* Warning Message */}
                        <div className={`p-3 rounded-lg ${warning.bg}`}>
                          <p className={`text-sm font-medium ${warning.text}`}>
                            {officer.warning_level?.message}
                          </p>
                        </div>

                        {/* Department */}
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">Department:</span>
                          <span className="font-medium">{officer.department_name}</span>
                        </div>

                        {/* Accountability Score Bar */}
                        <div>
                          <div className="flex items-center justify-between text-sm mb-1">
                            <span className="text-muted-foreground">Accountability</span>
                            <span className={getScoreColor(officer.accountability_score)}>
                              {officer.accountability_score}/100
                            </span>
                          </div>
                          <Progress 
                            value={officer.accountability_score} 
                            className="h-2"
                          />
                        </div>

                        {/* Violation Stats */}
                        <div className="grid grid-cols-3 gap-2">
                          <div className="text-center p-2 rounded-lg bg-background">
                            <p className="text-lg font-bold text-red-500">{officer.total_violations}</p>
                            <p className="text-xs text-muted-foreground">Total</p>
                          </div>
                          <div className="text-center p-2 rounded-lg bg-background">
                            <p className="text-lg font-bold text-orange-500">{officer.sustained_violations}</p>
                            <p className="text-xs text-muted-foreground">Sustained</p>
                          </div>
                          <div className="text-center p-2 rounded-lg bg-background">
                            <p className="text-lg font-bold text-yellow-500">{officer.pending_violations}</p>
                            <p className="text-xs text-muted-foreground">Pending</p>
                          </div>
                        </div>

                        {/* Recent Violations */}
                        {officer.recent_violations?.length > 0 && (
                          <div>
                            <p className="text-sm font-medium mb-2">Recent Violations:</p>
                            <div className="space-y-1">
                              {officer.recent_violations.slice(0, 3).map((v, idx) => (
                                <div key={idx} className="flex items-center justify-between text-xs bg-background rounded p-2">
                                  <Badge variant={v.outcome === 'sustained' ? 'destructive' : 'secondary'} className="text-xs">
                                    {v.violation_type?.replace(/_/g, ' ')}
                                  </Badge>
                                  <span className="text-muted-foreground">{v.incident_date}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Action Buttons */}
                        <div className="flex gap-2 pt-2">
                          <Button 
                            variant="outline" 
                            size="sm" 
                            className="flex-1"
                            onClick={() => window.open(`/accountability?officer=${officer.officer_id}`, '_blank')}
                          >
                            <ExternalLink className="w-3 h-3 mr-1" />
                            Full Profile
                          </Button>
                          <Button 
                            variant="destructive" 
                            size="sm" 
                            className="flex-1"
                            onClick={() => {
                              toast.info('Start recording to document this encounter');
                            }}
                          >
                            <BadgeAlert className="w-3 h-3 mr-1" />
                            Start Recording
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </ScrollArea>
          )}

          {/* Clear Results Button */}
          {searched && (
            <Button variant="ghost" size="sm" onClick={handleClear} className="w-full">
              <X className="w-4 h-4 mr-1" />
              Clear & Search Again
            </Button>
          )}
        </div>
      )}

      {/* Info Notice */}
      {!searched && (
        <Card className="bg-blue-500/10 border-blue-500/20">
          <CardContent className="py-4 flex items-start gap-3">
            <Shield className="w-5 h-5 text-blue-500 mt-0.5" />
            <div className="text-sm text-blue-700 dark:text-blue-400">
              <p className="font-medium">Know Before You Engage</p>
              <p className="text-xs mt-1 opacity-80">
                Look up any officer's accountability record before or during an encounter. 
                All data is from public records and citizen reports.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );

  if (variant === 'inline') {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="w-5 h-5" />
            Quick Officer Lookup
          </CardTitle>
          <CardDescription>
            Check an officer's accountability record by badge number
          </CardDescription>
        </CardHeader>
        <CardContent>
          <LookupContent />
        </CardContent>
      </Card>
    );
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className={className} data-testid="quick-lookup-btn">
          <Search className="w-4 h-4 mr-2" />
          Officer Lookup
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Search className="w-5 h-5" />
            Quick Officer Lookup
          </DialogTitle>
          <DialogDescription>
            Check an officer's accountability record by badge number
          </DialogDescription>
        </DialogHeader>
        <LookupContent />
      </DialogContent>
    </Dialog>
  );
}

export default QuickOfficerLookup;
