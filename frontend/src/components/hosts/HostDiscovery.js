import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import api from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../contexts/ToastContext';
import './HostDiscovery.css';

const SERVICE_CATEGORIES = {
    http: 'web', https: 'secure', ssh: 'remote', ftp: 'remote',
    mysql: 'database', postgresql: 'database', redis: 'database',
    mongodb: 'database', smtp: 'mail', imap: 'mail', pop3: 'mail',
    dns: 'other', snmp: 'other', telnet: 'remote', rdp: 'remote',
};

const getServiceCategory = (name) => SERVICE_CATEGORIES[name?.toLowerCase()] || 'other';

const getVendorDisplay = (host) => {
    if ((host.vendor_source === 'mdns_guess' || host.vendor_source === 'ssdp_guess') && host.vendor) {
        return {
            label: host.vendor,
            hint: host.device_hint || 'Vendor inferred from network advertisement',
            badgeClass: 'mac-type-mdns-guess',
        };
    }
    if (!host.mac_address) {
        return { label: host.vendor || '—', hint: host.device_hint || '', badgeClass: host.vendor ? 'mac-type-mdns-guess' : '' };
    }
    if (host.mac_type === 'private') {
        return {
            label: 'Private MAC',
            hint: host.device_hint || 'Randomized privacy address — no manufacturer OUI',
            badgeClass: 'mac-type-private',
        };
    }
    if (host.mac_type === 'unknown') {
        return {
            label: host.vendor || 'Unknown',
            hint: host.device_hint || 'Not found in IEEE OUI database',
            badgeClass: 'mac-type-unknown',
        };
    }
    return {
        label: host.vendor || '—',
        hint: host.device_hint || '',
        badgeClass: 'mac-type-manufacturer',
    };
};

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
    return date.toLocaleString();
};

const RadarIcon = () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <circle cx="12" cy="12" r="6" />
        <circle cx="12" cy="12" r="2" />
        <line x1="12" y1="2" x2="12" y2="6" />
    </svg>
);

const ChevronDown = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="6 9 12 15 18 9" />
    </svg>
);

const CheckCircle = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
        <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
);

const AlertCircle = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
);

const SearchIcon = () => (
    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
);

