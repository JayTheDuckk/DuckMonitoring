import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../services/api';
import './SecuritySettings.css';

const SecuritySettings = () => {
    const { user } = useAuth();
    const [twoFactorStatus, setTwoFactorStatus] = useState({
        enabled: false,
        backup_codes_remaining: 0
    });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);

    // 2FA Setup state
    const [setupMode, setSetupMode] = useState(false);
    const [qrCode, setQrCode] = useState(null);
    const [secret, setSecret] = useState(null);
    const [verifyCode, setVerifyCode] = useState('');
    const [backupCodes, setBackupCodes] = useState(null);

    // Disable 2FA state
    const [disableMode, setDisableMode] = useState(false);
    const [disablePassword, setDisablePassword] = useState('');

    const fetchStatus = useCallback(async () => {
        try {
            const response = await api.get('/auth/2fa/status');
            setTwoFactorStatus(response.data);
        } catch (err) {
            console.error('Failed to fetch 2FA status:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchStatus();
    }, [fetchStatus]);

    const handleStartSetup = async () => {
        setError(null);
        setSuccess(null);
        try {
            const response = await api.post('/auth/2fa/setup');
            setQrCode(response.data.qr_code);
            setSecret(response.data.secret);
            setSetupMode(true);
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to start 2FA setup');
        }
    };

    const handleVerifySetup = async (e) => {
        e.preventDefault();
        setError(null);
        try {
            const response = await api.post('/auth/2fa/verify', { code: verifyCode });
            setBackupCodes(response.data.backup_codes);
            setSuccess('2FA has been enabled successfully!');
            setSetupMode(false);
            fetchStatus();
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to verify code');
        }
    };

    const handleDisable2FA = async (e) => {
        e.preventDefault();
        setError(null);
        try {
            await api.post('/auth/2fa/disable', { password: disablePassword });
            setSuccess('2FA has been disabled');
            setDisableMode(false);
            setDisablePassword('');
            fetchStatus();
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to disable 2FA');
        }
    };

    const copyBackupCodes = () => {
        if (backupCodes) {
            navigator.clipboard.writeText(backupCodes.join('\n'));
            setSuccess('Backup codes copied to clipboard!');
        }
    };

    if (loading) {
        return <div className="security-loading">Loading security settings...</div>;
    }

    return (
        <div className="security-container">
            <div className="security-header">
                <h1>Security Settings</h1>
                <p className="subtitle">Manage your account security</p>
            </div>

            {error && <div className="security-error">{error}</div>}
            {success && <div className="security-success">{success}</div>}

            {/* 2FA Section */}
            <div className="security-card">
                <div className="card-header">
                    <div className="card-title">
                        <span className="icon">🔐</span>
                        <h2>Two-Factor Authentication</h2>
                    </div>
                    <span className={`status-badge ${twoFactorStatus.enabled ? 'enabled' : 'disabled'}`}>
                        {twoFactorStatus.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                </div>

                <div className="card-content">
                    {!twoFactorStatus.enabled && !setupMode && (
                        <div className="two-factor-promo">
                            <p>
                                Add an extra layer of security to your account. When enabled, you'll need to
                                enter a code from your authenticator app in addition to your password.
                            </p>
                            <button className="btn-primary" onClick={handleStartSetup}>
                                Enable Two-Factor Authentication
                            </button>
                        </div>
                    )}

                    {setupMode && (
                        <div className="two-factor-setup">
                            <h3>Set Up Two-Factor Authentication</h3>

                            <div className="setup-steps">
                                <div className="step">
                                    <span className="step-number">1</span>
                                    <div className="step-content">
                                        <h4>Scan QR Code</h4>
                                        <p>Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)</p>
                                        {qrCode && (
                                            <div className="qr-container">
                                                <img src={qrCode} alt="2FA QR Code" />
                                            </div>
                                        )}
                                        <p className="manual-entry">
                                            Or enter this code manually: <code>{secret}</code>
                                        </p>
                                    </div>
                                </div>

                                <div className="step">
                                    <span className="step-number">2</span>
                                    <div className="step-content">
                                        <h4>Enter Verification Code</h4>
                                        <p>Enter the 6-digit code from your authenticator app</p>
                                        <form onSubmit={handleVerifySetup} className="verify-form">
                                            <input
                                                type="text"
                                                value={verifyCode}
                                                onChange={(e) => setVerifyCode(e.target.value)}
                                                placeholder="000000"
                                                maxLength="6"
                                                pattern="[0-9]*"
                                                autoComplete="one-time-code"
                                            />
                                            <div className="form-actions">
                                                <button type="button" className="btn-secondary" onClick={() => setSetupMode(false)}>
                                                    Cancel
                                                </button>
                                                <button type="submit" className="btn-primary">
                                                    Verify & Enable
                                                </button>
                                            </div>
                                        </form>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {backupCodes && (
                        <div className="backup-codes-modal">
                            <div className="backup-codes-content">
                                <h3>⚠️ Save Your Backup Codes</h3>
                                <p>
                                    These codes can be used to access your account if you lose your authenticator.
                                    Each code can only be used once. <strong>Save them somewhere safe!</strong>
                                </p>
                                <div className="codes-grid">
                                    {backupCodes.map((code, index) => (
                                        <span key={index} className="backup-code">{code}</span>
                                    ))}
                                </div>
                                <div className="codes-actions">
                                    <button className="btn-secondary" onClick={copyBackupCodes}>
                                        Copy Codes
                                    </button>
                                    <button className="btn-primary" onClick={() => setBackupCodes(null)}>
                                        I've Saved My Codes
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {twoFactorStatus.enabled && !disableMode && (
                        <div className="two-factor-enabled">
                            <div className="status-info">
                                <p>✅ Two-factor authentication is enabled for your account.</p>
                                <p className="backup-info">
                                    Backup codes remaining: <strong>{twoFactorStatus.backup_codes_remaining}</strong>
                                </p>
                            </div>
                            <button className="btn-danger" onClick={() => setDisableMode(true)}>
                                Disable Two-Factor Authentication
                            </button>
                        </div>
                    )}

                    {disableMode && (
                        <div className="disable-2fa">
                            <h3>Disable Two-Factor Authentication</h3>
                            <p>Enter your password to confirm disabling 2FA.</p>
                            <form onSubmit={handleDisable2FA} className="disable-form">
                                <input
                                    type="password"
                                    value={disablePassword}
                                    onChange={(e) => setDisablePassword(e.target.value)}
                                    placeholder="Enter your password"
                                />
                                <div className="form-actions">
                                    <button type="button" className="btn-secondary" onClick={() => {
                                        setDisableMode(false);
                                        setDisablePassword('');
                                    }}>
                                        Cancel
                                    </button>
                                    <button type="submit" className="btn-danger">
                                        Disable 2FA
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}
                </div>
            </div>

            {/* Account Info Section */}
            <div className="security-card">
                <div className="card-header">
                    <div className="card-title">
                        <span className="icon">👤</span>
                        <h2>Account Information</h2>
                    </div>
                </div>
                <div className="card-content">
                    <div className="info-row">
                        <label>Username:</label>
                        <span>{user?.username}</span>
                    </div>
                    <div className="info-row">
                        <label>Email:</label>
                        <span>{user?.email}</span>
                    </div>
                    <div className="info-row">
                        <label>Role:</label>
                        <span className="role-badge">{user?.role || 'viewer'}</span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SecuritySettings;
