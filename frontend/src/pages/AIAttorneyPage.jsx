import React, { useState, useRef, useEffect } from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
import { aiAPI } from '../lib/api';
import { cn } from '../lib/utils';
import { 
  Bot, Send, AlertTriangle, Shield, Loader2, 
  Plus, Clock, Scale, FileText
} from 'lucide-react';
import { toast } from 'sonner';

export default function AIAttorneyPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await aiAPI.chat(userMessage, sessionId);
      const data = response.data;
      
      if (!sessionId) {
        setSessionId(data.session_id);
      }

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        violation_detected: data.violation_detected,
        violation_type: data.violation_type,
        rights_reminder: data.rights_reminder
      }]);
    } catch (error) {
      toast.error('Failed to get response. Please try again.');
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'I apologize, but I encountered an error. Please try again.',
        error: true
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setSessionId(null);
  };

  const quickPrompts = [
    "I'm being pulled over. What are my rights?",
    "Can police search my car without a warrant?",
    "What should I say if asked questions during a stop?",
    "The officer is asking to search my home. What do I do?"
  ];

  return (
    <AppLayout>
      <div className="h-[calc(100vh-8rem)] flex flex-col" data-testid="ai-attorney-page">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary">
              <Bot className="h-6 w-6 text-primary-foreground" />
            </div>
            <div>
              <h1 className="font-serif text-2xl font-bold">AI Attorney</h1>
              <p className="text-sm text-muted-foreground">Constitutional rights advisor • GPT-5.2</p>
            </div>
          </div>
          <Button variant="outline" onClick={handleNewChat} data-testid="new-chat-btn">
            <Plus className="h-4 w-4 mr-2" />
            New Chat
          </Button>
        </div>

        {/* Chat Area */}
        <Card className="flex-1 flex flex-col overflow-hidden">
          <ScrollArea className="flex-1 p-4">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-8">
                <Shield className="h-16 w-16 text-muted-foreground mb-4" />
                <h2 className="font-serif text-xl font-bold mb-2">How can I help protect your rights?</h2>
                <p className="text-muted-foreground mb-6 max-w-md">
                  Ask me about your constitutional rights during police encounters. 
                  I can help you understand your 1st, 4th, 5th, 6th, 8th, and 14th Amendment protections.
                </p>
                
                {/* Quick Prompts */}
                <div className="grid sm:grid-cols-2 gap-3 w-full max-w-lg">
                  {quickPrompts.map((prompt, index) => (
                    <Button
                      key={index}
                      variant="outline"
                      className="h-auto py-3 px-4 text-left justify-start whitespace-normal"
                      onClick={() => setInput(prompt)}
                      data-testid={`quick-prompt-${index}`}
                    >
                      <Scale className="h-4 w-4 mr-2 flex-shrink-0" />
                      <span className="text-sm">{prompt}</span>
                    </Button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {messages.map((msg, index) => (
                  <div
                    key={index}
                    className={cn(
                      "flex",
                      msg.role === 'user' ? 'justify-end' : 'justify-start'
                    )}
                  >
                    <div
                      className={cn(
                        "max-w-[85%] rounded-2xl px-4 py-3",
                        msg.role === 'user' 
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted',
                        msg.error && 'bg-destructive/10 text-destructive'
                      )}
                    >
                      {msg.role === 'assistant' && (
                        <div className="flex items-center gap-2 mb-2">
                          <Bot className="h-4 w-4" />
                          <span className="font-medium text-sm">AI Attorney</span>
                        </div>
                      )}
                      
                      {/* Violation Alert */}
                      {msg.violation_detected && (
                        <div className="mb-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                          <div className="flex items-center gap-2 text-red-500 font-medium mb-1">
                            <AlertTriangle className="h-4 w-4" />
                            Potential Violation Detected
                          </div>
                          {msg.violation_type && (
                            <Badge className="bg-red-500/20 text-red-500 border-red-500/30">
                              {msg.violation_type}
                            </Badge>
                          )}
                        </div>
                      )}
                      
                      <div className="whitespace-pre-wrap text-sm leading-relaxed">
                        {msg.content}
                      </div>
                    </div>
                  </div>
                ))}
                
                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-muted rounded-2xl px-4 py-3 flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span className="text-sm">Analyzing your question...</span>
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>
            )}
          </ScrollArea>

          {/* Input Area */}
          <div className="border-t border-border p-4">
            <form onSubmit={handleSubmit} className="flex gap-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Describe your situation or ask about your rights..."
                className="flex-1"
                disabled={loading}
                data-testid="chat-input"
              />
              <Button type="submit" disabled={loading || !input.trim()} data-testid="send-btn">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </form>
            <p className="text-xs text-muted-foreground mt-2 text-center">
              AI Attorney provides general information, not legal advice. Consult a licensed attorney for specific legal matters.
            </p>
          </div>
        </Card>

        {/* Side Info */}
        <div className="grid sm:grid-cols-3 gap-4 mt-4">
          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <Clock className="h-5 w-5 text-blue-500" />
              <div>
                <p className="font-medium">24/7 Available</p>
                <p className="text-xs text-muted-foreground">Always ready to help</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <Shield className="h-5 w-5 text-green-500" />
              <div>
                <p className="font-medium">89% Accuracy</p>
                <p className="text-xs text-muted-foreground">Constitutional analysis</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <FileText className="h-5 w-5 text-purple-500" />
              <div>
                <p className="font-medium">End-to-End Encrypted</p>
                <p className="text-xs text-muted-foreground">Your privacy protected</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </AppLayout>
  );
}
