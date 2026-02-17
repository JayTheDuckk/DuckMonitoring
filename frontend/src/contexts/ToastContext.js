import React, { createContext, useContext, useState, useCallback } from 'react';
import '../components/common/Toast.css';

const ToastContext = createContext(null);

export const ToastProvider = ({ children }) => {
    const [toasts, setToasts] = useState([]);

    const addToast = useCallback((type, title, message, duration = 5000) => {
        const id = Date.now().toString() + Math.random().toString();
        setToasts(prev => [...prev, { id, type, title, message, duration, isLeaving: false }]);

        if (duration > 0) {
            setTimeout(() => {
                removeToast(id);
            }, duration);
        }
    }, []);

    const removeToast = useCallback((id) => {
        setToasts(prev => prev.map(t => t.id === id ? { ...t, isLeaving: true } : t));

        // Allow animation to finish
        setTimeout(() => {
            setToasts(prev => prev.filter(t => t.id !== id));
        }, 300);
    }, []);

    const showSuccess = (title, message) => addToast('success', title, message);
    const showError = (title, message) => addToast('error', title, message);
    const showInfo = (title, message) => addToast('info', title, message);
    const showWarning = (title, message) => addToast('warning', title, message);

    return (
        <ToastContext.Provider value={{ showSuccess, showError, showInfo, showWarning, addToast, removeToast }}>
            {children}
            <div className="toast-container">
                {toasts.map(toast => (
                    <div
                        key={toast.id}
                        className={`toast ${toast.type} ${toast.isLeaving ? 'leaving' : ''}`}
                        role="alert"
                    >
                        <div className="toast-icon">
                            {toast.type === 'success' && '✓'}
                            {toast.type === 'error' && '✕'}
                            {toast.type === 'warning' && '⚠'}
                            {toast.type === 'info' && 'ℹ'}
                        </div>
                        <div className="toast-content">
                            {toast.title && <div className="toast-title">{toast.title}</div>}
                            <div className="toast-message">{toast.message}</div>
                        </div>
                        <button className="toast-close" onClick={() => removeToast(toast.id)}>
                            ×
                        </button>
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    );
};

export const useToast = () => {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within a ToastProvider');
    }
    return context;
};
