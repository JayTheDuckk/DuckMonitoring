import React, { createContext, useState, useContext, useEffect, useRef } from 'react';
import api, { login as apiLogin, register as apiRegister, getProfile } from '../services/api';
// We import named exports to use them directly or use 'api' instance for other calls

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isSetup, setIsSetup] = useState(true); // Default to true to prevent redirect flash
  const [token, setToken] = useState(localStorage.getItem('access_token'));
  const skipAuthCheckRef = useRef(false);

  // Set token in axios defaults
  useEffect(() => {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      localStorage.setItem('access_token', token);
    } else {
      delete api.defaults.headers.common['Authorization'];
      localStorage.removeItem('access_token');
    }
  }, [token]);

  // Check setup status
  const checkSetup = async () => {
    try {
      const { getSetupStatus } = require('../services/api');
      const response = await getSetupStatus();
      setIsSetup(response.data.is_setup);
      return response.data.is_setup;
    } catch (error) {
      console.error('Failed to check setup status:', error);
      return false;
    }
  };

  useEffect(() => {
    checkSetup();
  }, []);

  // Check if user is authenticated on mount
  useEffect(() => {
    const checkAuth = async () => {
      if (skipAuthCheckRef.current) {
        skipAuthCheckRef.current = false;
        setLoading(false);
        return;
      }

      if (token) {
        try {
          // Verify token and get user details
          const response = await getProfile();
          setUser(response.data);
        } catch (error) {
          console.error('Auth check failed:', error);
          // Only clear if 401 (unauthorized)
          if (error.response?.status === 401) {
            setToken(null);
            setUser(null);
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
          }
        }
      }
      setLoading(false);
    };
    checkAuth();
  }, [token]);

  const login = async (username, password) => {
    try {
      console.log('AuthContext: Starting login for:', username);
      // 1. Get Token
      const response = await apiLogin({ username, password });
      console.log('AuthContext: Token received', response.data);

      const { access, refresh } = response.data;

      // Store tokens
      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);

      // Update state
      setToken(access);
      api.defaults.headers.common['Authorization'] = `Bearer ${access}`;

      // 2. Get User Profile immediately
      const userResponse = await getProfile();
      setUser(userResponse.data);

      skipAuthCheckRef.current = true;
      setLoading(false);

      console.log('AuthContext: Login successful');
      return { success: true };
    } catch (error) {
      console.error('AuthContext: Login error:', error);
      let errorMessage = 'Login failed';

      if (error.code === 'ECONNREFUSED' || error.message.includes('Network Error')) {
        errorMessage = 'Cannot connect to server. Please check your connection.';
      } else if (error.response?.status === 401) {
        errorMessage = 'Invalid username or password';
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }

      return {
        success: false,
        error: errorMessage
      };
    }
  };

  const register = async (username, email, password) => {
    try {
      // 1. Register
      await apiRegister({ username, email, password });

      // 2. Login automatically (optional, depends on backend behavior)
      // For now, let the user login manually or if register returns tokens use them.
      // My RegisterView implementation in Django likely returns the user object but not tokens unless I customized it.
      // Standard practice: check response.

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Registration failed'
      };
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    // Optional: Call backend logout if using blacklisting
  };

  const value = {
    user,
    token,
    loading,
    isSetup,
    checkSetup,
    login,
    register,
    logout,
    isAuthenticated: !!user,
    isAdmin: user?.is_admin || user?.role === 'admin'
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
