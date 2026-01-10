import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { ScrollArea } from '../components/ui/scroll-area';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Badge } from '../components/ui/badge';
import { messagesAPI, attorneysAPI } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import { useWebSocket } from '../contexts/WebSocketContext';
import { cn, formatDateTime, getInitials } from '../lib/utils';
import { Send, MessageCircle, Search, Loader2, Users, CheckCheck } from 'lucide-react';
import { toast } from 'sonner';

export default function MessagesPage() {
  const { user } = useAuth();
  const { sendTyping, notifications } = useWebSocket();
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [sendingMessage, setSendingMessage] = useState(false);
  const [participants, setParticipants] = useState({});
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchConversations();
    fetchAttorneys();
  }, []);

  useEffect(() => {
    // Refresh messages when new notification comes in
    if (notifications.length > 0 && selectedConversation) {
      const lastNotification = notifications[notifications.length - 1];
      if (lastNotification.type === 'new_message' && 
          lastNotification.conversation_id === selectedConversation.conversation_id) {
        fetchMessages(selectedConversation.conversation_id);
      }
    }
  }, [notifications, selectedConversation]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchConversations = async () => {
    try {
      const response = await messagesAPI.getConversations();
      setConversations(response.data);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAttorneys = async () => {
    try {
      const response = await attorneysAPI.list({});
      const map = {};
      response.data.forEach(a => {
        map[a.user_id] = a;
      });
      setParticipants(map);
    } catch (error) {
      console.error('Failed to load attorneys:', error);
    }
  };

  const fetchMessages = async (conversationId) => {
    try {
      const response = await messagesAPI.getMessages(conversationId);
      setMessages(response.data);
    } catch (error) {
      toast.error('Failed to load messages');
    }
  };

  const handleSelectConversation = async (conv) => {
    setSelectedConversation(conv);
    await fetchMessages(conv.conversation_id);
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedConversation) return;

    const recipientId = selectedConversation.participants.find(p => p !== user.user_id);
    
    setSendingMessage(true);
    try {
      await messagesAPI.send({
        recipient_id: recipientId,
        case_id: selectedConversation.case_id,
        content: newMessage.trim()
      });
      setNewMessage('');
      await fetchMessages(selectedConversation.conversation_id);
      await fetchConversations();
    } catch (error) {
      toast.error('Failed to send message');
    } finally {
      setSendingMessage(false);
    }
  };

  const handleTyping = () => {
    if (selectedConversation) {
      const recipientId = selectedConversation.participants.find(p => p !== user.user_id);
      sendTyping(recipientId, selectedConversation.conversation_id);
    }
  };

  const getParticipantName = (participantId) => {
    if (participantId === user.user_id) return 'You';
    const attorney = participants[participantId];
    return attorney?.name || 'Unknown';
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

  return (
    <AppLayout>
      <div className="h-[calc(100vh-8rem)]" data-testid="messages-page">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="font-serif text-3xl font-bold">Messages</h1>
            <p className="text-muted-foreground mt-1">Secure attorney-client communication</p>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-4 h-[calc(100%-4rem)]">
          {/* Conversations List */}
          <Card className="lg:col-span-1 flex flex-col overflow-hidden">
            <CardHeader className="py-3 px-4 border-b">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input placeholder="Search conversations..." className="pl-10" />
              </div>
            </CardHeader>
            <ScrollArea className="flex-1">
              {conversations.length === 0 ? (
                <div className="p-8 text-center">
                  <Users className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                  <p className="text-muted-foreground">No conversations yet</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Start a conversation from the Attorney Directory
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {conversations.map((conv) => {
                    const otherParticipant = conv.participants.find(p => p !== user.user_id);
                    const participantInfo = participants[otherParticipant];
                    
                    return (
                      <div
                        key={conv.conversation_id}
                        onClick={() => handleSelectConversation(conv)}
                        className={cn(
                          "p-4 cursor-pointer hover:bg-muted/50 transition-colors",
                          selectedConversation?.conversation_id === conv.conversation_id && "bg-muted"
                        )}
                      >
                        <div className="flex items-start gap-3">
                          <Avatar>
                            <AvatarImage src={participantInfo?.picture} />
                            <AvatarFallback>{getInitials(participantInfo?.name)}</AvatarFallback>
                          </Avatar>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between">
                              <p className="font-medium truncate">
                                {participantInfo?.name || 'Unknown'}
                              </p>
                              {conv.unread_count > 0 && (
                                <Badge className="bg-primary text-primary-foreground">
                                  {conv.unread_count}
                                </Badge>
                              )}
                            </div>
                            <p className="text-sm text-muted-foreground truncate">
                              {conv.last_message || 'No messages yet'}
                            </p>
                            {conv.last_message_at && (
                              <p className="text-xs text-muted-foreground mt-1">
                                {formatDateTime(conv.last_message_at)}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </ScrollArea>
          </Card>

          {/* Chat Area */}
          <Card className="lg:col-span-2 flex flex-col overflow-hidden">
            {selectedConversation ? (
              <>
                {/* Chat Header */}
                <CardHeader className="py-3 px-4 border-b flex-shrink-0">
                  <div className="flex items-center gap-3">
                    <Avatar>
                      <AvatarImage 
                        src={participants[selectedConversation.participants.find(p => p !== user.user_id)]?.picture} 
                      />
                      <AvatarFallback>
                        {getInitials(getParticipantName(selectedConversation.participants.find(p => p !== user.user_id)))}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <CardTitle className="text-base">
                        {getParticipantName(selectedConversation.participants.find(p => p !== user.user_id))}
                      </CardTitle>
                      {selectedConversation.case_id && (
                        <p className="text-xs text-muted-foreground">Case: {selectedConversation.case_id}</p>
                      )}
                    </div>
                  </div>
                </CardHeader>

                {/* Messages */}
                <ScrollArea className="flex-1 p-4">
                  <div className="space-y-4">
                    {messages.map((msg) => (
                      <div
                        key={msg.message_id}
                        className={cn(
                          "flex",
                          msg.sender_id === user.user_id ? "justify-end" : "justify-start"
                        )}
                      >
                        <div
                          className={cn(
                            "max-w-[75%] rounded-2xl px-4 py-2",
                            msg.sender_id === user.user_id
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted"
                          )}
                        >
                          <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                          <div className="flex items-center justify-end gap-1 mt-1">
                            <span className="text-xs opacity-70">
                              {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                            {msg.sender_id === user.user_id && msg.read && (
                              <CheckCheck className="h-3 w-3 opacity-70" />
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                    <div ref={messagesEndRef} />
                  </div>
                </ScrollArea>

                {/* Input */}
                <div className="p-4 border-t flex-shrink-0">
                  <form onSubmit={handleSendMessage} className="flex gap-2">
                    <Input
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      onKeyDown={handleTyping}
                      placeholder="Type a message..."
                      disabled={sendingMessage}
                      data-testid="message-input"
                    />
                    <Button type="submit" disabled={sendingMessage || !newMessage.trim()} data-testid="send-message-btn">
                      {sendingMessage ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                    </Button>
                  </form>
                  <p className="text-xs text-muted-foreground mt-2 text-center">
                    Messages are end-to-end encrypted
                  </p>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <MessageCircle className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
                  <h3 className="font-serif text-xl font-bold mb-2">Select a conversation</h3>
                  <p className="text-muted-foreground">
                    Choose a conversation from the list or start a new one
                  </p>
                </div>
              </div>
            )}
          </Card>
        </div>
      </div>
    </AppLayout>
  );
}
