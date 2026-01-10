import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import { Shield, Loader2 } from 'lucide-react';

export default function AuthCallback() {
  const hasProcessed = useRef(false);
  const { processOAuthSession } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Prevent double processing in StrictMode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      try {
        // Extract session_id from URL fragment
        const hash = window.location.hash;
        const params = new URLSearchParams(hash.slice(1));
        const sessionId = params.get('session_id');

        if (!sessionId) {
          toast.error('Authentication failed: No session ID');
          navigate('/login');
          return;
        }

        // Process the session
        await processOAuthSession(sessionId);
        
        // Clear the hash from URL
        window.history.replaceState(null, '', '/dashboard');
        
        toast.success('Welcome to JUSTICE!');
        navigate('/dashboard', { replace: true });
      } catch (error) {
        console.error('Auth callback error:', error);
        toast.error('Authentication failed. Please try again.');
        navigate('/login');
      }
    };

    processAuth();
  }, [processOAuthSession, navigate]);

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center">
      <Shield className="h-16 w-16 mb-6" style={{ color: '#3B82F6' }} />
      <div className="flex items-center gap-3">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
        <span className="text-lg">Completing sign in...</span>
      </div>
    </div>
  );
}
