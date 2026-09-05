import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import api, { getSetupStatus } from '../../services/api';
import './Auth.css';

const STEP_ORDER = [
    { id: 'account', label: 'Account' },
    { id: 'network', label: 'Network' },
    { id: 'devices', label: 'Devices' },
    { id: 'done', label: 'Done' },
];

function guessLanCidr(hostname) {
    const parts = String(hostname || '').split('.');
    if (parts.length !== 4) {
        return '';
    }
    const octets = parts.map((part) => Number(part));
    if (octets.some((n) => !Number.isInteger(n) || n < 0 || n > 255)) {
        return '';
    }
    const [a, b, c] = octets;
    const isLan =
        a === 10 ||
        (a === 192 && b === 168) ||
        (a === 172 && b >= 16 && b <= 31);
    if (!isLan) {
        return '';
    }
    return `${a}.${b}.${c}.0/24`;
}

function hostDisplayName(host) {
    return host.mdns_name || host.hostname || host.ip_address;
}

function hasSuggestedName(host) {
    const name = (host.mdns_name || host.hostname || '').trim();
    return Boolean(name) && name !== host.ip_address;
}

function apiErrorMessage(err, fallback) {
    return err.response?.data?.error || err.response?.data?.detail || fallback;
}

function StepIndicator({ current }) {
    const currentIndex = STEP_ORDER.findIndex((step) => step.id === current);
    return (
        <nav className="setup-steps" aria-label="Setup progress">
            {STEP_ORDER.map((step, index) => (
                <React.Fragment key={step.id}>
                    {index > 0 && <span className="setup-step-sep" aria-hidden="true">→</span>}
                    <span
                        className={`setup-step${index === currentIndex ? ' is-active' : ''}${index < currentIndex ? ' is-done' : ''}`}
                    >
                        {step.label}
                    </span>
                </React.Fragment>
            ))}
        </nav>
    );
}

