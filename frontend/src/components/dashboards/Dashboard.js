import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { getHosts, createHost, updateHost, deleteHost, getHostGroups, createHostGroup, updateHostGroup, deleteHostGroup, clearUngroupedHosts, getLanWatch, updateLanWatch } from '../../services/api';
import AgentInstall from '../settings/AgentInstall';
import Modal from '../common/Modal';
import { AgentIcon, ChevronIcon, CloseIcon, EditIcon, PlusIcon, RefreshIcon, SearchIcon } from '../common/Icons';
import './Dashboard.css';

const formatLastSeen = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const deltaMs = Date.now() - date.getTime();
  const minutes = Math.floor(deltaMs / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString();
};

const looksLikeIp = (value) => /^\d{1,3}(\.\d{1,3}){3}$/.test(String(value || '').trim());

const isAssumedName = (value, ip) => {
  const name = String(value || '').trim();
  if (!name) return false;
  if (ip && name === ip) return false;
  if (looksLikeIp(name)) return false;
  return true;
};

const hostDisplayName = (host) => {
  const candidates = [host.display_name, host.mdns_name, host.hostname, host.apple_model];
  for (const candidate of candidates) {
    if (isAssumedName(candidate, host.ip_address)) return candidate;
  }
  return '';
};

const hostSecondaryName = (host) => {
  const primary = hostDisplayName(host);
  const candidates = [host.mdns_name, host.hostname];
  for (const candidate of candidates) {
    if (isAssumedName(candidate, host.ip_address) && candidate !== primary) return candidate;
  }
  return null;
};

const hostMatchesSearch = (host, query) => {
  if (!query) return true;
  const q = query.toLowerCase();
  return [
    host.hostname,
    host.display_name,
    host.mdns_name,
    host.ip_address,
    host.mac_address,
    host.vendor,
    host.device_class,
    host.os_guess,
    host.apple_model,
  ].some((value) => (value || '').toLowerCase().includes(q));
};

const SPECIFIC_OS = new Set(['Windows', 'macOS', 'iOS', 'tvOS', 'Android', 'Linux', 'Embedded Linux']);

const osFromAppleModel = (model) => {
  const value = String(model || '').toLowerCase();
  if (!value) return null;
  if (value.startsWith('mac') || value.includes('macbook') || value.includes('imac')) return 'macOS';
  if (value.includes('iphone') || value.includes('ipad') || value.includes('ipod')) return 'iOS';
  if (value.includes('appletv') || value.includes('apple tv')) return 'tvOS';
  return null;
};

const assumedOs = (host) => {
  if (SPECIFIC_OS.has(host.os_guess)) return host.os_guess;
  return osFromAppleModel(host.apple_model);
};

const HostIpCell = ({ host }) => (
  <td className="host-ip-cell">
    <Link to={`/host/${host.id}`} className="host-link">
      {host.ip_address || '—'}
    </Link>
  </td>
);

const HostIdentityCell = ({ host }) => {
  const name = hostDisplayName(host);
  const secondary = hostSecondaryName(host);
  if (!name) {
    return <td className="hostname-cell muted-cell" />;
  }
  return (
    <td className="hostname-cell">
      <span className="host-assumed-name">{name}</span>
      {secondary && <span className="host-identity-secondary">{secondary}</span>}
      {host.apple_model && host.apple_model !== name && (
        <span className="host-apple-model">{host.apple_model}</span>
      )}
    </td>
  );
};

const HostDeviceCell = ({ host }) => {
  const os = assumedOs(host);
  if (!os) {
    return <td className="muted-cell">—</td>;
  }
  return (
    <td>
      <span
        className="device-pill os"
        title={(host.identification_clues || []).join(' · ') || undefined}
      >
        {os}
      </span>
    </td>
  );
};

const vendorLabel = (host) => {
  const vendor = String(host.vendor || '').trim();
  if (!vendor) return '';
  if (host.mac_type === 'private' || /private|random|unknown/i.test(vendor)) {
    return '';
  }
  return vendor;
};

const SERVICE_CATEGORIES = {
  http: 'web', https: 'secure', ssh: 'remote', ftp: 'remote',
  mysql: 'database', postgresql: 'database', redis: 'database',
  mongodb: 'database', smtp: 'mail', imap: 'mail', pop3: 'mail',
};

const hostServices = (host) => host.services || host.discovered_services || [];

const serviceCategory = (name) => SERVICE_CATEGORIES[String(name || '').toLowerCase()] || 'other';

const formatAbsolute = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleString();
};

