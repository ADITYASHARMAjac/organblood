import React from 'react';
import { Link, NavLink } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

const publicLinks = [
  { to: '/', label: 'Home' },
  { to: '/about', label: 'About' },
  { to: '/how-it-works', label: 'How It Works' },
  { to: '/eligibility', label: 'Eligibility' },
  { to: '/contact', label: 'Contact' },
];

function PublicLayout({ children }) {
  const { auth } = useAuth();

  return (
    <div className="public-shell">
      <header className="public-header">
        <div className="public-header-inner">
          <Link to="/" className="brand-link">
            <span className="brand-mark">CareFlow</span>
            <span className="brand-subtitle">Blood and Organ Donation Network</span>
          </Link>

          <nav className="public-nav" aria-label="Main navigation">
            {publicLinks.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => (isActive ? 'public-nav-link active' : 'public-nav-link')}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="public-actions">
            {auth?.token ? (
              <Link to="/dashboard" className="btn-solid">Open Portal</Link>
            ) : (
              <>
                <Link to="/auth" className="btn-ghost">Sign In</Link>
                <Link to="/auth" className="btn-solid">Get Started</Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="public-main">{children}</main>

      <footer className="public-footer">
        <div className="public-footer-inner">
          <div>
            <h3>CareFlow</h3>
            <p>
              A coordinated donation ecosystem connecting donors, recipients, hospitals,
              and administrators in one secure platform.
            </p>
          </div>
          <div>
            <h4>Explore</h4>
            <div className="footer-links">
              <Link to="/about">Our Mission</Link>
              <Link to="/how-it-works">Process</Link>
              <Link to="/eligibility">Eligibility Checker</Link>
              <Link to="/contact">Contact</Link>
            </div>
          </div>
          <div>
            <h4>Portal Access</h4>
            <div className="footer-links">
              <Link to="/auth">Login / Register</Link>
              <Link to="/dashboard">User Dashboard</Link>
              <a href="http://localhost:8002/docs" target="_blank" rel="noreferrer">API Documentation</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default PublicLayout;
