import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const AuthContext = createContext();

// Helper to safely get token from localStorage
const getStoredToken = () => {
  try {
    return localStorage.getItem('justice-token');
  } catch (e) {
    console.error('Error accessing localStorage:', e);
    return null;
  }
};

// Helper to safely set token in localStorage
const setStoredToken = (token) => {
  try {
    if (token) {
      localStorage.setItem('justice-token', token);
    } else {
      localStorage.removeItem('justice-token');
    }
    return true;
  } catch (e) {
    console.error('Error writing to localStorage:', e);
    return false;
  }
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => getStoredToken());
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  // Clear auth state completely
  const clearAuth = useCallback(() => {
    console.log('[Auth] Clearing auth state');
    setStoredToken(null);
    setToken(null);
    setUser(null);
    setAuthError(null);
  }, []);

  // Verify token and get user data
  useEffect(() => {
    const checkAuth = async () => {
      const storedToken = getStoredToken();
      
      // If no token in localStorage but we have one in state, clear state
      if (!storedToken && token) {
        console.log('[Auth] Token mismatch - clearing state');
        setToken(null);
        setUser(null);
        setLoading(false);
        return;
      }
      
      if (!storedToken) {
        console.log('[Auth] No token found');
        setLoading(false);
        return;
      }
      
      try {
        console.log('[Auth] Verifying token...');
        const response = await axios.get(`${API}/auth/me`, {
          headers: { Authorization: `Bearer ${storedToken}` }
        });
        console.log('[Auth] Token verified successfully');
        setUser(response.data);
        setToken(storedToken);
        setAuthError(null);
      } catch (error) {
        console.error('[Auth] Token verification failed:', error.response?.status, error.message);
        // Only clear on 401/403 (auth errors), not on network errors
        if (error.response?.status === 401 || error.response?.status === 403) {
          console.log('[Auth] Clearing invalid token');
          clearAuth();
        } else {
          // Network error - keep token but mark error
          setAuthError('Network error - please check connection');
        }
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, [token, clearAuth]);

  const login = async (email, password) => {
    console.log('[Auth] Attempting login...');
    setAuthError(null);
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const { access_token, user: userData } = response.data;
      
      if (!access_token) {
        throw new Error('No access token received');
      }
      
      setStoredToken(access_token);
      setToken(access_token);
      setUser(userData);
      console.log('[Auth] Login successful');
      return userData;
    } catch (error) {
      console.error('[Auth] Login failed:', error.message);
      clearAuth();
      throw error;
    }
  };

  const register = async (email, password, name, phone) => {
    console.log('[Auth] Attempting registration...');
    setAuthError(null);
    try {
      const response = await axios.post(`${API}/auth/register`, { 
        email, 
        password, 
        name,
        phone 
      });
      const { access_token, user: userData } = response.data;
      
      if (!access_token) {
        throw new Error('No access token received');
      }
      
      setStoredToken(access_token);
      setToken(access_token);
      setUser(userData);
      console.log('[Auth] Registration successful');
      return userData;
    } catch (error) {
      console.error('[Auth] Registration failed:', error.message);
      clearAuth();
      throw error;
    }
  };

  const loginWithGoogle = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const processOAuthSession = async (sessionId) => {
    console.log('[Auth] Processing OAuth session...');
    setAuthError(null);
    try {
      const response = await axios.post(`${API}/auth/session`, { session_id: sessionId });
      const { access_token, user: userData } = response.data;
      
      // Store token if provided in OAuth response
      if (access_token) {
        setStoredToken(access_token);
        setToken(access_token);
      }
      
      setUser(userData || response.data);
      console.log('[Auth] OAuth session processed successfully');
      return userData || response.data;
    } catch (error) {
      console.error('[Auth] OAuth session processing failed:', error.message);
      clearAuth();
      throw error;
    }
  };

  const logout = async () => {
    console.log('[Auth] Logging out...');
    const currentToken = token || getStoredToken();
    
    try {
      if (currentToken) {
        await axios.post(`${API}/auth/logout`, {}, {
          headers: { Authorization: `Bearer ${currentToken}` }
        });
      }
    } catch (error) {
      // Ignore logout errors - we're clearing state anyway
      console.log('[Auth] Logout API error (ignored):', error.message);
    }
    
    clearAuth();
    console.log('[Auth] Logout complete');
  };

  const value = {
    user,
    token,
    loading,
    authError,
    login,
    register,
    loginWithGoogle,
    processOAuthSession,
    logout,
    clearAuth,
    isAuthenticated: !!user && !!token
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