const Setup = () => {
    const [step, setStep] = useState('account');
    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: '',
        confirmPassword: ''
    });
    const [network, setNetwork] = useState(() => guessLanCidr(window.location.hostname));
    const [hosts, setHosts] = useState([]);
    const [selected, setSelected] = useState(() => new Set());
    const [error, setError] = useState('');
    const [busy, setBusy] = useState('');
    const { register, login, checkSetup } = useAuth();
    const navigate = useNavigate();

    useEffect(() => {
        if (step !== 'account') {
            return;
        }
        let cancelled = false;
        const checkStatus = async () => {
            try {
                const response = await getSetupStatus();
                if (!cancelled && response.data.is_setup) {
                    navigate('/login');
                }
            } catch (err) {
                console.error('Failed to check setup status', err);
            }
        };
        checkStatus();
        return () => {
            cancelled = true;
        };
    }, [navigate, step]);

    const finishWizard = async () => {
        setError('');
        setBusy('finish');
        await checkSetup();
        navigate('/', { replace: true });
    };

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const handleAccountSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (formData.password !== formData.confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        if (formData.password.length < 6) {
            setError('Password must be at least 6 characters');
            return;
        }

        setBusy('register');

        const result = await register(formData.username, formData.email, formData.password);

        if (!result.success) {
            setError(result.error);
            setBusy('');
            return;
        }

        // Stay on /setup: do not call checkSetup() here or App.js will unmount this page.
        const loginResult = await login(formData.username, formData.password);
        if (!loginResult.success) {
            setError(
                `${loginResult.error} Your admin account was created. You can log in manually if automatic sign-in does not work.`
            );
        }

        setStep('network');
        setBusy('');
    };

    const handleScan = async (e) => {
        e.preventDefault();
        setError('');
        const cidr = network.trim();
        if (!cidr) {
            setError('Enter a LAN subnet in CIDR notation.');
            return;
        }

        setBusy('scan');
        try {
            const response = await api.post('/inventory/discovery/scan/', {
                network: cidr,
                scan_type: 'quick',
            });
            const found = response.data?.hosts || [];
            setHosts(found);
            setSelected(new Set(found.filter(hasSuggestedName).map((host) => host.ip_address)));
            setStep('devices');
        } catch (err) {
            setError(apiErrorMessage(err, 'Scan failed. Check the subnet and try again.'));
        } finally {
            setBusy('');
        }
    };

    const toggleHost = (ip) => {
        setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(ip)) {
                next.delete(ip);
            } else {
                next.add(ip);
            }
            return next;
        });
    };

    const handleImport = async () => {
        setError('');
        if (selected.size === 0) {
            setError('Select at least one host, or skip this step.');
            return;
        }

        setBusy('import');
        try {
            const hostsToImport = hosts.filter((host) => selected.has(host.ip_address));
            await api.post('/inventory/discovery/import_hosts/', { hosts: hostsToImport });
            await checkSetup();
            navigate('/', { replace: true });
        } catch (err) {
            setError(apiErrorMessage(err, 'Could not import hosts.'));
            setBusy('');
        }
    };

    const heading = {
        account: { title: 'Initial Setup', subtitle: 'Create your Admin Account' },
        network: { title: 'Initial Setup', subtitle: 'Scan your LAN' },
        devices: { title: 'Initial Setup', subtitle: 'Import devices' },
    }[step];

    return (
        <div className="auth-container">
            <div className={`auth-card${step !== 'account' ? ' setup-card-wide' : ''}`}>
                <div className="auth-header">
                    <h1>{heading.title}</h1>
                    <p>{heading.subtitle}</p>
                </div>

                <StepIndicator current={step} />

                {step === 'account' && (
                    <form onSubmit={handleAccountSubmit} className="auth-form">
                        {error && <div className="error-message">{error}</div>}

                        <div className="form-group">
                            <label htmlFor="username">Username</label>
                            <input
                                type="text"
                                id="username"
                                name="username"
                                value={formData.username}
                                onChange={handleChange}
                                required
                                autoFocus
                                placeholder="admin"
                                disabled={Boolean(busy)}
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="email">Email</label>
                            <input
                                type="email"
                                id="email"
                                name="email"
                                value={formData.email}
                                onChange={handleChange}
                                required
                                placeholder="admin@example.com"
                                disabled={Boolean(busy)}
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="password">Password</label>
                            <input
                                type="password"
                                id="password"
                                name="password"
                                value={formData.password}
                                onChange={handleChange}
                                required
                                minLength="6"
                                placeholder="At least 6 characters"
                                disabled={Boolean(busy)}
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="confirmPassword">Confirm Password</label>
                            <input
                                type="password"
                                id="confirmPassword"
                                name="confirmPassword"
                                value={formData.confirmPassword}
                                onChange={handleChange}
                                required
                                placeholder="Re-enter your password"
                                disabled={Boolean(busy)}
                            />
                        </div>

                        <button type="submit" className="auth-button" disabled={Boolean(busy)}>
                            {busy === 'register' ? 'Creating Admin...' : 'Create Admin'}
                        </button>
                    </form>
                )}

                {step === 'network' && (
                    <form onSubmit={handleScan} className="auth-form">
                        {error && <div className="error-message">{error}</div>}

                        <p className="setup-help">
                            Enter the subnet Duck Monitoring should scan. Use CIDR notation.
                        </p>

                        <div className="form-group">
                            <label htmlFor="network">LAN subnet</label>
                            <input
                                type="text"
                                id="network"
                                name="network"
                                value={network}
                                onChange={(e) => setNetwork(e.target.value)}
                                required
                                autoFocus
                                placeholder="192.168.1.0/24"
                                disabled={Boolean(busy)}
                                autoComplete="off"
                            />
                        </div>

                        <button type="submit" className="auth-button" disabled={Boolean(busy)}>
                            {busy === 'scan' ? 'Scanning network...' : 'Scan network'}
                        </button>
                        <button
                            type="button"
                            className="back-button"
                            onClick={finishWizard}
                            disabled={Boolean(busy)}
                        >
                            {busy === 'finish' ? 'Finishing...' : 'Skip'}
                        </button>
                    </form>
                )}

                {step === 'devices' && (
                    <div className="auth-form">
                        {error && <div className="error-message">{error}</div>}

                        {hosts.length === 0 ? (
                            <p className="setup-help">
                                No devices were found on this subnet. You can scan again or skip
                                and add hosts later from Discovery.
                            </p>
                        ) : (
                            <p className="setup-help">
                                Named hosts are selected. Review the list and import the devices
                                you want to monitor.
                            </p>
                        )}

                        {hosts.length > 0 && (
                            <div className="setup-host-list">
                                {hosts.map((host) => {
                                    const isSelected = selected.has(host.ip_address);
                                    const extra = [host.vendor, host.device_class]
                                        .filter((value) => value && value !== 'unknown')
                                        .join(' · ');
                                    return (
                                        <label
                                            key={host.ip_address}
                                            className={`setup-host-item${isSelected ? ' is-selected' : ''}`}
                                        >
                                            <input
                                                type="checkbox"
                                                checked={isSelected}
                                                onChange={() => toggleHost(host.ip_address)}
                                                disabled={Boolean(busy)}
                                            />
                                            <span className="setup-host-meta">
                                                <span className="setup-host-name">{hostDisplayName(host)}</span>
                                                <span className="setup-host-detail">
                                                    {host.ip_address}
                                                    {extra ? ` · ${extra}` : ''}
                                                </span>
                                            </span>
                                        </label>
                                    );
                                })}
                            </div>
                        )}

                        {hosts.length === 0 ? (
                            <button
                                type="button"
                                className="auth-button"
                                onClick={() => {
                                    setError('');
                                    setStep('network');
                                }}
                                disabled={Boolean(busy)}
                            >
                                Scan again
                            </button>
                        ) : (
                            <button
                                type="button"
                                className="auth-button"
                                onClick={handleImport}
                                disabled={Boolean(busy) || selected.size === 0}
                            >
                                {busy === 'import' ? 'Importing...' : 'Import selected'}
                            </button>
                        )}
                        <button
                            type="button"
                            className="back-button"
                            onClick={finishWizard}
                            disabled={Boolean(busy)}
                        >
                            {busy === 'finish' ? 'Finishing...' : 'Skip'}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Setup;
