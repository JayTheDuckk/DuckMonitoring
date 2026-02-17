import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import api, { getAlerts, getAlertRules, getChannels } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import './AlertsDashboard.css';

const AlertsDashboard = () => {
    const { user } = useAuth();
    const [alerts, setAlerts] = useState([]);
    const [rules, setRules] = useState([]);
    const [channels, setChannels] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState('alerts');

    // Filters
    const [statusFilter, setStatusFilter] = useState('');
    const [severityFilter, setSeverityFilter] = useState('');

    // Modal states
    const [showAcknowledgeModal, setShowAcknowledgeModal] = useState(false);
    const [selectedAlert, setSelectedAlert] = useState(null);
    const [acknowledgeNote, setAcknowledgeNote] = useState('');

    const isAdmin = user?.is_admin || user?.role === 'admin';

    const fetchAlertsData = useCallback(async () => {
        try {
            // Using raw api.get for filtering params, or could enhance getAlerts in api.js
            // let's stick to raw for complex filtering if getAlerts doesn't support it well yet
            // actually api.js getAlerts doesn't take params.
            // But api.js base URL is /api so `/alerts/alerts/` is correct.
            // Old code was `/alerts?params`. New is `/alerts/alerts/?params`

            const params = new URLSearchParams();
            if (statusFilter) params.append('status', statusFilter);
            if (severityFilter) params.append('severity', severityFilter);

            const response = await api.get(`/alerts/alerts/?${params.toString()}`);
            // Handle different response formats (array, paginated, or object)
            const alertsData = Array.isArray(response.data) 
                ? response.data 
                : response.data.results || response.data.data || [];
            setAlerts(alertsData);
        } catch (err) {
            console.error('Failed to fetch alerts:', err);
            // Ensure alerts is always an array even on error
            setAlerts([]);
        }
    }, [statusFilter, severityFilter]);

    const fetchRulesData = useCallback(async () => {
        try {
            const response = await getAlertRules();
            // Handle different response formats (array, paginated, or object)
            const rulesData = Array.isArray(response.data) 
                ? response.data 
                : response.data.results || response.data.data || [];
            setRules(rulesData);
        } catch (err) {
            console.error('Failed to fetch rules:', err);
            // Ensure rules is always an array even on error
            setRules([]);
        }
    }, []);

    const fetchChannelsData = useCallback(async () => {
        try {
            const response = await getChannels();
            // Handle different response formats (array, paginated, or object)
            const channelsData = Array.isArray(response.data) 
                ? response.data 
                : response.data.results || response.data.data || [];
            setChannels(channelsData);
        } catch (err) {
            console.error('Failed to fetch channels:', err);
            // Ensure channels is always an array even on error
            setChannels([]);
        }
    }, []);

    useEffect(() => {
        const loadData = async () => {
            setLoading(true);
            await Promise.all([fetchAlertsData(), fetchRulesData(), fetchChannelsData()]);
            setLoading(false);
        };
        loadData();

        // Auto-refresh alerts every 30 seconds
        const interval = setInterval(fetchAlertsData, 30000);
        return () => clearInterval(interval);
    }, [fetchAlertsData, fetchRulesData, fetchChannelsData]);

    const handleAcknowledge = async () => {
        if (!selectedAlert) return;

        try {
            // New endpoint for acknowledge? 
            // My AlertViewSet doesn't have custom actions for acknowledge yet!
            // I need to add that to backend or use standard update.
            // For now, let's assume standard update (PATCH) of status=acknowledged

            await api.patch(`/alerts/alerts/${selectedAlert.id}/`, {
                status: 'acknowledged',
                note: acknowledgeNote
            });

            setShowAcknowledgeModal(false);
            setSelectedAlert(null);
            setAcknowledgeNote('');
            fetchAlertsData();
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to acknowledge alert');
        }
    };

    const handleResolve = async (alertId) => {
        try {
            // Similar for resolve -> PATCH status=resolved
            await api.patch(`/alerts/alerts/${alertId}/`, { status: 'resolved' });
            fetchAlertsData();
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to resolve alert');
        }
    };

    const getSeverityIcon = (severity) => {
        switch (severity) {
            case 'critical': return '🔴';
            case 'warning': return '🟡';
            case 'info': return '🔵';
            default: return '⚪';
        }
    };

    const getStatusBadgeClass = (status) => {
        switch (status) {
            case 'firing': return 'badge-firing';
            case 'acknowledged': return 'badge-acknowledged';
            case 'resolved': return 'badge-resolved';
            default: return '';
        }
    };

    const formatTime = (timestamp) => {
        if (!timestamp) return '-';
        return new Date(timestamp).toLocaleString();
    };

    const activeAlertCount = Array.isArray(alerts) ? alerts.filter(a => a.status === 'firing').length : 0;
    const acknowledgedCount = Array.isArray(alerts) ? alerts.filter(a => a.status === 'acknowledged').length : 0;

    if (loading) {
        return <div className="alerts-loading">Loading alerts...</div>;
    }

    return (
        <div className="alerts-container">
            <div className="alerts-header">
                <div className="header-content">
                    <h1>Alerts</h1>
                    <p className="subtitle">Monitor and manage system alerts</p>
                </div>
                <div className="header-stats">
                    <div className="stat firing">
                        <span className="stat-value">{activeAlertCount}</span>
                        <span className="stat-label">Firing</span>
                    </div>
                    <div className="stat acknowledged">
                        <span className="stat-value">{acknowledgedCount}</span>
                        <span className="stat-label">Acknowledged</span>
                    </div>
                </div>
            </div>

            {error && <div className="alerts-error">{error}</div>}

            {/* Tabs */}
            <div className="alerts-tabs">
                <button
                    className={`tab ${activeTab === 'alerts' ? 'active' : ''}`}
                    onClick={() => setActiveTab('alerts')}
                >
                    Active Alerts
                </button>
                <button
                    className={`tab ${activeTab === 'rules' ? 'active' : ''}`}
                    onClick={() => setActiveTab('rules')}
                >
                    Alert Rules ({rules.length})
                </button>
                <button
                    className={`tab ${activeTab === 'channels' ? 'active' : ''}`}
                    onClick={() => setActiveTab('channels')}
                >
                    Notification Channels ({channels.length})
                </button>
            </div>

            {/* Alerts Tab */}
            {activeTab === 'alerts' && (
                <div className="alerts-content">
                    <div className="alerts-filters">
                        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                            <option value="">All Active</option>
                            <option value="firing">Firing</option>
                            <option value="acknowledged">Acknowledged</option>
                            <option value="resolved">Resolved</option>
                        </select>
                        <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
                            <option value="">All Severities</option>
                            <option value="critical">Critical</option>
                            <option value="warning">Warning</option>
                            <option value="info">Info</option>
                        </select>
                    </div>

                    <div className="alerts-list">
                        {!Array.isArray(alerts) || alerts.length === 0 ? (
                            <div className="no-alerts">
                                <span className="no-alerts-icon">✓</span>
                                <p>No active alerts</p>
                            </div>
                        ) : (
                            alerts.map(alert => (
                                <div key={alert.id} className={`alert-card ${alert.severity}`}>
                                    <div className="alert-header">
                                        <div className="alert-severity">
                                            {getSeverityIcon(alert.severity)}
                                        </div>
                                        <div className="alert-info">
                                            <h3>{alert.title}</h3>
                                            <p className="alert-message">{alert.message}</p>
                                        </div>
                                        <span className={`status-badge ${getStatusBadgeClass(alert.status)}`}>
                                            {alert.status}
                                        </span>
                                    </div>
                                    <div className="alert-meta">
                                        <span>Triggered: {formatTime(alert.triggered_at)}</span>
                                        {alert.acknowledged_at && (
                                            <span>Acknowledged: {formatTime(alert.acknowledged_at)}</span>
                                        )}
                                    </div>
                                    <div className="alert-actions">
                                        {alert.status === 'firing' && (
                                            <button
                                                className="btn-acknowledge"
                                                onClick={() => {
                                                    setSelectedAlert(alert);
                                                    setShowAcknowledgeModal(true);
                                                }}
                                            >
                                                Acknowledge
                                            </button>
                                        )}
                                        {alert.status !== 'resolved' && (
                                            <button
                                                className="btn-resolve"
                                                onClick={() => handleResolve(alert.id)}
                                            >
                                                Resolve
                                            </button>
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}

            {/* Rules Tab */}
            {activeTab === 'rules' && (
                <div className="rules-content">
                    {isAdmin && (
                        <div className="rules-actions">
                            <Link to="/alerts/rules/new" className="btn-primary">
                                + Create Rule
                            </Link>
                        </div>
                    )}
                    <div className="rules-list">
                        {Array.isArray(rules) && rules.length > 0 ? (
                            rules.map(rule => (
                            <div key={rule.id} className="rule-card">
                                <div className="rule-header">
                                    <h3>{rule.name}</h3>
                                    <span className={`severity-badge ${rule.severity}`}>
                                        {rule.severity}
                                    </span>
                                </div>
                                <p className="rule-description">{rule.description || 'No description'}</p>
                                <div className="rule-meta">
                                    <span>Type: {rule.condition_type}</span>
                                    <span className={`enabled-badge ${rule.enabled ? 'enabled' : 'disabled'}`}>
                                        {rule.enabled ? 'Enabled' : 'Disabled'}
                                    </span>
                                </div>
                            </div>
                        ))
                        ) : (
                            <div className="no-alerts">
                                <span className="no-alerts-icon">📋</span>
                                <p>No alert rules configured</p>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Channels Tab */}
            {activeTab === 'channels' && (
                <div className="channels-content">
                    {isAdmin && (
                        <div className="channels-actions">
                            <Link to="/alerts/channels/new" className="btn-primary">
                                + Add Channel
                            </Link>
                        </div>
                    )}
                    <div className="channels-list">
                        {Array.isArray(channels) && channels.length > 0 ? (
                            channels.map(channel => (
                            <div key={channel.id} className="channel-card">
                                <div className="channel-icon">
                                    {channel.channel_type === 'email' && '📧'}
                                    {channel.channel_type === 'slack' && '💬'}
                                    {channel.channel_type === 'discord' && '🎮'}
                                    {channel.channel_type === 'webhook' && '🔗'}
                                </div>
                                <div className="channel-info">
                                    <h3>{channel.name}</h3>
                                    <p className="channel-type">{channel.channel_type}</p>
                                </div>
                            </div>
                        ))
                        ) : (
                            <div className="no-alerts">
                                <span className="no-alerts-icon">📡</span>
                                <p>No notification channels configured</p>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Acknowledge Modal */}
            {showAcknowledgeModal && (
                <div className="modal-overlay" onClick={() => setShowAcknowledgeModal(false)}>
                    <div className="modal" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>Acknowledge Alert</h2>
                            <button className="modal-close" onClick={() => setShowAcknowledgeModal(false)}>×</button>
                        </div>
                        <div className="modal-content">
                            <p>You are acknowledging: <strong>{selectedAlert?.title}</strong></p>
                            <div className="form-group">
                                <label>Note (optional)</label>
                                <textarea
                                    value={acknowledgeNote}
                                    onChange={(e) => setAcknowledgeNote(e.target.value)}
                                    placeholder="Add a note about this acknowledgment..."
                                    rows={3}
                                />
                            </div>
                        </div>
                        <div className="modal-actions">
                            <button className="btn-secondary" onClick={() => setShowAcknowledgeModal(false)}>
                                Cancel
                            </button>
                            <button className="btn-primary" onClick={handleAcknowledge}>
                                Acknowledge
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AlertsDashboard;