const hostLatency = (host) => {
  const raw = host.latency_ms ?? host.latency;
  if (raw == null || raw === '') {
    const ping = (host.service_checks || []).find((check) => check.check_type === 'ping');
    const match = ping?.last_output && String(ping.last_output).match(/([\d.]+)\s*ms/i);
    return match ? Number(match[1]) : null;
  }
  const value = Number(raw);
  return Number.isFinite(value) ? value : null;
};

const ttlHint = (ttl) => {
  if (ttl == null || ttl === '') return '';
  if (ttl <= 64) return 'Unix-like / mobile';
  if (ttl <= 128) return 'Windows-like';
  return 'Network gear';
};

const MetricItem = ({ label, value, hint }) => {
  if (value == null || value === '') return null;
  return (
    <div className="host-metric">
      <span className="host-metric-label">{label}</span>
      <span className="host-metric-value">{value}</span>
      {hint && <span className="host-metric-hint">{hint}</span>}
    </div>
  );
};

const HostMacCell = ({ host }) => (
  <td className="host-mac-cell">{host.mac_address || '—'}</td>
);

const HostVendorCell = ({ host }) => {
  const label = vendorLabel(host);
  return (
    <td className={label ? undefined : 'muted-cell'}>
      {label}
    </td>
  );
};

const ipToSortValue = (ip) => {
  if (!ip) return null;
  const parts = String(ip).split('.');
  if (parts.length === 4 && parts.every((part) => /^\d+$/.test(part))) {
    return parts.reduce((acc, part) => acc * 256 + Number(part), 0);
  }
  return String(ip).toLowerCase();
};

const compareSortValues = (a, b, dir) => {
  const aEmpty = a == null || a === '';
  const bEmpty = b == null || b === '';
  if (aEmpty && bEmpty) return 0;
  if (aEmpty) return 1;
  if (bEmpty) return -1;
  const cmp = typeof a === 'number' && typeof b === 'number'
    ? a - b
    : String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' });
  return dir === 'desc' ? -cmp : cmp;
};

const hostSortValue = (host, key) => {
  switch (key) {
    case 'device':
      return (hostDisplayName(host) || '').toLowerCase();
    case 'ip':
      return ipToSortValue(host.ip_address);
    case 'mac':
      return (host.mac_address || '').replace(/[:-]/g, '').toLowerCase();
    case 'type':
      return (assumedOs(host) || '').toLowerCase();
    case 'vendor':
      return vendorLabel(host).replace('—', '').toLowerCase();
    case 'last_seen': {
      const raw = host.last_seen || host.last_check;
      const time = raw ? Date.parse(raw) : NaN;
      return Number.isNaN(time) ? null : time;
    }
    case 'status':
      return host.status || '';
    case 'services':
      return hostServices(host).length;
    default:
      return '';
  }
};

const sortHosts = (list, key, dir) => (
  [...list].sort((left, right) => {
    const cmp = compareSortValues(hostSortValue(left, key), hostSortValue(right, key), dir);
    if (cmp !== 0) return cmp;
    return compareSortValues(ipToSortValue(left.ip_address), ipToSortValue(right.ip_address), 'asc');
  })
);

const DEFAULT_GROUP_COLOR = '#0f6e6a';

