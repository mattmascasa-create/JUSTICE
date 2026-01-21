import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { incidentsAPI } from '../lib/api';
import { formatDate, getSeverityColor } from '../lib/utils';
import { 
  Map, Filter, AlertTriangle, TrendingUp, BarChart3, 
  RefreshCw, Layers, ZoomIn, ZoomOut
} from 'lucide-react';
import { toast } from 'sonner';
import 'leaflet/dist/leaflet.css';

// Fix for default marker icons in react-leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom marker icons by severity
const createIcon = (color) => new L.Icon({
  iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const severityIcons = {
  critical: createIcon('red'),
  high: createIcon('orange'),
  medium: createIcon('yellow'),
  low: createIcon('green'),
};

// Map zoom controls component
function ZoomControl() {
  const map = useMap();
  return (
    <div className="absolute bottom-4 right-4 z-[1000] flex flex-col gap-2">
      <Button size="icon" variant="secondary" onClick={() => map.zoomIn()}>
        <ZoomIn className="h-4 w-4" />
      </Button>
      <Button size="icon" variant="secondary" onClick={() => map.zoomOut()}>
        <ZoomOut className="h-4 w-4" />
      </Button>
    </div>
  );
}

const violationTypes = [
  "All Types",
  "4th Amendment - Unlawful Search/Seizure",
  "5th Amendment - Self-Incrimination",
  "1st Amendment - Free Speech",
  "6th Amendment - Right to Counsel",
  "8th Amendment - Excessive Force",
  "14th Amendment - Equal Protection",
  "False Arrest",
  "Racial Profiling",
  "Police Misconduct"
];

const severities = ["All", "critical", "high", "medium", "low"];
const statuses = ["All", "open", "under_review", "resolved", "closed"];

export default function IncidentMapPage() {
  const [incidents, setIncidents] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    violation_type: 'All Types',
    severity: 'All',
    status: 'All'
  });

  useEffect(() => {
    fetchData();
  }, [filters]);

  const fetchData = async () => {
    try {
      const params = {};
      if (filters.violation_type !== 'All Types') params.violation_type = filters.violation_type;
      if (filters.severity !== 'All') params.severity = filters.severity;
      if (filters.status !== 'All') params.status = filters.status;

      const [incidentsRes, statsRes] = await Promise.all([
        incidentsAPI.getForMap(params),
        incidentsAPI.getStats()
      ]);
      setIncidents(incidentsRes.data);
      setStats(statsRes.data);
    } catch (error) {
      toast.error('Failed to load incident data');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  // Calculate center from incidents or default to US center
  const center = incidents.length > 0
    ? [
        incidents.reduce((sum, i) => sum + i.latitude, 0) / incidents.length,
        incidents.reduce((sum, i) => sum + i.longitude, 0) / incidents.length
      ]
    : [39.8283, -98.5795]; // US center

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
      <div className="space-y-6" data-testid="incident-map-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-serif text-3xl font-bold">Incident Map</h1>
            <p className="text-muted-foreground mt-1">Visualize civil rights incidents across the country</p>
          </div>
          <Button variant="outline" onClick={fetchData} data-testid="refresh-map">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid sm:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <Map className="h-8 w-8 text-blue-500" />
                <div>
                  <p className="text-2xl font-bold">{stats.total_incidents || incidents.length}</p>
                  <p className="text-sm text-muted-foreground">Total Incidents</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <AlertTriangle className="h-8 w-8 text-red-500" />
                <div>
                  <p className="text-2xl font-bold">
                    {incidents.filter(i => i.severity === 'critical').length}
                  </p>
                  <p className="text-sm text-muted-foreground">Critical</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <TrendingUp className="h-8 w-8 text-orange-500" />
                <div>
                  <p className="text-2xl font-bold">
                    {incidents.filter(i => i.severity === 'high').length}
                  </p>
                  <p className="text-sm text-muted-foreground">High Severity</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <BarChart3 className="h-8 w-8 text-green-500" />
                <div>
                  <p className="text-2xl font-bold">
                    {incidents.filter(i => i.status === 'resolved').length}
                  </p>
                  <p className="text-sm text-muted-foreground">Resolved</p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Filters */}
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Filters:</span>
              </div>
              <Select value={filters.violation_type} onValueChange={(v) => handleFilterChange('violation_type', v)}>
                <SelectTrigger className="w-full sm:w-64" data-testid="violation-filter">
                  <SelectValue placeholder="Violation Type" />
                </SelectTrigger>
                <SelectContent>
                  {violationTypes.map(type => (
                    <SelectItem key={type} value={type}>{type}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={filters.severity} onValueChange={(v) => handleFilterChange('severity', v)}>
                <SelectTrigger className="w-full sm:w-40" data-testid="severity-filter">
                  <SelectValue placeholder="Severity" />
                </SelectTrigger>
                <SelectContent>
                  {severities.map(s => (
                    <SelectItem key={s} value={s}>{s === 'All' ? 'All Severities' : s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={filters.status} onValueChange={(v) => handleFilterChange('status', v)}>
                <SelectTrigger className="w-full sm:w-40" data-testid="status-filter">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  {statuses.map(s => (
                    <SelectItem key={s} value={s}>{s === 'All' ? 'All Statuses' : s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Map */}
        <Card className="overflow-hidden">
          <div className="h-[500px] relative">
            <MapContainer
              center={center}
              zoom={4}
              style={{ height: '100%', width: '100%' }}
              className="z-0"
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {incidents.map((incident) => (
                <Marker
                  key={incident.case_id}
                  position={[incident.latitude, incident.longitude]}
                  icon={severityIcons[incident.severity] || severityIcons.medium}
                >
                  <Popup>
                    <div className="min-w-[200px]">
                      <h3 className="font-bold text-sm mb-1">{incident.title}</h3>
                      <div className="space-y-1 text-xs">
                        <p className="flex items-center gap-1">
                          <Badge className={getSeverityColor(incident.severity)}>
                            {incident.severity}
                          </Badge>
                        </p>
                        <p><strong>Type:</strong> {incident.violation_type}</p>
                        <p><strong>Date:</strong> {formatDate(incident.incident_date)}</p>
                        <p><strong>Status:</strong> {incident.status}</p>
                        {incident.department && (
                          <p><strong>Dept:</strong> {incident.department}</p>
                        )}
                      </div>
                    </div>
                  </Popup>
                </Marker>
              ))}
              <ZoomControl />
            </MapContainer>

            {/* Legend */}
            <div className="absolute top-4 left-4 z-[1000] bg-background/95 rounded-lg p-3 shadow-lg border">
              <p className="text-xs font-bold mb-2">Severity Legend</p>
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-xs">
                  <div className="w-3 h-3 rounded-full bg-red-500" />
                  <span>Critical</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <div className="w-3 h-3 rounded-full bg-orange-500" />
                  <span>High</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <div className="w-3 h-3 rounded-full bg-yellow-500" />
                  <span>Medium</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <div className="w-3 h-3 rounded-full bg-green-500" />
                  <span>Low</span>
                </div>
              </div>
            </div>
          </div>
        </Card>

        {/* Violation Type Distribution */}
        {stats?.by_violation_type?.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="font-serif">Incidents by Violation Type</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {stats.by_violation_type.slice(0, 9).map((item, index) => (
                  <div key={index} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                    <span className="text-sm truncate">{item.type || 'Unknown'}</span>
                    <Badge variant="secondary">{item.count}</Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </AppLayout>
  );
}
