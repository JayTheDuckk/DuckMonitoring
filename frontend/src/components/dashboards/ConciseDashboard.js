import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getHosts, getHostGroups } from '../../services/api';
import './ConciseDashboard.css';

const ConciseDashboard = () => {
  const [hosts, setHosts] = useState([]);
  const [hostGroups, setHostGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [hostsRes, groupsRes] = await Promise.all([
        getHosts(),
        getHostGroups()
      ]);
      setHosts(Array.isArray(hostsRes.data) ? hostsRes.data : hostsRes.data.results || []);
      setHostGroups(Array.isArray(groupsRes.data) ? groupsRes.data : groupsRes.data.results || []);
      setError(null);
    } catch (err) {
      setError('Failed to load hosts');
      console.error(err);
    } finally {
      setLoading(false);
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

  // Group hosts by their group_id
  const grouped = {};
  const ungrouped = [];

  hosts.forEach(host => {
    if (host.group_id && host.group) {
      const groupId = host.group_id;
      if (!grouped[groupId]) {
        grouped[groupId] = {
          group: host.group,
          hosts: []
        };
      }
      grouped[groupId].hosts.push(host);
    } else {
      ungrouped.push(host);
    }
  });

  // Get status counts
  const getStatusCounts = () => {
    const counts = { up: 0, down: 0, unknown: 0 };
    hosts.forEach(host => {
      counts[host.status] = (counts[host.status] || 0) + 1;
    });
    return counts;
  };

  const statusCounts = getStatusCounts();

  if (loading) {
    return <div className="concise-loading">Loading hosts...</div>;
  }

  if (error) {
    return <div className="concise-error">{error}</div>;
  }

  return (
    <div className="concise-dashboard">
      <div className="concise-header">
        <h2>Host Status Overview</h2>
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
      </div>

      <div className="concise-content">
        {/* Grouped hosts */}
        {Object.keys(grouped).length > 0 && Object.values(grouped).map(({ group, hosts: groupHosts }) => {
          const groupStatus = groupHosts.reduce((acc, h) => {
            acc[h.status] = (acc[h.status] || 0) + 1;
            return acc;
          }, { up: 0, down: 0, unknown: 0 });

          return (
            <div
              key={group.id}
              className="concise-group-section"
              style={{
                borderColor: group.color,
                backgroundColor: hexToRgba(group.color, 0.1)
              }}
            >
              <div className="concise-group-header">
                <h3>{group.name}</h3>
                {group.description && <span className="group-desc">{group.description}</span>}
                <div className="group-status-badges">
                  <span className="status-badge-tiny" style={{ backgroundColor: '#4caf50' }}>
                    {groupStatus.up} Up
                  </span>
                  <span className="status-badge-tiny" style={{ backgroundColor: '#f44336' }}>
                    {groupStatus.down} Down
                  </span>
                  <span className="status-badge-tiny" style={{ backgroundColor: '#ff9800' }}>
                    {groupStatus.unknown} Unknown
                  </span>
                </div>
              </div>
              <table className="hosts-table">
                <thead>
                  <tr>
                    <th>Hostname</th>
                    <th>IP Address</th>
                    <th>Status</th>
                    <th>Last Check</th>
                    <th>Type</th>
                  </tr>
                </thead>
                <tbody>
                  {groupHosts.map(host => (
                    <tr key={host.id} className="host-row">
                      <td>
                        <Link to={`/host/${host.id}`} className="host-link" style={{ color: 'var(--accent-primary)' }}>
                          {host.display_name || host.hostname}
                        </Link>
                      </td>
                      <td>{host.ip_address || 'N/A'}</td>
                      <td>
                        <span
                          className="status-badge-table"
                          style={{ backgroundColor: getStatusColor(host.status) }}
                        >
                          {host.status.toUpperCase()}
                        </span>
                      </td>
                      <td>
                        {host.last_check
                          ? new Date(host.last_check).toLocaleString()
                          : 'Never'
                        }
                      </td>
                      <td>
                        {host.agent_id ? (
                          <span className="type-badge agent">Agent</span>
                        ) : (
                          <span className="type-badge agentless">Agentless</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        })}

        {/* Ungrouped hosts */}
        {ungrouped.length > 0 && (
          <div className="concise-group-section">
            <div className="concise-group-header">
              <h3>Ungrouped Hosts</h3>
            </div>
            <table className="hosts-table">
              <thead>
                <tr>
                  <th>Hostname</th>
                  <th>IP Address</th>
                  <th>Status</th>
                  <th>Last Check</th>
                  <th>Type</th>
                </tr>
              </thead>
              <tbody>
                {ungrouped.map(host => (
                  <tr key={host.id} className="host-row">
                    <td>
                      <Link to={`/host/${host.id}`} className="host-link" style={{ color: 'var(--accent-primary)' }}>
                        {host.display_name || host.hostname}
                      </Link>
                    </td>
                    <td>{host.ip_address || 'N/A'}</td>
                    <td>
                      <span
                        className="status-badge-table"
                        style={{ backgroundColor: getStatusColor(host.status) }}
                      >
                        {host.status.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      {host.last_check
                        ? new Date(host.last_check).toLocaleString()
                        : 'Never'
                      }
                    </td>
                    <td>
                      {host.agent_id ? (
                        <span className="type-badge agent">Agent</span>
                      ) : (
                        <span className="type-badge agentless">Agentless</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {Object.keys(grouped).length === 0 && ungrouped.length === 0 && (
          <div className="concise-empty">
            <p>No hosts registered yet.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ConciseDashboard;


