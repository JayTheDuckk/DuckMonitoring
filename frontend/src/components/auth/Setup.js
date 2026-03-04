import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { getSetupStatus } from '../../services/api';
import './Register.css'; // Reuse register styles

const Setup = () => {
    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: '',
        confirmPassword: ''
    });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { register, checkSetup } = useAuth();
    const navigate = useNavigate();

    useEffect(() => {
        // Double check if setup is already done
        const checkStatus = async () => {
            try {
                const response = await getSetupStatus();
                if (response.data.is_setup) {
                    navigate('/login');
                }
            } catch (err) {
                console.error('Failed to check setup status', err);
            }
        };
        checkStatus();
    }, [navigate]);

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (formData.password !== formData.confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        if (formData.password.length < 6) {
            setError('Password must be at least 6 characters');
            return;
        }

        setLoading(true);

        const result = await register(formData.username, formData.email, formData.password);

        if (result.success) {
            // Refresh setup status in context to update routing
            // The checkSetup function itself navigates if setup is true,
            // so calling it here will ensure the global state is updated
            // and potentially trigger a navigation if the context relies on it.
            // If authCheckSetupStatus exists in useAuth, it might be more appropriate here.
            await checkSetup();
            // Setup complete! Redirect to login
            navigate('/login', { state: { message: 'Admin account created! Please login.' } });
        } else {
            setError(result.error);
            setLoading(false);
        }
    };

    return (
        <div className="register-container">
            <div className="register-card">
                <div className="register-header">
                    <h1>Initial Setup</h1>
                    <p>Create your Admin Account</p>
                </div>

                <form onSubmit={handleSubmit} className="register-form">
                    {error && <div className="error-message">{error}</div>}

                    <div className="form-group">
                        <label htmlFor="username">Username</label>
                        <input
                            type="text"
                            id="username"
                            name="username"
                            value={formData.username}
                            onChange={handleChange}
                            required
                            autoFocus
                            placeholder="admin"
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="email">Email</label>
                        <input
                            type="email"
                            id="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            required
                            placeholder="admin@example.com"
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">Password</label>
                        <input
                            type="password"
                            id="password"
                            name="password"
                            value={formData.password}
                            onChange={handleChange}
                            required
                            minLength="6"
                            placeholder="At least 6 characters"
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="confirmPassword">Confirm Password</label>
                        <input
                            type="password"
                            id="confirmPassword"
                            name="confirmPassword"
                            value={formData.confirmPassword}
                            onChange={handleChange}
                            required
                            placeholder="Re-enter your password"
                        />
                    </div>

                    <button type="submit" className="register-button" disabled={loading}>
                        {loading ? 'Creating Admin...' : 'Complete Setup'}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default Setup;
