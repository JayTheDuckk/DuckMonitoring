import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import './Modal.css';

const Modal = ({
    isOpen,
    onClose,
    title,
    children,
    footer,
    size = 'medium', // small, medium, large
    closeOnOverlayClick = true
}) => {

    // Prevent body scroll when modal is open
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = 'unset';
        }
        return () => {
            document.body.style.overflow = 'unset';
        };
    }, [isOpen]);

    // Close on Escape key
    useEffect(() => {
        const handleEsc = (e) => {
            if (e.key === 'Escape') onClose();
        };
        if (isOpen) {
            window.addEventListener('keydown', handleEsc);
        }
        return () => window.removeEventListener('keydown', handleEsc);
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    return createPortal(
        <div
            className="modal-overlay"
            onClick={closeOnOverlayClick ? onClose : undefined}
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
        >
            <div
                className={`modal-content ${size}`}
                onClick={e => e.stopPropagation()}
            >
                <div className="modal-header">
                    <h3 id="modal-title">{title}</h3>
                    <button
                        className="modal-close"
                        onClick={onClose}
                        aria-label="Close modal"
                    >
                        ×
                    </button>
                </div>

                <div className="modal-body">
                    {children}
                </div>

                {footer && (
                    <div className="modal-footer">
                        {footer}
                    </div>
                )}
            </div>
        </div>,
        document.body
    );
};

export default Modal;
