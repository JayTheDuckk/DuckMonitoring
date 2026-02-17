import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getSNMPDevice, getSNMPDeviceMetrics, getSNMPDeviceMetricsSummary, getSNMPDeviceModels } from '../../services/api';
import MetricChart from '../common/MetricChart';
import './SNMPDetail.css';

const SNMPDetail = () => {
  const { deviceId } = useParams();
  const [device, setDevice] = useState(null);
  const [metricsSummary, setMetricsSummary] = useState([]);
  const [snmpModels, setSnmpModels] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hours, setHours] = useState(24);

  useEffect(() => {
    loadDevice();
    loadMetricsSummary();
    loadSNMPModels();
    const interval = setInterval(() => {
      loadDevice();
      loadMetricsSummary();
    }, 30000);
    return () => clearInterval(interval);
  }, [deviceId]);

  const loadDevice = async () => {
    try {
      const response = await getSNMPDevice(deviceId);
      setDevice(response.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to load SNMP device');
      console.error('Load SNMP device error:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadMetricsSummary = async () => {
    try {
      const response = await getSNMPDeviceMetricsSummary(deviceId, { hours });
      setMetricsSummary(response.data);
    } catch (err) {
      console.error('Load metrics summary error:', err);
    }
  };

  const loadSNMPModels = async () => {
    try {
      const response = await getSNMPDeviceModels();
      setSnmpModels(response.data);
    } catch (err) {
      console.error('Load SNMP models error:', err);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'ok':
        return '#4caf50';
      case 'warning':
        return '#ff9800';
      case 'critical':
        return '#f44336';
      default:
        return '#9e9e9e';
    }
  };

  const getMetricValue = (metricName) => {
    const metric = metricsSummary.find(m => m.name === metricName);
    return metric ? metric.latest_value : null;
  };

  const getModelInfo = () => {
    if (!device) return null;
    const allModels = Object.values(snmpModels).flat();
    return allModels.find(m => m.key === device.model_key);
  };

  if (loading) {
    return <div className="loading">Loading SNMP device...</div>;
  }

  if (error || !device) {
    return (
      <div className="snmp-detail">
        <div className="error-message">{error || 'SNMP device not found'}</div>
        <Link to="/snmp" className="btn-back">← Back to SNMP Dashboard</Link>
      </div>
    );
  }

  const modelInfo = getModelInfo();
  const numericMetrics = metricsSummary.filter(m => m.value !== null && typeof m.value === 'number');

  return (
    <div className="snmp-detail">
      <div className="snmp-detail-header">
        <div>
          <Link to="/snmp" className="btn-back">← Back to SNMP Dashboard</Link>
          <h2>{device.name}</h2>
          {device.location && <p className="device-location">{device.location}</p>}
        </div>
        <div className="header-status">
          <span
            className="status-badge-large"
            style={{ backgroundColor: getStatusColor(device.status) }}
          >
            {device.status.toUpperCase()}
          </span>
        </div>
      </div>

      <div className="snmp-overview">
        <div className="overview-card">
          <h3>Device Information</h3>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">IP Address:</span>
              <span className="info-value">{device.ip_address}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Model:</span>
              <span className="info-value">{modelInfo ? modelInfo.name : device.model_key}</span>
            </div>
            {modelInfo && (
              <div className="info-item">
                <span className="info-label">Manufacturer:</span>
                <span className="info-value">{modelInfo.manufacturer}</span>
              </div>
            )}
            <div className="info-item">
              <span className="info-label">SNMP Community:</span>
              <span className="info-value">{device.snmp_community}</span>
            </div>
            <div className="info-item">
              <span className="info-label">SNMP Version:</span>
              <span className="info-value">v{device.snmp_version}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Last Check:</span>
              <span className="info-value">
                {device.last_check ? new Date(device.last_check).toLocaleString() : 'Never'}
              </span>
            </div>
            <div className="info-item">
              <span className="info-label">Check Interval:</span>
              <span className="info-value">{device.check_interval}s</span>
            </div>
            {device.last_output && (
              <div className="info-item full-width">
                <span className="info-label">Last Output:</span>
                <span className="info-value output-text">{device.last_output}</span>
              </div>
            )}
          </div>
        </div>

        <div className="overview-card">
          <h3>Current Metrics</h3>
          {numericMetrics.length > 0 ? (
            <div className="metrics-grid">
              {numericMetrics.slice(0, 6).map(metric => (
                <div key={metric.name} className="metric-card">
                  <div className="metric-label">{metric.name.replace(/_/g, ' ')}</div>
                  <div className="metric-value">
                    {metric.value !== null
                      ? `${metric.value}${metric.unit ? ' ' + metric.unit : ''}`
                      : metric.value_string || 'N/A'}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-metrics">No numeric metrics available yet. Run a check to collect data.</p>
          )}
        </div>
      </div>

      <div className="time-range-selector">
        <label>Time Range:</label>
        <select value={hours} onChange={(e) => setHours(parseInt(e.target.value))}>
          <option value={1}>Last Hour</option>
          <option value={6}>Last 6 Hours</option>
          <option value={24}>Last 24 Hours</option>
          <option value={48}>Last 48 Hours</option>
          <option value={168}>Last Week</option>
        </select>
      </div>

      {numericMetrics.length > 0 && (
        <div className="snmp-charts">
          {numericMetrics.slice(0, 4).map(metric => (
            <div key={metric.name} className="chart-card">
              <h3>{metric.name.replace(/_/g, ' ')}</h3>
              <MetricChart
                hostId={parseInt(deviceId)}
                metricName={metric.name}
                hours={hours}
                unit={metric.unit || ''}
                color={getChartColor(metric.metric_type)}
                isUPS={false}
                isSNMP={true}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const getChartColor = (metricType) => {
  const colors = {
    health: '#4caf50',
    temperature: '#ff9800',
    power: '#2196f3',
    fan: '#9c27b0',
    system: '#4D9CFF',
    other: '#9e9e9e'
  };
  return colors[metricType] || colors.other;
};

export default SNMPDetail;


