import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { getUsers, updateUser, deleteUser } from '../../services/api';
import './UserManagement.css';

const UserManagement = () => {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({ role: 'viewer', is_admin: false });
  const [showEditModal, setShowEditModal] = useState(false);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const response = await getUsers();
      setUsers(Array.isArray(response.data) ? response.data : response.data.results || []);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (user) => {
    setEditingUser(user);
    setFormData({
      role: user.role || 'viewer',
      is_admin: user.is_admin || false
    });
    setShowEditModal(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      await updateUser(editingUser.id, formData);
      await loadUsers();
      setShowEditModal(false);
      setEditingUser(null);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to update user');
    }
  };

  const handleDelete = async (userId, username) => {
    if (!window.confirm(`Are you sure you want to delete user "${username}"?`)) {
      return;
    }
    try {
      await deleteUser(userId);
      await loadUsers();
      setError(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to delete user');
    }
  };

  const getRoleBadgeColor = (role, isAdmin) => {
    if (isAdmin || role === 'admin') return '#f44336';
    if (role === 'operator') return '#2196f3';
    return '#9e9e9e';
  };

  const getRoleLabel = (role, isAdmin) => {
    if (isAdmin || role === 'admin') return 'Admin';
    if (role === 'operator') return 'Operator';
    return 'Viewer';
  };

  if (loading) {
    return <div className="loading">Loading users...</div>;
  }

  return (
    <div className="user-management">
      <div className="page-header">
        <h1>User Management</h1>
        <p>Manage user permissions and roles</p>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="users-table-container">
        <table className="users-table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th>Created</th>
              <th>Last Login</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>
                  <strong>{user.username}</strong>
                  {user.id === currentUser?.id && (
                    <span className="current-user-badge">(You)</span>
                  )}
                </td>
                <td>{user.email}</td>
                <td>
                  <span
                    className="role-badge"
                    style={{ backgroundColor: getRoleBadgeColor(user.role, user.is_admin) }}
                  >
                    {getRoleLabel(user.role, user.is_admin)}
                  </span>
                </td>
                <td>
                  {user.created_at
                    ? new Date(user.created_at).toLocaleDateString()
                    : 'N/A'}
                </td>
                <td>
                  {user.last_login
                    ? new Date(user.last_login).toLocaleString()
                    : 'Never'}
                </td>
                <td>
                  <div className="action-buttons">
                    <button
                      className="btn-edit"
                      onClick={() => handleEdit(user)}
                      disabled={user.id === currentUser?.id}
                      title={user.id === currentUser?.id ? 'Cannot edit your own permissions' : 'Edit user'}
                    >
                      Edit
                    </button>
                    <button
                      className="btn-delete"
                      onClick={() => handleDelete(user.id, user.username)}
                      disabled={user.id === currentUser?.id}
                      title={user.id === currentUser?.id ? 'Cannot delete your own account' : 'Delete user'}
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showEditModal && editingUser && (
        <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Edit User: {editingUser.username}</h3>
              <button className="modal-close" onClick={() => setShowEditModal(false)}>×</button>
            </div>

            <form onSubmit={handleSave} className="user-edit-form">
              <div className="form-group">
                <label htmlFor="role">Role</label>
                <select
                  id="role"
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value, is_admin: e.target.value === 'admin' })}
                >
                  <option value="viewer">Viewer (Read-only)</option>
                  <option value="operator">Operator (Read & Write)</option>
                  <option value="admin">Admin (Full Access)</option>
                </select>
                <p className="form-hint">
                  <strong>Viewer:</strong> Can view hosts, metrics, and checks<br />
                  <strong>Operator:</strong> Can view and create/edit hosts and checks<br />
                  <strong>Admin:</strong> Full access including user management and deletion
                </p>
              </div>

              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.is_admin}
                    onChange={(e) => {
                      const isAdmin = e.target.checked;
                      setFormData({
                        ...formData,
                        is_admin: isAdmin,
                        role: isAdmin ? 'admin' : formData.role
                      });
                    }}
                  />
                  Grant Admin Privileges
                </label>
                <p className="form-hint">
                  Admin users have full system access including user management.
                </p>
              </div>

              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={() => setShowEditModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-save">
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagement;


