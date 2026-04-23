import React, { useEffect, useRef, useState } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

const publicLinks = [
  { to: '/', label: 'Home' },
  { to: '/about', label: 'About' },
  { to: '/how-it-works', label: 'How It Works' },
  { to: '/eligibility', label: 'Eligibility' },
  { to: '/contact', label: 'Contact' },
];

function AdminLayout({ children }) {
  const { auth, logout } = useAuth();
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const profileMenuRef = useRef(null);
  const isAdminLoggedIn = Boolean(auth?.token && auth?.user?.role === 'ADMIN');

  useEffect(() => {
    function handleClickOutside(event) {
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target)) {
        setProfileMenuOpen(false);
      }
    }

    function handleEscKey(event) {
      if (event.key === 'Escape') {
        setProfileMenuOpen(false);
      }
    }

    window.addEventListener('mousedown', handleClickOutside);
    window.addEventListener('keydown', handleEscKey);
    return () => {
      window.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('keydown', handleEscKey);
    };
  }, []);

  return (
    <div className="admin-site-shell">
      <header className="admin-public-header">
        <div className="admin-public-header-inner">
          <Link to="/" className="brand-link">
            <span className="brand-mark">CareFlow</span>
            <span className="brand-subtitle">Hospital Coordination Network</span>
          </Link>

          <nav className="public-nav" aria-label="Public navigation">
            {publicLinks.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) => (isActive ? 'public-nav-link active' : 'public-nav-link')}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          {isAdminLoggedIn && (
            <div className="admin-profile-menu" ref={profileMenuRef}>
              <button
                type="button"
                className="admin-header-avatar"
                title={auth?.user?.username || 'admin'}
                onClick={() => setProfileMenuOpen((prev) => !prev)}
              >
                <span className="admin-header-avatar-fallback">A</span>
                <span className="admin-header-avatar-caret" aria-hidden="true" />
              </button>

              {profileMenuOpen && (
                <div className="admin-profile-dropdown">
                  <div className="admin-profile-dropdown-header">
                    <strong>{auth?.user?.username || 'Admin'}</strong>
                    <span>Central command account</span>
                  </div>
                  <button
                    type="button"
                    className="admin-dropdown-action danger"
                    onClick={() => {
                      setProfileMenuOpen(false);
                      logout();
                    }}
                  >
                    Logout
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </header>

      <div className="admin-site-grid">
        <aside className="admin-sidebar panel">
          <div>
            <p className="eyebrow">Operations</p>
            <h1>CareFlow Command Center</h1>
            <p className="subtitle">Unified workspace for governance, request routing, and inter-hospital approvals.</p>
          </div>

          <nav className="admin-sidebar-nav">
            <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/admin/recipient-requests">Requesting Hospitals</NavLink>
            <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/admin/donor-requests">Fulfilling Hospitals</NavLink>
            <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/admin/schedules">Transfer Schedules</NavLink>
          </nav>
        </aside>

        <main className="admin-site-main">
          {children}
        </main>
      </div>
    </div>
  );
}

export default AdminLayout;
