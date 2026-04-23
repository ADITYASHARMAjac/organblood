import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import FlashBar from '../components/FlashBar';
import heroNetwork from '../assets/hero-network.svg';

const initialRegister = {
  email: '',
  phone: '',
  username: '',
  password: '',
  role: 'DONOR',
};

const initialLogin = {
  email: '',
  password: '',
};

const demoCredentials = {
  admin: {
    label: 'Central Command',
    email: 'admin@blooddonation.com',
    password: 'SecurePass@123',
  },
  donor: {
    label: 'Fulfilling Hospital',
    email: 'donor@blooddonation.com',
    password: 'SecurePass@123',
  },
  recipient: {
    label: 'Requesting Hospital',
    email: 'recipient@blooddonation.com',
    password: 'SecurePass@123',
  },
};

const roleLabels = {
  DONOR: 'Fulfilling Hospital',
  RECIPIENT: 'Requesting Hospital',
  ADMIN: 'Central Command',
};

function AuthPage() {
  const navigate = useNavigate();
  const { login, register, flash, setFlash } = useAuth();

  const [mode, setMode] = useState('login');
  const [registerForm, setRegisterForm] = useState(initialRegister);
  const [loginForm, setLoginForm] = useState(initialLogin);
  const [rememberMe, setRememberMe] = useState(true);
  const [busy, setBusy] = useState(false);

  function applyDemo(type) {
    const creds = demoCredentials[type];
    if (!creds) return;
    setMode('login');
    setLoginForm({
      email: creds.email,
      password: creds.password,
    });
  }

  async function handleRegister(event) {
    event.preventDefault();
    setBusy(true);
    try {
      await register(registerForm);
      navigate('/verify');
    } catch (error) {
      setFlash({ type: 'error', text: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleLogin(event) {
    event.preventDefault();
    setBusy(true);
    try {
      const data = await login(loginForm);
      const userRole = data?.user?.role;

      if (userRole === 'DONOR') {
        navigate('/donor/medical-profile');
      } else if (userRole === 'ADMIN') {
        navigate('/admin/recipient-requests');
      } else if (userRole === 'RECIPIENT') {
        navigate('/recipient/request');
      } else {
        navigate('/dashboard');
      }
    } catch (error) {
      setFlash({ type: 'error', text: error.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-shell auth-modern-shell">
      <div className="auth-modern-wrap">
        <section className="auth-modern-left">
          <div className="auth-modern-brand-row">
            <Link to="/" className="auth-modern-brand">
              <span className="auth-modern-mark" aria-hidden="true">
                <i />
                <i />
                <i />
                <i />
              </span>
              <strong>CareFlow</strong>
            </Link>
            <Link to="/" className="btn-ghost auth-back-btn">Back to Landing</Link>
          </div>

          <div className="auth-modern-card">
            <h1>{mode === 'login' ? 'Welcome back' : 'Create account'}</h1>
            <p className="auth-modern-subtitle">
              {mode === 'login' ? 'Please enter your details' : 'Set up your secure network access'}
            </p>

            <FlashBar flash={flash} />

            <div className="auth-modern-switch">
              <button
                type="button"
                className={mode === 'login' ? 'active' : ''}
                onClick={() => setMode('login')}
              >
                Sign In
              </button>
              <button
                type="button"
                className={mode === 'register' ? 'active' : ''}
                onClick={() => setMode('register')}
              >
                Register
              </button>
            </div>

            {mode === 'login' ? (
              <form onSubmit={handleLogin} className="auth-modern-form">
                <label>
                  Email address
                  <input
                    type="email"
                    placeholder="hospital.team@example.com"
                    value={loginForm.email}
                    onChange={(e) => setLoginForm((prev) => ({ ...prev, email: e.target.value }))}
                    required
                  />
                </label>

                <label>
                  Password
                  <input
                    type="password"
                    placeholder="Enter your password"
                    value={loginForm.password}
                    onChange={(e) => setLoginForm((prev) => ({ ...prev, password: e.target.value }))}
                    required
                  />
                </label>

                <div className="auth-modern-row">
                  <label className="auth-modern-check">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                    />
                    Remember for 30 days
                  </label>
                  <Link to="/contact" className="auth-modern-link">Forgot password</Link>
                </div>

                <button type="submit" className="btn-solid auth-modern-submit" disabled={busy}>
                  {busy ? 'Signing in...' : 'Sign in'}
                </button>

                <div className="auth-modern-demo">
                  <p>Quick login (auto-fill)</p>
                  <div className="auth-modern-demo-actions">
                    <button type="button" className="btn-ghost" onClick={() => applyDemo('recipient')}>
                      Requesting
                    </button>
                    <button type="button" className="btn-ghost" onClick={() => applyDemo('donor')}>
                      Fulfilling
                    </button>
                    <button type="button" className="btn-ghost" onClick={() => applyDemo('admin')}>
                      Command
                    </button>
                  </div>
                </div>
              </form>
            ) : (
              <form onSubmit={handleRegister} className="auth-modern-form auth-modern-form-register">
                <label>
                  Email address
                  <input
                    type="email"
                    placeholder="hospital.team@example.com"
                    value={registerForm.email}
                    onChange={(e) => setRegisterForm((prev) => ({ ...prev, email: e.target.value }))}
                    required
                  />
                </label>

                <label>
                  Phone
                  <input
                    placeholder="+91xxxxxxxxxx"
                    value={registerForm.phone}
                    onChange={(e) => setRegisterForm((prev) => ({ ...prev, phone: e.target.value }))}
                    required
                  />
                </label>

                <label>
                  Username
                  <input
                    placeholder="Choose a username"
                    value={registerForm.username}
                    onChange={(e) => setRegisterForm((prev) => ({ ...prev, username: e.target.value }))}
                    required
                  />
                </label>

                <label>
                  Password
                  <input
                    type="password"
                    placeholder="Create a strong password"
                    value={registerForm.password}
                    onChange={(e) => setRegisterForm((prev) => ({ ...prev, password: e.target.value }))}
                    required
                  />
                </label>

                <label>
                  Role
                  <select
                    value={registerForm.role}
                    onChange={(e) => setRegisterForm((prev) => ({ ...prev, role: e.target.value }))}
                  >
                    <option value="DONOR">{roleLabels.DONOR}</option>
                    <option value="RECIPIENT">{roleLabels.RECIPIENT}</option>
                    <option value="ADMIN">{roleLabels.ADMIN}</option>
                  </select>
                </label>

                <button type="submit" className="btn-solid auth-modern-submit" disabled={busy}>
                  {busy ? 'Creating account...' : 'Create account'}
                </button>
              </form>
            )}

            <p className="auth-modern-bottom">
              {mode === 'login' ? "Don't have an account?" : 'Already have an account?'}{' '}
              <button
                type="button"
                className="auth-modern-inline-btn"
                onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
              >
                {mode === 'login' ? 'Sign up' : 'Sign in'}
              </button>
            </p>
          </div>
        </section>

        <section className="auth-modern-right" aria-hidden="true">
          <div className="auth-modern-visual">
            <img src={heroNetwork} alt="CareFlow support visual" />
          </div>
        </section>
      </div>
    </div>
  );
}

export default AuthPage;
