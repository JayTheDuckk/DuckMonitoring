import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { 
  getUPSDevices, createUPSDevice, updateUPSDevice, deleteUPSDevice, 
  getUPSModels, runUPSCheck, getUPSMetricsSummary 
} from '../../services/api';
import './UPSDashboard.css';

const UPSDashboard = () => {
  const { user } = useAuth();
  const [devices, setDevices] = useState([]);
  const [upsModels, setUpsModels] = useState([]);
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
    location: '',
    notes: ''
  });
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadData();
    loadUPSModels();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const response = await getUPSDevices();
      // Handle different response formats (array, paginated, or object)
      const devicesData = Array.isArray(response.data) 
        ? response.data 
        : response.data.results || response.data.data || [];
      setDevices(devicesData);
      setError(null);
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'Failed to load UPS devices';
      setError(errorMessage);
      console.error('Load UPS devices error:', err);
      // Ensure devices is always an array even on error
      setDevices([]);
    } finally {
      setLoading(false);
    }
  };

  const loadUPSModels = async () => {
    try {
      const response = await getUPSModels();
      setUpsModels(response.data);
    } catch (err) {
      console.error('Load UPS models error:', err);
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    
    if (!formData.name.trim() || !formData.ip_address.trim() || !formData.model_key) {
      setFormError('Name, IP address, and UPS model are required');
      return;
    }

    setSubmitting(true);
    try {
      if (editingDevice) {
        await updateUPSDevice(editingDevice.id, formData);
      } else {
        await createUPSDevice(formData);
      }
      await loadData();
      handleCloseModal();
    } catch (err) {
      setFormError(err.response?.data?.error || err.message || 'Failed to save UPS device');
      console.error('Save UPS device error:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (deviceId, deviceName) => {
    if (!window.confirm(`Are you sure you want to delete UPS device "${deviceName}"?`)) {
      return;
    }
    try {
      await deleteUPSDevice(deviceId);
      await loadData();
    } catch (err) {
      alert('Failed to delete UPS device: ' + (err.response?.data?.error || err.message));
      console.error('Delete UPS device error:', err);
    }
  };

  const handleRunCheck = async (deviceId) => {
    try {
      await runUPSCheck(deviceId);
      await loadData();
    } catch (err) {
      console.error('Run UPS check error:', err);
    }
  };

  const getModelName = (modelKey) => {
    const model = upsModels.find(m => m.key === modelKey);
    return model ? model.name : modelKey;
  };

  if (loading && devices.length === 0) {
    return <div className="loading">Loading UPS devices...</div>;
  }

  return (
    <div className="ups-dashboard">
      <div className="ups-dashboard-header">
        <div>
          <h2>UPS Monitoring</h2>
          {user && <p className="welcome-message">Monitor UPS devices via SNMP</p>}
        </div>
        {(user?.is_admin || user?.role === 'admin' || user?.role === 'operator') && (
          <button className="btn-add-ups" onClick={() => handleOpenModal()}>
            + Add UPS Device
          </button>
        )}
      </div>

      {error && <div className="error-message">{error}</div>}

      {!Array.isArray(devices) || devices.length === 0 ? (
        <div className="empty-state">
          <p>No UPS devices configured.</p>
          <p>Add a UPS device to start monitoring.</p>
        </div>
      ) : (
        <div className="ups-devices-grid">
          {devices.map(device => (
            <div key={device.id} className="ups-device-card">
              <div className="ups-device-header">
                <h3>{device.name}</h3>
                <span
                  className="status-badge"
                  style={{ backgroundColor: getStatusColor(device.status) }}
                >
                  {device.status.toUpperCase()}
                </span>
                {!device.enabled && <span className="disabled-badge">DISABLED</span>}
              </div>
              
              <div className="ups-device-info">
                <div className="info-row">
                  <span className="info-label">Model:</span>
                  <span className="info-value">{getModelName(device.model_key)}</span>
                </div>
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
              </div>

              <div className="ups-device-actions">
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
                  to={`/ups/${device.id}`}
                  className="btn-small btn-primary"
                >
                  View Details
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {showAddModal && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal-content ups-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingDevice ? 'Edit UPS Device' : 'Add UPS Device'}</h3>
              <button className="modal-close" onClick={handleCloseModal}>×</button>
            </div>
            
            <form onSubmit={handleSubmit} className="ups-form">
              {formError && <div className="error-message">{formError}</div>}
              
              <div className="form-group">
                <label>Device Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Server Room UPS"
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
                <label>UPS Model *</label>
                <select
                  value={formData.model_key}
                  onChange={(e) => setFormData({ ...formData, model_key: e.target.value })}
                  required
                >
                  <option value="">Select a UPS model...</option>
                  {upsModels.map(model => (
                    <option key={model.key} value={model.key}>
                      {model.manufacturer} - {model.name}
                    </option>
                  ))}
                </select>
                {formData.model_key && (
                  <small>
                    {upsModels.find(m => m.key === formData.model_key)?.description}
                  </small>
                )}
              </div>

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
                  placeholder="Additional notes about this UPS device..."
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

export default UPSDashboard;


