import React, { useState } from 'react';

const initialState = {
  fullName: '',
  email: '',
  phone: '',
  subject: 'General Inquiry',
  message: '',
};

function ContactPage() {
  const [form, setForm] = useState(initialState);
  const [submitted, setSubmitted] = useState(false);

  function onChange(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function onSubmit(event) {
    event.preventDefault();
    setSubmitted(true);
    setForm(initialState);
  }

  return (
    <section className="section-wrap content-page">
      <p className="eyebrow">Contact</p>
      <h1>Reach the CareFlow coordination team</h1>
      <p>
        For hospital onboarding, emergency coordination, partnership requests, or technical support,
        send us a message. The form submission currently stores data locally for demo use.
      </p>

      <div className="contact-grid">
        <form className="panel form-panel" onSubmit={onSubmit}>
          <label>
            Full Name
            <input value={form.fullName} onChange={(e) => onChange('fullName', e.target.value)} required />
          </label>
          <label>
            Email
            <input type="email" value={form.email} onChange={(e) => onChange('email', e.target.value)} required />
          </label>
          <label>
            Phone
            <input value={form.phone} onChange={(e) => onChange('phone', e.target.value)} required />
          </label>
          <label>
            Subject
            <select value={form.subject} onChange={(e) => onChange('subject', e.target.value)}>
              <option>General Inquiry</option>
              <option>Hospital Onboarding</option>
              <option>Urgent Request Support</option>
              <option>Technical Support</option>
            </select>
          </label>
          <label>
            Message
            <textarea value={form.message} onChange={(e) => onChange('message', e.target.value)} rows={6} required />
          </label>
          <button type="submit" className="btn-solid">Send Message</button>
          {submitted && <p className="form-success">Thanks. Your message has been recorded in this demo.</p>}
        </form>

        <aside className="panel contact-aside">
          <h3>Direct Channels</h3>
          <p>Email: careflow-support@example.org</p>
          <p>Emergency Desk: +91 90000 00000</p>
          <p>Hours: 24x7 for active emergency requests</p>

          <h3>Head Office</h3>
          <p>CareFlow Operations Center</p>
          <p>Sector 18, Navi Mumbai, India</p>
        </aside>
      </div>
    </section>
  );
}

export default ContactPage;
