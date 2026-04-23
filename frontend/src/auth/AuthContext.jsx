import React, { createContext, useContext, useEffect, useState } from 'react';
import { apiRequest } from '../api/client';

const AuthContext = createContext(null);

const defaultRegister = {
  email: '',
  phone: '',
  username: '',
  password: '',
  role: 'DONOR',
};

const defaultOtp = {
  email: '',
  phone: '',
  emailOtp: '',
  phoneOtp: '',
};

function getStoredAuth() {
  const raw = localStorage.getItem('donation_auth');
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw);
  } catch (error) {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(getStoredAuth);
  const [otp, setOtp] = useState(defaultOtp);
  const [registerDraft, setRegisterDraft] = useState(defaultRegister);
  const [flash, setFlash] = useState({ type: 'info', text: 'Welcome. Sign in to continue.' });

  const token = auth?.token || '';
  const role = auth?.user?.role || '';

  function persistAuth(nextAuth) {
    if (nextAuth) {
      localStorage.setItem('donation_auth', JSON.stringify(nextAuth));
    } else {
      localStorage.removeItem('donation_auth');
    }
    setAuth(nextAuth);
  }

  async function register(payload) {
    const data = await apiRequest('/auth/register', {
      method: 'POST',
      body: payload,
    });

    persistAuth({
      token: data.tokens.access_token,
      refreshToken: data.tokens.refresh_token,
      user: data.user,
    });

    setRegisterDraft(payload);
    setOtp({
      email: payload.email,
      phone: payload.phone,
      emailOtp: data.otp_preview?.email_otp || '',
      phoneOtp: data.otp_preview?.phone_otp || '',
    });

    setFlash({ type: 'success', text: 'Registered successfully. Complete OTP verification.' });
    return data;
  }

  async function login(payload) {
    const data = await apiRequest('/auth/login', {
      method: 'POST',
      body: payload,
    });

    persistAuth({
      token: data.tokens.access_token,
      refreshToken: data.tokens.refresh_token,
      user: data.user,
    });

    setFlash({ type: 'success', text: 'Login successful.' });
    return data;
  }

  async function verifyEmail(otpValue) {
    if (!otp.email) {
      throw new Error('Email not available. Register first.');
    }

    const result = await apiRequest('/auth/verify-email', {
      method: 'POST',
      body: {
        email: otp.email,
        otp: otpValue,
      },
    });

    setFlash({ type: 'success', text: 'Email verified successfully.' });
    return result;
  }

  async function verifyPhone(otpValue) {
    if (!otp.phone) {
      throw new Error('Phone not available. Register first.');
    }

    const result = await apiRequest('/auth/verify-phone', {
      method: 'POST',
      body: {
        phone: otp.phone,
        otp: otpValue,
      },
    });

    setFlash({ type: 'success', text: 'Phone verified successfully.' });
    return result;
  }

  function logout() {
    persistAuth(null);
    setFlash({ type: 'info', text: 'Logged out.' });
  }

  useEffect(() => {
    function onAuthExpired() {
      persistAuth(null);
      setFlash({ type: 'error', text: 'Session expired. Please login again.' });
    }

    window.addEventListener('auth-expired', onAuthExpired);
    return () => {
      window.removeEventListener('auth-expired', onAuthExpired);
    };
  }, []);

  const value = {
    auth,
    token,
    role,
    otp,
    setOtp,
    registerDraft,
    flash,
    setFlash,
    register,
    login,
    verifyEmail,
    verifyPhone,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}
