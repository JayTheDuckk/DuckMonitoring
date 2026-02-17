import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getUPSDevice, getUPSMetrics, getUPSMetricsSummary } from '../../services/api';
import MetricChart from '../common/MetricChart';
import './UPSDetail.css';

const UPSDetail = () => {
  const { deviceId } = useParams();
  const [device, setDevice] = useState(null);
  const [metricsSummary, setMetricsSummary] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hours, setHours] = useState(24);

  useEffect(() => {
    loadDevice();
    loadMetricsSummary();
    const interval = setInterval(() => {
      loadDevice();
      loadMetricsSummary();
    }, 30000);
    return () => clearInterval(interval);
  }, [deviceId]);

  const loadDevice = async () => {
    try {
      const response = await getUPSDevice(deviceId);
      setDevice(response.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to load UPS device');
      console.error('Load UPS device error:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadMetricsSummary = async () => {
    try {
      const response = await getUPSMetricsSummary(deviceId, { hours });
      setMetricsSummary(response.data);
    } catch (err) {
      console.error('Load metrics summary error:', err);
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

  if (loading) {
    return <div className="loading">Loading UPS device...</div>;
  }

  if (error || !device) {
    return (
      <div className="ups-detail">
        <div className="error-message">{error || 'UPS device not found'}</div>
        <Link to="/ups" className="btn-back">← Back to UPS Dashboard</Link>
      </div>
    );
  }

  return (
    <div className="ups-detail">
      <div className="ups-detail-header">
        <div>
          <Link to="/ups" className="btn-back">← Back to UPS Dashboard</Link>
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

      <div className="ups-overview">
        <div className="overview-card">
          <h3>Device Information</h3>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">IP Address:</span>
              <span className="info-value">{device.ip_address}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Model:</span>
              <span className="info-value">{device.model_key}</span>
            </div>
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
          </div>
        </div>

        <div className="overview-card">
          <h3>Current Status</h3>
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-label">Battery Capacity</div>
              <div className="metric-value">
                {getMetricValue('battery_capacity') !== null
                  ? `${getMetricValue('battery_capacity')}%`
                  : 'N/A'}
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Output Load</div>
              <div className="metric-value">
                {getMetricValue('output_load') !== null
                  ? `${getMetricValue('output_load')}%`
                  : 'N/A'}
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Battery Voltage</div>
              <div className="metric-value">
                {getMetricValue('battery_voltage') !== null
                  ? `${getMetricValue('battery_voltage')}V`
                  : 'N/A'}
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Input Voltage</div>
              <div className="metric-value">
                {getMetricValue('input_voltage') !== null
                  ? `${getMetricValue('input_voltage')}V`
                  : 'N/A'}
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Output Voltage</div>
              <div className="metric-value">
                {getMetricValue('output_voltage') !== null
                  ? `${getMetricValue('output_voltage')}V`
                  : 'N/A'}
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Estimated Runtime</div>
              <div className="metric-value">
                {getMetricValue('estimated_runtime') !== null
                  ? `${getMetricValue('estimated_runtime')} min`
                  : 'N/A'}
              </div>
            </div>
          </div>
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

      <div className="ups-charts">
        <div className="chart-card">
          <h3>Battery Capacity</h3>
          <MetricChart
            hostId={parseInt(deviceId)}
            metricName="battery_capacity"
            hours={hours}
            unit="%"
            color="#4caf50"
            isUPS={true}
          />
        </div>
        <div className="chart-card">
          <h3>Output Load</h3>
          <MetricChart
            hostId={parseInt(deviceId)}
            metricName="output_load"
            hours={hours}
            unit="%"
            color="#2196f3"
            isUPS={true}
          />
        </div>
        <div className="chart-card">
          <h3>Battery Voltage</h3>
          <MetricChart
            hostId={parseInt(deviceId)}
            metricName="battery_voltage"
            hours={hours}
            unit="V"
            color="#ff9800"
            isUPS={true}
          />
        </div>
        <div className="chart-card">
          <h3>Input Voltage</h3>
          <MetricChart
            hostId={parseInt(deviceId)}
            metricName="input_voltage"
            hours={hours}
            unit="V"
            color="#9c27b0"
            isUPS={true}
          />
        </div>
      </div>
    </div>
  );
};

export default UPSDetail;

