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

function DonorLayout({ children }) {
  const { auth, logout } = useAuth();
  const location = useLocation();
  const [headerPhoto, setHeaderPhoto] = useState(() => localStorage.getItem('donor_profile_photo') || '');
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const profileMenuRef = useRef(null);
  const isCompactPage = ['/donor/donation-history', '/donor/matching-system', '/donor/appointment'].includes(location.pathname);

  useEffect(() => {
    function handlePhotoUpdated(event) {
      setHeaderPhoto(event.detail || '');
    }

    window.addEventListener('donor-photo-updated', handlePhotoUpdated);
    return () => window.removeEventListener('donor-photo-updated', handlePhotoUpdated);
  }, []);

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

  const isDonorLoggedIn = Boolean(auth?.token && auth?.user?.role === 'DONOR');

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

          {isDonorLoggedIn && (
            <div className="donor-profile-menu" ref={profileMenuRef}>
              <button
                type="button"
                className="donor-header-avatar"
                title={auth?.user?.username || 'donor'}
                onClick={() => setProfileMenuOpen((prev) => !prev)}
              >
                {headerPhoto ? (
                  <img src={headerPhoto} alt="Donor profile" />
                ) : (
                  <span className="donor-header-avatar-fallback">U</span>
                )}
                <span className="donor-header-avatar-caret" aria-hidden="true" />
              </button>

              {profileMenuOpen && (
                <div className="donor-profile-dropdown">
                  <div className="donor-profile-dropdown-header">
                    <strong>{auth?.user?.username || 'Donor'}</strong>
                    <span>Fulfilling hospital account</span>
                  </div>

                  <NavLink to="/donor/medical-profile" onClick={() => setProfileMenuOpen(false)}>
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
            <h1>CareFlow Fulfilling Hospital Desk</h1>
          </div>

          <nav className="donor-sidebar-nav">
            <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/donor/medical-profile">Fulfillment Profile</NavLink>
            <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/donor/donation-history">Fulfillment History</NavLink>
            <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/donor/recipient-requests">Network Requests</NavLink>
            <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/donor/nearby-requests">Approved Cases</NavLink>
            <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/donor/appointment">Transfer Scheduling</NavLink>
            <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/donor/matching-system">Active Handovers</NavLink>
          </nav>

        </aside>

        <main className={`donor-site-main ${isCompactPage ? 'donor-site-main-compact' : ''}`}>
          {children}
        </main>
      </div>
    </div>
  );
}

export default DonorLayout;