const HostDiscovery = () => {
    const { user } = useAuth();
    const { showSuccess, showError } = useToast();
    const [network, setNetwork] = useState('');
    const [scanType, setScanType] = useState('quick');
    const [scanning, setScanning] = useState(false);
    const [results, setResults] = useState(null);
    const [error, setError] = useState(null);
    const [selectedHosts, setSelectedHosts] = useState(new Set());
    const [selectedServices, setSelectedServices] = useState({});
    const [importing, setImporting] = useState(false);
    const [importResults, setImportResults] = useState(null);
    const [expandedHosts, setExpandedHosts] = useState(new Set());
    const [searchFilter, setSearchFilter] = useState('');
    const [scanElapsed, setScanElapsed] = useState(0);
    const [changes, setChanges] = useState(null);
    const timerRef = useRef(null);

    const loadChanges = (networkFilter) => {
        const params = new URLSearchParams({ days: '7' });
        if (networkFilter) params.set('network', networkFilter);
        return api.get(`/inventory/discovery/changes/?${params.toString()}`)
            .then((response) => setChanges(response.data))
            .catch(() => {});
    };

    useEffect(() => {
        let cancelled = false;
        api.get('/inventory/discovery/history/')
            .then((response) => {
                if (!cancelled && response.data?.hosts?.length) {
                    setResults((prev) => prev || response.data);
                }
            })
            .catch(() => {});
        loadChanges();
        return () => { cancelled = true; };
    }, []);

    // Scan timer
    useEffect(() => {
        if (scanning) {
            setScanElapsed(0);
            timerRef.current = setInterval(() => setScanElapsed(prev => prev + 1), 1000);
        } else {
            clearInterval(timerRef.current);
        }
        return () => clearInterval(timerRef.current);
    }, [scanning]);

    const formatTime = (seconds) => {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}:${s.toString().padStart(2, '0')}`;
    };

    const handleScan = async (e) => {
        e.preventDefault();
        setError(null);
        setResults(null);
        setSelectedHosts(new Set());
        setSelectedServices({});
        setImportResults(null);
        setExpandedHosts(new Set());
        setScanning(true);

        try {
            const response = await api.post('/inventory/discovery/scan/', {
                network,
                scan_type: scanType
            });
            setResults(response.data);
            loadChanges(network);

            // Auto-select all discovered hosts
            const allIps = new Set(response.data.hosts.map(h => h.ip_address));
            setSelectedHosts(allIps);

            // Auto-select all services for each host
            const services = {};
            response.data.hosts.forEach(host => {
                if (host.services && host.services.length > 0) {
                    services[host.ip_address] = new Set(host.services.map(s => s.port));
                }
            });
            setSelectedServices(services);

            // Auto-expand hosts that have services
            const hostsWithServices = new Set(
                response.data.hosts.filter(h => h.services?.length > 0).map(h => h.ip_address)
            );
            setExpandedHosts(hostsWithServices);
        } catch (err) {
            setError(err.response?.data?.error || 'Scan failed. Check the network range and try again.');
        } finally {
            setScanning(false);
        }
    };

    const handleImport = async () => {
        if (selectedHosts.size === 0) return;
        setImporting(true);
        setImportResults(null);

        try {
            const hostsToImport = results.hosts
                .filter(h => selectedHosts.has(h.ip_address))
                .map(h => ({
                    ...h,
                    // Include only selected services for this host
                    services: (h.services || []).filter(s =>
                        selectedServices[h.ip_address]?.has(s.port)
                    )
                }));

            const response = await api.post('/inventory/discovery/import_hosts/', {
                hosts: hostsToImport
            });
            setImportResults(response.data);
            showSuccess('Import Complete', `Imported ${response.data.count} hosts successfully.`);
        } catch (err) {
            showError('Import Failed', err.response?.data?.error || 'Could not import hosts.');
        } finally {
            setImporting(false);
        }
    };

    const toggleHostSelection = (ip) => {
        setSelectedHosts(prev => {
            const next = new Set(prev);
            if (next.has(ip)) next.delete(ip); else next.add(ip);
            return next;
        });
    };

    const toggleAllHosts = (checked) => {
        if (checked) {
            setSelectedHosts(new Set(filteredHosts.map(h => h.ip_address)));
        } else {
            setSelectedHosts(new Set());
        }
    };

    const toggleServiceSelection = (hostIp, port) => {
        setSelectedServices(prev => {
            const hostServices = new Set(prev[hostIp] || []);
            if (hostServices.has(port)) hostServices.delete(port); else hostServices.add(port);
            return { ...prev, [hostIp]: hostServices };
        });
    };

    const toggleAllServicesForHost = (hostIp, services, selectAll) => {
        setSelectedServices(prev => ({
            ...prev,
            [hostIp]: selectAll ? new Set(services.map(s => s.port)) : new Set()
        }));
    };

    const toggleHostExpanded = (ip) => {
        setExpandedHosts(prev => {
            const next = new Set(prev);
            if (next.has(ip)) next.delete(ip); else next.add(ip);
            return next;
        });
    };

    // Computed values
    const filteredHosts = results?.hosts?.filter(h => {
        if (!searchFilter) return true;
        const q = searchFilter.toLowerCase();
        return h.ip_address.includes(q) ||
            (h.hostname || '').toLowerCase().includes(q) ||
            (h.mdns_name || '').toLowerCase().includes(q) ||
            (h.ssdp_name || '').toLowerCase().includes(q) ||
            (h.apple_model || '').toLowerCase().includes(q) ||
            (h.mac_address || '').toLowerCase().includes(q) ||
            (h.vendor || '').toLowerCase().includes(q) ||
            (h.os_guess || '').toLowerCase().includes(q) ||
            (h.device_class || '').toLowerCase().includes(q) ||
            (h.suggested_type || '').toLowerCase().includes(q);
    }) || [];

    const totalSelectedServices = Object.values(selectedServices)
        .reduce((acc, set) => acc + set.size, 0);

    const totalDetectedServices = results?.hosts?.reduce(
        (acc, h) => acc + (h.services?.length || 0), 0
    ) || 0;

    return (
        <div className="discovery-container">
            {/* Page Header */}
            <div className="discovery-page-header">
                <div className="header-icon">
                    <RadarIcon />
                </div>
                <div>
                    <h1>Network Discovery</h1>
                    <p>Scan your network to find devices, MAC addresses, open ports, and services</p>
                </div>
            </div>

            {/* Scan Configuration */}
            <div className="scan-config-panel">
                <form onSubmit={handleScan} className="scan-form-row">
                    <div className="scan-form-group">
                        <label htmlFor="network-range">Network Range</label>
                        <input
                            id="network-range"
                            type="text"
                            value={network}
                            onChange={(e) => setNetwork(e.target.value)}
                            placeholder="e.g. 192.168.1.0/24"
                            disabled={scanning}
                            required
                        />
                        <small className="help-text">CIDR notation — supports /24, /16, etc.</small>
                    </div>

                    <div className="scan-form-group">
                        <label htmlFor="scan-type">Scan Type</label>
                        <select
                            id="scan-type"
                            value={scanType}
                            onChange={(e) => setScanType(e.target.value)}
                            disabled={scanning}
                        >
                            <option value="quick">Quick Ping Scan</option>
                            <option value="full">Full Port Scan (Slower)</option>
                        </select>
                    </div>

                    <button type="submit" className="btn-scan" disabled={scanning || !network}>
                        <RadarIcon />
                        {scanning ? 'Scanning…' : 'Start Scan'}
                    </button>
                </form>
            </div>

            {/* Error */}
            {error && (
                <div className="discovery-error">
                    <AlertCircle />
                    {error}
                </div>
            )}

            {/* Scanning State */}
            {scanning && (
                <div className="scanning-state">
                    <div className="radar-container">
                        <div className="radar-circle">
                            <div className="radar-sweep"></div>
                            <div className="radar-center-dot"></div>
                            <div className="radar-ring"></div>
                            <div className="radar-ring"></div>
                        </div>
                    </div>
                    <h3>Scanning Network…</h3>
                    <p>Discovering hosts on <strong>{network}</strong></p>
                    <div className="scan-timer">{formatTime(scanElapsed)}</div>
                </div>
            )}

            {/* Results */}
            {results && !scanning && (
                <div className="results-panel">
                    {changes && (
                        <div className="changes-strip" aria-live="polite">
                            <span>{changes.new?.length || 0} new this week</span>
                            <span className="changes-strip-sep" aria-hidden="true">·</span>
                            <span>{changes.gone?.length || 0} gone</span>
                            <span className="changes-strip-sep" aria-hidden="true">·</span>
                            <span>{changes.unnamed_mobile?.length || 0} unnamed mobiles</span>
                        </div>
                    )}

                    {/* Summary Stats */}
                    <div className="results-summary-bar">
                        <div className="summary-stat highlight">
                            <div className="stat-value">{results.hosts.length}</div>
                            <div className="stat-label">Hosts Found</div>
                        </div>
                        <div className="summary-stat">
                            <div className="stat-value">{results.mdns_devices_found ?? '—'}</div>
                            <div className="stat-label">mDNS Names</div>
                        </div>
                        <div className="summary-stat">
                            <div className="stat-value">{totalDetectedServices}</div>
                            <div className="stat-label">Services Detected</div>
                        </div>
                        <div className="summary-stat">
                            <div className="stat-value">{selectedHosts.size}</div>
                            <div className="stat-label">Selected to Import</div>
                        </div>
                        <div className="summary-stat">
                            <div className="stat-value">{totalSelectedServices}</div>
                            <div className="stat-label">Service Checks</div>
                        </div>
                    </div>

                    {/* Import Results Banner */}
                    {importResults && (
                        <div className="import-results-banner">
                            <CheckCircle />
                            <div className="import-text">
                                <strong>Imported {importResults.count} host{importResults.count !== 1 ? 's' : ''}</strong>
                                {importResults.service_checks_created > 0 && (
                                    <span> — {importResults.service_checks_created} service check{importResults.service_checks_created !== 1 ? 's' : ''} created</span>
                                )}
                            </div>
                            <Link to="/" className="btn-go-inventory">Go to Dashboard →</Link>
                        </div>
                    )}

                    {/* Toolbar */}
                    <div className="results-toolbar">
                        <div className="toolbar-left">
                            <label>
                                <input
                                    type="checkbox"
                                    checked={filteredHosts.length > 0 && filteredHosts.every(h => selectedHosts.has(h.ip_address))}
                                    onChange={(e) => toggleAllHosts(e.target.checked)}
                                />
                                Select All
                            </label>
                            <input
                                type="text"
                                className="results-search"
                                placeholder="Filter by IP, hostname…"
                                value={searchFilter}
                                onChange={(e) => setSearchFilter(e.target.value)}
                            />
                        </div>
                        <div className="toolbar-right">
                            <button
                                className="btn-import"
                                onClick={handleImport}
                                disabled={importing || selectedHosts.size === 0}
                            >
                                {importing ? 'Importing…' : `Import ${selectedHosts.size} Host${selectedHosts.size !== 1 ? 's' : ''}`}
                                {totalSelectedServices > 0 && ` + ${totalSelectedServices} Check${totalSelectedServices !== 1 ? 's' : ''}`}
                            </button>
                        </div>
                    </div>

                    {/* Host Table */}
                    {filteredHosts.length === 0 ? (
                        <div className="no-results-state">
                            <SearchIcon />
                            <h3>No hosts match your filter</h3>
                            <p>Try a different search term</p>
                        </div>
                    ) : (
                        <div className="table-scroll-wrapper">
                            <table className="hosts-table">
                                <thead>
                                    <tr>
                                        <th></th>
                                        <th>Status</th>
                                        <th>IP Address</th>
                                        <th>MAC Address</th>
                                        <th>Vendor</th>
                                        <th>Hostname / mDNS</th>
                                        <th>Latency</th>
                                        <th>Services</th>
                                        <th>OS / Device</th>
                                        <th></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredHosts.map(host => (
                                        <React.Fragment key={host.ip_address}>
                                            <tr
                                                className={`host-table-row ${selectedHosts.has(host.ip_address) ? 'selected' : ''} ${host.seen_this_scan === false ? 'not-in-scan' : ''}`}
                                                onClick={() => host.services?.length > 0 && toggleHostExpanded(host.ip_address)}
                                            >
                                                <td onClick={(e) => e.stopPropagation()}>
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedHosts.has(host.ip_address)}
                                                        onChange={() => toggleHostSelection(host.ip_address)}
                                                    />
                                                </td>
                                                <td>
                                                    <span className="host-status-dot"></span>
                                                    {host.seen_this_scan === false && (
                                                        <span className="not-in-scan-badge">Not in this scan</span>
                                                    )}
                                                </td>
                                                <td className="host-ip-cell">{host.ip_address}</td>
                                                <td className="host-mac-cell">{host.mac_address || '—'}</td>
                                                <td className="host-vendor-cell">
                                                    {(() => {
                                                        const v = getVendorDisplay(host);
                                                        return (
                                                            <span
                                                                className={`vendor-label ${v.badgeClass}`}
                                                                title={v.hint || undefined}
                                                            >
                                                                {v.label}
                                                            </span>
                                                        );
                                                    })()}
                                                </td>
                                                <td className="host-hostname-cell">
                                                    {host.mdns_name ? (
                                                        <>
                                                            <span className="mdns-name" title={host.mdns_hostname || host.hostname}>
                                                                {host.mdns_name}
                                                            </span>
                                                            {host.apple_model && (
                                                                <span className="apple-model-label">{host.apple_model}</span>
                                                            )}
                                                        </>
                                                    ) : (
                                                        host.hostname || '—'
                                                    )}
                                                    {host.last_seen && (
                                                        <span className="last-seen-label">
                                                            Last seen {formatLastSeen(host.last_seen)}
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="host-latency-cell">
                                                    {host.latency != null ? (
                                                        <span className={`latency-badge ${host.latency > 100 ? 'slow' : ''}`}>
                                                            {host.latency.toFixed(1)} ms
                                                        </span>
                                                    ) : '—'}
                                                </td>
                                                <td className="service-count-cell">
                                                    {host.services?.length > 0 ? (
                                                        <span className="service-count-badge">{host.services.length}</span>
                                                    ) : '—'}
                                                </td>
                                                <td>
                                                    {host.device_class === 'privacy_device' ? (
                                                        <div className="privacy-device-cell">
                                                            <span
                                                                className="privacy-device-label"
                                                                title={host.privacy_reason || (host.identification_clues || []).join(' · ') || host.device_hint || undefined}
                                                            >
                                                                Privacy device
                                                            </span>
                                                            {(host.privacy_reason || host.identification_clues?.[0]) && (
                                                                <span className="privacy-device-reason">
                                                                    {host.privacy_reason || host.identification_clues[0]}
                                                                </span>
                                                            )}
                                                        </div>
                                                    ) : (
                                                        <>
                                                            <span
                                                                className={`os-badge confidence-${host.confidence || 'low'}`}
                                                                title={(host.identification_clues || []).join(' · ') || host.device_hint || undefined}
                                                            >
                                                                {host.os_guess && host.os_guess !== 'Unknown'
                                                                    ? host.os_guess
                                                                    : (host.suggested_type || 'unknown')}
                                                            </span>
                                                            {host.device_class && host.device_class !== 'unknown' && (
                                                                <span className="device-class-label">{host.device_class}</span>
                                                            )}
                                                        </>
                                                    )}
                                                </td>
                                                <td>
                                                    {host.services?.length > 0 && (
                                                        <button
                                                            className={`expand-btn ${expandedHosts.has(host.ip_address) ? 'expanded' : ''}`}
                                                            onClick={(e) => { e.stopPropagation(); toggleHostExpanded(host.ip_address); }}
                                                        >
                                                            <ChevronDown />
                                                        </button>
                                                    )}
                                                </td>
                                            </tr>

                                            {/* Expanded services row */}
                                            {expandedHosts.has(host.ip_address) && host.services?.length > 0 && (
                                                <tr className="services-expansion">
                                                    <td colSpan="10">
                                                        <div className="services-expansion-inner">
                                                            <div className="services-expansion-header">
                                                                <h4>Detected Services — select to create service checks</h4>
                                                                <div className="services-toggle-all">
                                                                    <button onClick={() => toggleAllServicesForHost(host.ip_address, host.services, true)}>
                                                                        Select All
                                                                    </button>
                                                                    <button onClick={() => toggleAllServicesForHost(host.ip_address, host.services, false)}>
                                                                        Deselect
                                                                    </button>
                                                                </div>
                                                            </div>
                                                            <div className="services-pills">
                                                                {host.services.map(service => {
                                                                    const category = getServiceCategory(service.service);
                                                                    const isChecked = selectedServices[host.ip_address]?.has(service.port);
                                                                    return (
                                                                        <div
                                                                            key={service.port}
                                                                            className={`service-pill ${isChecked ? 'checked' : ''}`}
                                                                            onClick={() => toggleServiceSelection(host.ip_address, service.port)}
                                                                        >
                                                                            <input
                                                                                type="checkbox"
                                                                                checked={!!isChecked}
                                                                                onChange={() => { }}
                                                                                onClick={(e) => e.stopPropagation()}
                                                                            />
                                                                            <div className="service-pill-info">
                                                                                <span className="service-pill-port">Port {service.port}</span>
                                                                                <span className="service-pill-name">{service.service}</span>
                                                                            </div>
                                                                            <span className={`service-pill-protocol ${category}`}>
                                                                                {category}
                                                                            </span>
                                                                        </div>
                                                                    );
                                                                })}
                                                            </div>
                                                        </div>
                                                    </td>
                                                </tr>
                                            )}
                                        </React.Fragment>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default HostDiscovery;
