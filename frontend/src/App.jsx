import React from 'react';
import { HashRouter, Navigate, Route, Routes } from 'react-router-dom';

import { AuthProvider, useAuth } from './auth/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import MainLayout from './layouts/MainLayout';
import DonorLayout from './layouts/DonorLayout';
import AdminLayout from './layouts/AdminLayout';
import RecipientLayout from './layouts/RecipientLayout';
import PublicLayout from './layouts/PublicLayout';
import LandingPage from './pages/LandingPage';
import AboutPage from './pages/AboutPage';
import HowItWorksPage from './pages/HowItWorksPage';
import ContactPage from './pages/ContactPage';
import EligibilityPage from './pages/EligibilityPage';
import AuthPage from './pages/AuthPage';
import VerifyPage from './pages/VerifyPage';
import DashboardPage from './pages/DashboardPage';
import DonorPage from './pages/DonorPage';
import RecipientPage from './pages/RecipientPage';
import NotificationsPage from './pages/NotificationsPage';
import AdminPage from './pages/AdminPage';
import NotFoundPage from './pages/NotFoundPage';

import './App.css';

function PortalRedirect() {
  const { auth } = useAuth();
  if (!auth?.token) {
    return <Navigate to="/auth" replace />;
  }

  if (auth?.user?.role === 'ADMIN') {
    return <Navigate to="/admin/recipient-requests" replace />;
  }

  if (auth?.user?.role === 'DONOR') {
    return <Navigate to="/donor/medical-profile" replace />;
  }

  if (auth?.user?.role === 'RECIPIENT') {
    return <Navigate to="/recipient/request" replace />;
  }

  return <Navigate to="/dashboard" replace />;
}

function ProtectedLayout({ children, roles }) {
  const { role } = useAuth();

  if (role === 'ADMIN' && !(roles || []).includes('ADMIN')) {
    return <Navigate to="/admin/recipient-requests" replace />;
  }

  return (
    <ProtectedRoute roles={roles}>
      <MainLayout>{children}</MainLayout>
    </ProtectedRoute>
  );
}

function DonorWebsiteLayout({ children }) {
  return (
    <ProtectedRoute roles={['DONOR']}>
      <DonorLayout>{children}</DonorLayout>
    </ProtectedRoute>
  );
}

function AdminWebsiteLayout({ children }) {
  return (
    <ProtectedRoute roles={['ADMIN']}>
      <AdminLayout>{children}</AdminLayout>
    </ProtectedRoute>
  );
}

