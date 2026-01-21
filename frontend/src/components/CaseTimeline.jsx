import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { timelineAPI } from '../lib/api';
import { formatDateTime } from '../lib/utils';
import { 
  Clock, FileText, Scale, MessageCircle, User, 
  FolderPlus, Edit, AlertTriangle, CheckCircle,
  Plus, Send
} from 'lucide-react';
import { toast } from 'sonner';

const eventIcons = {
  created: FolderPlus,
  status_change: Edit,
  evidence_added: FileText,
  attorney_assigned: Scale,
  message: MessageCircle,
  note: Edit,
  violation_detected: AlertTriangle,
  resolved: CheckCircle,
};

const eventColors = {
  created: 'bg-blue-500',
  status_change: 'bg-yellow-500',
  evidence_added: 'bg-green-500',
  attorney_assigned: 'bg-purple-500',
  message: 'bg-cyan-500',
  note: 'bg-gray-500',
  violation_detected: 'bg-red-500',
  resolved: 'bg-green-600',
};

export default function CaseTimeline({ caseId }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newNote, setNewNote] = useState('');
  const [addingNote, setAddingNote] = useState(false);

  useEffect(() => {
    fetchTimeline();
  }, [caseId]);

  const fetchTimeline = async () => {
    try {
      const response = await timelineAPI.get(caseId);
      setEvents(response.data);
    } catch (error) {
      console.error('Failed to load timeline:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddNote = async (e) => {
    e.preventDefault();
    if (!newNote.trim()) return;

    setAddingNote(true);
    try {
      await timelineAPI.addEvent(caseId, {
        event_type: 'note',
        description: newNote.trim()
      });
      setNewNote('');
      fetchTimeline();
      toast.success('Note added to timeline');
    } catch (error) {
      toast.error('Failed to add note');
    } finally {
      setAddingNote(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="case-timeline">
      <CardHeader>
        <CardTitle className="font-serif flex items-center gap-2">
          <Clock className="h-5 w-5" />
          Case Timeline
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Add Note Form */}
        <form onSubmit={handleAddNote} className="flex gap-2 mb-6">
          <Input
            placeholder="Add a note to the timeline..."
            value={newNote}
            onChange={(e) => setNewNote(e.target.value)}
            disabled={addingNote}
            data-testid="timeline-note-input"
          />
          <Button type="submit" disabled={addingNote || !newNote.trim()} data-testid="add-note-btn">
            {addingNote ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
          </Button>
        </form>

        {/* Timeline */}
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-border" />

          <div className="space-y-6">
            {events.map((event, index) => {
              const Icon = eventIcons[event.event_type] || Clock;
              const bgColor = eventColors[event.event_type] || 'bg-gray-500';

              return (
                <div key={event.event_id} className="relative flex gap-4 pl-10" data-testid={`timeline-event-${index}`}>
                  {/* Icon */}
                  <div className={`absolute left-0 p-2 rounded-full ${bgColor} text-white z-10`}>
                    <Icon className="h-4 w-4" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 bg-muted/50 rounded-lg p-4">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <p className="font-medium">{event.description}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {formatDateTime(event.created_at)}
                        </p>
                      </div>
                      <Badge variant="secondary" className="text-xs">
                        {event.event_type.replace('_', ' ')}
                      </Badge>
                    </div>

                    {/* Metadata */}
                    {event.metadata && Object.keys(event.metadata).length > 0 && (
                      <div className="mt-2 pt-2 border-t border-border">
                        <div className="flex flex-wrap gap-2">
                          {event.metadata.status && (
                            <Badge variant="outline">Status: {event.metadata.status}</Badge>
                          )}
                          {event.metadata.severity && (
                            <Badge variant="outline">Severity: {event.metadata.severity}</Badge>
                          )}
                          {event.metadata.file_type && (
                            <Badge variant="outline">Type: {event.metadata.file_type}</Badge>
                          )}
                          {event.metadata.blockchain_hash && (
                            <Badge variant="outline" className="font-mono text-xs">
                              ✓ Verified
                            </Badge>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {events.length === 0 && (
            <div className="text-center py-8">
              <Clock className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
              <p className="text-muted-foreground">No events yet</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