const HostDetailsRow = ({ host, colSpan }) => {
  const services = hostServices(host);
  const latency = hostLatency(host);
  const ttl = host.ping_ttl;
  const checks = (host.service_checks || []).filter((check) => check.enabled !== false);
  const macKind = host.mac_type === 'private' ? 'Private / randomized' : (host.mac_type || '');

  return (
    <tr className="services-expansion">
      <td colSpan={colSpan}>
        <div className="services-expansion-inner host-details-inner">
          <div className="host-metrics-grid">
            <MetricItem
              label="Latency"
              value={latency != null ? `${latency.toFixed(latency >= 10 ? 0 : 1)} ms` : null}
              hint={latency != null && latency > 150 ? 'High — weak Wi‑Fi or sleeping device' : null}
            />
            <MetricItem label="Ping TTL" value={ttl} hint={ttlHint(ttl)} />
            <MetricItem label="First seen" value={formatAbsolute(host.first_seen)} />
            <MetricItem label="Last check" value={host.last_check ? formatLastSeen(host.last_check) : null} />
            <MetricItem
              label="Identity"
              value={host.confidence != null ? `${host.confidence}% confidence` : null}
            />
            <MetricItem label="Class" value={host.device_class && host.device_class !== 'unknown' ? host.device_class.replace(/_/g, ' ') : null} />
            <MetricItem label="MAC" value={macKind} />
            <MetricItem label="Agent" value={host.agent_id ? `${String(host.agent_id).slice(0, 8)}…` : 'None'} />
          </div>

          {checks.length > 0 && (
            <div className="host-detail-section">
              <h4>Watched checks</h4>
              <div className="check-pills">
                {checks.map((check) => (
                  <span key={check.id || check.check_name} className={`check-pill status-${check.status || 'unknown'}`}>
                    {check.check_name || check.check_type}
                    {check.port ? ` :${check.port}` : ''}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="host-detail-section">
            <h4>Open ports</h4>
            {services.length === 0 ? (
              <p className="services-empty">No open ports stored yet. Run Discovery to fill this in.</p>
            ) : (
              <div className="services-pills">
                {services.map((service) => {
                  const name = service.service || service.check_type || 'unknown';
                  const category = serviceCategory(name);
                  return (
                    <div key={`${service.port}-${name}`} className="service-pill readonly">
                      <div className="service-pill-info">
                        <span className="service-pill-port">Port {service.port || '—'}</span>
                        <span className="service-pill-name">{name}</span>
                      </div>
                      <span className={`service-pill-protocol ${category}`}>{category}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </td>
    </tr>
  );
};

const normalizeGroupId = (value) => {
  if (value == null || value === '' || value === 'ungrouped') return null;
  return String(value);
};

const HostTableRow = ({
  host,
  expanded,
  onToggle,
  canManage,
  canDelete,
  onEdit,
  onDelete,
  getStatusColor,
  extraAfterLastSeen,
  dragEnabled,
  isDragging,
  onHostDragStart,
  onHostDragEnd,
}) => {
  const services = hostServices(host);
  const colSpan = 8 + (extraAfterLastSeen ? 1 : 0) + (canManage ? 1 : 0);
  const skipClickRef = React.useRef(false);

  const handleRowClick = (event) => {
    if (skipClickRef.current) {
      skipClickRef.current = false;
      return;
    }
    if (event.target.closest('a, button, select, input, label')) return;
    onToggle(host.id);
  };

  const handleDragStart = (event) => {
    if (!dragEnabled) return;
    if (event.target.closest('a, button, select, input, label')) {
      event.preventDefault();
      return;
    }
    skipClickRef.current = true;
    event.dataTransfer.setData('text/plain', String(host.id));
    event.dataTransfer.effectAllowed = 'move';
    onHostDragStart?.(host.id);
  };

  return (
    <>
      <tr
        className={`host-row ${expanded ? 'is-expanded' : ''} ${dragEnabled ? 'is-draggable' : ''} ${isDragging ? 'is-dragging' : ''}`}
        draggable={Boolean(dragEnabled)}
        onDragStart={handleDragStart}
        onDragEnd={() => onHostDragEnd?.()}
        onClick={handleRowClick}
      >
        <td className="expand-cell">
          <button
            type="button"
            className={`row-expand-btn ${expanded ? 'expanded' : ''}`}
            onClick={(e) => {
              e.stopPropagation();
              onToggle(host.id);
            }}
            aria-expanded={expanded}
            title={expanded ? 'Hide host details' : 'Show latency, ports, and other metrics'}
          >
            <ChevronIcon expanded={expanded} />
          </button>
          <span
            className="status-dot-large"
            style={{ backgroundColor: getStatusColor(host.status) }}
            title={host.status.toUpperCase()}
          />
        </td>
        <HostIpCell host={host} />
        <HostIdentityCell host={host} />
        <HostMacCell host={host} />
        <HostDeviceCell host={host} />
        <HostVendorCell host={host} />
        <td className="last-seen-cell">
          {host.last_seen ? formatLastSeen(host.last_seen) : (host.last_check ? formatLastSeen(host.last_check) : '—')}
        </td>
        {extraAfterLastSeen}
        <td className="ports-cell">{services.length}</td>
        {canManage && (
          <td className="actions-cell">
            <button
              type="button"
              className="btn-icon"
              onClick={(e) => {
                e.stopPropagation();
                onEdit(host);
              }}
              title="Edit host"
            >
              <EditIcon />
            </button>
            {canDelete && (
              <button
                type="button"
                className="btn-icon btn-icon-danger"
                onClick={(e) => onDelete(host.id, host.hostname, e)}
                title="Delete host"
              >
                <CloseIcon />
              </button>
            )}
          </td>
        )}
      </tr>
      {expanded && <HostDetailsRow host={host} colSpan={colSpan} />}
    </>
  );
};

const HostCard = ({
  host,
  canManage,
  canDelete,
  onEdit,
  onDelete,
  getStatusColor,
  dragEnabled,
  isDragging,
  onHostDragStart,
  onHostDragEnd,
}) => {
  const [expanded, setExpanded] = React.useState(false);
  const latency = hostLatency(host);
  const services = hostServices(host);
  const name = hostDisplayName(host);
  const displayName = name || host.ip_address;
  const showIp = Boolean(name && host.ip_address);

  const handleDragStart = (event) => {
    if (!dragEnabled) return;
    if (event.target.closest('a, button')) {
      event.preventDefault();
      return;
    }
    event.dataTransfer.setData('text/plain', String(host.id));
    event.dataTransfer.effectAllowed = 'move';
    onHostDragStart?.(host.id);
  };

  return (
    <div
      className={`host-card-wrapper ${dragEnabled ? 'is-draggable' : ''} ${isDragging ? 'is-dragging' : ''} ${expanded ? 'is-expanded' : ''}`}
      draggable={Boolean(dragEnabled)}
      onDragStart={handleDragStart}
      onDragEnd={() => onHostDragEnd?.()}
    >
      <div className="host-card">
        <div className="host-card-header">
          <button
            type="button"
            className={`row-expand-btn ${expanded ? 'expanded' : ''}`}
            onClick={() => setExpanded((open) => !open)}
            aria-expanded={expanded}
            title={expanded ? 'Hide host details' : 'Show MAC, latency, ports, and other metrics'}
          >
            <ChevronIcon expanded={expanded} />
          </button>
          <Link to={`/host/${host.id}`} className="host-card-title" title={displayName}>
            <h3>{displayName}</h3>
            {showIp && <span className="host-subtitle">{host.ip_address}</span>}
          </Link>
          <span
            className="status-badge"
            style={{ backgroundColor: getStatusColor(host.status) }}
          >
            {host.status.toUpperCase()}
          </span>
        </div>
        {expanded && (
          <div className="host-card-body">
            {host.ip_address && (
              <div className="host-info">
                <span className="info-label">IP Address:</span>
                <span className="info-value">{host.ip_address}</span>
              </div>
            )}
            {host.mac_address && (
              <div className="host-info">
                <span className="info-label">MAC:</span>
                <span className="info-value">{host.mac_address}</span>
              </div>
            )}
            {latency != null && (
              <div className="host-info">
                <span className="info-label">Latency:</span>
                <span className="info-value">{latency.toFixed(1)} ms</span>
              </div>
            )}
            {vendorLabel(host) && (
              <div className="host-info">
                <span className="info-label">Vendor:</span>
                <span className="info-value">{vendorLabel(host)}</span>
              </div>
            )}
            {services.length > 0 && (
              <div className="host-info host-card-services">
                <span className="info-label">Ports:</span>
                <span className="info-value">
                  {services.map((service) => service.port).filter(Boolean).join(', ')}
                </span>
              </div>
            )}
            {assumedOs(host) && (
              <div className="host-info">
                <span className="info-label">OS:</span>
                <span className="info-value">{assumedOs(host)}</span>
              </div>
            )}
            {host.apple_model && (
              <div className="host-info">
                <span className="info-label">Model:</span>
                <span className="info-value">{host.apple_model}</span>
              </div>
            )}
            {(host.last_seen || host.last_check) && (
              <div className="host-info">
                <span className="info-label">Last seen:</span>
                <span className="info-value">
                  {formatLastSeen(host.last_seen || host.last_check)}
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
        )}
      </div>
      {canManage && (
        <div className="host-actions">
          <button
            className="host-edit-btn"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onEdit(host);
            }}
            title="Edit host"
          >
            <EditIcon />
          </button>
          {canDelete && (
            <button
              className="host-delete-btn"
              onClick={(e) => onDelete(host.id, host.hostname, e)}
              title="Delete host"
            >
              <CloseIcon />
            </button>
          )}
        </div>
      )}
    </div>
  );
};

const SortableTh = ({ column, label, sortKey, sortDir, onSort }) => {
  const active = sortKey === column;
  return (
    <th
      className={`sortable-th ${active ? 'sorted' : ''}`}
      aria-sort={active ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
    >
      <button
        type="button"
        className="sort-header-btn"
        onClick={() => onSort(column)}
      >
        {label}
        <span className="sort-indicator" aria-hidden="true">
          {active ? (sortDir === 'asc' ? '▲' : '▼') : '↕'}
        </span>
      </button>
    </th>
  );
};

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
    color: DEFAULT_GROUP_COLOR
  });
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [viewMode, setViewMode] = useState('grouped'); // 'grouped' or 'all'
  const [showAgentInstall, setShowAgentInstall] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');
  const [lanWatch, setLanWatch] = useState({ auto_add_hosts: false });
  const [watchSaving, setWatchSaving] = useState(false);
  const [sortKey, setSortKey] = useState('ip');
  const [sortDir, setSortDir] = useState('asc');
  const [expandedHosts, setExpandedHosts] = useState(() => new Set());
  const [dragHostId, setDragHostId] = useState(null);
  const [dropTarget, setDropTarget] = useState(null);

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
      await Promise.all([loadHosts(), loadHostGroups(), loadLanWatch()]);
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

  const loadLanWatch = async () => {
    try {
      const response = await getLanWatch();
      setLanWatch(response.data || { auto_add_hosts: false });
    } catch (err) {
      console.error('Load LAN watch error:', err);
    }
  };

  const handleToggleLanWatch = async () => {
    if (!(user?.is_admin || user?.role === 'admin')) return;
    setWatchSaving(true);
    try {
      const response = await updateLanWatch({
        auto_add_hosts: !lanWatch.auto_add_hosts,
        network: lanWatch.network || '192.168.0.0/24',
      });
      setLanWatch(response.data || { auto_add_hosts: !lanWatch.auto_add_hosts });
      await loadHosts();
      setError(null);
    } catch (err) {
      setError('Failed to update LAN watch: ' + (err.response?.data?.error || err.message));
    } finally {
      setWatchSaving(false);
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
  const handleSort = (column) => {
    if (sortKey === column) {
      setSortDir((dir) => (dir === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortKey(column);
    setSortDir(column === 'last_seen' || column === 'services' ? 'desc' : 'asc');
  };

  const getGroupHosts = (groupId) => sortHosts(
    hosts.filter((h) => normalizeGroupId(h.group) === normalizeGroupId(groupId) && hostMatchesSearch(h, searchFilter)),
    sortKey,
    sortDir,
  );

  const getUngroupedHosts = () => sortHosts(
    hosts.filter((h) => normalizeGroupId(h.group) == null && hostMatchesSearch(h, searchFilter)),
    sortKey,
    sortDir,
  );

  const handleAddHost = async (e) => {
    e.preventDefault();
    setFormError('');

    if (!formData.hostname.trim()) {
      setFormError('Hostname / device is required');
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
                setGroupFormData({ name: '', description: '', color: DEFAULT_GROUP_COLOR });
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
      color: group.color || DEFAULT_GROUP_COLOR
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

  const handleClearUngrouped = () => {
    const count = hosts.filter(h => !h.group).length;
    setItemToDelete({
      type: 'ungrouped',
      id: null,
      name: `${count} ungrouped host${count === 1 ? '' : 's'}`,
      count
    });
    setShowDeleteModal(true);
  };

  const executeClearUngrouped = async () => {
    try {
      await clearUngroupedHosts();
      await loadData();
      setShowDeleteModal(false);
      setItemToDelete(null);
      setError(null);
    } catch (err) {
      setError('Failed to clear ungrouped hosts: ' + (err.response?.data?.error || err.message));
      setShowDeleteModal(false);
    }
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

  const handleAssignHostGroup = async (hostId, groupId) => {
    const host = hosts.find((item) => String(item.id) === String(hostId));
    if (!host) return;

    const nextGroupKey = normalizeGroupId(groupId);
    if (normalizeGroupId(host.group) === nextGroupKey) return;

    const nextGroup = nextGroupKey == null
      ? null
      : (hostGroups.find((group) => normalizeGroupId(group.id) === nextGroupKey)?.id ?? nextGroupKey);
    const previousGroup = host.group ?? null;
    setHosts((prev) => prev.map((item) => (
      String(item.id) === String(hostId) ? { ...item, group: nextGroup } : item
    )));
    setError(null);

    try {
      await updateHost(hostId, {
        hostname: host.hostname,
        group: nextGroup,
      });
    } catch (err) {
      setHosts((prev) => prev.map((item) => (
        String(item.id) === String(hostId) ? { ...item, group: previousGroup } : item
      )));
      setError('Failed to assign group: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleHostDragStart = (hostId) => {
    setDragHostId(hostId);
    setDropTarget(null);
  };

  const handleHostDragEnd = () => {
    setDragHostId(null);
    setDropTarget(null);
  };

  const handleGroupDragOver = (event, targetId) => {
    if (!canManage) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    if (dropTarget !== targetId) setDropTarget(targetId);
  };

  const handleGroupDragLeave = (event, targetId) => {
    if (event.currentTarget.contains(event.relatedTarget)) return;
    if (dropTarget === targetId) setDropTarget(null);
  };

  const handleGroupDrop = (event, targetId) => {
    event.preventDefault();
    const hostId = event.dataTransfer.getData('text/plain') || dragHostId;
    setDragHostId(null);
    setDropTarget(null);
    if (hostId) handleAssignHostGroup(hostId, targetId);
  };

  const canManage = Boolean(user?.is_admin || user?.role === 'admin' || user?.role === 'operator');
  const canDelete = Boolean(user?.is_admin || user?.role === 'admin');

  const toggleExpanded = (hostId) => {
    setExpandedHosts((prev) => {
      const next = new Set(prev);
      if (next.has(hostId)) next.delete(hostId);
      else next.add(hostId);
      return next;
    });
  };

  const hostRowProps = {
    onToggle: toggleExpanded,
    canManage,
    canDelete,
    onEdit: handleEditHost,
    onDelete: handleDeleteHost,
    getStatusColor,
    dragEnabled: canManage,
    onHostDragStart: handleHostDragStart,
    onHostDragEnd: handleHostDragEnd,
  };

  if (loading) {
    return <div className="loading">Loading hosts...</div>;
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="dashboard-heading">
          <h2>Hosts Overview</h2>
          <div className="status-summary">
            <div className="status-item status-item-up">
              <span className="status-dot"></span>
              <span>{statusCounts.up} up</span>
            </div>
            <div className="status-item status-item-down">
              <span className="status-dot"></span>
              <span>{statusCounts.down} down</span>
            </div>
            <div className="status-item status-item-unknown">
              <span className="status-dot"></span>
              <span>{statusCounts.unknown} unknown</span>
            </div>
          </div>
        </div>
        <div className="host-control-bar">
          <label className="toolbar-search">
            <SearchIcon />
            <input
              type="search"
              className="inventory-search"
              placeholder="Filter by name, IP, vendor, type…"
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
            />
          </label>
          <label
            className={`lan-watch-toggle ${lanWatch.auto_add_hosts ? 'active' : ''}`}
            title={lanWatch.auto_add_hosts ? 'Auto-adding newly seen LAN devices' : 'Discovery only — new devices are not auto-added'}
          >
            <input
              type="checkbox"
              checked={Boolean(lanWatch.auto_add_hosts)}
              onChange={handleToggleLanWatch}
              disabled={watchSaving || !canDelete}
            />
            <span className="lan-watch-copy">Watch LAN</span>
          </label>
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
          <div className="toolbar-actions">
            <button
              className="btn-refresh"
              onClick={loadData}
              title="Refresh hosts"
              disabled={loading}
            >
              <RefreshIcon /> Refresh
            </button>
            {canManage && (
              <>
                {canDelete && (
                  <button className="btn-add-group" onClick={() => {
                    setEditingGroup(null);
                    setGroupFormData({ name: '', description: '', color: DEFAULT_GROUP_COLOR });
                    setShowGroupModal(true);
                  }}>
                    <PlusIcon /> Group
                  </button>
                )}
                <button className="btn-add-host" onClick={() => setShowAddModal(true)}>
                  <PlusIcon /> Host
                </button>
                <button className="btn-install-agent" onClick={() => setShowAgentInstall(true)}>
                  <AgentIcon /> Agent
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {viewMode === 'grouped' ? (
        <div className={`hosts-by-groups ${dragHostId != null ? 'is-host-dragging' : ''}`}>
          {hostGroups.map(group => {
            const groupHosts = getGroupHosts(group.id);
            if (searchFilter && groupHosts.length === 0 && dragHostId == null) return null;
            const groupStatus = groupHosts.reduce((acc, h) => {
              acc[h.status] = (acc[h.status] || 0) + 1;
              return acc;
            }, { up: 0, down: 0, unknown: 0 });
            const groupDropId = String(group.id);

            return (
              <div
                key={group.id}
                className={`host-group-section ${dropTarget === groupDropId ? 'is-drop-target' : ''}`}
                style={{
                  borderTopColor: group.color,
                }}
                onDragOver={(event) => handleGroupDragOver(event, groupDropId)}
                onDragLeave={(event) => handleGroupDragLeave(event, groupDropId)}
                onDrop={(event) => handleGroupDrop(event, groupDropId)}
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
                          <SortableTh column="ip" label="IP" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                          <SortableTh column="device" label="Device" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                          <SortableTh column="mac" label="MAC" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                          <SortableTh column="type" label="Type" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                          <SortableTh column="vendor" label="Vendor" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                          <SortableTh column="last_seen" label="Last seen" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                          <SortableTh column="services" label="Ports" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                          {canManage && <th>Actions</th>}
                        </tr>
                      </thead>
                      <tbody>
                        {groupHosts.map(host => (
                          <HostTableRow
                            key={host.id}
                            host={host}
                            expanded={expandedHosts.has(host.id)}
                            isDragging={String(dragHostId) === String(host.id)}
                            {...hostRowProps}
                          />
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="empty-group-message">
                    {canManage ? 'Drop a host here to add it to this group.' : 'No hosts in this group'}
                  </div>
                )}
              </div>
            );
          })}

          {(getUngroupedHosts().length > 0 || dragHostId != null) && (
            <div
              className={`host-group-section ungrouped-section ${dropTarget === 'ungrouped' ? 'is-drop-target' : ''}`}
              onDragOver={(event) => handleGroupDragOver(event, 'ungrouped')}
              onDragLeave={(event) => handleGroupDragLeave(event, 'ungrouped')}
              onDrop={(event) => handleGroupDrop(event, 'ungrouped')}
            >
              <div className="group-header">
                <div className="group-title">
                  <h3>Ungrouped Hosts</h3>
                  <span className="group-host-count">{getUngroupedHosts().length} host{getUngroupedHosts().length !== 1 ? 's' : ''}</span>
                </div>
                {(user?.is_admin || user?.role === 'admin') && (
                  <div className="group-actions">
                    <button
                      className="btn-small btn-danger"
                      onClick={handleClearUngrouped}
                      title="Remove every host that is not in a group"
                    >
                      Clear ungrouped
                    </button>
                  </div>
                )}
              </div>
              {getUngroupedHosts().length === 0 ? (
                <div className="empty-group-message">Drop a host here to remove it from its group.</div>
              ) : (
              <div className="table-responsive">
                <table className="host-group-table compact">
                  <thead>
                    <tr>
                      <th style={{ width: '30px' }}></th>
                      <SortableTh column="ip" label="IP" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                      <SortableTh column="device" label="Device" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                      <SortableTh column="mac" label="MAC" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                      <SortableTh column="type" label="Type" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                      <SortableTh column="vendor" label="Vendor" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                      <SortableTh column="last_seen" label="Last seen" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                      <th>Group</th>
                      <SortableTh column="services" label="Ports" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                      {canManage && <th>Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {getUngroupedHosts().map(host => (
                      <HostTableRow
                        key={host.id}
                        host={host}
                        expanded={expandedHosts.has(host.id)}
                        isDragging={String(dragHostId) === String(host.id)}
                        extraAfterLastSeen={
                          <td className="quick-group-cell">
                            <select
                              className="quick-group-select"
                              onChange={(e) => handleAssignHostGroup(host.id, e.target.value)}
                              defaultValue=""
                              onClick={(e) => e.stopPropagation()}
                            >
                              <option value="" disabled>Assign…</option>
                              {hostGroups.map(g => (
                                <option key={g.id} value={g.id}>{g.name}</option>
                              ))}
                            </select>
                          </td>
                        }
                        {...hostRowProps}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
              )}
            </div>
          )}

          {hostGroups.length === 0 && getUngroupedHosts().length === 0 && hosts.length === 0 && (
            <div className="empty-state">
              <p>No hosts registered yet.</p>
              <p className="empty-state-hint">
                {searchFilter
                  ? 'Nothing matches that filter.'
                  : 'Scan in Discovery and import devices, or add a host to start watching.'}
              </p>
            </div>
          )}
        </div>
      ) : (
        <div className={`hosts-by-groups card-groups ${dragHostId != null ? 'is-host-dragging' : ''}`}>
          {hosts.length === 0 ? (
            <div className="empty-state">
              <p>No hosts registered yet.</p>
              <p className="empty-state-hint">Start an agent to begin monitoring.</p>
            </div>
          ) : (
            <>
              {hostGroups.map((group) => {
                const groupHosts = getGroupHosts(group.id);
                if (searchFilter && groupHosts.length === 0 && dragHostId == null) return null;
                const groupStatus = groupHosts.reduce((acc, h) => {
                  acc[h.status] = (acc[h.status] || 0) + 1;
                  return acc;
                }, { up: 0, down: 0, unknown: 0 });
                const groupDropId = String(group.id);

                return (
                  <div
                    key={group.id}
                    className={`host-group-section ${dropTarget === groupDropId ? 'is-drop-target' : ''}`}
                    style={{ borderTopColor: group.color }}
                    onDragOver={(event) => handleGroupDragOver(event, groupDropId)}
                    onDragLeave={(event) => handleGroupDragLeave(event, groupDropId)}
                    onDrop={(event) => handleGroupDrop(event, groupDropId)}
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
                      {canManage && (
                        <div className="group-actions">
                          <button className="btn-small" onClick={() => handleEditGroup(group)} title="Edit group">
                            Edit
                          </button>
                          {canDelete && (
                            <button className="btn-small btn-danger" onClick={() => handleDeleteGroup(group.id)} title="Delete group">
                              Delete
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                    {groupHosts.length > 0 ? (
                      <div className="hosts-grid">
                        {groupHosts.map((host) => (
                          <HostCard
                            key={host.id}
                            host={host}
                            isDragging={String(dragHostId) === String(host.id)}
                            {...hostRowProps}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="empty-group-message">
                        {canManage ? 'Drop a host here to add it to this group.' : 'No hosts in this group'}
                      </div>
                    )}
                  </div>
                );
              })}

              {(getUngroupedHosts().length > 0 || dragHostId != null) && (
                <div
                  className={`host-group-section ungrouped-section ${dropTarget === 'ungrouped' ? 'is-drop-target' : ''}`}
                  onDragOver={(event) => handleGroupDragOver(event, 'ungrouped')}
                  onDragLeave={(event) => handleGroupDragLeave(event, 'ungrouped')}
                  onDrop={(event) => handleGroupDrop(event, 'ungrouped')}
                >
                  <div className="group-header">
                    <div className="group-title">
                      <h3>Ungrouped Hosts</h3>
                      <span className="group-host-count">
                        {getUngroupedHosts().length} host{getUngroupedHosts().length !== 1 ? 's' : ''}
                      </span>
                    </div>
                    {canDelete && getUngroupedHosts().length > 0 && (
                      <div className="group-actions">
                        <button
                          className="btn-small btn-danger"
                          onClick={handleClearUngrouped}
                          title="Remove every host that is not in a group"
                        >
                          Clear ungrouped
                        </button>
                      </div>
                    )}
                  </div>
                  {getUngroupedHosts().length === 0 ? (
                    <div className="empty-group-message">Drop a host here to remove it from its group.</div>
                  ) : (
                    <div className="hosts-grid">
                      {getUngroupedHosts().map((host) => (
                        <HostCard
                          key={host.id}
                          host={host}
                          isDragging={String(dragHostId) === String(host.id)}
                          {...hostRowProps}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
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
            <label htmlFor="hostname">Hostname / Device *</label>
            <input
              type="text"
              id="hostname"
              value={formData.hostname}
              onChange={(e) => setFormData({ ...formData, hostname: e.target.value })}
              placeholder="e.g., Den TV or nas-01"
              required
              autoFocus
            />
            <small>Friendly device name or hostname — either works</small>
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
          setGroupFormData({ name: '', description: '', color: DEFAULT_GROUP_COLOR });
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
                setGroupFormData({ name: '', description: '', color: DEFAULT_GROUP_COLOR });
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
                placeholder={DEFAULT_GROUP_COLOR}
                style={{ flex: 1, marginLeft: '0.5rem' }}
              />
            </div>
            <small>Color used to identify this group in the dashboard</small>
          </div>
        </form>
      </Modal>

      {showAgentInstall && (
        <AgentInstall
          serverUrl={import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000/api`}
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
        title={
          itemToDelete?.type === 'group'
            ? 'Delete Host Group'
            : itemToDelete?.type === 'ungrouped'
              ? 'Clear ungrouped hosts'
              : 'Delete Host'
        }
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
                } else if (itemToDelete?.type === 'ungrouped') {
                  executeClearUngrouped();
                } else {
                  executeDeleteHost();
                }
              }}
            >
              {itemToDelete?.type === 'ungrouped' ? 'Clear all' : 'Delete'}
            </button>
          </>
        }
      >
        <div className="confirmation-content">
          <p>
            Are you sure you want to {itemToDelete?.type === 'ungrouped' ? 'clear' : 'delete'}{' '}
            <strong>{itemToDelete?.name}</strong>?
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
          {itemToDelete?.type === 'ungrouped' && (
            <p className="warning-text">
              This removes every host that is not in a group, including their checks and history. Grouped hosts are left alone.
            </p>
          )}
        </div>
      </Modal>
    </div>
  );
};

export default Dashboard;

