import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api, { getChannels } from '../../services/api';
import { useToast } from '../../contexts/ToastContext';
import './AlertsDashboard.css'; // Re-use styles

const ChannelForm = () => {
    const { channelId } = useParams();
    const navigate = useNavigate();
    const { showToast } = useToast();
    const isEditMode = !!channelId;

    const [formData, setFormData] = useState({
        name: '',
        channel_type: 'email',
        config: {},
        enabled: true
    });

    // Config fields based on type
    const [emailTo, setEmailTo] = useState('');
    const [webhookUrl, setWebhookUrl] = useState('');

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (isEditMode) {
            fetchChannel();
        }
    }, [channelId]);

    const fetchChannel = async () => {
        try {
            const response = await api.get(`/alerts/channels/${channelId}/`);
            const data = response.data;
            setFormData({
                name: data.name,
                channel_type: data.channel_type,
                config: data.config,
                enabled: data.enabled
            });

            // Populate helper fields
            if (data.channel_type === 'email') {
                setEmailTo(data.config.email || data.config.to || '');
            } else {
                setWebhookUrl(data.config.webhook_url || data.config.url || '');
            }
        } catch (err) {
            setError('Failed to fetch channel details');
            showToast('Failed to load channel', 'error');
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        // Build config object
        let config = {};
        if (formData.channel_type === 'email') {
            config = { email: emailTo };
        } else {
            config = { webhook_url: webhookUrl };
        }

        const payload = {
            ...formData,
            config
        };

        try {
            if (isEditMode) {
                await api.put(`/alerts/channels/${channelId}/`, payload);
                showToast('Channel updated successfully', 'success');
            } else {
                await api.post('/alerts/channels/', payload);
                showToast('Channel created successfully', 'success');
            }
            navigate('/alerts');
        } catch (err) {
            const msg = err.response?.data?.name?.[0] || 'Failed to save channel';
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
                    <h1>{isEditMode ? 'Edit Channel' : 'New Notification Channel'}</h1>
                    <p className="subtitle">Configure where alerts are sent</p>
                </div>
            </div>

            <div className="alerts-content" style={{ maxWidth: '600px' }}>
                {error && <div className="alerts-error">{error}</div>}

                <form onSubmit={handleSubmit} className="channel-form">
                    <div className="form-group">
                        <label>Name</label>
                        <input
                            type="text"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            required
                            placeholder="e.g., DevOps Slack"
                        />
                    </div>

                    <div className="form-group">
                        <label>Type</label>
                        <select
                            value={formData.channel_type}
                            onChange={(e) => setFormData({ ...formData, channel_type: e.target.value })}
                        >
                            <option value="email">Email</option>
                            <option value="slack">Slack</option>
                            <option value="discord">Discord</option>
                            <option value="webhook">Webhook</option>
                        </select>
                    </div>

                    {formData.channel_type === 'email' && (
                        <div className="form-group">
                            <label>Recipient Email</label>
                            <input
                                type="email"
                                value={emailTo}
                                onChange={(e) => setEmailTo(e.target.value)}
                                required
                                placeholder="alert@example.com"
                            />
                        </div>
                    )}

                    {['slack', 'discord', 'webhook'].includes(formData.channel_type) && (
                        <div className="form-group">
                            <label>Webhook URL</label>
                            <input
                                type="url"
                                value={webhookUrl}
                                onChange={(e) => setWebhookUrl(e.target.value)}
                                required
                                placeholder="https://hooks.slack.com/services/..."
                            />
                        </div>
                    )}

                    <div className="form-group checkbox-group">
                        <label>
                            <input
                                type="checkbox"
                                checked={formData.enabled}
                                onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                            />
                            Enable this channel
                        </label>
                    </div>

                    <div className="form-actions">
                        <button type="button" className="btn-secondary" onClick={() => navigate('/alerts')}>
                            Cancel
                        </button>
                        <button type="submit" className="btn-primary" disabled={loading}>
                            {loading ? 'Saving...' : (isEditMode ? 'Update Channel' : 'Create Channel')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default ChannelForm;
