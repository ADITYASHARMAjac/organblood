import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

function NotFoundPage() {
  const { auth } = useAuth();

  return (
    <div className="auth-shell">
      <div className="panel auth-card">
        <h2>Page Not Found</h2>
        <p>The page you requested does not exist.</p>
        <div className="tab-row top-space">
          <Link className="nav-link" to="/">Go to Home</Link>
          <Link className="nav-link" to={auth?.token ? '/dashboard' : '/auth'}>
            {auth?.token ? 'Go to Dashboard' : 'Go to Login'}
          </Link>
        </div>
      </div>
    </div>
  );
}

export default NotFoundPage;
