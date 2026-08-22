import React from 'react';
import './Header.css';

interface HeaderProps {
  onManageBooking: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onManageBooking }) => {
  return (
    <header className="header">
      <div className="header-inner">
        {/* Logo & Branding */}
        <div className="header-brand">
          <div className="header-logo-icon">🏠</div>
          <h1 className="header-logo-text">
            <span className="text-gradient">The Property Scout</span>
          </h1>
        </div>

        {/* Right Actions */}
        <div className="header-actions">
          <button 
            className="btn btn-ghost header-manage-btn"
            onClick={onManageBooking}
          >
            <span>📅</span>
            <span>Manage Booking</span>
          </button>

          <div className="header-status">
            <span className="header-status-dot"></span>
            <span className="header-status-text">Online</span>
          </div>
        </div>
      </div>
    </header>
  );
};
