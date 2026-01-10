import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('justice-token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await axios.get(`${API}/auth/me`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          withCredentials: true
        });
        setUser(response.data);
      } catch (error) {
        setUser(null);
        setToken(null);
        localStorage.removeItem('justice-token');
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, [token]);

  const login = async (email, password) => {
    const response = await axios.post(`${API}/auth/login`, { email, password });
    const { access_token, user: userData } = response.data;
    localStorage.setItem('justice-token', access_token);
    setToken(access_token);
    setUser(userData);
    return userData;
  };

  const register = async (email, password, name, phone) => {
    const response = await axios.post(`${API}/auth/register`, { 
      email, 
      password, 
      name,
      phone 
    });
    const { access_token, user: userData } = response.data;
    localStorage.setItem('justice-token', access_token);
    setToken(access_token);
    setUser(userData);
    return userData;
  };

  const loginWithGoogle = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const processOAuthSession = async (sessionId) => {
    const response = await axios.post(`${API}/auth/session`, { session_id: sessionId }, {
      withCredentials: true
    });
    setUser(response.data);
    return response.data;
  };

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        withCredentials: true
      });
    } catch (error) {
      console.error('Logout error:', error);
    }
    localStorage.removeItem('justice-token');
    setToken(null);
    setUser(null);
  };

  const value = {
    user,
    token,
    loading,
    login,
    register,
    loginWithGoogle,
    processOAuthSession,
    logout,
    isAuthenticated: !!user
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
