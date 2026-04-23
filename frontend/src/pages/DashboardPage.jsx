import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { apiRequest, healthCheck } from '../api/client';

function DashboardPage() {
  const { token, role, auth, setFlash } = useAuth();
  const [health, setHealth] = useState('Checking...');
  const [counts, setCounts] = useState({ requests: 0, notifications: 0, users: 0 });

  const quickActions = [
    { to: '/verify', label: 'Complete Verification', roles: [] },
    { to: '/notifications', label: 'Open Notifications', roles: [] },
    { to: '/donor', label: 'Open Fulfilling Hospital Desk', roles: ['DONOR'] },
    { to: '/recipient/request', label: 'Open Requesting Hospital Desk', roles: ['RECIPIENT'] },
    { to: '/admin/recipient-requests', label: 'Open Network Command Center', roles: ['ADMIN'] },
  ].filter((item) => item.roles.length === 0 || item.roles.includes(role));

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const healthData = await healthCheck();
        if (active) {
          setHealth(`${healthData.status} (${healthData.version})`);
        }

        const requestData = await apiRequest('/requests', { token });
        const notificationData = await apiRequest('/notifications/me?unread_only=true', { token });

        let userCount = 0;
        if (role === 'ADMIN') {
          const users = await apiRequest('/admin/users?page=1&page_size=10', { token });
          userCount = users.total || 0;
        }

        if (active) {
          setCounts({
            requests: requestData.count || 0,
            notifications: notificationData.count || 0,
            users: userCount,
          });
        }
      } catch (error) {
        if (active) {
          setFlash({ type: 'error', text: error.message });
        }
      }
    }

    load();

    return () => {
      active = false;
    };
  }, [token, role, setFlash]);

  return (
    <section className="panel full">
      <h2>Hospital Operations Dashboard</h2>
      <p>Logged in as {auth?.user?.username} ({role})</p>
      <p className="muted-text">
        Use this dashboard as your launch point for verification, case routing, inter-hospital tracking,
        and role-specific operational modules.
      </p>

      <div className="tab-row top-space">
        {quickActions.map((item) => (
          <Link key={item.to} to={item.to} className="nav-link">
            {item.label}
          </Link>
        ))}
      </div>

      <div className="kpi-grid">
        <div className="kpi">
          <h3>Backend Health</h3>
          <p>{health}</p>
        </div>
        <div className="kpi">
          <h3>Total Requests</h3>
          <p>{counts.requests}</p>
        </div>
        <div className="kpi">
          <h3>Unread Notifications</h3>
          <p>{counts.notifications}</p>
        </div>
        {role === 'ADMIN' && (
          <div className="kpi">
            <h3>Total Users</h3>
            <p>{counts.users}</p>
          </div>
        )}
      </div>
    </section>
  );
}

export default DashboardPage;
