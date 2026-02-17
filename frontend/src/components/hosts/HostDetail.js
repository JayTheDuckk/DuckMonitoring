import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getHost, getHostChecks, getHostMetrics, getMetricsSummary, getServiceChecks, clearHostHistory, scanHostPorts, createServiceCheck, updateHost } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../contexts/ToastContext';
import Modal from '../common/Modal';
import MetricChart from '../common/MetricChart';
import ServiceCheckChart from '../common/ServiceCheckChart';
import ServiceCheckConfig from './ServiceCheckConfig';
import Speedometer from '../common/Speedometer';
import './HostDetail.css';

const HostDetail = () => {
  const { hostId } = useParams();
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const [host, setHost] = useState(null);
  const [checks, setChecks] = useState([]);
  const [metricsSummary, setMetricsSummary] = useState([]);
  const [serviceChecks, setServiceChecks] = useState([]);
  const [selectedMetric, setSelectedMetric] = useState(null);
  const [selectedServiceCheck, setSelectedServiceCheck] = useState(null);
  const [viewMode, setViewMode] = useState('metrics'); // 'metrics' or 'service-checks'
  const [timeRange, setTimeRange] = useState(24);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [clearing, setClearing] = useState(false);
  const [chartKey, setChartKey] = useState(0); // Key to force chart remount

  // Scan state
  const [showScanModal, setShowScanModal] = useState(false);
  const [scanResults, setScanResults] = useState([]);
  const [scanning, setScanning] = useState(false);
  const [selectedPorts, setSelectedPorts] = useState({});

  // Clear history confirmation
  const [showClearHistoryModal, setShowClearHistoryModal] = useState(false);

  // Edit Name state
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState('');

  useEffect(() => {
    loadHostData();
    const interval = setInterval(loadHostData, 30000);
    return () => clearInterval(interval);
  }, [hostId]);

  const loadHostData = async () => {
    try {
      const [hostRes, checksRes, summaryRes, serviceChecksRes] = await Promise.all([
        getHost(hostId),
        getHostChecks(hostId),
        getMetricsSummary(hostId, { hours: timeRange }),
        getServiceChecks(hostId).catch(() => ({ data: [] })) // Don't fail if no service checks
      ]);

      setHost(hostRes.data);
      setChecks(Array.isArray(checksRes.data) ? checksRes.data : checksRes.data.results || []);
      setMetricsSummary(summaryRes.data);
      setServiceChecks((Array.isArray(serviceChecksRes.data) ? serviceChecksRes.data : serviceChecksRes.data.results) || []);

      if (summaryRes.data.length > 0 && !selectedMetric && viewMode === 'metrics') {
        setSelectedMetric(summaryRes.data[0]);
      }
      if (serviceChecksRes.data && serviceChecksRes.data.length > 0 && !selectedServiceCheck && viewMode === 'service-checks') {
        setSelectedServiceCheck(serviceChecksRes.data[0]);
      }

      setError(null);
    } catch (err) {
      setError('Failed to load host data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveName = async () => {
    try {
      await updateHost(hostId, { display_name: editedName });
      setHost(prev => ({ ...prev, display_name: editedName }));
      setIsEditingName(false);
      showSuccess('Name Updated', 'Host display name saved successfully.');
    } catch (err) {
      showError('Update Failed', 'Could not save display name.');
    }
  };

  const handleScanServices = async () => {
    setScanning(true);
    setScanResults([]);
    setSelectedPorts({});
    setShowScanModal(true);
    try {
      const response = await scanHostPorts(hostId);
      setScanResults(response.data);
      // Pre-select all open ports
      const initialSelection = {};
      response.data.forEach(p => {
        if (p.open) initialSelection[p.port] = true;
      });
      setSelectedPorts(initialSelection);
    } catch (err) {
      showError('Scan Failed', err.response?.data?.error || err.message);
      setShowScanModal(false);
    } finally {
      setScanning(false);
    }
  };

  const handleAddSelectedServices = async () => {
    const portsToAdd = scanResults.filter(p => selectedPorts[p.port]);
    if (portsToAdd.length === 0) return;

    setScanning(true);

    try {
      let addedCount = 0;
      for (const result of portsToAdd) {
        // Check if check already exists (basic de-dupe on port/type)
        const exists = checks.some(c =>
          c.check_type === result.service &&
          c.parameters?.port === result.port
        );

        if (!exists) {
          await createServiceCheck(hostId, {
            check_type: result.service,
            check_name: `${result.service.toUpperCase()} Check`,
            check_interval: 60,
            timeout: 10,
            parameters: { port: result.port }
          });
          addedCount++;
        }
      }

      showSuccess('Services Added', `Added ${addedCount} new service check(s).`);
      setShowScanModal(false);
      loadHostData(); // Refresh UI
    } catch (err) {
      showError('Failed to Add Services', err.response?.data?.error || err.message);
    } finally {
      setScanning(false);
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

  const handleClearHistory = () => {
    setShowClearHistoryModal(true);
  };

  const executeClearHistory = async () => {
    setClearing(true);
    setShowClearHistoryModal(false);

    try {
      const response = await clearHostHistory(hostId);
      showSuccess('History Cleared', `Deleted: ${response.data.deleted.total} records`);

      // Reset chart selections to force reload
      setSelectedMetric(null);
      setSelectedServiceCheck(null);

      // Increment chart key to force chart components to remount and reload
      setChartKey(prev => prev + 1);

      // Wait a bit longer to ensure backend has fully processed deletion
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Reload host data to reflect cleared data
      await loadHostData();

      // Force another key increment after data reload to ensure charts refresh
      setChartKey(prev => prev + 1);

      // Wait a bit more, then reset selections if data exists
      await new Promise(resolve => setTimeout(resolve, 500));

      // Reload host data one more time to ensure we have the latest state
      await loadHostData();

      // Now set selections if data exists
      if (metricsSummary.length > 0 && viewMode === 'metrics') {
        setSelectedMetric(metricsSummary[0]);
      }
      if (serviceChecks.length > 0 && viewMode === 'service-checks') {
        setSelectedServiceCheck(serviceChecks[0]);
      }
    } catch (err) {
      showError('Clear Failed', err.response?.data?.error || err.message);
      console.error(err);
    } finally {
      setClearing(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading host details...</div>;
  }

  if (error || !host) {
    return (
      <div className="error-container">
        <div className="error-message">{error || 'Host not found'}</div>
        <Link to="/" className="back-link">← Back to Dashboard</Link>
      </div>
    );
  }

  return (
    <div className="host-detail">
      <div className="host-detail-header">
        <Link to="/" className="back-link">← Back to Dashboard</Link>
        <div className="host-title-section">
          <div className="host-title-row">
            {isEditingName ? (
              <div className="edit-name-container">
                <input
                  type="text"
                  className="edit-name-input"
                  value={editedName}
                  onChange={(e) => setEditedName(e.target.value)}
                  placeholder="Enter display name"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSaveName();
                    if (e.key === 'Escape') setIsEditingName(false);
                  }}
                />
                <button className="btn-save-name" onClick={handleSaveName}>Save</button>
                <button className="btn-cancel-name" onClick={() => setIsEditingName(false)}>Cancel</button>
              </div>
            ) : (
              <>
                <h2 title={host.hostname}>{host.display_name || host.hostname}</h2>
                {(user?.is_admin || user?.role === 'admin' || user?.role === 'operator') && (
                  <button
                    className="btn-edit-name"
                    onClick={() => {
                      setEditedName(host.display_name || '');
                      setIsEditingName(true);
                    }}
                    title="Edit Display Name"
                  >
                    ✎
                  </button>
                )}
              </>
            )}
          </div>
          {host.display_name && <div className="host-subtitle">{host.hostname}</div>}
        </div>


        <span
          className="status-badge-large"
          style={{ backgroundColor: getStatusColor(host.status) }}
        >
          {host.status.toUpperCase()}
        </span>
      </div>

      <div className="host-info-grid">
        <div className="info-item">
          <span className="info-label">IP Address:</span>
          <span className="info-value">{host.ip_address || 'N/A'}</span>
        </div>
        {host.last_check && (
          <div className="info-item">
            <span className="info-label">Last Check:</span>
            <span className="info-value">
              {new Date(host.last_check).toLocaleString()}
            </span>
          </div>
        )}
      </div>
      {
        (user?.is_admin || user?.role === 'admin' || user?.role === 'operator') && (
          <div className="host-header-actions">
            <button
              className="btn-primary"
              onClick={handleScanServices}
              disabled={scanning}
              style={{ marginRight: '1rem' }}
            >
              {scanning ? 'Scanning...' : 'Scan Services'}
            </button>
            <button
              className="btn-clear-history"
              onClick={handleClearHistory}
              disabled={clearing}
              title="Clear all historical data for this host"
            >
              {clearing ? 'Clearing...' : 'Clear Historical Data'}
            </button>
          </div>
        )
      }


      <div className="host-detail-content">
        {/* Show speedometer gauges for agent-installed hosts */}
        {host.agent_id && (
          <div className="speedometer-section">
            <Speedometer hostId={host.id} hostname={host.hostname} />
          </div>
        )}

        <div className="service-checks-section">
          <ServiceCheckConfig
            hostId={host.id}
            hostname={host.hostname}
            ipAddress={host.ip_address}
          />
        </div>

        <div className="checks-section">
          <h3>Service Check Results</h3>
          <div className="checks-grid">
            {checks.length === 0 ? (
              <div className="empty-state">No checks available</div>
            ) : (
              checks.map(check => (
                <div key={check.id} className="check-card">
                  <div className="check-header">
                    <h4>{check.check_name}</h4>
                    <span
                      className="check-status"
                      style={{ backgroundColor: getStatusColor(check.status) }}
                    >
                      {check.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="check-body">
                    <div className="check-type">{check.check_type}</div>
                    {check.output && (
                      <div className="check-output">{check.output}</div>
                    )}
                    {check.last_check && (
                      <div className="check-time">
                        Last: {new Date(check.last_check).toLocaleString()}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="metrics-section">
          <div className="metrics-header">
            <h3>Historical Metrics</h3>
            <div className="metrics-controls">
              <div className="view-mode-toggle">
                <button
                  className={`toggle-btn ${viewMode === 'metrics' ? 'active' : ''}`}
                  onClick={() => {
                    setViewMode('metrics');
                    setSelectedServiceCheck(null);
                    if (metricsSummary.length > 0 && !selectedMetric) {
                      setSelectedMetric(metricsSummary[0]);
                    }
                  }}
                >
                  Agent Metrics
                </button>
                <button
                  className={`toggle-btn ${viewMode === 'service-checks' ? 'active' : ''}`}
                  onClick={() => {
                    setViewMode('service-checks');
                    setSelectedMetric(null);
                    if (serviceChecks.length > 0 && !selectedServiceCheck) {
                      setSelectedServiceCheck(serviceChecks[0]);
                    }
                  }}
                >
                  Service Checks
                </button>
              </div>
              <label>
                Time Range:
                <select
                  value={timeRange}
                  onChange={(e) => {
                    setTimeRange(Number(e.target.value));
                    setSelectedMetric(null);
                    setSelectedServiceCheck(null);
                  }}
                  className="time-range-select"
                >
                  <option value={1}>Last Hour</option>
                  <option value={6}>Last 6 Hours</option>
                  <option value={24}>Last 24 Hours</option>
                  <option value={168}>Last Week</option>
                </select>
              </label>
            </div>
          </div>

          {viewMode === 'metrics' ? (
            metricsSummary.length === 0 ? (
              <div className="empty-state">No metrics available</div>
            ) : (
              <>
                <div className="metrics-selector">
                  <label>
                    Select Metric:
                    <select
                      value={selectedMetric?.name || ''}
                      onChange={(e) => {
                        const metric = metricsSummary.find(m => m.name === e.target.value);
                        setSelectedMetric(metric);
                      }}
                      className="metric-select"
                    >
                      {metricsSummary.map(metric => (
                        <option key={metric.name} value={metric.name}>
                          {metric.name} ({metric.latest_value} {metric.unit || ''})
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                {selectedMetric && (
                  <div className="chart-container">
                    <MetricChart
                      key={`metric-${chartKey}-${selectedMetric.name}-${timeRange}`}
                      hostId={hostId}
                      metricName={selectedMetric.name}
                      metricType={selectedMetric.type}
                      unit={selectedMetric.unit}
                      hours={timeRange}
                      forceRefresh={chartKey}
                    />
                  </div>
                )}
              </>
            )
          ) : (
            serviceChecks.length === 0 ? (
              <div className="empty-state">No service checks configured</div>
            ) : (
              <>
                <div className="metrics-selector">
                  <label>
                    Select Service Check:
                    <select
                      value={selectedServiceCheck?.id || ''}
                      onChange={(e) => {
                        const check = serviceChecks.find(c => c.id === parseInt(e.target.value));
                        setSelectedServiceCheck(check);
                      }}
                      className="metric-select"
                    >
                      {serviceChecks.map(check => (
                        <option key={check.id} value={check.id}>
                          {check.check_name} ({check.check_type}) - {check.status.toUpperCase()}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                {selectedServiceCheck && (
                  <div className="chart-container">
                    <ServiceCheckChart
                      key={`service-check-${chartKey}-${selectedServiceCheck.id}-${timeRange}`}
                      checkId={selectedServiceCheck.id}
                      checkName={selectedServiceCheck.check_name}
                      checkType={selectedServiceCheck.check_type}
                      hours={timeRange}
                      forceRefresh={chartKey}
                    />
                  </div>
                )}
              </>
            )
          )}
        </div>
      </div>
      {
        showScanModal && (
          <div className="modal-overlay" onClick={() => !scanning && setShowScanModal(false)}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
              <div className="modal-header">
                <h3>Scan Results: {host.hostname}</h3>
                {!scanning && (
                  <button className="modal-close" onClick={() => setShowScanModal(false)}>×</button>
                )}
              </div>

              <div className="modal-body">
                {scanning && scanResults.length === 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', padding: '2rem' }}>
                    <div className="loading-spinner"></div>
                    <p>Scanning common ports...</p>
                  </div>
                ) : (
                  <>
                    <p>Found {scanResults.length} open ports. Select services to monitor:</p>
                    <div className="scan-results-list" style={{ maxHeight: '300px', overflowY: 'auto', margin: '1rem 0' }}>
                      {scanResults.length === 0 ? (
                        <p>No open common ports found.</p>
                      ) : (
                        scanResults.map(result => (
                          <div key={result.port} className="scan-result-item" style={{ padding: '0.5rem', borderBottom: '1px solid #eee', display: 'flex', gap: '1rem', alignItems: 'center' }}>
                            <input
                              type="checkbox"
                              checked={!!selectedPorts[result.port]}
                              onChange={(e) => setSelectedPorts({ ...selectedPorts, [result.port]: e.target.checked })}
                              id={`port-${result.port}`}
                            />
                            <label htmlFor={`port-${result.port}`} style={{ cursor: 'pointer', flex: 1 }}>
                              <strong>Port {result.port}</strong> ({result.service.toUpperCase()})
                            </label>
                          </div>
                        ))
                      )}
                    </div>
                  </>
                )}
              </div>

              <div className="modal-actions">
                <button
                  className="btn-secondary"
                  onClick={() => setShowScanModal(false)}
                  disabled={scanning}
                >
                  Cancel
                </button>
                <button
                  className="btn-primary"
                  onClick={handleAddSelectedServices}
                  disabled={scanning || scanResults.length === 0}
                >
                  {scanning ? 'Processing...' : 'Add Selected Services'}
                </button>
              </div>
            </div>
          </div>
        )
      }

      <Modal
        isOpen={showClearHistoryModal}
        onClose={() => setShowClearHistoryModal(false)}
        title="Clear Historical Data"
        footer={
          <>
            <button
              className="btn-secondary"
              onClick={() => setShowClearHistoryModal(false)}
            >
              Cancel
            </button>
            <button
              className="btn-danger"
              onClick={executeClearHistory}
            >
              Clear Data
            </button>
          </>
        }
      >
        <div className="confirmation-content">
          <p>
            Are you sure you want to clear all historical data for <strong>{host.hostname}</strong>?
          </p>
          <div className="warning-box" style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(248, 113, 113, 0.1)', border: '1px solid rgba(248, 113, 113, 0.3)', borderRadius: '6px' }}>
            <p className="warning-text" style={{ color: '#c53030', margin: 0, fontWeight: 500 }}>
              ⚠ This action cannot be undone.
            </p>
            <ul style={{ margin: '0.5rem 0 0 1.5rem', color: '#c53030', fontSize: '0.9rem' }}>
              <li>All collected metrics will be deleted</li>
              <li>Service check history will be removed</li>
              <li>Charts will be reset</li>
            </ul>
          </div>
        </div>
      </Modal>
    </div >
  );
};

export default HostDetail;
