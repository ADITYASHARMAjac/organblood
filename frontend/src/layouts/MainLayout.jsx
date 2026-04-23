import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import FlashBar from '../components/FlashBar';

function MainLayout({ children }) {
  const { role, auth, flash, logout } = useAuth();
  const location = useLocation();

  const links = [
    { to: '/dashboard', label: 'Dashboard' },
    { to: '/verify', label: 'Verify Contacts' },
    { to: '/notifications', label: 'Notifications' },
  ];

  if (role === 'DONOR') {
    links.push({ to: '/donor', label: 'Donor Center' });
  }
  if (role === 'RECIPIENT') {
    links.push({ to: '/recipient/request', label: 'Recipient Center' });
  }
  if (role === 'ADMIN') {
    links.push({ to: '/admin/recipient-requests', label: 'Admin Console' });
  }

  return (
    <div className="app-shell">
      <header className="hero portal-hero">
        <div className="hero-inner">
          <div className="portal-hero-top">
            <div>
              <p className="eyebrow">Secure Operations Portal</p>
              <h1>CareFlow Command Center</h1>
              <p className="subtitle">Operational dashboard for real donor-recipient workflows.</p>
            </div>
            <div className="tab-row">
              <Link className="nav-link" to="/">Public Site</Link>
              <a className="nav-link" href="http://localhost:8002/docs" target="_blank" rel="noreferrer">API Docs</a>
            </div>
          </div>
          <div className="status-row">
            <span className="chip">User: {auth?.user?.username || 'Unknown'}</span>
            <span className="chip">Role: {role || 'Guest'}</span>
          </div>
        </div>
      </header>

      <main className="layout app-grid">
        <aside className="panel sidebar">
          <h3>Navigation</h3>
          <nav className="nav-list">
            {links.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={location.pathname === item.to ? 'nav-link active' : 'nav-link'}
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <button className="danger" onClick={logout}>Logout</button>
        </aside>

        <section className="content-area">
          <div className="panel full">
            <FlashBar flash={flash} />
          </div>
          {children}
        </section>
      </main>
    </div>
  );
}

export default MainLayout;
