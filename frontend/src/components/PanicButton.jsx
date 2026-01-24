import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Siren, Video, MapPin, Users, Phone, X, Grip, Shield } from 'lucide-react';
import { cn } from '../lib/utils';
import { toast } from 'sonner';
import { sosAPI } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';

export default function PanicButton() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [isActive, setIsActive] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [position, setPosition] = useState(() => {
    // Initialize from localStorage synchronously
    const saved = localStorage.getItem('panic-button-position');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        // Use default
      }
    }
    return { x: 20, y: typeof window !== 'undefined' ? window.innerHeight - 100 : 500 };
  });
  const buttonRef = useRef(null);
  const dragOffset = useRef({ x: 0, y: 0 });

  // Save position on change
  useEffect(() => {
    localStorage.setItem('panic-button-position', JSON.stringify(position));
  }, [position]);

  const handleMouseDown = (e) => {
    if (e.target.closest('.panic-action')) return;
    setIsDragging(true);
    const rect = buttonRef.current.getBoundingClientRect();
    dragOffset.current = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    };
  };

  useEffect(() => {
    if (isDragging) {
      const handleMove = (e) => {
        const newX = Math.max(0, Math.min(window.innerWidth - 70, e.clientX - dragOffset.current.x));
        const newY = Math.max(0, Math.min(window.innerHeight - 70, e.clientY - dragOffset.current.y));
        setPosition({ x: newX, y: newY });
      };
      
      const handleUp = () => {
        setIsDragging(false);
      };
      
      window.addEventListener('mousemove', handleMove);
      window.addEventListener('mouseup', handleUp);
      return () => {
        window.removeEventListener('mousemove', handleMove);
        window.removeEventListener('mouseup', handleUp);
      };
    }
  }, [isDragging]);

  // Touch events for mobile
  const handleTouchStart = (e) => {
    if (e.target.closest('.panic-action')) return;
    setIsDragging(true);
    const touch = e.touches[0];
    const rect = buttonRef.current.getBoundingClientRect();
    dragOffset.current = {
      x: touch.clientX - rect.left,
      y: touch.clientY - rect.top
    };
  };

  const handleTouchMove = (e) => {
    if (!isDragging) return;
    const touch = e.touches[0];
    const newX = Math.max(0, Math.min(window.innerWidth - 70, touch.clientX - dragOffset.current.x));
    const newY = Math.max(0, Math.min(window.innerHeight - 70, touch.clientY - dragOffset.current.y));
    setPosition({ x: newX, y: newY });
  };

  const handleTouchEnd = () => {
    setIsDragging(false);
  };

  // Panic actions
  const triggerFullPanic = async () => {
    setIsActive(true);
    toast.loading('Activating emergency mode...', { id: 'panic' });
    
    try {
      // Get location
      const position = await new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 });
      });

      // Navigate to encounter mode with emergency flag
      navigate('/encounter?emergency=true');
      
      // Send SOS alert
      try {
        await sosAPI.quickAlert({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          message: 'EMERGENCY: Panic button activated'
        });
        toast.success('Emergency contacts alerted!', { id: 'panic' });
      } catch (e) {
        toast.success('Recording started - Configure emergency contacts in settings', { id: 'panic' });
      }
    } catch (error) {
      // Still navigate to encounter even without location
      navigate('/encounter?emergency=true');
      toast.info('Recording started', { id: 'panic' });
    }
    
    setIsActive(false);
    setIsOpen(false);
  };

  const startRecording = () => {
    navigate('/encounter');
    setIsOpen(false);
  };

  const sendSOSOnly = async () => {
    toast.loading('Sending SOS...', { id: 'sos' });
    try {
      const position = await new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 });
      });
      
      await sosAPI.quickAlert({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        message: 'SOS Alert from JUSTICE app'
      });
      toast.success('SOS sent to emergency contacts!', { id: 'sos' });
    } catch (error) {
      toast.error('Failed to send SOS. Check emergency contacts in settings.', { id: 'sos' });
    }
    setIsOpen(false);
  };

  const callEmergency = () => {
    window.location.href = 'tel:911';
    setIsOpen(false);
  };

  if (!user) return null;

  return (
    <div
      ref={buttonRef}
      className="fixed z-50 select-none"
      style={{ left: position.x, top: position.y }}
      onMouseDown={handleMouseDown}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Expanded Menu */}
      {isOpen && (
        <div 
          className="absolute bottom-16 left-1/2 -translate-x-1/2 bg-background border rounded-2xl shadow-2xl p-3 min-w-[200px] animate-in fade-in slide-in-from-bottom-4 duration-200"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between mb-3 pb-2 border-b">
            <span className="font-semibold text-sm flex items-center gap-2">
              <Shield className="h-4 w-4 text-primary" />
              Quick Actions
            </span>
            <button 
              onClick={() => setIsOpen(false)}
              className="p-1 hover:bg-muted rounded-full panic-action"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          
          <div className="space-y-2">
            {/* Full Panic */}
            <button
              onClick={triggerFullPanic}
              className="panic-action w-full flex items-center gap-3 p-3 rounded-xl bg-red-500 hover:bg-red-600 text-white transition-colors"
            >
              <Siren className="h-5 w-5" />
              <div className="text-left">
                <div className="font-semibold text-sm">FULL EMERGENCY</div>
                <div className="text-xs opacity-80">Record + SOS + Location</div>
              </div>
            </button>

            {/* Start Recording */}
            <button
              onClick={startRecording}
              className="panic-action w-full flex items-center gap-3 p-3 rounded-xl bg-blue-500 hover:bg-blue-600 text-white transition-colors"
            >
              <Video className="h-5 w-5" />
              <div className="text-left">
                <div className="font-semibold text-sm">Start Recording</div>
                <div className="text-xs opacity-80">Open Encounter Mode</div>
              </div>
            </button>

            {/* Send SOS */}
            <button
              onClick={sendSOSOnly}
              className="panic-action w-full flex items-center gap-3 p-3 rounded-xl bg-orange-500 hover:bg-orange-600 text-white transition-colors"
            >
              <Users className="h-5 w-5" />
              <div className="text-left">
                <div className="font-semibold text-sm">Alert Contacts</div>
                <div className="text-xs opacity-80">Send SOS with location</div>
              </div>
            </button>

            {/* Call 911 */}
            <button
              onClick={callEmergency}
              className="panic-action w-full flex items-center gap-3 p-3 rounded-xl border hover:bg-muted transition-colors"
            >
              <Phone className="h-5 w-5 text-green-500" />
              <div className="text-left">
                <div className="font-semibold text-sm">Call 911</div>
                <div className="text-xs text-muted-foreground">Emergency services</div>
              </div>
            </button>
          </div>

          <div className="mt-3 pt-2 border-t">
            <p className="text-xs text-muted-foreground text-center flex items-center justify-center gap-1">
              <Grip className="h-3 w-3" />
              Drag button to reposition
            </p>
          </div>
        </div>
      )}

      {/* Main Button */}
      <button
        onClick={() => !isDragging && setIsOpen(!isOpen)}
        className={cn(
          "w-14 h-14 rounded-full flex items-center justify-center shadow-lg transition-all duration-300",
          "bg-red-500 hover:bg-red-600 text-white",
          isActive && "animate-pulse",
          isOpen && "ring-4 ring-red-500/30",
          isDragging && "cursor-grabbing scale-110"
        )}
        data-testid="panic-button"
      >
        <Siren className={cn("h-7 w-7", isActive && "animate-bounce")} />
      </button>

      {/* Pulse rings when active */}
      {isActive && (
        <>
          <span className="absolute inset-0 rounded-full bg-red-500 animate-ping opacity-75" />
          <span className="absolute inset-0 rounded-full bg-red-500 animate-ping opacity-50 animation-delay-150" />
        </>
      )}
    </div>
  );
}
