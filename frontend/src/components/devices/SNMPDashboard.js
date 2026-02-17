import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { 
  getSNMPDevices, createSNMPDevice, updateSNMPDevice, deleteSNMPDevice, 
  getSNMPDeviceModels, runSNMPDeviceCheck, getSNMPDeviceMetricsSummary 
} from '../../services/api';
import './SNMPDashboard.css';

const SNMPDashboard = () => {
  const { user } = useAuth();
  const [devices, setDevices] = useState([]);
  const [snmpModels, setSnmpModels] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingDevice, setEditingDevice] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    ip_address: '',
    model_key: '',
    snmp_community: 'public',
    snmp_version: 2,
    snmp_port: 161,
    check_interval: 60,
    timeout: 10,
    enabled: true,
    monitored_metrics: [],
    location: '',
    notes: ''
  });
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('all');

  useEffect(() => {
    loadData();
    loadSNMPModels();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const response = await getSNMPDevices();
      // Handle different response formats (array, paginated, or object)
      const devicesData = Array.isArray(response.data) 
        ? response.data 
        : response.data.results || response.data.data || [];
      setDevices(devicesData);
      setError(null);
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'Failed to load SNMP devices';
      setError(errorMessage);
      console.error('Load SNMP devices error:', err);
      // Ensure devices is always an array even on error
      setDevices([]);
    } finally {
      setLoading(false);
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

  const handleOpenModal = (device = null) => {
    if (device) {
      setEditingDevice(device);
      setFormData({
        name: device.name || '',
        ip_address: device.ip_address || '',
        model_key: device.model_key || '',
        snmp_community: device.snmp_community || 'public',
        snmp_version: device.snmp_version || 2,
        snmp_port: device.snmp_port || 161,
        check_interval: device.check_interval || 60,
        timeout: device.timeout || 10,
        enabled: device.enabled !== undefined ? device.enabled : true,
        monitored_metrics: device.monitored_metrics || [],
        location: device.location || '',
        notes: device.notes || ''
      });
    } else {
      setEditingDevice(null);
      setFormData({
        name: '',
        ip_address: '',
        model_key: '',
        snmp_community: 'public',
        snmp_version: 2,
        snmp_port: 161,
        check_interval: 60,
        timeout: 10,
        enabled: true,
        monitored_metrics: [],
        location: '',
        notes: ''
      });
    }
    setShowAddModal(true);
  };

  const handleCloseModal = () => {
    setShowAddModal(false);
    setEditingDevice(null);
    setFormError('');
  };

  const handleModelChange = (modelKey) => {
    const model = Object.values(snmpModels).flat().find(m => m.key === modelKey);
    if (model) {
      // Set default monitored metrics based on available metrics
      const defaultMetrics = model.available_metrics.filter(m => 
        ['health_status', 'system_name', 'system_uptime', 'temperature', 'power_status'].includes(m)
      );
      setFormData({
        ...formData,
        model_key: modelKey,
        monitored_metrics: defaultMetrics
      });
    } else {
      setFormData({
        ...formData,
        model_key: modelKey,
        monitored_metrics: []
      });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    
    if (!formData.name.trim() || !formData.ip_address.trim() || !formData.model_key) {
      setFormError('Name, IP address, and device model are required');
      return;
    }

    setSubmitting(true);
    try {
      if (editingDevice) {
        await updateSNMPDevice(editingDevice.id, formData);
      } else {
        await createSNMPDevice(formData);
      }
      await loadData();
      handleCloseModal();
    } catch (err) {
      setFormError(err.response?.data?.error || err.message || 'Failed to save SNMP device');
      console.error('Save SNMP device error:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (deviceId, deviceName) => {
    if (!window.confirm(`Are you sure you want to delete SNMP device "${deviceName}"?`)) {
      return;
    }
    try {
      await deleteSNMPDevice(deviceId);
      await loadData();
    } catch (err) {
      alert('Failed to delete SNMP device: ' + (err.response?.data?.error || err.message));
      console.error('Delete SNMP device error:', err);
    }
  };

  const handleRunCheck = async (deviceId) => {
    try {
      await runSNMPDeviceCheck(deviceId);
      await loadData();
    } catch (err) {
      console.error('Run SNMP device check error:', err);
    }
  };

  const getModelName = (modelKey) => {
    const allModels = Object.values(snmpModels).flat();
    const model = allModels.find(m => m.key === modelKey);
    return model ? model.name : modelKey;
  };

  const getModelInfo = (modelKey) => {
    const allModels = Object.values(snmpModels).flat();
    return allModels.find(m => m.key === modelKey);
  };

  const toggleMetric = (metricName) => {
    const current = formData.monitored_metrics || [];
    if (current.includes(metricName)) {
      setFormData({
        ...formData,
        monitored_metrics: current.filter(m => m !== metricName)
      });
    } else {
      setFormData({
        ...formData,
        monitored_metrics: [...current, metricName]
      });
    }
  };

  // Get filtered models by category
  const getFilteredModels = () => {
    if (selectedCategory === 'all') {
      return snmpModels;
    }
    return Object.fromEntries(
      Object.entries(snmpModels).filter(([category]) => category === selectedCategory)
    );
  };

  if (loading && devices.length === 0) {
    return <div className="loading">Loading SNMP devices...</div>;
  }

  const filteredModels = getFilteredModels();
  const categories = ['all', ...Object.keys(snmpModels)];

  return (
    <div className="snmp-dashboard">
      <div className="snmp-dashboard-header">
        <div>
          <h2>SNMP Device Monitoring</h2>
          {user && <p className="welcome-message">Monitor Out Of Band management systems and SNMP devices</p>}
        </div>
        {(user?.is_admin || user?.role === 'admin' || user?.role === 'operator') && (
          <button className="btn-add-snmp" onClick={() => handleOpenModal()}>
            + Add SNMP Device
          </button>
        )}
      </div>

      {error && <div className="error-message">{error}</div>}

      {!Array.isArray(devices) || devices.length === 0 ? (
        <div className="empty-state">
          <p>No SNMP devices configured.</p>
          <p>Add an SNMP device to start monitoring.</p>
        </div>
      ) : (
        <div className="snmp-devices-grid">
          {devices.map(device => {
            const modelInfo = getModelInfo(device.model_key);
            return (
              <div key={device.id} className="snmp-device-card">
                <div className="snmp-device-header">
                  <h3>{device.name}</h3>
                  <span
                    className="status-badge"
                    style={{ backgroundColor: getStatusColor(device.status) }}
                  >
                    {device.status.toUpperCase()}
                  </span>
                  {!device.enabled && <span className="disabled-badge">DISABLED</span>}
                </div>
                
                <div className="snmp-device-info">
                  <div className="info-row">
                    <span className="info-label">Model:</span>
                    <span className="info-value">{getModelName(device.model_key)}</span>
                  </div>
                  {modelInfo && (
                    <div className="info-row">
                      <span className="info-label">Manufacturer:</span>
                      <span className="info-value">{modelInfo.manufacturer}</span>
                    </div>
                  )}
                  <div className="info-row">
                    <span className="info-label">IP Address:</span>
                    <span className="info-value">{device.ip_address}</span>
                  </div>
                  {device.location && (
                    <div className="info-row">
                      <span className="info-label">Location:</span>
                      <span className="info-value">{device.location}</span>
                    </div>
                  )}
                  {device.last_check && (
                    <div className="info-row">
                      <span className="info-label">Last Check:</span>
                      <span className="info-value">
                        {new Date(device.last_check).toLocaleString()}
                      </span>
                    </div>
                  )}
                  <div className="info-row">
                    <span className="info-label">Check Interval:</span>
                    <span className="info-value">{device.check_interval}s</span>
                  </div>
                  {device.last_output && (
                    <div className="info-row">
                      <span className="info-label">Last Output:</span>
                      <span className="info-value output-text">{device.last_output}</span>
                    </div>
                  )}
                </div>

                <div className="snmp-device-actions">
                  <button
                    className="btn-small"
                    onClick={() => handleRunCheck(device.id)}
                    title="Run check now"
                  >
                    Check Now
                  </button>
                  {(user?.is_admin || user?.role === 'admin' || user?.role === 'operator') && (
                    <>
                      <button
                        className="btn-small"
                        onClick={() => handleOpenModal(device)}
                        title="Edit device"
                      >
                        Edit
                      </button>
                      <button
                        className="btn-small btn-danger"
                        onClick={() => handleDelete(device.id, device.name)}
                        title="Delete device"
                      >
                        Delete
                      </button>
                    </>
                  )}
                  <Link
                    to={`/snmp/${device.id}`}
                    className="btn-small btn-primary"
                  >
                    View Details
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showAddModal && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal-content snmp-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingDevice ? 'Edit SNMP Device' : 'Add SNMP Device'}</h3>
              <button className="modal-close" onClick={handleCloseModal}>×</button>
            </div>
            
            <form onSubmit={handleSubmit} className="snmp-form">
              {formError && <div className="error-message">{formError}</div>}
              
              <div className="form-group">
                <label>Device Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Server Room iLO"
                  required
                />
              </div>

              <div className="form-group">
                <label>IP Address *</label>
                <input
                  type="text"
                  value={formData.ip_address}
                  onChange={(e) => setFormData({ ...formData, ip_address: e.target.value })}
                  placeholder="192.168.1.100"
                  required
                />
              </div>

              <div className="form-group">
                <label>Device Category</label>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                >
                  {categories.map(cat => (
                    <option key={cat} value={cat}>
                      {cat === 'all' ? 'All Categories' : cat}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Device Model *</label>
                <select
                  value={formData.model_key}
                  onChange={(e) => handleModelChange(e.target.value)}
                  required
                >
                  <option value="">Select a device model...</option>
                  {Object.entries(filteredModels).map(([category, models]) => (
                    <optgroup key={category} label={category}>
                      {models.map(model => (
                        <option key={model.key} value={model.key}>
                          {model.manufacturer} - {model.name}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
                {formData.model_key && (
                  <small>
                    {Object.values(filteredModels).flat().find(m => m.key === formData.model_key)?.description}
                  </small>
                )}
              </div>

              {formData.model_key && (() => {
                const model = Object.values(filteredModels).flat().find(m => m.key === formData.model_key);
                return model && model.available_metrics && model.available_metrics.length > 0 ? (
                  <div className="form-group">
                    <label>Metrics to Monitor</label>
                    <div className="metrics-checkboxes">
                      {model.available_metrics.map(metric => (
                        <label key={metric} className="checkbox-label">
                          <input
                            type="checkbox"
                            checked={formData.monitored_metrics.includes(metric)}
                            onChange={() => toggleMetric(metric)}
                          />
                          <span>{metric.replace(/_/g, ' ')}</span>
                        </label>
                      ))}
                    </div>
                    <small>Select which metrics to monitor for this device</small>
                  </div>
                ) : null;
              })()}

              <div className="form-row">
                <div className="form-group">
                  <label>SNMP Community</label>
                  <input
                    type="text"
                    value={formData.snmp_community}
                    onChange={(e) => setFormData({ ...formData, snmp_community: e.target.value })}
                    placeholder="public"
                  />
                </div>
                <div className="form-group">
                  <label>SNMP Version</label>
                  <select
                    value={formData.snmp_version}
                    onChange={(e) => setFormData({ ...formData, snmp_version: parseInt(e.target.value) })}
                  >
                    <option value={1}>SNMP v1</option>
                    <option value={2}>SNMP v2c</option>
                    <option value={3}>SNMP v3</option>
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>SNMP Port</label>
                  <input
                    type="number"
                    value={formData.snmp_port}
                    onChange={(e) => setFormData({ ...formData, snmp_port: parseInt(e.target.value) || 161 })}
                    min="1"
                    max="65535"
                  />
                </div>
                <div className="form-group">
                  <label>Check Interval (seconds)</label>
                  <input
                    type="number"
                    value={formData.check_interval}
                    onChange={(e) => setFormData({ ...formData, check_interval: parseInt(e.target.value) || 60 })}
                    min="10"
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Timeout (seconds)</label>
                <input
                  type="number"
                  value={formData.timeout}
                  onChange={(e) => setFormData({ ...formData, timeout: parseInt(e.target.value) || 10 })}
                  min="1"
                  max="60"
                />
              </div>

              <div className="form-group">
                <label>Location</label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  placeholder="e.g., Server Room A"
                />
              </div>

              <div className="form-group">
                <label>Notes</label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="Additional notes about this SNMP device..."
                  rows="3"
                />
              </div>

              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.enabled}
                    onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                  />
                  Enabled
                </label>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={handleCloseModal}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? 'Saving...' : (editingDevice ? 'Update' : 'Create')} Device
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default SNMPDashboard;


