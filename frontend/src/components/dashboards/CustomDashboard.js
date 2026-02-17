import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import './CustomDashboard.css';

// Widget Components
const HostStatusWidget = ({ config, data }) => {
    if (!data) return <div className="widget-loading">Loading...</div>;

    const statusColors = { up: '#16a34a', down: '#dc2626', unknown: '#6b7280' };

    return (
        <div className="host-status-widget">
            <div className="host-name">{data.hostname || 'Unknown Host'}</div>
            <div
                className="host-status"
                style={{ color: statusColors[data.status] || statusColors.unknown }}
            >
                {data.status?.toUpperCase()}
            </div>
            {data.ip_address && <div className="host-ip">{data.ip_address}</div>}
        </div>
    );
};

const AlertListWidget = ({ config, data }) => {
    if (!data) return <div className="widget-loading">Loading...</div>;

    return (
        <div className="alert-list-widget">
            {data.length === 0 ? (
                <div className="no-alerts">✓ No active alerts</div>
            ) : (
                <ul className="alert-items">
                    {data.map(alert => (
                        <li key={alert.id} className={`alert-item ${alert.severity}`}>
                            <span className="alert-severity">
                                {alert.severity === 'critical' ? '🔴' : alert.severity === 'warning' ? '🟡' : '🔵'}
                            </span>
                            <span className="alert-title">{alert.title}</span>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
};

const ClockWidget = ({ config }) => {
    const [time, setTime] = useState(new Date());

    useEffect(() => {
        const interval = setInterval(() => setTime(new Date()), 1000);
        return () => clearInterval(interval);
    }, []);

    const format = config?.format || '24h';
    const timeString = format === '12h'
        ? time.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true })
        : time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

    return (
        <div className="clock-widget">
            <div className="clock-time">{timeString}</div>
            <div className="clock-date">{time.toLocaleDateString()}</div>
        </div>
    );
};

const TextWidget = ({ config }) => (
    <div className="text-widget">
        <div className="text-content">{config?.content || 'No content'}</div>
    </div>
);

const ServiceGridWidget = ({ config, data }) => {
    if (!data) return <div className="widget-loading">Loading...</div>;

    return (
        <div className="service-grid-widget">
            {data.map(host => (
                <div key={host.id} className={`grid-host ${host.status}`}>
                    <span className="grid-hostname">{host.hostname}</span>
                </div>
            ))}
        </div>
    );
};

const HostGroupSummaryWidget = ({ config, data }) => {
    if (!data) return <div className="widget-loading">Loading...</div>;

    return (
        <div className="group-summary-widget">
            <div className="group-name">{data.group?.name || 'Group'}</div>
            <div className="group-stats">
                <span className="stat up">{data.up} Up</span>
                <span className="stat down">{data.down} Down</span>
                <span className="stat unknown">{data.unknown} Unknown</span>
            </div>
        </div>
    );
};

const GenericWidget = ({ widgetType }) => (
    <div className="generic-widget">
        <div className="widget-icon">📊</div>
        <div className="widget-type">{widgetType}</div>
    </div>
);

// Widget renderer based on type
const renderWidget = (widget, data) => {
    switch (widget.widget_type) {
        case 'host_status':
            return <HostStatusWidget config={widget.config} data={data} />;
        case 'alert_list':
            return <AlertListWidget config={widget.config} data={data} />;
        case 'clock':
            return <ClockWidget config={widget.config} />;
        case 'text_widget':
            return <TextWidget config={widget.config} />;
        case 'service_grid':
            return <ServiceGridWidget config={widget.config} data={data} />;
        case 'host_group_summary':
            return <HostGroupSummaryWidget config={widget.config} data={data} />;
        default:
            return <GenericWidget widgetType={widget.widget_type} />;
    }
};

const CustomDashboard = () => {
    const { dashboardId } = useParams();
    const navigate = useNavigate();
    const { user } = useAuth();

    const [dashboards, setDashboards] = useState([]);
    const [currentDashboard, setCurrentDashboard] = useState(null);
    const [widgetData, setWidgetData] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchDashboards = useCallback(async () => {
        try {
            const response = await api.get('/monitoring/dashboards/');
            setDashboards(response.data.results || response.data); // Handle pagination if present
        } catch (err) {
            console.error('Failed to fetch dashboards:', err);
        }
    }, []);

    const fetchDashboard = useCallback(async (id) => {
        try {
            setLoading(true);
            const response = await api.get(`/monitoring/dashboards/${id}/`);
            setCurrentDashboard(response.data);

            // Fetch data for each widget
            if (response.data.widgets) {
                const dataPromises = response.data.widgets.map(async (widget) => {
                    try {
                        const dataResponse = await api.get(`/monitoring/widgets/${widget.id}/data/`);
                        return { id: widget.id, data: dataResponse.data };
                    } catch (err) {
                        return { id: widget.id, data: null };
                    }
                });

                const results = await Promise.all(dataPromises);
                const dataMap = {};
                results.forEach(result => {
                    dataMap[result.id] = result.data;
                });
                setWidgetData(dataMap);
            }
        } catch (err) {
            setError('Failed to load dashboard');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchDashboards();
    }, [fetchDashboards]);

    useEffect(() => {
        if (dashboardId) {
            fetchDashboard(dashboardId);
        } else if (dashboards.length > 0 && !dashboardId) {
            // Navigate to first dashboard if none selected
            navigate(`/dashboards/${dashboards[0].id}`, { replace: true });
        }
    }, [dashboardId, dashboards, fetchDashboard, navigate]);

    // Auto-refresh widget data
    useEffect(() => {
        if (!currentDashboard || !currentDashboard.widgets) return;

        const interval = setInterval(() => {
            currentDashboard.widgets.forEach(async (widget) => {
                if (widget.refresh_interval > 0) {
                    try {
                        const response = await api.get(`/monitoring/widgets/${widget.id}/data/`);
                        setWidgetData(prev => ({ ...prev, [widget.id]: response.data }));
                    } catch (err) {
                        console.error(`Failed to refresh widget ${widget.id}`);
                    }
                }
            });
        }, 30000);

        return () => clearInterval(interval);
    }, [currentDashboard]);

    const handleCreateDashboard = async () => {
        try {
            const response = await api.post('/monitoring/dashboards/', { name: 'New Dashboard' });
            setDashboards([...dashboards, response.data]);
            navigate(`/dashboards/${response.data.id}`);
        } catch (err) {
            setError('Failed to create dashboard');
        }
    };

    const handleDeleteDashboard = async (id) => {
        if (!window.confirm('Delete this dashboard?')) return;

        try {
            await api.delete(`/monitoring/dashboards/${id}/`);
            setDashboards(dashboards.filter(d => d.id !== id));
            if (currentDashboard?.id === id) {
                navigate('/dashboards');
            }
        } catch (err) {
            setError('Failed to delete dashboard');
        }
    };

    const isOwner = currentDashboard && user && currentDashboard.user_id === user.id;

    if (loading && !currentDashboard) {
        return <div className="dashboard-loading">Loading dashboards...</div>;
    }

    return (
        <div className="custom-dashboard-container">
            {/* Sidebar */}
            <div className="dashboard-sidebar">
                <div className="sidebar-header">
                    <h2>Dashboards</h2>
                    <button className="btn-add" onClick={handleCreateDashboard}>+</button>
                </div>

                <div className="dashboard-list">
                    {dashboards.map(dashboard => (
                        <div
                            key={dashboard.id}
                            className={`dashboard-item ${currentDashboard?.id === dashboard.id ? 'active' : ''}`}
                        >
                            <Link to={`/dashboards/${dashboard.id}`} className="dashboard-link">
                                {dashboard.name}
                                {dashboard.is_public && <span className="public-badge">Public</span>}
                            </Link>
                            {dashboard.user_id === user?.id && (
                                <button
                                    className="btn-delete"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        handleDeleteDashboard(dashboard.id);
                                    }}
                                >
                                    ×
                                </button>
                            )}
                        </div>
                    ))}

                    {dashboards.length === 0 && (
                        <div className="no-dashboards">
                            <p>No dashboards yet</p>
                            <button onClick={handleCreateDashboard}>Create your first dashboard</button>
                        </div>
                    )}
                </div>
            </div>

            {/* Main Dashboard Area */}
            <div className="dashboard-main">
                {error && <div className="dashboard-error">{error}</div>}

                {currentDashboard ? (
                    <>
                        <div className="dashboard-header">
                            <div className="dashboard-title">
                                <h1>{currentDashboard.name}</h1>
                                {currentDashboard.description && (
                                    <p className="dashboard-description">{currentDashboard.description}</p>
                                )}
                            </div>
                            {isOwner && (
                                <Link to={`/dashboards/${currentDashboard.id}/edit`} className="btn-edit">
                                    ✏️ Edit
                                </Link>
                            )}
                        </div>

                        <div className="widgets-grid">
                            {!currentDashboard.widgets || currentDashboard.widgets.length === 0 ? (
                                <div className="no-widgets">
                                    <p>No widgets yet</p>
                                    {isOwner && (
                                        <Link to={`/dashboards/${currentDashboard.id}/edit`} className="btn-primary">
                                            Add Widgets
                                        </Link>
                                    )}
                                </div>
                            ) : (
                                currentDashboard.widgets.map(widget => (
                                    <div
                                        key={widget.id}
                                        className="widget-card"
                                        style={{
                                            gridColumn: `span ${widget.width}`,
                                            gridRow: `span ${widget.height}`
                                        }}
                                    >
                                        {widget.title && <div className="widget-header">{widget.title}</div>}
                                        <div className="widget-content">
                                            {renderWidget(widget, widgetData[widget.id])}
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </>
                ) : (
                    <div className="no-dashboard-selected">
                        <p>Select a dashboard or create a new one</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default CustomDashboard;
