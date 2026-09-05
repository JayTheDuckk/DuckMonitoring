import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Dashboard from './components/dashboards/Dashboard';
import HostDetail from './components/hosts/HostDetail';
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import Setup from './components/auth/Setup';
import UserManagement from './components/settings/UserManagement';
import UPSDashboard from './components/devices/UPSDashboard';
import UPSDetail from './components/devices/UPSDetail';
import SNMPDashboard from './components/devices/SNMPDashboard';
import SNMPDetail from './components/devices/SNMPDetail';
import AuditLogs from './components/settings/AuditLogs';
import SecuritySettings from './components/settings/SecuritySettings';
import AlertsDashboard from './components/dashboards/AlertsDashboard';
import ChannelForm from './components/dashboards/ChannelForm';
import RuleForm from './components/dashboards/RuleForm';
import CustomDashboard from './components/dashboards/CustomDashboard';
import HostDiscovery from './components/hosts/HostDiscovery';
import ProtectedRoute from './components/auth/ProtectedRoute';
import TopologyGraph from './components/NetworkMap/TopologyGraph';

import './App.css';

const Navbar = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const [menuOpen, setMenuOpen] = React.useState(false);

  // Theme state
  const [theme, setTheme] = React.useState(() => {
    return localStorage.getItem('theme') || 'light';
  });

  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const handleLogout = async () => {
    setMenuOpen(false);
    await logout();
  };

  const closeMenu = () => setMenuOpen(false);

  if (!isAuthenticated) {
    return null;
  }

  const isAdmin = user?.is_admin || user?.role === 'admin';

  return (
    <nav className="navbar">
      <div className="nav-container">
        <Link to="/" className="nav-logo">
          <h1 className="nav-logo-text">Duck Monitoring</h1>
        </Link>

        {/* Main Navigation - Essential Items */}
        <div className="nav-menu">
          <Link to="/" className="nav-link">Dashboard</Link>
          <Link to="/ups" className="nav-link">UPS</Link>
          <Link to="/snmp" className="nav-link">SNMP</Link>
          <Link to="/topology" className="nav-link">Topology</Link>
          <Link to="/alerts" className="nav-link">Alerts</Link>
        </div>

        <div className="nav-user">
          <span className="nav-username">{user?.username}</span>

          <button
            className="theme-switch"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          />

          {isAdmin && <span className="nav-badge">Admin</span>}
          <button onClick={handleLogout} className="nav-logout">Logout</button>
        </div>

        {/* Hamburger Menu */}
        <div className="nav-hamburger-container">
          <button
            className={`nav-hamburger ${menuOpen ? 'open' : ''}`}
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Menu"
          >
            <span></span>
            <span></span>
            <span></span>
          </button>

          {menuOpen && (
            <>
              <div className="nav-dropdown-overlay" onClick={closeMenu}></div>
              <div className="nav-dropdown">
                <div className="nav-dropdown-header">
                  <span className="nav-dropdown-user">{user?.username}</span>
                  {isAdmin && <span className="nav-badge">Admin</span>}
                </div>

                <div className="nav-dropdown-section">
                  <button
                    className="nav-dropdown-link"
                    onClick={() => { toggleTheme(); }}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.75rem'
                    }}
                  >
                    {theme === 'light' ? '🌙 Dark Mode' : '☀️ Light Mode'}
                  </button>
                  <Link to="/dashboards" className="nav-dropdown-link" onClick={closeMenu}>
                    📊 My Dashboards
                  </Link>
                  <Link to="/security" className="nav-dropdown-link" onClick={closeMenu}>
                    🔐 Security Settings
                  </Link>
                </div>

                {isAdmin && (
                  <div className="nav-dropdown-section">
                    <div className="nav-dropdown-label">Administration</div>
                    <Link to="/discovery" className="nav-dropdown-link" onClick={closeMenu}>
                      🔍 Network Discovery
                    </Link>
                    <Link to="/users" className="nav-dropdown-link" onClick={closeMenu}>
                      👥 User Management
                    </Link>
                    <Link to="/audit-logs" className="nav-dropdown-link" onClick={closeMenu}>
                      📋 Audit Logs
                    </Link>
                  </div>
                )}

                <div className="nav-dropdown-section">
                  <button onClick={handleLogout} className="nav-dropdown-logout">
                    Logout
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </nav>
  );
};

import { ToastProvider } from './contexts/ToastContext';

