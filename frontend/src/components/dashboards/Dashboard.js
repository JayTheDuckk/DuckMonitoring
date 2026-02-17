import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { getHosts, createHost, updateHost, deleteHost, getHostGroups, createHostGroup, updateHostGroup, deleteHostGroup } from '../../services/api';
import AgentInstall from '../settings/AgentInstall';
import Modal from '../common/Modal';
import './Dashboard.css';

const Dashboard = () => {
  const { user } = useAuth();
  const [hosts, setHosts] = useState([]);
  const [hostGroups, setHostGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [editingGroup, setEditingGroup] = useState(null);
  const [editingHost, setEditingHost] = useState(null);
  const [formData, setFormData] = useState({
    hostname: '',
    ip_address: '',
    group_id: ''
  });
  const [groupFormData, setGroupFormData] = useState({
    name: '',
    description: '',
    color: '#4D9CFF'
  });
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [viewMode, setViewMode] = useState('grouped'); // 'grouped' or 'all'
  const [showAgentInstall, setShowAgentInstall] = useState(false);

  // Delete confirmation state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [itemToDelete, setItemToDelete] = useState(null); // { type: 'host'|'group', id, name }

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      await Promise.all([loadHosts(), loadHostGroups()]);
    } finally {
      setLoading(false);
    }
  };

  const loadHosts = async () => {
    try {
      const response = await getHosts();
      setHosts(Array.isArray(response.data) ? response.data : response.data.results || []);
      setError(null);
    } catch (err) {
      const errorMessage = err.response?.data?.msg || err.response?.data?.error || err.message || 'Failed to load hosts';
      setError(`Failed to load hosts: ${errorMessage}`);
      console.error('Load hosts error:', err);

      // If it's an auth error, the token might be invalid
      if (err.response?.status === 401) {
        console.error('Authentication failed - token may be invalid');
      }
    }
  };

  const loadHostGroups = async () => {
    try {
      const response = await getHostGroups();
      setHostGroups(Array.isArray(response.data) ? response.data : response.data.results || []);
    } catch (err) {
      console.error('Load host groups error:', err);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'up':
        return '#4caf50';
      case 'down':
        return '#f44336';
      default:
        return '#ff9800';
    }
  };

  // Helper function to convert hex color to rgba with transparency
  const hexToRgba = (hex, alpha = 0.1) => {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  const getStatusCounts = () => {
    const counts = { up: 0, down: 0, unknown: 0 };
    hosts.forEach(host => {
      counts[host.status] = (counts[host.status] || 0) + 1;
    });
    return counts;
  };

  const statusCounts = getStatusCounts();

  // No longer using groupedHosts helper in the same way, we will iterate hostGroups directly in render
  // and filter hosts there.
  const getGroupHosts = (groupId) => {
    // API returns 'group' as the ID, not an object
    return hosts.filter(h => h.group === groupId);
  };

  const getUngroupedHosts = () => {
    // API returns 'group' as the ID or null
    return hosts.filter(h => !h.group);
  };

  const handleAddHost = async (e) => {
    e.preventDefault();
    setFormError('');

    if (!formData.hostname.trim()) {
      setFormError('Hostname is required');
      return;
    }

    setSubmitting(true);
    try {
      if (editingHost) {
        await updateHost(editingHost.id, {
          hostname: formData.hostname.trim(),
          ip_address: formData.ip_address.trim() || null,
          group: formData.group_id || null // API expects 'group', not 'group_id'
        });
      } else {
        await createHost({
          hostname: formData.hostname.trim(),
          ip_address: formData.ip_address.trim() || null,
          group: formData.group_id || null // API expects 'group', not 'group_id'
        });
      }
      setShowAddModal(false);
      setEditingHost(null);
      setFormData({ hostname: '', ip_address: '', group_id: '' });
      await loadData();
    } catch (err) {
      setFormError(err.response?.data?.error || err.message || 'Failed to save host');
      console.error('Save host error:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleEditHost = (host) => {
    setEditingHost(host);
    setFormData({
      hostname: host.hostname || '',
      ip_address: host.ip_address || '',
      group_id: host.group || '' // API returns 'group' (ID), not 'group_id'
    });
    setShowAddModal(true);
  };

  const handleAddGroup = async (e) => {
    e.preventDefault();
    setFormError('');

    if (!groupFormData.name.trim()) {
      setFormError('Group name is required');
      return;
    }

    setSubmitting(true);
    try {
      if (editingGroup) {
        await updateHostGroup(editingGroup.id, groupFormData);
      } else {
        await createHostGroup(groupFormData);
      }
      setShowGroupModal(false);
      setEditingGroup(null);
      setGroupFormData({ name: '', description: '', color: '#4D9CFF' });
      await loadHostGroups();
    } catch (err) {
      setFormError(err.response?.data?.error || err.message || 'Failed to save group');
      console.error('Save group error:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteGroup = (groupId) => {
    const group = hostGroups.find(g => g.id === groupId);
    const groupName = group ? group.name : 'this group';

    setItemToDelete({
      type: 'group',
      id: groupId,
      name: groupName
    });
    setShowDeleteModal(true);
  };

  const executeDeleteGroup = async () => {
    try {
      await deleteHostGroup(itemToDelete.id);
      await loadData(); // Reload both hosts and groups to reflect changes
      setError(null);
      setShowDeleteModal(false);
      setItemToDelete(null);
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.message || 'Failed to delete group';
      setError(errorMsg);
      console.error('Delete group error:', err);
      // Keep modal open if there's an error? Or maybe close it and show error?
      // For now, let's close it and show the dashboard error
      setShowDeleteModal(false);
    }
  };

  const handleEditGroup = (group) => {
    setEditingGroup(group);
    setGroupFormData({
      name: group.name,
      description: group.description || '',
      color: group.color || '#4D9CFF'
    });
    setShowGroupModal(true);
  };

  const handleDeleteHost = (hostId, hostname, e) => {
    e.preventDefault();
    e.stopPropagation();

    setItemToDelete({
      type: 'host',
      id: hostId,
      name: hostname
    });
    setShowDeleteModal(true);
  };

  const executeDeleteHost = async () => {
    try {
      // Optimistically remove from UI
      setHosts(prev => prev.filter(h => h.id !== itemToDelete.id));
      await deleteHost(itemToDelete.id);
      await loadData(); // Refresh all data to be sure
      setShowDeleteModal(false);
      setItemToDelete(null);
    } catch (err) {
      // Revert if failed (loadData will handle this anyway)
      setError('Failed to delete host: ' + (err.response?.data?.error || err.message));
      loadData();
      setShowDeleteModal(false);
    }
  };

  const handleQuickGroupChange = async (hostId, groupId) => {
    if (!groupId) return;
    try {
      const host = hosts.find(h => h.id === hostId);
      if (!host) return;

      await updateHost(hostId, {
        hostname: host.hostname,
        group: groupId
      });

      await loadData();
    } catch (err) {
      console.error('Quick group assign error:', err);
      setError('Failed to assign group: ' + (err.response?.data?.error || err.message));
    }
  };

  if (loading) {
    return <div className="loading">Loading hosts...</div>;
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h2>Hosts Overview</h2>
          {user && <p className="welcome-message">Welcome back, {user.username}!</p>}
        </div>
        <div className="header-actions">
          <button
            className="btn-refresh"
            onClick={loadData}
            title="Refresh hosts"
            disabled={loading}
          >
            🔄 Refresh
          </button>
          <div className="status-summary">
            <div className="status-item">
              <span className="status-dot" style={{ backgroundColor: '#4caf50' }}></span>
              <span>Up: {statusCounts.up}</span>
            </div>
            <div className="status-item">
              <span className="status-dot" style={{ backgroundColor: '#f44336' }}></span>
              <span>Down: {statusCounts.down}</span>
            </div>
            <div className="status-item">
              <span className="status-dot" style={{ backgroundColor: '#ff9800' }}></span>
              <span>Unknown: {statusCounts.unknown}</span>
            </div>
          </div>
          <div className="view-toggle">
            <button
              className={`toggle-btn ${viewMode === 'grouped' ? 'active' : ''}`}
              onClick={() => setViewMode('grouped')}
            >
              Grouped
            </button>
            <button
              className={`toggle-btn ${viewMode === 'all' ? 'active' : ''}`}
              onClick={() => setViewMode('all')}
            >
              All
            </button>
          </div>
          {(user?.is_admin || user?.role === 'admin' || user?.role === 'operator') && (
            <>
              {(user?.is_admin || user?.role === 'admin') && (
                <button className="btn-add-group" onClick={() => {
                  setEditingGroup(null);
                  setGroupFormData({ name: '', description: '', color: '#4D9CFF' });
                  setShowGroupModal(true);
                }}>
                  + Add Group
                </button>
              )}
              <button className="btn-install-agent" onClick={() => setShowAgentInstall(true)}>
                📥 Install Agent
              </button>
              <button className="btn-add-host" onClick={() => setShowAddModal(true)}>
                + Add Host
              </button>
            </>
          )}
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {viewMode === 'grouped' ? (
        <div className="hosts-by-groups">
          {hostGroups.map(group => {
            const groupHosts = getGroupHosts(group.id);
            const groupStatus = groupHosts.reduce((acc, h) => {
              acc[h.status] = (acc[h.status] || 0) + 1;
              return acc;
            }, { up: 0, down: 0, unknown: 0 });

            return (
              <div
                key={group.id}
                className="host-group-section"
                style={{
                  borderTopColor: group.color,
                }}
              >
                <div className="group-header">
                  <div className="group-title">
                    <h3>{group.name}</h3>
                    {group.description && <span className="group-description">{group.description}</span>}
                    <span className="group-host-count">{groupHosts.length} host{groupHosts.length !== 1 ? 's' : ''}</span>
                  </div>
                  <div className="group-status-summary">
                    {groupStatus.up > 0 && (
                      <span className="status-badge-small" style={{ backgroundColor: '#4caf50' }}>
                        {groupStatus.up} Up
                      </span>
                    )}
                    {groupStatus.down > 0 && (
                      <span className="status-badge-small" style={{ backgroundColor: '#f44336' }}>
                        {groupStatus.down} Down
                      </span>
                    )}
                    {groupStatus.unknown > 0 && (
                      <span className="status-badge-small" style={{ backgroundColor: '#ff9800' }}>
                        {groupStatus.unknown} Unknown
                      </span>
                    )}
                  </div>
                  {(user?.is_admin || user?.role === 'admin' || user?.role === 'operator') && (
                    <div className="group-actions">
                      <button
                        className="btn-small"
                        onClick={() => handleEditGroup(group)}
                        title="Edit group"
                      >
                        Edit
                      </button>
                      <button
                        className="btn-small btn-danger"
                        onClick={() => handleDeleteGroup(group.id)}
                        title="Delete group"
                      >
                        Delete
                      </button>
                    </div>
                  )}
                </div>

                {groupHosts.length > 0 ? (
                  <div className="table-responsive">
                    <table className="host-group-table">
                      <thead>
                        <tr>
                          <th style={{ width: '40px' }}></th>
                          <th>Hostname</th>
                          <th>IP Address</th>
                          <th>Agent ID</th>
                          <th>Last Check</th>
                          <th>Status</th>
                          {(user?.is_admin || user?.role === 'admin' || user?.role === 'operator') && <th>Actions</th>}
                        </tr>
                      </thead>
                      <tbody>
                        {groupHosts.map(host => (
                          <tr key={host.id} className="host-row">
                            <td className="status-cell">
                              <span
                                className="status-dot-large"
                                style={{ backgroundColor: getStatusColor(host.status) }}
                                title={host.status.toUpperCase()}
                              ></span>
                            </td>
                            <td className="hostname-cell">
                              <Link to={`/host/${host.id}`} className="host-link">
                                {host.display_name || host.hostname}
                              </Link>
                            </td>
                            <td>{host.ip_address || '-'}</td>
                            <td>{host.agent_id ? <span className="agent-id-badge">{host.agent_id.substring(0, 8)}...</span> : '-'}</td>
                            <td>{host.last_check ? new Date(host.last_check).toLocaleString() : '-'}</td>
                            <td>
                              <span className={`status-text status-${host.status}`}>
                                {host.status.toUpperCase()}
                              </span>
                            </td>
                            {(user?.is_admin || user?.role === 'admin' || user?.role === 'operator') && (
                              <td className="actions-cell">
                                <button
                                  className="btn-icon"
                                  onClick={(e) => {
                                    handleEditHost(host);
                                  }}
                                  title="Edit host"
                                >
                                  ✎
                                </button>
                                {(user?.is_admin || user?.role === 'admin') && (
                                  <button
                                    className="btn-icon btn-icon-danger"
                                    onClick={(e) => handleDeleteHost(host.id, host.hostname, e)}
                                    title="Delete host"
                                  >
                                    ×
                                  </button>
                                )}
                              </td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="empty-group-message">No hosts in this group</div>
                )}
              </div>
            );
          })}

          {getUngroupedHosts().length > 0 && (
            <div className="host-group-section ungrouped-section">
              <div className="group-header">
                <div className="group-title">
                  <h3>Ungrouped Hosts</h3>
                  <span className="group-host-count">{getUngroupedHosts().length} host{getUngroupedHosts().length !== 1 ? 's' : ''}</span>
                </div>
              </div>
              <div className="table-responsive">
                <table className="host-group-table compact">
                  <thead>
                    <tr>
                      <th style={{ width: '30px' }}></th>
                      <th>Hostname</th>
                      <th>IP</th>
                      <th>Agent</th>
                      <th>Quick Group</th>
                      <th>Status</th>
                      {(user?.is_admin || user?.role === 'admin' || user?.role === 'operator') && <th>Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {getUngroupedHosts().map(host => (
                      <tr key={host.id} className="host-row">
                        <td className="status-cell">
                          <span
                            className="status-dot-large"
                            style={{ backgroundColor: getStatusColor(host.status) }}
                            title={host.status.toUpperCase()}
                          ></span>
                        </td>
                        <td className="hostname-cell">
                          <Link to={`/host/${host.id}`} className="host-link">
                            {host.display_name || host.hostname}
                          </Link>
                        </td>
                        <td>{host.ip_address || '-'}</td>
                        <td>{host.agent_id ? <span className="agent-id-badge" title={host.agent_id}>{host.agent_id.substring(0, 6)}..</span> : '-'}</td>
                        <td className="quick-group-cell">
                          <select
                            className="quick-group-select"
                            onChange={(e) => handleQuickGroupChange(host.id, e.target.value)}
                            defaultValue=""
                            onClick={(e) => e.stopPropagation()}
                          >
                            <option value="" disabled>Assign...</option>
                            {hostGroups.map(g => (
                              <option key={g.id} value={g.id}>{g.name}</option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <span className={`status-text status-${host.status}`}>
                            {host.status.toUpperCase()}
                          </span>
                        </td>
                        {(user?.is_admin || user?.role === 'admin' || user?.role === 'operator') && (
                          <td className="actions-cell">
                            <button
                              className="btn-icon"
                              onClick={(e) => {
                                handleEditHost(host);
                              }}
                              title="Edit host"
                            >
                              ✎
                            </button>
                            {(user?.is_admin || user?.role === 'admin') && (
                              <button
                                className="btn-icon btn-icon-danger"
                                onClick={(e) => handleDeleteHost(host.id, host.hostname, e)}
                                title="Delete host"
                              >
                                ×
                              </button>
                            )}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {hostGroups.length === 0 && getUngroupedHosts().length === 0 && hosts.length === 0 && (
            <div className="empty-state">
              <p>No hosts registered yet.</p>
              <p className="empty-state-hint">Start an agent or add a host to begin monitoring.</p>
            </div>
          )}
        </div>
      ) : (
        <div className="hosts-grid">
          {hosts.length === 0 ? (
            <div className="empty-state">
              <p>No hosts registered yet.</p>
              <p className="empty-state-hint">Start an agent to begin monitoring.</p>
            </div>
          ) : (
            hosts.map(host => (
              <div key={host.id} className="host-card-wrapper">
                <Link to={`/host/${host.id}`} className="host-card">
                  <div className="host-card-header">
                    <div className="host-card-title">
                      <h3 title={host.hostname}>{host.display_name || host.hostname}</h3>
                      {host.display_name && <span className="host-subtitle">{host.hostname}</span>}
                    </div>
                    <span
                      className="status-badge"
                      style={{ backgroundColor: getStatusColor(host.status) }}
                    >
                      {host.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="host-card-body">
                    <div className="host-info">
                      <span className="info-label">IP Address:</span>
                      <span className="info-value">{host.ip_address || 'N/A'}</span>
                    </div>
                    {host.last_check && (
                      <div className="host-info">
                        <span className="info-label">Last Check:</span>
                        <span className="info-value">
                          {new Date(host.last_check).toLocaleString()}
                        </span>
                      </div>
                    )}
                    {host.agent_id && (
                      <div className="host-info">
                        <span className="info-label">Agent ID:</span>
                        <span className="info-value agent-id">{host.agent_id.substring(0, 8)}...</span>
                      </div>
                    )}
                  </div>
                </Link>
                {(user?.is_admin || user?.role === 'admin' || user?.role === 'operator') && (
                  <div className="host-actions">
                    <button
                      className="host-edit-btn"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        handleEditHost(host);
                      }}
                      title="Edit host"
                    >
                      ✎
                    </button>
                    {(user?.is_admin || user?.role === 'admin') && (
                      <button
                        className="host-delete-btn"
                        onClick={(e) => handleDeleteHost(host.id, host.hostname, e)}
                        title="Delete host"
                      >
                        ×
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      <Modal
        isOpen={showAddModal}
        onClose={() => {
          setShowAddModal(false);
          setEditingHost(null);
          setFormData({ hostname: '', ip_address: '', group_id: '' });
          setFormError('');
        }}
        title={editingHost ? 'Edit Host' : 'Add New Host'}
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setShowAddModal(false);
                setEditingHost(null);
                setFormData({ hostname: '', ip_address: '', group_id: '' });
                setFormError('');
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              form="add-host-form" // Link button to form via ID
              className="btn-primary"
              disabled={submitting}
            >
              {submitting ? (editingHost ? 'Updating...' : 'Adding...') : (editingHost ? 'Update Host' : 'Add Host')}
            </button>
          </>
        }
      >
        <form id="add-host-form" onSubmit={handleAddHost}>
          {formError && <div className="error-message">{formError}</div>}

          <div className="form-group">
            <label htmlFor="hostname">Hostname *</label>
            <input
              type="text"
              id="hostname"
              value={formData.hostname}
              onChange={(e) => setFormData({ ...formData, hostname: e.target.value })}
              placeholder="e.g., web-server-01"
              required
              autoFocus
            />
            <small>Unique hostname for this host</small>
          </div>

          <div className="form-group">
            <label htmlFor="ip_address">IP Address</label>
            <input
              type="text"
              id="ip_address"
              value={formData.ip_address}
              onChange={(e) => setFormData({ ...formData, ip_address: e.target.value })}
              placeholder="e.g., 192.168.1.100"
            />
            <small>Optional - IP address for agentless monitoring</small>
          </div>

          <div className="form-group">
            <label htmlFor="group_id">Host Group</label>
            <select
              id="group_id"
              value={formData.group_id}
              onChange={(e) => setFormData({ ...formData, group_id: e.target.value || '' })}
            >
              <option value="">No Group</option>
              {hostGroups.map(group => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </select>
            <small>Optional - Assign host to a group</small>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={showGroupModal}
        onClose={() => {
          setShowGroupModal(false);
          setEditingGroup(null);
          setGroupFormData({ name: '', description: '', color: '#4D9CFF' });
          setFormError('');
        }}
        title={editingGroup ? 'Edit Host Group' : 'Add Host Group'}
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setShowGroupModal(false);
                setEditingGroup(null);
                setGroupFormData({ name: '', description: '', color: '#4D9CFF' });
                setFormError('');
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              form="add-group-form"
              className="btn-primary"
              disabled={submitting}
            >
              {submitting ? 'Saving...' : (editingGroup ? 'Update' : 'Create') + ' Group'}
            </button>
          </>
        }
      >
        <form id="add-group-form" onSubmit={handleAddGroup}>
          {formError && <div className="error-message">{formError}</div>}

          <div className="form-group">
            <label htmlFor="group_name">Group Name *</label>
            <input
              type="text"
              id="group_name"
              value={groupFormData.name}
              onChange={(e) => setGroupFormData({ ...groupFormData, name: e.target.value })}
              placeholder="e.g., Web Servers"
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="group_description">Description</label>
            <textarea
              id="group_description"
              value={groupFormData.description}
              onChange={(e) => setGroupFormData({ ...groupFormData, description: e.target.value })}
              placeholder="Optional description for this group"
              rows="3"
            />
          </div>

          <div className="form-group">
            <label htmlFor="group_color">Color</label>
            <div className="color-picker-group">
              <input
                type="color"
                id="group_color"
                value={groupFormData.color}
                onChange={(e) => setGroupFormData({ ...groupFormData, color: e.target.value })}
                style={{ width: '60px', height: '40px', cursor: 'pointer' }}
              />
              <input
                type="text"
                value={groupFormData.color}
                onChange={(e) => setGroupFormData({ ...groupFormData, color: e.target.value })}
                placeholder="#4D9CFF"
                style={{ flex: 1, marginLeft: '0.5rem' }}
              />
            </div>
            <small>Color used to identify this group in the dashboard</small>
          </div>
        </form>
      </Modal>

      {showAgentInstall && (
        <AgentInstall
          serverUrl={process.env.REACT_APP_API_URL || 'http://localhost:5001/api'}
          onClose={() => setShowAgentInstall(false)}
        />
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false);
          setItemToDelete(null);
        }}
        title={`Delete {itemToDelete?.type === 'group' ? 'Host Group' : 'Host'}`}
        footer={
          <>
            <button
              className="btn-secondary"
              onClick={() => {
                setShowDeleteModal(false);
                setItemToDelete(null);
              }}
            >
              Cancel
            </button>
            <button
              className="btn-danger"
              onClick={() => {
                if (itemToDelete?.type === 'group') {
                  executeDeleteGroup();
                } else {
                  executeDeleteHost();
                }
              }}
            >
              Delete
            </button>
          </>
        }
      >
        <div className="confirmation-content">
          <p>
            Are you sure you want to delete <strong>{itemToDelete?.name}</strong>?
          </p>
          {itemToDelete?.type === 'group' && (
            <p className="warning-text">
              All hosts in this group will be unassigned and moved to the "Ungrouped" section.
            </p>
          )}
          {itemToDelete?.type === 'host' && (
            <p className="warning-text">
              This action cannot be undone. All historical data for this host will be permanently removed.
            </p>
          )}
        </div>
      </Modal>
    </div>
  );
};

export default Dashboard;

