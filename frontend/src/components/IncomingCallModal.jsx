import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { callsAPI } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import { Phone, PhoneOff, Video, User } from 'lucide-react';
import { Button } from './ui/button';

export default function IncomingCallModal() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [incomingCall, setIncomingCall] = useState(null);
  const [isAnswering, setIsAnswering] = useState(false);

  // Poll for incoming calls
  useEffect(() => {
    if (!user) return;

    const checkForCalls = async () => {
      try {
        const res = await callsAPI.getIncomingCalls();
        if (res.data.incoming_calls?.length > 0) {
          setIncomingCall(res.data.incoming_calls[0]);
        } else {
          setIncomingCall(null);
        }
      } catch (error) {
        // Silently fail - user might not be logged in
      }
    };

    // Check immediately
    checkForCalls();

    // Then poll every 3 seconds
    const interval = setInterval(checkForCalls, 3000);

    return () => clearInterval(interval);
  }, [user]);

  const handleAnswer = async () => {
    if (!incomingCall) return;
    
    setIsAnswering(true);
    try {
      await callsAPI.answerCall(incomingCall.call_id);
      navigate(`/call/${incomingCall.call_id}?incoming=true`);
    } catch (error) {
      toast.error('Failed to answer call');
      setIsAnswering(false);
    }
  };

  const handleReject = async () => {
    if (!incomingCall) return;
    
    try {
      await callsAPI.rejectCall(incomingCall.call_id);
      setIncomingCall(null);
      toast.info('Call rejected');
    } catch (error) {
      toast.error('Failed to reject call');
    }
  };

  if (!incomingCall) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4" data-testid="incoming-call-modal">
      <div className="bg-gray-900 rounded-2xl p-8 max-w-sm w-full text-center animate-in zoom-in-95 duration-300">
        {/* Caller Avatar */}
        <div className="relative mx-auto mb-6">
          <div className="h-24 w-24 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center mx-auto animate-pulse">
            <User className="h-12 w-12 text-white" />
          </div>
          <div className="absolute -bottom-1 -right-1 h-8 w-8 rounded-full bg-green-500 flex items-center justify-center">
            <Video className="h-4 w-4 text-white" />
          </div>
        </div>

        {/* Caller Info */}
        <h2 className="text-2xl font-semibold text-white mb-1">
          {incomingCall.caller_name || 'Unknown Caller'}
        </h2>
        <p className="text-gray-400 mb-8">
          Incoming {incomingCall.call_type === 'video' ? 'Video' : 'Voice'} Call
        </p>

        {/* Action Buttons */}
        <div className="flex items-center justify-center gap-8">
          <button
            onClick={handleReject}
            className="h-16 w-16 rounded-full bg-red-500 hover:bg-red-600 flex items-center justify-center transition-colors"
            data-testid="reject-call-btn"
          >
            <PhoneOff className="h-7 w-7 text-white" />
          </button>
          
          <button
            onClick={handleAnswer}
            disabled={isAnswering}
            className="h-16 w-16 rounded-full bg-green-500 hover:bg-green-600 flex items-center justify-center transition-colors animate-bounce"
            data-testid="answer-call-btn"
          >
            <Phone className="h-7 w-7 text-white" />
          </button>
        </div>

        {/* Ringing indicator */}
        <div className="mt-6 flex items-center justify-center gap-1">
          <span className="h-2 w-2 rounded-full bg-blue-400 animate-ping" style={{ animationDelay: '0ms' }}></span>
          <span className="h-2 w-2 rounded-full bg-blue-400 animate-ping" style={{ animationDelay: '150ms' }}></span>
          <span className="h-2 w-2 rounded-full bg-blue-400 animate-ping" style={{ animationDelay: '300ms' }}></span>
        </div>
      </div>
    </div>
  );
}
