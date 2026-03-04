import React, { useState, useEffect } from 'react';
import { getServiceChecks, createServiceCheck, updateServiceCheck, deleteServiceCheck, runServiceCheck, clearServiceCheckResults } from '../../services/api';
import './ServiceCheckConfig.css';

const ServiceCheckConfig = ({ hostId, hostname, ipAddress }) => {
  const [checks, setChecks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingCheck, setEditingCheck] = useState(null);
  const [formData, setFormData] = useState({
    check_type: 'ping',
    check_name: '',
    interval: 60,
    timeout: 10,
    enabled: true,
    parameters: {}
  });

  useEffect(() => {
    loadServiceChecks();
    const interval = setInterval(loadServiceChecks, 30000);
    return () => clearInterval(interval);
  }, [hostId]);

  const loadServiceChecks = async () => {
    try {
      const response = await getServiceChecks(hostId);
      setChecks(Array.isArray(response.data) ? response.data : response.data.results || []);
    } catch (error) {
      console.error('Failed to load service checks:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = (check = null) => {
    if (check) {
      setEditingCheck(check);
      setFormData({
        check_type: check.check_type,
        check_name: check.check_name,
        interval: check.interval,
        timeout: check.timeout,
        enabled: check.enabled,
        parameters: check.parameters || {}
      });
    } else {
      setEditingCheck(null);
      setFormData({
        check_type: 'ping',
        check_name: '',
        interval: 60,
        timeout: 10,
        enabled: true,
        parameters: getDefaultParameters('ping')
      });
    }
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingCheck(null);
  };

  const getDefaultParameters = (checkType) => {
    const defaults = {
      ping: { count: 3 },
      ssh: { port: 22 },
      http: { port: 80, path: '/', expected_status: 200 },
      https: { port: 443, path: '/', expected_status: 200 },
      tcp: { port: 80 },
      udp: { port: 53 },
      dns: { server: '8.8.8.8', record_type: 'A' },
      ssl_expiry: { port: 443 },
      http_content: { port: 80, path: '/', content: '', use_https: false },
      snmp: { community: 'public', snmp_version: 2, port: 161, oid: '1.3.6.1.2.1.1.1.0' },
      ilo: { community: 'public', snmp_version: 2, port: 161, check_type: 'health' },
      idrac: { community: 'public', snmp_version: 2, port: 161, check_type: 'health' }
    };
    return defaults[checkType] || {};
  };

  const handleCheckTypeChange = (checkType) => {
    setFormData({
      ...formData,
      check_type: checkType,
      parameters: getDefaultParameters(checkType)
    });
  };

  const handleParameterChange = (key, value) => {
    setFormData({
      ...formData,
      parameters: {
        ...formData.parameters,
        [key]: value
      }
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingCheck) {
        await updateServiceCheck(editingCheck.id, formData);
      } else {
        await createServiceCheck(hostId, formData);
      }
      await loadServiceChecks();
      handleCloseModal();
    } catch (error) {
      console.error('Failed to save service check:', error);
      alert('Failed to save service check: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleDelete = async (checkId) => {
    if (!window.confirm('Are you sure you want to delete this service check?')) {
      return;
    }
    try {
      await deleteServiceCheck(checkId);
      await loadServiceChecks();
    } catch (error) {
      console.error('Failed to delete service check:', error);
      alert('Failed to delete service check');
    }
  };

  const handleRunNow = async (checkId) => {
    try {
      await runServiceCheck(checkId);
      await loadServiceChecks();
    } catch (error) {
      console.error('Failed to run service check:', error);
    }
  };

  const handleClearResults = async (checkId, checkName) => {
    if (!window.confirm(`Are you sure you want to clear all historical results for "${checkName}"? This will delete all past check records but keep the service check configuration.`)) {
      return;
    }
    try {
      const response = await clearServiceCheckResults(checkId);
      const count = response.data?.deleted_count || 0;
      alert(`Successfully cleared ${count} check result(s).`);
      await loadServiceChecks();
    } catch (error) {
      console.error('Failed to clear service check results:', error);
      alert('Failed to clear results: ' + (error.response?.data?.error || error.message));
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

  const getCheckTypeLabel = (type) => {
    const labels = {
      ping: 'Ping',
      ssh: 'SSH',
      http: 'HTTP',
      https: 'HTTPS',
      tcp: 'TCP Port',
      udp: 'UDP Port',
      dns: 'DNS',
      snmp: 'SNMP',
      ilo: 'HPE iLO',
      idrac: 'Dell iDRAC'
    };
    return labels[type] || type;
  };

  if (loading) {
    return <div className="loading">Loading service checks...</div>;
  }

  return (
    <div className="service-check-config">
      <div className="service-check-header">
        <h3>Service Checks</h3>
        <button className="btn-primary" onClick={() => handleOpenModal()}>
          + Add Service Check
        </button>
      </div>

      {checks.length === 0 ? (
        <div className="empty-state">
          <p>No service checks configured.</p>
          <p>Add a service check to monitor this host without an agent.</p>
        </div>
      ) : (
        <div className="service-checks-list">
          {checks.map(check => (
            <div key={check.id} className="service-check-item">
              <div className="service-check-info">
                <div className="service-check-title">
                  <h4>{check.check_name}</h4>
                  <span
                    className="status-badge"
                    style={{ backgroundColor: getStatusColor(check.status) }}
                  >
                    {check.status.toUpperCase()}
                  </span>
                  {!check.enabled && <span className="disabled-badge">DISABLED</span>}
                </div>
                <div className="service-check-details">
                  <span className="check-type">{getCheckTypeLabel(check.check_type)}</span>
                  <span className="check-interval">Every {check.interval}s</span>
                  {check.last_check && (
                    <span className="check-time">
                      Last: {new Date(check.last_check).toLocaleString()}
                    </span>
                  )}
                </div>
                {check.last_output && (
                  <div className="check-output">{check.last_output}</div>
                )}
              </div>
              <div className="service-check-actions">
                <button
                  className="btn-small"
                  onClick={() => handleRunNow(check.id)}
                  title="Run check now"
                >
                  Run Now
                </button>
                <button
                  className="btn-small"
                  onClick={() => handleOpenModal(check)}
                  title="Edit check"
                >
                  Edit
                </button>
                <button
                  className="btn-small btn-warning"
                  onClick={() => handleClearResults(check.id, check.check_name)}
                  title="Clear historical check results"
                >
                  Clear Results
                </button>
                <button
                  className="btn-small btn-danger"
                  onClick={() => handleDelete(check.id)}
                  title="Delete check"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingCheck ? 'Edit Service Check' : 'Add Service Check'}</h3>
              <button className="modal-close" onClick={handleCloseModal}>×</button>
            </div>

            <form onSubmit={handleSubmit} className="service-check-form">
              <div className="form-group">
                <label>Check Type *</label>
                <select
                  value={formData.check_type}
                  onChange={(e) => handleCheckTypeChange(e.target.value)}
                  required
                >
                  <option value="ping">Ping (ICMP)</option>
                  <option value="ssh">SSH</option>
                  <option value="http">HTTP</option>
                  <option value="https">HTTPS</option>
                  <option value="tcp">TCP Port</option>
                  <option value="udp">UDP Port</option>
                  <option value="dns">DNS Resolution</option>
                  <option value="snmp">SNMP (Generic)</option>
                  <option value="ilo">HPE iLO (SNMP)</option>
                  <option value="idrac">Dell iDRAC (SNMP)</option>
                </select>
              </div>

              <div className="form-group">
                <label>Check Name *</label>
                <input
                  type="text"
                  value={formData.check_name}
                  onChange={(e) => setFormData({ ...formData, check_name: e.target.value })}
                  placeholder={`e.g., ${getCheckTypeLabel(formData.check_type)} Check for ${hostname}`}
                  required
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Check Interval (seconds) *</label>
                  <input
                    type="number"
                    value={formData.interval}
                    onChange={(e) => setFormData({ ...formData, interval: parseInt(e.target.value) || 60 })}
                    min="10"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Timeout (seconds) *</label>
                  <input
                    type="number"
                    value={formData.timeout}
                    onChange={(e) => setFormData({ ...formData, timeout: parseInt(e.target.value) || 10 })}
                    min="1"
                    max="60"
                    required
                  />
                </div>
              </div>

              {/* Check-specific parameters */}
              {formData.check_type === 'ssh' && (
                <div className="form-group">
                  <label>SSH Port</label>
                  <input
                    type="number"
                    value={formData.parameters.port || 22}
                    onChange={(e) => handleParameterChange('port', parseInt(e.target.value) || 22)}
                    min="1"
                    max="65535"
                  />
                </div>
              )}

              {(formData.check_type === 'http' || formData.check_type === 'https') && (
                <>
                  <div className="form-group">
                    <label>Port</label>
                    <input
                      type="number"
                      value={formData.parameters.port || (formData.check_type === 'https' ? 443 : 80)}
                      onChange={(e) => handleParameterChange('port', parseInt(e.target.value) || 80)}
                      min="1"
                      max="65535"
                    />
                  </div>
                  <div className="form-group">
                    <label>Path</label>
                    <input
                      type="text"
                      value={formData.parameters.path || '/'}
                      onChange={(e) => handleParameterChange('path', e.target.value)}
                      placeholder="/"
                    />
                  </div>
                  <div className="form-group">
                    <label>Expected HTTP Status</label>
                    <input
                      type="number"
                      value={formData.parameters.expected_status || 200}
                      onChange={(e) => handleParameterChange('expected_status', parseInt(e.target.value) || 200)}
                      min="100"
                      max="599"
                    />
                  </div>
                </>
              )}

              {formData.check_type === 'http_content' && (
                <>
                  <div className="form-group">
                    <label>
                      <input
                        type="checkbox"
                        checked={formData.parameters.use_https || false}
                        onChange={(e) => handleParameterChange('use_https', e.target.checked)}
                      />
                      Use HTTPS
                    </label>
                  </div>
                  <div className="form-group">
                    <label>Port</label>
                    <input
                      type="number"
                      value={formData.parameters.port || (formData.parameters.use_https ? 443 : 80)}
                      onChange={(e) => handleParameterChange('port', parseInt(e.target.value) || 80)}
                      min="1"
                      max="65535"
                    />
                  </div>
                  <div className="form-group">
                    <label>Path</label>
                    <input
                      type="text"
                      value={formData.parameters.path || '/'}
                      onChange={(e) => handleParameterChange('path', e.target.value)}
                      placeholder="/"
                    />
                  </div>
                  <div className="form-group">
                    <label>Content to Match *</label>
                    <input
                      type="text"
                      value={formData.parameters.content || ''}
                      onChange={(e) => handleParameterChange('content', e.target.value)}
                      placeholder="e.g. Welcome to Dashboard"
                      required
                    />
                    <small>Check will FAIL if this text is not found in the response body.</small>
                  </div>
                </>
              )}

              {formData.check_type === 'ssl_expiry' && (
                <div className="form-group">
                  <label>Port</label>
                  <input
                    type="number"
                    value={formData.parameters.port || 443}
                    onChange={(e) => handleParameterChange('port', parseInt(e.target.value) || 443)}
                    min="1"
                    max="65535"
                  />
                </div>
              )}

              {formData.check_type === 'dns' && (
                <>
                  <div className="form-group">
                    <label>DNS Server</label>
                    <input
                      type="text"
                      value={formData.parameters.server || '8.8.8.8'}
                      onChange={(e) => handleParameterChange('server', e.target.value)}
                      placeholder="8.8.8.8"
                    />
                  </div>
                  <div className="form-group">
                    <label>Record Type</label>
                    <select
                      value={formData.parameters.record_type || 'A'}
                      onChange={(e) => handleParameterChange('record_type', e.target.value)}
                    >
                      <option value="A">A (IPv4)</option>
                      <option value="AAAA">AAAA (IPv6)</option>
                      <option value="CNAME">CNAME</option>
                      <option value="MX">MX</option>
                      <option value="TXT">TXT</option>
                      <option value="NS">NS</option>
                    </select>
                  </div>
                </>
              )}

              {(formData.check_type === 'tcp' || formData.check_type === 'udp') && (
                <div className="form-group">
                  <label>Port *</label>
                  <input
                    type="number"
                    value={formData.parameters.port || ''}
                    onChange={(e) => handleParameterChange('port', parseInt(e.target.value) || '')}
                    min="1"
                    max="65535"
                    required
                  />
                </div>
              )}

              {formData.check_type === 'ping' && (
                <div className="form-group">
                  <label>Ping Count</label>
                  <input
                    type="number"
                    value={formData.parameters.count || 3}
                    onChange={(e) => handleParameterChange('count', parseInt(e.target.value) || 3)}
                    min="1"
                    max="10"
                  />
                </div>
              )}

              {formData.check_type === 'snmp' && (
                <>
                  <div className="form-group">
                    <label>SNMP Community *</label>
                    <input
                      type="text"
                      value={formData.parameters.community || 'public'}
                      onChange={(e) => handleParameterChange('community', e.target.value)}
                      placeholder="public"
                      required
                    />
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label>SNMP Version</label>
                      <select
                        value={formData.parameters.snmp_version || 2}
                        onChange={(e) => handleParameterChange('snmp_version', parseInt(e.target.value))}
                      >
                        <option value={1}>SNMP v1</option>
                        <option value={2}>SNMP v2c</option>
                        <option value={3}>SNMP v3</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label>SNMP Port</label>
                      <input
                        type="number"
                        value={formData.parameters.port || 161}
                        onChange={(e) => handleParameterChange('port', parseInt(e.target.value) || 161)}
                        min="1"
                        max="65535"
                      />
                    </div>
                  </div>
                  <div className="form-group">
                    <label>OID *</label>
                    <input
                      type="text"
                      value={formData.parameters.oid || ''}
                      onChange={(e) => handleParameterChange('oid', e.target.value)}
                      placeholder="1.3.6.1.2.1.1.1.0"
                      required
                    />
                    <small>Example: 1.3.6.1.2.1.1.1.0 (system description)</small>
                  </div>
                </>
              )}

              {formData.check_type === 'ilo' && (
                <>
                  <div className="form-group">
                    <label>SNMP Community *</label>
                    <input
                      type="text"
                      value={formData.parameters.community || 'public'}
                      onChange={(e) => handleParameterChange('community', e.target.value)}
                      placeholder="public"
                      required
                    />
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label>SNMP Version</label>
                      <select
                        value={formData.parameters.snmp_version || 2}
                        onChange={(e) => handleParameterChange('snmp_version', parseInt(e.target.value))}
                      >
                        <option value={1}>SNMP v1</option>
                        <option value={2}>SNMP v2c</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label>SNMP Port</label>
                      <input
                        type="number"
                        value={formData.parameters.port || 161}
                        onChange={(e) => handleParameterChange('port', parseInt(e.target.value) || 161)}
                        min="1"
                        max="65535"
                      />
                    </div>
                  </div>
                  <div className="form-group">
                    <label>Check Type</label>
                    <select
                      value={formData.parameters.check_type || 'health'}
                      onChange={(e) => handleParameterChange('check_type', e.target.value)}
                    >
                      <option value="health">Health Status</option>
                      <option value="temperature">Temperature</option>
                      <option value="power">Power Status</option>
                      <option value="fan">Fan Status</option>
                      <option value="system">System Info</option>
                    </select>
                    <small>Select what to monitor on the iLO device</small>
                  </div>
                </>
              )}

              {formData.check_type === 'idrac' && (
                <>
                  <div className="form-group">
                    <label>SNMP Community *</label>
                    <input
                      type="text"
                      value={formData.parameters.community || 'public'}
                      onChange={(e) => handleParameterChange('community', e.target.value)}
                      placeholder="public"
                      required
                    />
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label>SNMP Version</label>
                      <select
                        value={formData.parameters.snmp_version || 2}
                        onChange={(e) => handleParameterChange('snmp_version', parseInt(e.target.value))}
                      >
                        <option value={1}>SNMP v1</option>
                        <option value={2}>SNMP v2c</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label>SNMP Port</label>
                      <input
                        type="number"
                        value={formData.parameters.port || 161}
                        onChange={(e) => handleParameterChange('port', parseInt(e.target.value) || 161)}
                        min="1"
                        max="65535"
                      />
                    </div>
                  </div>
                  <div className="form-group">
                    <label>Check Type</label>
                    <select
                      value={formData.parameters.check_type || 'health'}
                      onChange={(e) => handleParameterChange('check_type', e.target.value)}
                    >
                      <option value="health">Health Status</option>
                      <option value="temperature">Temperature</option>
                      <option value="power">Power Status</option>
                      <option value="fan">Fan Status</option>
                      <option value="system">System Info</option>
                    </select>
                    <small>Select what to monitor on the iDRAC device</small>
                  </div>
                </>
              )}

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
                <button type="submit" className="btn-primary">
                  {editingCheck ? 'Update' : 'Create'} Check
                </button>
              </div>
            </form>
          </div>
        </div>
      )
      }
    </div >
  );
};

export default ServiceCheckConfig;

