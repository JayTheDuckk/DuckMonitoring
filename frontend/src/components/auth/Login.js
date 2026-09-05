import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../services/api';
import './Auth.css';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // 2FA state
  const [requires2FA, setRequires2FA] = useState(false);
  const [tempToken, setTempToken] = useState(null);
  const [twoFactorCode, setTwoFactorCode] = useState('');

  const { login, isAuthenticated, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const isSubmittingRef = useRef(false);

  // Redirect if already authenticated
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, authLoading, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Prevent double submission
    if (isSubmittingRef.current) {
      return;
    }

    isSubmittingRef.current = true;
    setError('');
    setLoading(true);

    const usernameValue = username;
    const passwordValue = password;

    try {
      const result = await login(usernameValue, passwordValue);

      if (result.success) {
        navigate('/', { replace: true });
      } else if (result.requires2FA) {
        // 2FA required - show code input
        setRequires2FA(true);
        setTempToken(result.tempToken);
        setLoading(false);
        isSubmittingRef.current = false;
      } else {
        setError(result.error);
        setLoading(false);
        isSubmittingRef.current = false;
        setUsername(usernameValue);
        setPassword('');
      }
    } catch (err) {
      console.error('Login form error:', err);
      setError('An unexpected error occurred. Please try again.');
      setLoading(false);
      isSubmittingRef.current = false;
      setUsername(usernameValue);
      setPassword('');
    }
  };

  const handleVerify2FA = async (e) => {
    e.preventDefault();

    if (isSubmittingRef.current || !tempToken) {
      return;
    }

    isSubmittingRef.current = true;
    setError('');
    setLoading(true);

    try {
      // Set temp token for this request
      api.defaults.headers.common['Authorization'] = `Bearer ${tempToken}`;

      const response = await api.post('/auth/2fa/authenticate', { code: twoFactorCode });

      const { access_token, refresh_token, user } = response.data;

      // Store tokens
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

      // Navigate after successful 2FA
      window.location.reload(); // Refresh to trigger AuthContext
    } catch (err) {
      console.error('2FA verification error:', err);
      setError(err.response?.data?.error || 'Invalid verification code');
      setLoading(false);
      isSubmittingRef.current = false;
      setTwoFactorCode('');
    }
  };

  const handleBack = () => {
    setRequires2FA(false);
    setTempToken(null);
    setTwoFactorCode('');
    setPassword('');
    setError('');
  };

  if (authLoading) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <h1>Duck Monitoring</h1>
            <p>Loading...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h1>Duck Monitoring</h1>
          <p>{requires2FA ? 'Two-Factor Authentication' : 'Network Monitoring System'}</p>
        </div>

        {!requires2FA ? (
          <form onSubmit={handleSubmit} className="auth-form">
            {error && <div className="error-message">{error}</div>}

            <div className="form-group">
              <label htmlFor="username">Username</label>
              <input
                type="text"
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="auth-button" disabled={loading}>
              {loading ? 'Logging in...' : 'Login'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleVerify2FA} className="auth-form">
            {error && <div className="error-message">{error}</div>}

            <div className="two-factor-prompt">
              <div className="two-factor-icon">🔐</div>
              <p>Enter the 6-digit code from your authenticator app</p>
            </div>

            <div className="form-group">
              <label htmlFor="twoFactorCode">Verification Code</label>
              <input
                type="text"
                id="twoFactorCode"
                value={twoFactorCode}
                onChange={(e) => setTwoFactorCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                required
                autoFocus
                placeholder="000000"
                maxLength="6"
                pattern="[0-9]*"
                autoComplete="one-time-code"
                className="totp-input"
              />
            </div>

            <button type="submit" className="auth-button" disabled={loading || twoFactorCode.length !== 6}>
              {loading ? 'Verifying...' : 'Verify'}
            </button>

            <button type="button" className="back-button" onClick={handleBack} disabled={loading}>
              ← Back to Login
            </button>
          </form>
        )}

        {!requires2FA && (
          <div className="auth-footer">
            <p>
              Don't have an account? <Link to="/register">Register here</Link>
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Login;
