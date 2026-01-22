import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '../components/ui/dialog';
import { attorneyCollabAPI, encounterAPI, API_URL } from '../lib/api';
import { toast } from 'sonner';
import { useAuth } from '../contexts/AuthContext';
import { 
  FileText, MessageCircle, Clock, MapPin, 
  AlertTriangle, Shield, Play, Pause,
  StickyNote, Send, Trash2, Edit, Plus,
  ArrowLeft, Download, Eye, Video, Mic,
  CheckCircle, XCircle
} from 'lucide-react';

export default function AttorneyEncounterWorkspacePage() {
  const { encounterId } = useParams();
  const { user } = useAuth();
  
  const [encounter, setEncounter] = useState(null);
  const [notes, setNotes] = useState([]);
  const [messages, setMessages] = useState([]);
  const [highlights, setHighlights] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Note editing
  const [showNoteDialog, setShowNoteDialog] = useState(false);
  const [editingNote, setEditingNote] = useState(null);
  const [noteForm, setNoteForm] = useState({ content: '', noteType: 'general' });
  
  // Messaging
  const [messageInput, setMessageInput] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchAllData();
  }, [encounterId]);

  useEffect(() => {
    // Scroll to bottom when messages change
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      // Fetch encounter details, notes, and messages in parallel
      const [encounterRes, notesRes, highlightsRes] = await Promise.all([
        attorneyCollabAPI.getEncounters(),
        attorneyCollabAPI.getNotes(encounterId),
        encounterAPI.getHighlights(encounterId).catch(() => ({ data: { highlights: [] } }))
      ]);

      // Find the specific encounter
      const enc = encounterRes.data.encounters?.find(e => e.encounter_id === encounterId);
      if (enc) {
        setEncounter(enc);
        // Fetch messages with this client
        const msgRes = await attorneyCollabAPI.getMessages(enc.client_id, encounterId);
        setMessages(msgRes.data.messages || []);
      }
      
      setNotes(notesRes.data.notes || []);
      setHighlights(highlightsRes.data.highlights || []);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load encounter data');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveNote = async () => {
    if (!noteForm.content.trim()) {
      toast.error('Note content is required');
      return;
    }

    try {
      if (editingNote) {
        await attorneyCollabAPI.updateNote(editingNote.note_id, noteForm.content, noteForm.noteType);
        toast.success('Note updated');
      } else {
        await attorneyCollabAPI.createNote(encounterId, noteForm.content, noteForm.noteType);
        toast.success('Note created');
      }
      
      setShowNoteDialog(false);
      setEditingNote(null);
      setNoteForm({ content: '', noteType: 'general' });
      
      // Refresh notes
      const res = await attorneyCollabAPI.getNotes(encounterId);
      setNotes(res.data.notes || []);
    } catch (error) {
      toast.error('Failed to save note');
    }
  };

  const handleDeleteNote = async (noteId) => {
    if (!window.confirm('Delete this note?')) return;
    
    try {
      await attorneyCollabAPI.deleteNote(noteId);
      toast.success('Note deleted');
      setNotes(notes.filter(n => n.note_id !== noteId));
    } catch (error) {
      toast.error('Failed to delete note');
    }
  };

  const handleSendMessage = async () => {
    if (!messageInput.trim() || !encounter) return;
    
    setSendingMessage(true);
    try {
      await attorneyCollabAPI.sendMessage(
        encounter.client_id,
        messageInput,
        encounterId
      );
      
      setMessageInput('');
      
      // Refresh messages
      const res = await attorneyCollabAPI.getMessages(encounter.client_id, encounterId);
      setMessages(res.data.messages || []);
    } catch (error) {
      toast.error('Failed to send message');
    } finally {
      setSendingMessage(false);
    }
  };

  const openEditNote = (note) => {
    setEditingNote(note);
    setNoteForm({ content: note.content, noteType: note.note_type });
    setShowNoteDialog(true);
  };

  const openNewNote = () => {
    setEditingNote(null);
    setNoteForm({ content: '', noteType: 'general' });
    setShowNoteDialog(true);
  };

  const getNoteTypeColor = (type) => {
    const colors = {
      general: 'bg-gray-100 text-gray-800',
      legal_analysis: 'bg-blue-100 text-blue-800',
      strategy: 'bg-purple-100 text-purple-800',
      evidence_review: 'bg-green-100 text-green-800'
    };
    return colors[type] || colors.general;
  };

  const getSeverityColor = (severity) => {
    const colors = {
      critical: 'bg-red-100 text-red-800 border-red-300',
      high: 'bg-orange-100 text-orange-800 border-orange-300',
      medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      low: 'bg-blue-100 text-blue-800 border-blue-300'
    };
    return colors[severity] || colors.medium;
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </AppLayout>
    );
  }

  if (!encounter) {
    return (
      <AppLayout>
        <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
          <AlertTriangle className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-2xl font-bold">Encounter Not Found</h2>
          <p className="text-muted-foreground">
            You may not have access to this encounter.
          </p>
          <Link to="/attorney-dashboard">
            <Button>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Button>
          </Link>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="attorney-workspace">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <Link to="/attorney-dashboard">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="h-5 w-5" />
              </Button>
            </Link>
            <div>
              <h1 className="font-serif text-2xl font-bold">Encounter Workspace</h1>
              <p className="text-muted-foreground">
                Client: {encounter.client_name} • {encounter.encounter_type?.replace(/_/g, ' ')}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={encounter.status === 'active' ? 'default' : 'secondary'}>
              {encounter.status}
            </Badge>
            <Link to={`/encounters/${encounterId}`}>
              <Button variant="outline" size="sm">
                <Eye className="h-4 w-4 mr-2" />
                View Full Report
              </Button>
            </Link>
          </div>
        </div>

        {/* Encounter Info Card */}
        <Card>
          <CardContent className="p-6">
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="flex items-center gap-3">
                <MapPin className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground">Location</p>
                  <p className="text-sm font-medium">{encounter.address || 'Unknown'}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Clock className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground">Started</p>
                  <p className="text-sm font-medium">{new Date(encounter.started_at).toLocaleString()}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-5 w-5 text-yellow-500" />
                <div>
                  <p className="text-xs text-muted-foreground">Evidence Highlights</p>
                  <p className="text-sm font-medium">{encounter.highlights_count || 0} items</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Shield className="h-5 w-5 text-blue-500" />
                <div>
                  <p className="text-xs text-muted-foreground">Access Granted</p>
                  <p className="text-sm font-medium">{new Date(encounter.access_granted_at).toLocaleDateString()}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Main Content Tabs */}
        <Tabs defaultValue="highlights" className="space-y-4">
          <TabsList>
            <TabsTrigger value="highlights" data-testid="tab-highlights">
              <AlertTriangle className="h-4 w-4 mr-2" />
              Highlights ({highlights.length})
            </TabsTrigger>
            <TabsTrigger value="notes" data-testid="tab-notes">
              <StickyNote className="h-4 w-4 mr-2" />
              Case Notes ({notes.length})
            </TabsTrigger>
            <TabsTrigger value="messages" data-testid="tab-messages">
              <MessageCircle className="h-4 w-4 mr-2" />
              Messages ({messages.length})
            </TabsTrigger>
          </TabsList>

          {/* Highlights Tab */}
          <TabsContent value="highlights">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5" />
                  AI-Generated Evidence Highlights
                </CardTitle>
                <CardDescription>
                  Key moments and potential violations detected by AI analysis
                </CardDescription>
              </CardHeader>
              <CardContent>
                {highlights.length > 0 ? (
                  <div className="space-y-4">
                    {highlights.map((highlight, index) => (
                      <div 
                        key={highlight.highlight_id || index}
                        className={`p-4 rounded-lg border ${getSeverityColor(highlight.severity)}`}
                        data-testid={`highlight-${index}`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline">{highlight.category}</Badge>
                            <Badge className={getSeverityColor(highlight.severity)}>
                              {highlight.severity}
                            </Badge>
                          </div>
                          {highlight.timestamp && (
                            <span className="text-xs text-muted-foreground">
                              @ {Math.floor(highlight.timestamp / 60)}:{String(Math.floor(highlight.timestamp % 60)).padStart(2, '0')}
                            </span>
                          )}
                        </div>
                        <p className="mt-2 font-medium">{highlight.title}</p>
                        <p className="text-sm text-muted-foreground mt-1">{highlight.description}</p>
                        {highlight.legal_relevance && (
                          <p className="text-xs mt-2 italic text-muted-foreground">
                            Legal relevance: {highlight.legal_relevance}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No highlights have been generated yet.</p>
                    <p className="text-sm">Highlights are auto-generated after the encounter ends.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Notes Tab */}
          <TabsContent value="notes">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <StickyNote className="h-5 w-5" />
                    Case Notes
                  </CardTitle>
                  <CardDescription>
                    Your private notes and analysis for this encounter
                  </CardDescription>
                </div>
                <Button onClick={openNewNote} data-testid="add-note-btn">
                  <Plus className="h-4 w-4 mr-2" />
                  Add Note
                </Button>
              </CardHeader>
              <CardContent>
                {notes.length > 0 ? (
                  <div className="space-y-4">
                    {notes.map((note, index) => (
                      <div 
                        key={note.note_id}
                        className="p-4 rounded-lg border bg-card"
                        data-testid={`note-${index}`}
                      >
                        <div className="flex items-start justify-between">
                          <Badge className={getNoteTypeColor(note.note_type)}>
                            {note.note_type?.replace(/_/g, ' ')}
                          </Badge>
                          <div className="flex items-center gap-2">
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              onClick={() => openEditNote(note)}
                              data-testid={`edit-note-${index}`}
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button 
                              variant="ghost" 
                              size="icon"
                              onClick={() => handleDeleteNote(note.note_id)}
                              data-testid={`delete-note-${index}`}
                            >
                              <Trash2 className="h-4 w-4 text-red-500" />
                            </Button>
                          </div>
                        </div>
                        <p className="mt-3 whitespace-pre-wrap">{note.content}</p>
                        <p className="text-xs text-muted-foreground mt-3">
                          Created: {new Date(note.created_at).toLocaleString()}
                          {note.updated_at !== note.created_at && (
                            <> • Updated: {new Date(note.updated_at).toLocaleString()}</>
                          )}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <StickyNote className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No notes yet.</p>
                    <p className="text-sm">Add notes to document your legal analysis.</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Note Dialog */}
            <Dialog open={showNoteDialog} onOpenChange={setShowNoteDialog}>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>{editingNote ? 'Edit Note' : 'Add New Note'}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label htmlFor="note-type">Note Type</Label>
                    <Select 
                      value={noteForm.noteType} 
                      onValueChange={(v) => setNoteForm({ ...noteForm, noteType: v })}
                    >
                      <SelectTrigger data-testid="note-type-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="general">General</SelectItem>
                        <SelectItem value="legal_analysis">Legal Analysis</SelectItem>
                        <SelectItem value="strategy">Strategy</SelectItem>
                        <SelectItem value="evidence_review">Evidence Review</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="note-content">Content</Label>
                    <Textarea
                      id="note-content"
                      value={noteForm.content}
                      onChange={(e) => setNoteForm({ ...noteForm, content: e.target.value })}
                      placeholder="Enter your notes..."
                      rows={6}
                      data-testid="note-content-input"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowNoteDialog(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleSaveNote} data-testid="save-note-btn">
                    {editingNote ? 'Update Note' : 'Save Note'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </TabsContent>

          {/* Messages Tab */}
          <TabsContent value="messages">
            <Card className="flex flex-col h-[500px]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageCircle className="h-5 w-5" />
                  Client Communication
                </CardTitle>
                <CardDescription>
                  Secure messaging with {encounter.client_name}
                </CardDescription>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col">
                {/* Messages List */}
                <ScrollArea className="flex-1 pr-4 mb-4">
                  {messages.length > 0 ? (
                    <div className="space-y-4">
                      {messages.map((msg, index) => {
                        const isOwnMessage = msg.sender_id === user?.user_id;
                        return (
                          <div 
                            key={msg.message_id || index}
                            className={`flex ${isOwnMessage ? 'justify-end' : 'justify-start'}`}
                          >
                            <div className={`max-w-[70%] p-3 rounded-lg ${
                              isOwnMessage 
                                ? 'bg-primary text-primary-foreground' 
                                : 'bg-muted'
                            }`}>
                              <p className="text-sm">{msg.content}</p>
                              <p className={`text-xs mt-1 ${
                                isOwnMessage ? 'text-primary-foreground/70' : 'text-muted-foreground'
                              }`}>
                                {new Date(msg.created_at).toLocaleTimeString()}
                              </p>
                            </div>
                          </div>
                        );
                      })}
                      <div ref={messagesEndRef} />
                    </div>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      <MessageCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>No messages yet.</p>
                      <p className="text-sm">Start a conversation with your client.</p>
                    </div>
                  )}
                </ScrollArea>

                {/* Message Input */}
                <div className="flex items-center gap-2 pt-4 border-t">
                  <Input
                    value={messageInput}
                    onChange={(e) => setMessageInput(e.target.value)}
                    placeholder="Type your message..."
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                    data-testid="message-input"
                  />
                  <Button 
                    onClick={handleSendMessage}
                    disabled={!messageInput.trim() || sendingMessage}
                    data-testid="send-message-btn"
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  );
}
