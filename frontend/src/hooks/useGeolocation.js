/**
 * useGeolocation Hook
 * Handles location tracking for encounters
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { toast } from 'sonner';

// Initialize geolocation outside of React's render cycle
function initializeGeolocation(options, callbacks) {
  const { enableHighAccuracy, showErrors } = options;
  const { onSuccess, onError, onNotSupported } = callbacks;

  if (!navigator.geolocation) {
    onNotSupported();
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (position) => {
      onSuccess({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
        timestamp: position.timestamp
      });
    },
    (err) => {
      console.error('Geolocation error:', err);
      onError(err.message);
      
      if (showErrors) {
        toast.error('Could not get your location. Please enable location services.');
      }
    },
    { enableHighAccuracy }
  );
}

export function useGeolocation(options = {}) {
  const {
    enableHighAccuracy = true,
    watchPosition = false,
    showErrors = true
  } = options;

  const [location, setLocation] = useState(null);
  const [address, setAddress] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const hasInitializedRef = useRef(false);

  // Initial position fetch using external function
  useEffect(() => {
    if (hasInitializedRef.current) return;
    hasInitializedRef.current = true;

    initializeGeolocation(
      { enableHighAccuracy, showErrors },
      {
        onSuccess: (loc) => {
          setLocation(loc);
          setError(null);
          setLoading(false);
        },
        onError: (errMsg) => {
          setError(errMsg);
          setLoading(false);
        },
        onNotSupported: () => {
          setError('Geolocation is not supported by your browser');
          setLoading(false);
        }
      }
    );
  }, [enableHighAccuracy, showErrors]);

  // Manual refresh function
  const refresh = useCallback(() => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser');
      setLoading(false);
      return;
    }

    setLoading(true);
    
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          timestamp: position.timestamp
        });
        setError(null);
        setLoading(false);
      },
      (err) => {
        console.error('Geolocation error:', err);
        setError(err.message);
        setLoading(false);
        
        if (showErrors) {
          toast.error('Could not get your location. Please enable location services.');
        }
      },
      { enableHighAccuracy }
    );
  }, [enableHighAccuracy, showErrors]);

  // Optional: Watch position for continuous updates
  useEffect(() => {
    if (!watchPosition || !navigator.geolocation) return;

    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        setLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          timestamp: position.timestamp
        });
      },
      (err) => {
        console.error('Watch position error:', err);
      },
      { enableHighAccuracy }
    );

    return () => {
      navigator.geolocation.clearWatch(watchId);
    };
  }, [watchPosition, enableHighAccuracy]);

  const formatCoordinates = useCallback(() => {
    if (!location) return 'Location unavailable';
    return `${location.latitude.toFixed(6)}, ${location.longitude.toFixed(6)}`;
  }, [location]);

  return {
    location,
    address,
    setAddress,
    error,
    loading,
    refresh,
    formatCoordinates,
    hasLocation: !!location
  };
}

export default useGeolocation;
