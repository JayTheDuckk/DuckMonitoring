import React, { useState, useEffect, useCallback } from 'react';
import api from '../../services/api';
import './AuditLogs.css';

const AuditLogs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({
    page: 1,
    perPage: 25,
    total: 0,
    pages: 0
  });

  // Filters
  const [filters, setFilters] = useState({
    username: '',
    action: '',
    resourceType: '',
    startDate: '',
    endDate: ''
  });

  // Available filter options
  const [actions, setActions] = useState([]);
  const [resourceTypes, setResourceTypes] = useState([]);

  // Selected log for detail view
  const [selectedLog, setSelectedLog] = useState(null);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('page', pagination.page);
      params.append('per_page', pagination.perPage);

      if (filters.username) params.append('username', filters.username);
      if (filters.action) params.append('action', filters.action);
      if (filters.resourceType) params.append('resource_type', filters.resourceType);
      if (filters.startDate) params.append('start_date', new Date(filters.startDate).toISOString());
      if (filters.endDate) params.append('end_date', new Date(filters.endDate).toISOString());

      const response = await api.get(`/auth/audit-logs/?${params.toString()}`);
      setLogs(response.data.results);
      setPagination(prev => ({
        ...prev,
        total: response.data.count,
        pages: Math.ceil(response.data.count / pagination.perPage)
      }));
    } catch (err) {
      setError('Failed to load audit logs');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [pagination.page, pagination.perPage, filters]);

  const fetchFilterOptions = useCallback(async () => {
    try {
      const [actionsRes, resourceTypesRes] = await Promise.all([
        api.get('/auth/audit-logs/actions/'),
        api.get('/auth/audit-logs/resource-types/')
      ]);
      setActions(actionsRes.data);
      setResourceTypes(resourceTypesRes.data);
    } catch (err) {
      console.error('Failed to load filter options:', err);
    }
  }, []);

  useEffect(() => {
    fetchFilterOptions();
  }, [fetchFilterOptions]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({ ...prev, [name]: value }));
    setPagination(prev => ({ ...prev, page: 1 })); // Reset to first page on filter change
  };

  const clearFilters = () => {
    setFilters({
      username: '',
      action: '',
      resourceType: '',
      startDate: '',
      endDate: ''
    });
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  const handleExport = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.startDate) params.append('start_date', new Date(filters.startDate).toISOString());
      if (filters.endDate) params.append('end_date', new Date(filters.endDate).toISOString());

      const response = await api.get(`/auth/audit-logs/export/?${params.toString()}`, {
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `audit_logs_${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error('Export failed:', err);
      alert('Failed to export audit logs');
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  const getActionBadgeClass = (action) => {
    switch (action) {
      case 'login': return 'badge-success';
      case 'login_failed': return 'badge-danger';
      case 'logout': return 'badge-info';
      case 'create': return 'badge-primary';
      case 'update': return 'badge-warning';
      case 'delete': return 'badge-danger';
      default: return 'badge-secondary';
    }
  };

  if (loading && logs.length === 0) {
    return <div className="audit-logs-loading">Loading audit logs...</div>;
  }

  return (
    <div className="audit-logs-container">
      <div className="audit-logs-header">
        <h1>Audit Logs</h1>
        <p className="subtitle">Track all user actions and system events</p>
      </div>

      {/* Filters */}
      <div className="audit-filters">
        <div className="filter-row">
          <div className="filter-group">
            <label>Username</label>
            <input
              type="text"
              name="username"
              value={filters.username}
              onChange={handleFilterChange}
              placeholder="Search by username..."
            />
          </div>

          <div className="filter-group">
            <label>Action</label>
            <select name="action" value={filters.action} onChange={handleFilterChange}>
              <option value="">All Actions</option>
              {actions.map(action => (
                <option key={action} value={action}>{action}</option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>Resource Type</label>
            <select name="resourceType" value={filters.resourceType} onChange={handleFilterChange}>
              <option value="">All Resources</option>
              {resourceTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>Start Date</label>
            <input
              type="datetime-local"
              name="startDate"
              value={filters.startDate}
              onChange={handleFilterChange}
            />
          </div>

          <div className="filter-group">
            <label>End Date</label>
            <input
              type="datetime-local"
              name="endDate"
              value={filters.endDate}
              onChange={handleFilterChange}
            />
          </div>
        </div>

        <div className="filter-actions">
          <button className="btn-clear" onClick={clearFilters}>Clear Filters</button>
          <button className="btn-export" onClick={handleExport}>Export CSV</button>
        </div>
      </div>

      {error && <div className="audit-error">{error}</div>}

      {/* Logs Table */}
      <div className="audit-table-container">
        <table className="audit-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>User</th>
              <th>Action</th>
              <th>Resource</th>
              <th>IP Address</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {logs.map(log => (
              <tr key={log.id} onClick={() => setSelectedLog(log)}>
                <td className="timestamp">{formatTimestamp(log.timestamp)}</td>
                <td className="username">{log.username || '-'}</td>
                <td>
                  <span className={`badge ${getActionBadgeClass(log.action)}`}>
                    {log.action}
                  </span>
                </td>
                <td className="resource">
                  <span className="resource-type">{log.resource_type}</span>
                  {log.resource_name && (
                    <span className="resource-name">{log.resource_name}</span>
                  )}
                </td>
                <td className="ip-address">{log.ip_address || '-'}</td>
                <td className="details-cell">
                  <button className="btn-view-details">View</button>
                </td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr>
                <td colSpan="6" className="no-data">No audit logs found</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pagination.pages > 1 && (
        <div className="audit-pagination">
          <button
            disabled={pagination.page === 1}
            onClick={() => setPagination(prev => ({ ...prev, page: prev.page - 1 }))}
          >
            Previous
          </button>
          <span className="page-info">
            Page {pagination.page} of {pagination.pages} ({pagination.total} total)
          </span>
          <button
            disabled={pagination.page === pagination.pages}
            onClick={() => setPagination(prev => ({ ...prev, page: prev.page + 1 }))}
          >
            Next
          </button>
        </div>
      )}

      {/* Detail Modal */}
      {selectedLog && (
        <div className="audit-modal-overlay" onClick={() => setSelectedLog(null)}>
          <div className="audit-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Audit Log Details</h2>
              <button className="modal-close" onClick={() => setSelectedLog(null)}>×</button>
            </div>
            <div className="modal-content">
              <div className="detail-row">
                <label>Timestamp:</label>
                <span>{formatTimestamp(selectedLog.timestamp)}</span>
              </div>
              <div className="detail-row">
                <label>User:</label>
                <span>{selectedLog.username || '-'}</span>
              </div>
              <div className="detail-row">
                <label>Action:</label>
                <span className={`badge ${getActionBadgeClass(selectedLog.action)}`}>
                  {selectedLog.action}
                </span>
              </div>
              <div className="detail-row">
                <label>Resource Type:</label>
                <span>{selectedLog.resource_type}</span>
              </div>
              <div className="detail-row">
                <label>Resource ID:</label>
                <span>{selectedLog.resource_id || '-'}</span>
              </div>
              <div className="detail-row">
                <label>Resource Name:</label>
                <span>{selectedLog.resource_name || '-'}</span>
              </div>
              <div className="detail-row">
                <label>IP Address:</label>
                <span>{selectedLog.ip_address || '-'}</span>
              </div>
              <div className="detail-row">
                <label>User Agent:</label>
                <span className="user-agent">{selectedLog.user_agent || '-'}</span>
              </div>

              {selectedLog.old_values && (
                <div className="detail-row values">
                  <label>Previous Values:</label>
                  <pre>{JSON.stringify(selectedLog.old_values, null, 2)}</pre>
                </div>
              )}

              {selectedLog.new_values && (
                <div className="detail-row values">
                  <label>New Values:</label>
                  <pre>{JSON.stringify(selectedLog.new_values, null, 2)}</pre>
                </div>
              )}

              {selectedLog.details && (
                <div className="detail-row values">
                  <label>Additional Details:</label>
                  <pre>{JSON.stringify(selectedLog.details, null, 2)}</pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AuditLogs;
