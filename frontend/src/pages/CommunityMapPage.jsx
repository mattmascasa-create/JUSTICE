import React, { useState, useEffect, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { Separator } from '../components/ui/separator';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { Checkbox } from '../components/ui/checkbox';
import api from '../lib/api';
import { 
  MapPin, AlertTriangle, Shield, Filter, Loader2, 
  RefreshCw, BarChart3, TrendingUp, Eye, EyeOff,
  Crosshair, Layers, Info, Plus, ThumbsUp, Send, MessageSquare
} from 'lucide-react';
import { toast } from 'sonner';

// Fix Leaflet default marker icon issue
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Custom marker icons
const createIcon = (color) => new L.Icon({
  iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const icons = {
  traffic_stop: createIcon('red'),
  pedestrian_stop: createIcon('orange'),
  arrest: createIcon('violet'),
  complaint: createIcon('blue'),
  safety_tip: createIcon('green'),
  incident: createIcon('red'),
  concern: createIcon('yellow'),
  positive: createIcon('green'),
  default: createIcon('grey')
};

// Map center updater component
function MapCenterUpdater({ center }) {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.setView(center, map.getZoom());
    }
  }, [center, map]);
  return null;
}

export default function CommunityMapPage() {
  // State
  const [incidents, setIncidents] = useState([]);
  const [hotspots, setHotspots] = useState([]);
  const [communityReports, setCommunityReports] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Map settings
  const [center, setCenter] = useState([39.8283, -98.5795]); // US center
  const [showHotspots, setShowHotspots] = useState(true);
  const [showIncidents, setShowIncidents] = useState(true);
  const [showReports, setShowReports] = useState(true);
  
  // Filters
  const [radiusMiles, setRadiusMiles] = useState(50);
  const [daysFilter, setDaysFilter] = useState(90);
  const [typeFilter, setTypeFilter] = useState('all');
  
  // Report dialog state
  const [reportDialogOpen, setReportDialogOpen] = useState(false);
  const [reportForm, setReportForm] = useState({
    report_type: 'incident',
    description: '',
    address: '',
    anonymous: true,
    contact_email: '',
    useCurrentLocation: false
  });
  const [submittingReport, setSubmittingReport] = useState(false);
  const [userLocation, setUserLocation] = useState(null);

  // Load data
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const [incidentsRes, hotspotsRes, statsRes, reportsRes] = await Promise.all([
        api.get('/community-map/incidents', { 
          params: { 
            radius_miles: radiusMiles, 
            days: daysFilter,
            incident_types: typeFilter !== 'all' ? typeFilter : undefined
          } 
        }),
        api.get('/community-map/hotspots', { params: { days: daysFilter } }),
        api.get('/community-map/statistics'),
        api.get('/community-map/reports', { params: { days: daysFilter } })
      ]);
      
      setIncidents(incidentsRes.data.incidents || []);
      setHotspots(hotspotsRes.data.hotspots || []);
      setStatistics(statsRes.data.statistics || null);
      setCommunityReports(reportsRes.data.reports || []);
      
      // Center map on first incident if available
      if (incidentsRes.data.incidents?.length > 0) {
        const first = incidentsRes.data.incidents[0];
        setCenter([first.lat, first.lon]);
      }
    } catch (err) {
      console.error('Error loading map data:', err);
      setError('Failed to load incident data');
      toast.error('Failed to load map data');
    } finally {
      setLoading(false);
    }
  }, [radiusMiles, daysFilter, typeFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Get user location
  const centerOnUser = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const loc = { lat: pos.coords.latitude, lon: pos.coords.longitude };
          setUserLocation(loc);
          setCenter([loc.lat, loc.lon]);
          toast.success('Centered on your location');
        },
        () => toast.error('Could not get your location')
      );
    }
  };

  // Submit community report
  const handleSubmitReport = async () => {
    if (!reportForm.description || reportForm.description.length < 10) {
      toast.error('Please provide a description (at least 10 characters)');
      return;
    }
    
    setSubmittingReport(true);
    try {
      const params = new URLSearchParams({
        report_type: reportForm.report_type,
        description: reportForm.description,
        anonymous: reportForm.anonymous.toString()
      });
      
      if (reportForm.useCurrentLocation && userLocation) {
        params.append('latitude', userLocation.lat.toString());
        params.append('longitude', userLocation.lon.toString());
      }
      
      if (reportForm.address) {
        params.append('address', reportForm.address);
      }
      
      if (!reportForm.anonymous && reportForm.contact_email) {
        params.append('contact_email', reportForm.contact_email);
      }
      
      await api.post(`/community-map/report?${params.toString()}`);
      toast.success('Report submitted! It will be reviewed before appearing on the map.');
      setReportDialogOpen(false);
      setReportForm({
        report_type: 'incident',
        description: '',
        address: '',
        anonymous: true,
        contact_email: '',
        useCurrentLocation: false
      });
    } catch (err) {
      console.error('Error submitting report:', err);
      toast.error('Failed to submit report');
    } finally {
      setSubmittingReport(false);
    }
  };

  // Vote on a report
  const handleVoteReport = async (reportId) => {
    try {
      await api.post(`/community-map/reports/${reportId}/vote`);
      toast.success('Vote recorded!');
      loadData(); // Refresh to show updated votes
    } catch (err) {
      toast.error('Failed to vote');
    }
  };

  const getIncidentIcon = (type) => {
    return icons[type] || icons.default;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown date';
    return new Date(dateStr).toLocaleDateString();
  };

  const getReportTypeLabel = (type) => {
    const labels = {
      safety_tip: 'Safety Tip',
      incident: 'Incident Report',
      concern: 'Area Concern',
      positive: 'Positive Interaction'
    };
    return labels[type] || type;
  };

  return (
    <div className="min-h-screen bg-background" data-testid="community-map-page">
      {/* Header */}
      <header className="border-b bg-card sticky top-0 z-[1000]">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2">
                <MapPin className="h-6 w-6 text-red-500" />
                Community Incident Map
              </h1>
              <p className="text-sm text-muted-foreground">
                Public transparency portal - All data is anonymized
              </p>
            </div>
            
            <div className="flex items-center gap-4">
              <Dialog open={reportDialogOpen} onOpenChange={setReportDialogOpen}>
                <DialogTrigger asChild>
                  <Button size="sm" className="bg-green-600 hover:bg-green-700" data-testid="submit-report-btn">
                    <Plus className="h-4 w-4 mr-2" />
                    Submit Report
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-md">
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                      <MessageSquare className="h-5 w-5" />
                      Submit Community Report
                    </DialogTitle>
                    <DialogDescription>
                      Share safety tips, report incidents, or flag areas of concern. All reports are reviewed before publication.
                    </DialogDescription>
                  </DialogHeader>
                  
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label>Report Type</Label>
                      <Select value={reportForm.report_type} onValueChange={(v) => setReportForm(p => ({...p, report_type: v}))}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="incident">Incident Report</SelectItem>
                          <SelectItem value="safety_tip">Safety Tip</SelectItem>
                          <SelectItem value="concern">Area Concern</SelectItem>
                          <SelectItem value="positive">Positive Interaction</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Description *</Label>
                      <Textarea 
                        placeholder="Describe the incident, tip, or concern..."
                        value={reportForm.description}
                        onChange={(e) => setReportForm(p => ({...p, description: e.target.value}))}
                        rows={4}
                        maxLength={1000}
                      />
                      <p className="text-xs text-muted-foreground">{reportForm.description.length}/1000 characters</p>
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Location (optional)</Label>
                      <Input 
                        placeholder="Street, City, State"
                        value={reportForm.address}
                        onChange={(e) => setReportForm(p => ({...p, address: e.target.value}))}
                      />
                      <div className="flex items-center gap-2 mt-2">
                        <Checkbox 
                          id="use-location"
                          checked={reportForm.useCurrentLocation}
                          onCheckedChange={(checked) => {
                            setReportForm(p => ({...p, useCurrentLocation: checked}));
                            if (checked && !userLocation) centerOnUser();
                          }}
                        />
                        <Label htmlFor="use-location" className="text-sm font-normal cursor-pointer">
                          Use my current location (slightly randomized for privacy)
                        </Label>
                      </div>
                    </div>
                    
                    <Separator />
                    
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <Checkbox 
                          id="anonymous"
                          checked={reportForm.anonymous}
                          onCheckedChange={(checked) => setReportForm(p => ({...p, anonymous: checked}))}
                        />
                        <Label htmlFor="anonymous" className="text-sm font-normal cursor-pointer">
                          Submit anonymously
                        </Label>
                      </div>
                      
                      {!reportForm.anonymous && (
                        <div className="space-y-2 mt-2">
                          <Label>Contact Email (for follow-up)</Label>
                          <Input 
                            type="email"
                            placeholder="your@email.com"
                            value={reportForm.contact_email}
                            onChange={(e) => setReportForm(p => ({...p, contact_email: e.target.value}))}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setReportDialogOpen(false)}>Cancel</Button>
                    <Button onClick={handleSubmitReport} disabled={submittingReport} data-testid="submit-report-confirm">
                      {submittingReport ? (
                        <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Submitting...</>
                      ) : (
                        <><Send className="h-4 w-4 mr-2" />Submit Report</>
                      )}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
              
              <Button variant="outline" size="sm" onClick={centerOnUser}>
                <Crosshair className="h-4 w-4 mr-2" />
                My Location
              </Button>
              <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-80 border-r bg-card p-4 min-h-[calc(100vh-73px)] overflow-y-auto">
          {/* Statistics */}
          {statistics && (
            <Card className="mb-4">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <BarChart3 className="h-4 w-4" />
                  Statistics
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Total Incidents</span>
                  <span className="font-bold">{statistics.total_incidents}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Encounters</span>
                  <span>{statistics.total_encounters}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Complaints</span>
                  <span>{statistics.total_complaints}</span>
                </div>
                
                {statistics.violation_breakdown?.length > 0 && (
                  <>
                    <Separator className="my-2" />
                    <p className="text-xs font-medium text-muted-foreground">Top Violations</p>
                    {statistics.violation_breakdown.slice(0, 3).map((v, i) => (
                      <div key={i} className="flex justify-between text-xs">
                        <span className="truncate">{v.violation}</span>
                        <Badge variant="secondary" className="text-xs">{v.count}</Badge>
                      </div>
                    ))}
                  </>
                )}
              </CardContent>
            </Card>
          )}

          {/* Filters */}
          <Card className="mb-4">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Filter className="h-4 w-4" />
                Filters
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label className="text-xs">Time Period</Label>
                <Select value={String(daysFilter)} onValueChange={(v) => setDaysFilter(parseInt(v))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="30">Last 30 days</SelectItem>
                    <SelectItem value="90">Last 90 days</SelectItem>
                    <SelectItem value="180">Last 6 months</SelectItem>
                    <SelectItem value="365">Last year</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-xs">Incident Type</Label>
                <Select value={typeFilter} onValueChange={setTypeFilter}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Types</SelectItem>
                    <SelectItem value="traffic_stop">Traffic Stops</SelectItem>
                    <SelectItem value="pedestrian_stop">Pedestrian Stops</SelectItem>
                    <SelectItem value="arrest">Arrests</SelectItem>
                    <SelectItem value="complaint">Complaints</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Separator />

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs">Show Incidents</Label>
                  <Switch checked={showIncidents} onCheckedChange={setShowIncidents} />
                </div>
                <div className="flex items-center justify-between">
                  <Label className="text-xs">Show Hotspots</Label>
                  <Switch checked={showHotspots} onCheckedChange={setShowHotspots} />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Legend */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Layers className="h-4 w-4" />
                Legend
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-red-500 rounded-full" />
                <span>Traffic Stop</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-orange-500 rounded-full" />
                <span>Pedestrian Stop</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-violet-500 rounded-full" />
                <span>Arrest</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-blue-500 rounded-full" />
                <span>Complaint</span>
              </div>
              <Separator className="my-2" />
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 bg-red-500/30 rounded-full border-2 border-red-500" />
                <span>Hotspot (high activity)</span>
              </div>
            </CardContent>
          </Card>

          {/* Info */}
          <div className="mt-4 p-3 bg-muted/50 rounded-lg text-xs text-muted-foreground">
            <Info className="h-4 w-4 inline mr-1" />
            All locations are slightly randomized to protect privacy. This map shows 
            anonymized community data for awareness and transparency.
          </div>
        </aside>

        {/* Map */}
        <main className="flex-1">
          {loading && incidents.length === 0 ? (
            <div className="flex items-center justify-center h-[calc(100vh-73px)]">
              <div className="text-center">
                <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
                <p className="text-muted-foreground">Loading incident data...</p>
              </div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-[calc(100vh-73px)]">
              <div className="text-center">
                <AlertTriangle className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
                <p className="text-muted-foreground">{error}</p>
                <Button onClick={loadData} className="mt-4">Try Again</Button>
              </div>
            </div>
          ) : (
            <MapContainer
              center={center}
              zoom={10}
              style={{ height: 'calc(100vh - 73px)', width: '100%' }}
              className="z-0"
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              
              <MapCenterUpdater center={center} />

              {/* Hotspot circles */}
              {showHotspots && hotspots.map((hotspot, idx) => (
                <Circle
                  key={`hotspot-${idx}`}
                  center={[hotspot.lat, hotspot.lon]}
                  radius={1000 * hotspot.intensity}
                  pathOptions={{
                    color: 'red',
                    fillColor: 'red',
                    fillOpacity: 0.2 + (hotspot.intensity * 0.3)
                  }}
                >
                  <Popup>
                    <div className="text-sm">
                      <p className="font-bold">Hotspot Area</p>
                      <p>{hotspot.incident_count} incidents</p>
                      <p>{hotspot.violation_count} violations</p>
                    </div>
                  </Popup>
                </Circle>
              ))}

              {/* Incident markers */}
              {showIncidents && incidents.map((incident, idx) => (
                <Marker
                  key={`incident-${idx}`}
                  position={[incident.lat, incident.lon]}
                  icon={getIncidentIcon(incident.type)}
                >
                  <Popup>
                    <div className="text-sm min-w-[200px]">
                      <p className="font-bold capitalize mb-1">
                        {incident.type?.replace(/_/g, ' ') || 'Unknown'}
                      </p>
                      <p className="text-muted-foreground text-xs mb-2">
                        {formatDate(incident.date)}
                      </p>
                      {incident.area && (
                        <p className="text-xs mb-2">
                          <MapPin className="h-3 w-3 inline mr-1" />
                          {incident.area}
                        </p>
                      )}
                      {incident.violations?.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs font-medium text-red-600">Violations:</p>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {incident.violations.slice(0, 3).map((v, i) => (
                              <Badge key={i} variant="destructive" className="text-xs">
                                {v}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                      {incident.complaint_status && (
                        <p className="text-xs mt-2">
                          Status: <Badge variant="outline">{incident.complaint_status}</Badge>
                        </p>
                      )}
                    </div>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          )}
        </main>
      </div>
    </div>
  );
}
