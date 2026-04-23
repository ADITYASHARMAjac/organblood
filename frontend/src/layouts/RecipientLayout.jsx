import React, { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

const publicLinks = [
  { to: '/', label: 'Home' },
  { to: '/about', label: 'About' },
  { to: '/how-it-works', label: 'How It Works' },
  { to: '/eligibility', label: 'Eligibility' },
  { to: '/contact', label: 'Contact' },
];

function RecipientLayout({ children }) {
  const { auth, logout } = useAuth();
  const location = useLocation();
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const profileMenuRef = useRef(null);
  const isCompactPage = ['/recipient/profile', '/recipient/request', '/recipient/history'].includes(location.pathname);

  useEffect(() => {
    function handleClickOutside(event) {
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target)) {
        setProfileMenuOpen(false);
      }
    }

    function handleEscKey(event) {
      if (event.key === 'Escape') setProfileMenuOpen(false);
    }

    window.addEventListener('mousedown', handleClickOutside);
    window.addEventListener('keydown', handleEscKey);
    return () => {
      window.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('keydown', handleEscKey);
    };
  }, []);

  const isRecipientLoggedIn = Boolean(auth?.token && auth?.user?.role === 'RECIPIENT');
  const avatarInitial = (auth?.user?.username || 'R').trim().charAt(0).toUpperCase();

  return (
    <div className="donor-site-shell">
      <header className="donor-public-header">
        <div className="donor-public-header-inner">
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

          {isRecipientLoggedIn && (
            <div className="donor-profile-menu" ref={profileMenuRef}>
              <button
                type="button"
                className="donor-header-avatar"
                title={auth?.user?.username || 'recipient'}
                onClick={() => setProfileMenuOpen((prev) => !prev)}
              >
                <span className="donor-header-avatar-fallback">{avatarInitial}</span>
                <span className="donor-header-avatar-caret" aria-hidden="true" />
              </button>

              {profileMenuOpen && (
                <div className="donor-profile-dropdown">
                  <div className="donor-profile-dropdown-header">
                    <strong>{auth?.user?.username || 'Recipient'}</strong>
                    <span>Requesting hospital account</span>
                  </div>

                  <NavLink to="/recipient/profile" onClick={() => setProfileMenuOpen(false)}>
                    Edit Profile
                  </NavLink>
                  <button
                    type="button"
                    className="donor-dropdown-action danger"
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

      <div className="donor-site-grid">
        <aside className="donor-sidebar panel">
          <div>
            <p className="eyebrow">CareFlow</p>
            <h1>CareFlow Requesting Hospital Desk</h1>
          </div>

          <nav className="donor-sidebar-nav">
            <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/recipient/profile">Hospital Profile</NavLink>
            <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/recipient/request">Raise Requirement</NavLink>
            <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/recipient/history">Case History</NavLink>
          </nav>
        </aside>

        <main className={`donor-site-main recipient-site-main ${isCompactPage ? 'donor-site-main-compact recipient-site-main-compact' : ''}`}>
          {children}
        </main>
      </div>
    </div>
  );
}

export default RecipientLayout;
