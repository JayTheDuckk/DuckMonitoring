import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api, { getHosts, getChannels } from '../../services/api';
import { useToast } from '../../contexts/ToastContext';
import './AlertsDashboard.css';

const RuleForm = () => {
    const { ruleId } = useParams();
    const navigate = useNavigate();
    const { showToast } = useToast();
    const isEditMode = !!ruleId;

    const [formData, setFormData] = useState({
        name: '',
        description: '',
        host: '',
        host_group: '', // Not implemented in UI yet
        condition_type: 'threshold',
        condition: {
            field: 'status',
            operator: 'equals',
            value: 'critical'
        },
        severity: 'warning',
        duration_seconds: 0,
        channels: [],
        enabled: true
    });

    const [hosts, setHosts] = useState([]);
    const [availableChannels, setAvailableChannels] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchDependencies();
        if (isEditMode) {
            fetchRule();
        }
    }, [ruleId]);

    const fetchDependencies = async () => {
        try {
            const [hostsRes, channelsRes] = await Promise.all([
                getHosts(),
                getChannels()
            ]);

            setHosts(Array.isArray(hostsRes.data) ? hostsRes.data : hostsRes.data.results || []);
            setAvailableChannels(Array.isArray(channelsRes.data) ? channelsRes.data : channelsRes.data.results || []);
        } catch (err) {
            console.error("Failed to load dependencies", err);
        }
    };

    const fetchRule = async () => {
        try {
            const response = await api.get(`/alerts/rules/${ruleId}/`);
            const data = response.data;
            setFormData({
                name: data.name,
                description: data.description,
                host: data.host,
                host_group: data.host_group,
                condition_type: data.condition_type,
                condition: data.condition,
                severity: data.severity,
                duration_seconds: data.duration_seconds,
                channels: data.channels,
                enabled: data.enabled
            });
        } catch (err) {
            setError('Failed to fetch rule details');
            showToast('Failed to load rule', 'error');
        }
    };

    const handleConditionChange = (field, value) => {
        setFormData({
            ...formData,
            condition: {
                ...formData.condition,
                [field]: value
            }
        });
    };

    const handleChannelToggle = (channelId) => {
        const currentIds = formData.channels;
        if (currentIds.includes(channelId)) {
            setFormData({
                ...formData,
                channels: currentIds.filter(id => id !== channelId)
            });
        } else {
            setFormData({
                ...formData,
                channels: [...currentIds, channelId]
            });
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            if (isEditMode) {
                await api.put(`/alerts/rules/${ruleId}/`, formData);
                showToast('Rule updated successfully', 'success');
            } else {
                await api.post('/alerts/rules/', formData);
                showToast('Rule created successfully', 'success');
            }
            navigate('/alerts');
        } catch (err) {
            const msg = err.response?.data?.name?.[0] || 'Failed to save rule';
            setError(msg);
            showToast(msg, 'error');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="alerts-container">
            <div className="alerts-header">
                <div className="header-content">
                    <h1>{isEditMode ? 'Edit Alert Rule' : 'New Alert Rule'}</h1>
                    <p className="subtitle">Define conditions creating alerts</p>
                </div>
            </div>

            <div className="alerts-content" style={{ maxWidth: '800px' }}>
                {error && <div className="alerts-error">{error}</div>}

                <form onSubmit={handleSubmit} className="channel-form">
                    <div className="form-section">
                        <h3>General Info</h3>
                        <div className="form-group">
                            <label>Rule Name</label>
                            <input
                                type="text"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                required
                                placeholder="e.g., Web Server Down"
                            />
                        </div>
                        <div className="form-group">
                            <label>Description</label>
                            <textarea
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                rows={2}
                            />
                        </div>
                        <div className="form-group">
                            <label>Severity</label>
                            <select
                                value={formData.severity}
                                onChange={(e) => setFormData({ ...formData, severity: e.target.value })}
                            >
                                <option value="info">Info</option>
                                <option value="warning">Warning</option>
                                <option value="critical">Critical</option>
                            </select>
                        </div>
                    </div>

                    <div className="form-section">
                        <h3>Target</h3>
                        <div className="form-group">
                            <label>Apply to Host</label>
                            <select
                                value={formData.host || ''}
                                onChange={(e) => setFormData({ ...formData, host: e.target.value || null })}
                            >
                                <option value="">-- Apply to Host Group (Not Implemented) --</option>
                                {hosts.map(h => (
                                    <option key={h.id} value={h.id}>{h.display_name || h.hostname} ({h.ip_address})</option>
                                ))}
                            </select>
                            <small>Currently only direct host assignment is supported via UI.</small>
                        </div>
                    </div>

                    <div className="form-section">
                        <h3>Condition</h3>
                        <div className="form-group-row">
                            <div className="form-group">
                                <label>Field</label>
                                <select
                                    value={formData.condition.field}
                                    onChange={(e) => handleConditionChange('field', e.target.value)}
                                >
                                    <option value="status">Service Status</option>
                                    <option value="response_time">Response Time (ms)</option>
                                </select>
                            </div>
                            <div className="form-group">
                                <label>Operator</label>
                                <select
                                    value={formData.condition.operator}
                                    onChange={(e) => handleConditionChange('operator', e.target.value)}
                                >
                                    {formData.condition.field === 'status' ? (
                                        <>
                                            <option value="equals">Equals</option>
                                            <option value="not_equals">Not Equals</option>
                                        </>
                                    ) : (
                                        <>
                                            <option value="gt">Greater Than</option>
                                            <option value="lt">Less Than</option>
                                        </>
                                    )}
                                </select>
                            </div>
                            <div className="form-group">
                                <label>Value</label>
                                {formData.condition.field === 'status' ? (
                                    <select
                                        value={formData.condition.value}
                                        onChange={(e) => handleConditionChange('value', e.target.value)}
                                    >
                                        <option value="ok">OK</option>
                                        <option value="warning">Warning</option>
                                        <option value="critical">Critical</option>
                                        <option value="unknown">Unknown</option>
                                    </select>
                                ) : (
                                    <input
                                        type="number"
                                        value={formData.condition.value}
                                        onChange={(e) => handleConditionChange('value', e.target.value)}
                                    />
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="form-section">
                        <h3>Notifications</h3>
                        <div className="form-group">
                            <label>Send alerts to:</label>
                            <div className="channel-select-list">
                                {availableChannels.map(channel => (
                                    <label key={channel.id} className="channel-option">
                                        <input
                                            type="checkbox"
                                            checked={formData.channels.includes(channel.id)}
                                            onChange={() => handleChannelToggle(channel.id)}
                                        />
                                        <span>{channel.name} ({channel.channel_type})</span>
                                    </label>
                                ))}
                                {availableChannels.length === 0 && (
                                    <p className="no-data">No channels configured. Create one first!</p>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="form-group checkbox-group">
                        <label>
                            <input
                                type="checkbox"
                                checked={formData.enabled}
                                onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                            />
                            Enable this rule
                        </label>
                    </div>

                    <div className="form-actions">
                        <button type="button" className="btn-secondary" onClick={() => navigate('/alerts')}>
                            Cancel
                        </button>
                        <button type="submit" className="btn-primary" disabled={loading}>
                            {loading ? 'Saving...' : (isEditMode ? 'Update Rule' : 'Create Rule')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default RuleForm;
