import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Add request interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Add response interceptor
// Add response interceptor
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Check if error is 401 and we haven't retried yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          throw new Error('No refresh token available');
        }

        // Call refresh endpoint
        const response = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
          refresh: refreshToken
        });

        const { access } = response.data;

        // Store new token
        localStorage.setItem('access_token', access);

        // Update header for future requests
        api.defaults.headers.common['Authorization'] = `Bearer ${access}`;

        // Update header for this request
        originalRequest.headers['Authorization'] = `Bearer ${access}`;

        // Retry original request
        return api(originalRequest);
      } catch (refreshError) {
        console.error('Token refresh failed:', refreshError);

        // Clear tokens and redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';

        return Promise.reject(refreshError);
      }
    }

    console.error('API Error:', error.response?.status, error.response?.data);
    return Promise.reject(error);
  }
);

// --- Auth Endpoints ---
export const login = (credentials) => api.post('/auth/token/', credentials);
export const register = (userData) => api.post('/auth/register/', userData);
export const getProfile = () => api.get('/auth/me/');

// --- User Management (Admin) ---
export const getUsers = () => api.get('/auth/users/');
export const getUser = (userId) => api.get(`/auth/users/${userId}/`);
export const updateUser = (userId, userData) => api.put(`/auth/users/${userId}/`, userData);
export const deleteUser = (userId) => api.delete(`/auth/users/${userId}/`);

// --- Inventory (Hosts) ---
export const getHosts = () => api.get('/inventory/hosts/');
export const getHost = (hostId) => api.get(`/inventory/hosts/${hostId}/`);
export const createHost = (hostData) => api.post('/inventory/hosts/', hostData);
export const updateHost = (hostId, hostData) => api.patch(`/inventory/hosts/${hostId}/`, hostData);
export const deleteHost = (hostId) => api.delete(`/inventory/hosts/${hostId}/`);
export const clearHostHistory = (hostId) => api.delete(`/inventory/hosts/${hostId}/clear-history/`);
export const scanHostPorts = (hostId) => api.post(`/inventory/hosts/${hostId}/scan_ports/`);


// --- Inventory (Host Groups) ---
export const getHostGroups = () => api.get('/inventory/groups/');
export const getHostGroup = (groupId) => api.get(`/inventory/groups/${groupId}/`);
export const createHostGroup = (groupData) => api.post('/inventory/groups/', groupData);
export const updateHostGroup = (groupId, groupData) => api.put(`/inventory/groups/${groupId}/`, groupData);
export const deleteHostGroup = (groupId) => api.delete(`/inventory/groups/${groupId}/`);

// --- Inventory (UPS) ---
export const getUPSDevices = () => api.get('/inventory/ups/');
export const getUPSDevice = (deviceId) => api.get(`/inventory/ups/${deviceId}/`);
export const createUPSDevice = (deviceData) => api.post('/inventory/ups/', deviceData);
export const updateUPSDevice = (deviceId, deviceData) => api.put(`/inventory/ups/${deviceId}/`, deviceData);
export const deleteUPSDevice = (deviceId) => api.delete(`/inventory/ups/${deviceId}/`);

// New UPS functions
export const getUPSModels = () => api.get('/inventory/ups/models/');
export const runUPSCheck = (deviceId) => api.post(`/inventory/ups/${deviceId}/run/`);

// --- Inventory (SNMP) ---
export const getSNMPDevices = () => api.get('/inventory/snmp/');
export const getSNMPDevice = (deviceId) => api.get(`/inventory/snmp/${deviceId}/`);
export const createSNMPDevice = (deviceData) => api.post('/inventory/snmp/', deviceData);
export const updateSNMPDevice = (deviceId, deviceData) => api.put(`/inventory/snmp/${deviceId}/`, deviceData);
export const deleteSNMPDevice = (deviceId) => api.delete(`/inventory/snmp/${deviceId}/`);

// New SNMP functions
export const getSNMPDeviceModels = () => api.get('/inventory/snmp/models/');
export const runSNMPDeviceCheck = (deviceId) => api.post(`/inventory/snmp/${deviceId}/run/`);

// --- Monitoring (Service Checks) ---
export const getServiceChecks = (hostId) => api.get(`/monitoring/configs/?host=${hostId}`);
export const createServiceCheck = (hostId, checkData) => api.post('/monitoring/configs/', { ...checkData, host: hostId });
export const getServiceCheck = (checkId) => api.get(`/monitoring/configs/${checkId}/`);
export const updateServiceCheck = (checkId, checkData) => api.put(`/monitoring/configs/${checkId}/`, checkData);
export const deleteServiceCheck = (checkId) => api.delete(`/monitoring/configs/${checkId}/`);

// Custom actions
export const runServiceCheck = (checkId) => api.post(`/monitoring/configs/${checkId}/run/`);
export const clearServiceCheckResults = (checkId) => api.delete(`/monitoring/configs/${checkId}/clear-results/`);
export const getServiceCheckHistory = (checkId, params = {}) => {
  const queryParams = new URLSearchParams({ service_check: checkId });
  // Add any additional query parameters
  if (params.hours) {
    // Calculate timestamp for hours ago
    const hoursAgo = new Date(Date.now() - params.hours * 60 * 60 * 1000).toISOString();
    queryParams.append('timestamp__gte', hoursAgo);
  }
  if (params._t) {
    queryParams.append('_t', params._t);
  }
  return api.get(`/monitoring/results/?${queryParams.toString()}`);
};

// Alias for HostDetail.js
export const getHostChecks = getServiceChecks;

// --- Metrics ---
export const getHostMetrics = (hostId) => api.get(`/monitoring/metrics/?host=${hostId}`);
export const getUPSMetrics = (deviceId) => api.get(`/monitoring/ups-metrics/?ups_device=${deviceId}`);
export const getSNMPDeviceMetrics = (deviceId) => api.get(`/monitoring/snmp-metrics/?snmp_device=${deviceId}`);

// Metrics Summary (Aggregation)
export const getMetricsSummary = (hostId, params) => api.get(`/monitoring/metrics/summary/?host=${hostId}`, { params });
export const getUPSMetricsSummary = (deviceId, params) => api.get(`/monitoring/ups-metrics/summary/?ups_device=${deviceId}`, { params });
export const getSNMPDeviceMetricsSummary = (deviceId, params) => api.get(`/monitoring/snmp-metrics/summary/?snmp_device=${deviceId}`, { params });


// --- Alerts ---
export const getAlerts = () => api.get('/alerts/alerts/');
export const getAlertRules = () => api.get('/alerts/rules/');
export const getChannels = () => api.get('/alerts/channels/');
export const createChannel = (data) => api.post('/alerts/channels/', data);

// --- Installer ---
export const getInstallScriptUrl = () => {
  return `${API_BASE_URL.replace('/api', '')}/static/agent/install.sh`;
};

export default api;