const AppContent = () => {
  const { loading, isSetup } = useAuth();

  if (loading) {
    return <div className="loading-screen">Loading...</div>;
  }

  return (
    <div className="app-container">
      <Navbar />
      <main className="main-content">
        <Routes>
          {/* Public Routes */}
          <Route
            path="/login"
            element={!isSetup ? <Navigate to="/setup" replace /> : <Login />}
          />
          <Route path="/register" element={<Register />} />
          <Route
            path="/setup"
            element={isSetup ? <Navigate to="/login" replace /> : <Setup />}
          />

          {/* Protected Routes */}
          <Route
            path="/"
            element={
              !isSetup ? <Navigate to="/setup" replace /> :
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
            }
          />
          <Route
            path="/host/:hostId"
            element={
              !isSetup ? <Navigate to="/setup" replace /> :
                <ProtectedRoute>
                  <HostDetail />
                </ProtectedRoute>
            }
          />
          <Route
            path="/users"
            element={
              !isSetup ? <Navigate to="/setup" replace /> :
                <ProtectedRoute>
                  <UserManagement />
                </ProtectedRoute>
            }
          />
          <Route
            path="/ups"
            element={
              !isSetup ? <Navigate to="/setup" replace /> :
                <ProtectedRoute>
                  <UPSDashboard />
                </ProtectedRoute>
            }
          />
          <Route
            path="/ups/:deviceId"
            element={
              !isSetup ? <Navigate to="/setup" replace /> :
                <ProtectedRoute>
                  <UPSDetail />
                </ProtectedRoute>
            }
          />
          <Route
            path="/snmp"
            element={
              !isSetup ? <Navigate to="/setup" replace /> :
                <ProtectedRoute>
                  <SNMPDashboard />
                </ProtectedRoute>
            }
          />
          <Route
            path="/snmp/:deviceId"
            element={
              !isSetup ? <Navigate to="/setup" replace /> :
                <ProtectedRoute>
                  <SNMPDetail />
                </ProtectedRoute>
            }
          />
          <Route
            path="/audit-logs"
            element={
              !isSetup ? <Navigate to="/setup" replace /> :
                <ProtectedRoute>
                  <AuditLogs />
                </ProtectedRoute>
            }
          />
          <Route
            path="/discovery"
            element={
              !isSetup ? <Navigate to="/setup" replace /> :
                <ProtectedRoute>
                  <HostDiscovery />
                </ProtectedRoute>
            }
          />
          <Route
            path="/security"
            element={
              !isSetup ? <Navigate to="/setup" replace /> :
                <ProtectedRoute>
                  <SecuritySettings />
                </ProtectedRoute>
            }
          />
          <Route
            path="/alerts"
            element={
              !isSetup ? <Navigate to="/setup" replace /> :
                <ProtectedRoute>
                  <AlertsDashboard />
                </ProtectedRoute>
            }
          />
          <Route
            path="/alerts/channels/new"
            element={
              !isSetup ? <Navigate to="/setup" replace /> :
                <ProtectedRoute>
                  <ChannelForm />
                </ProtectedRoute>
            }
          />
          <Route
            path="/alerts/channels/:channelId"
            element={
              !isSetup ? <Navigate to="/setup" replace /> :
                <ProtectedRoute>
                  <ChannelForm />
                </ProtectedRoute>
            }
          />
          <Route
            path="/alerts/rules/new"
            element={
              !isSetup ? <Navigate to="/setup" replace /> :
                <ProtectedRoute>
                  <RuleForm />
                </ProtectedRoute>
            }
          />
          <Route
            path="/alerts/rules/:ruleId"
            element={
              !isSetup ? <Navigate to="/setup" replace /> :
                <ProtectedRoute>
                  <RuleForm />
                </ProtectedRoute>
            }
          />
          <Route
            path="/dashboards"
            element={
              !isSetup ? <Navigate to="/setup" replace /> :
                <ProtectedRoute>
                  <CustomDashboard />
                </ProtectedRoute>
            }
          />
          <Route
            path="/dashboards/:dashboardId"
            element={
              !isSetup ? <Navigate to="/setup" replace /> :
                <ProtectedRoute>
                  <CustomDashboard />
                </ProtectedRoute>
            }
          />
          <Route
            path="/topology"
            element={
              !isSetup ? <Navigate to="/setup" replace /> :
                <ProtectedRoute>
                  <TopologyGraph />
                </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
};

function App() {
  return (
    <Router>
      <AuthProvider>
        <ToastProvider>
          <AppContent />
        </ToastProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;


