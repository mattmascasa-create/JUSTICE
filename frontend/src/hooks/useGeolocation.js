/**
 * useGeolocation Hook
 * Handles location tracking for encounters
 */

import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';

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

  const getPosition = useCallback(() => {
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

  // Initial position fetch - using a ref to track if we've already fetched
  const hasInitializedRef = useRef(false);
  useEffect(() => {
    if (!hasInitializedRef.current) {
      hasInitializedRef.current = true;
      getPosition();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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

  const refresh = useCallback(() => {
    getPosition();
  }, [getPosition]);

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
