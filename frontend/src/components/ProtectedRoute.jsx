import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

function ProtectedRoute({ children, roles = [] }) {
  const { auth, role } = useAuth();

  if (!auth?.token) {
    return <Navigate to="/auth" replace />;
  }

  if (roles.length > 0 && !roles.includes(role)) {
    if (role === 'RECIPIENT') {
      return <Navigate to="/recipient/request" replace />;
    }
    if (role === 'DONOR') {
      return <Navigate to="/donor/medical-profile" replace />;
    }
    if (role === 'ADMIN') {
      return <Navigate to="/admin/recipient-requests" replace />;
    }
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

export default ProtectedRoute;
