import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

function VerifyPage() {
  const { otp, setOtp, verifyEmail, verifyPhone, setFlash } = useAuth();
  const [busy, setBusy] = useState(false);

  async function onVerifyEmail() {
    setBusy(true);
    try {
      await verifyEmail(otp.emailOtp);
    } catch (error) {
      setFlash({ type: 'error', text: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function onVerifyPhone() {
    setBusy(true);
    try {
      await verifyPhone(otp.phoneOtp);
    } catch (error) {
      setFlash({ type: 'error', text: error.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel full">
      <h2>Verify Email and Phone</h2>
      <p>In development, OTP preview values are auto-filled after registration.</p>
      <p className="muted-text">Complete both checks to ensure full account trust before operational activity.</p>

      <div className="otp-row">
        <label>Email</label>
        <input value={otp.email} readOnly />
      </div>
      <div className="otp-row">
        <label>Email OTP</label>
        <input
          value={otp.emailOtp}
          onChange={(e) => setOtp((prev) => ({ ...prev, emailOtp: e.target.value }))}
          placeholder="Enter email OTP"
        />
        <button onClick={onVerifyEmail} disabled={busy}>Verify Email</button>
      </div>

      <div className="otp-row">
        <label>Phone</label>
        <input value={otp.phone} readOnly />
      </div>
      <div className="otp-row">
        <label>Phone OTP</label>
        <input
          value={otp.phoneOtp}
          onChange={(e) => setOtp((prev) => ({ ...prev, phoneOtp: e.target.value }))}
          placeholder="Enter phone OTP"
        />
        <button onClick={onVerifyPhone} disabled={busy}>Verify Phone</button>
      </div>

      <div className="tab-row top-space">
        <Link className="nav-link" to="/dashboard">Go to Dashboard</Link>
      </div>
    </section>
  );
}

export default VerifyPage;