function DashboardRoute() {
  const { role } = useAuth();

  if (role === 'DONOR') {
    return <Navigate to="/donor/medical-profile" replace />;
  }

  if (role === 'ADMIN') {
    return <Navigate to="/admin/recipient-requests" replace />;
  }

  if (role === 'RECIPIENT') {
    return <Navigate to="/recipient/request" replace />;
  }

  return (
    <ProtectedLayout>
      <DashboardPage />
    </ProtectedLayout>
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/"
        element={(
          <PublicLayout>
            <LandingPage />
          </PublicLayout>
        )}
      />
      <Route
        path="/about"
        element={(
          <PublicLayout>
            <AboutPage />
          </PublicLayout>
        )}
      />
      <Route
        path="/how-it-works"
        element={(
          <PublicLayout>
            <HowItWorksPage />
          </PublicLayout>
        )}
      />
      <Route
        path="/contact"
        element={(
          <PublicLayout>
            <ContactPage />
          </PublicLayout>
        )}
      />
      <Route
        path="/eligibility"
        element={(
          <PublicLayout>
            <EligibilityPage />
          </PublicLayout>
        )}
      />

      <Route path="/portal" element={<PortalRedirect />} />
      <Route path="/auth" element={<AuthPage />} />

      <Route
        path="/dashboard"
        element={<DashboardRoute />}
      />

      <Route
        path="/verify"
        element={(
          <ProtectedLayout>
            <VerifyPage />
          </ProtectedLayout>
        )}
      />

      <Route
        path="/donor"
        element={<Navigate to="/donor/medical-profile" replace />}
      />

      <Route
        path="/donor/medical-profile"
        element={(
          <DonorWebsiteLayout>
            <DonorPage view="medical-profile" />
          </DonorWebsiteLayout>
        )}
      />

      <Route
        path="/donor/donation-history"
        element={(
          <DonorWebsiteLayout>
            <DonorPage view="donation-history" />
          </DonorWebsiteLayout>
        )}
      />

      <Route
        path="/donor/recipient-requests"
        element={(
          <DonorWebsiteLayout>
            <DonorPage view="recipient-requests" />
          </DonorWebsiteLayout>
        )}
      />

      <Route
        path="/donor/nearby-requests"
        element={(
          <DonorWebsiteLayout>
            <DonorPage view="nearby-requests" />
          </DonorWebsiteLayout>
        )}
      />

      <Route
        path="/donor/appointment"
        element={(
          <DonorWebsiteLayout>
            <DonorPage view="donor-appointment" />
          </DonorWebsiteLayout>
        )}
      />

      <Route path="/donor/appointment-scheduling" element={<Navigate to="/donor/appointment" replace />} />

      <Route
        path="/donor/matching-system"
        element={(
          <DonorWebsiteLayout>
            <DonorPage view="matching-system" />
          </DonorWebsiteLayout>
        )}
      />

      <Route path="/donor/overview" element={<Navigate to="/donor/medical-profile" replace />} />
      <Route path="/donor/profile" element={<Navigate to="/donor/medical-profile" replace />} />
      <Route path="/donor/availability" element={<Navigate to="/donor/medical-profile" replace />} />
      <Route path="/donor/requests" element={<Navigate to="/donor/recipient-requests" replace />} />
      <Route path="/donor/matches" element={<Navigate to="/donor/matching-system" replace />} />
      <Route path="/donor/appointments" element={<Navigate to="/donor/appointment" replace />} />

      <Route path="/recipient" element={<Navigate to="/recipient/request" replace />} />
      <Route
        path="/recipient/profile"
        element={(
          <ProtectedRoute roles={['RECIPIENT']}>
            <RecipientLayout>
              <RecipientPage view="profile" />
            </RecipientLayout>
          </ProtectedRoute>
        )}
      />
      <Route
        path="/recipient/request"
        element={(
          <ProtectedRoute roles={['RECIPIENT']}>
            <RecipientLayout>
              <RecipientPage view="request" />
            </RecipientLayout>
          </ProtectedRoute>
        )}
      />
      <Route
        path="/recipient/history"
        element={(
          <ProtectedRoute roles={['RECIPIENT']}>
            <RecipientLayout>
              <RecipientPage view="history" />
            </RecipientLayout>
          </ProtectedRoute>
        )}
      />

      <Route
        path="/notifications"
        element={(
          <ProtectedLayout>
            <NotificationsPage />
          </ProtectedLayout>
        )}
      />

      <Route
        path="/admin"
        element={<Navigate to="/admin/recipient-requests" replace />}
      />

      <Route
        path="/admin/requests"
        element={<Navigate to="/admin/recipient-requests" replace />}
      />

      <Route
        path="/admin/recipient-requests"
        element={(
          <AdminWebsiteLayout>
            <AdminPage view="recipient-requests" />
          </AdminWebsiteLayout>
        )}
      />

      <Route
        path="/admin/donor-requests"
        element={(
          <AdminWebsiteLayout>
            <AdminPage view="donor-requests" />
          </AdminWebsiteLayout>
        )}
      />

      <Route
        path="/admin/schedules"
        element={(
          <AdminWebsiteLayout>
            <AdminPage view="schedules" />
          </AdminWebsiteLayout>
        )}
      />

      <Route path="/admin/users" element={<Navigate to="/admin/recipient-requests" replace />} />
      <Route path="/admin/operations" element={<Navigate to="/admin/recipient-requests" replace />} />
      <Route path="/admin/schedule" element={<Navigate to="/admin/schedules" replace />} />

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <HashRouter>
        <AppRoutes />
      </HashRouter>
    </AuthProvider>
  );
}

export default App;
