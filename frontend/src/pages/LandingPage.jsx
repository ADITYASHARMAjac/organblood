import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import heroNetwork from '../assets/hero-network.svg';

const impactItems = [
  { value: '24x7', label: 'Response Readiness' },
  { value: '< 5 min', label: 'Critical Alert Broadcast' },
  { value: '3 Roles', label: 'Request, Fulfill, Command' },
  { value: '100%', label: 'Traceable Workflow Events' },
];

const capabilityItems = [
  {
    title: 'Request Desk',
    text: 'Capture urgent blood or organ need with patient context, urgency, and target window in one guided form.',
  },
  {
    title: 'Fulfillment Desk',
    text: 'Review compatible incoming requests, confirm feasibility, and close handover loops faster.',
  },
  {
    title: 'Command Center',
    text: 'Oversee approvals, monitor route states, and manage cross-hospital coordination from one screen.',
  },
  {
    title: 'Live Signals',
    text: 'Receive real-time status updates for request, assignment, and completion milestones.',
  },
];

const processItems = [
  {
    step: '01',
    title: 'Hospital Raises Need',
    text: 'Recipient team submits verified requirement with urgency and timing details.',
  },
  {
    step: '02',
    title: 'Command Validates',
    text: 'Central desk checks eligibility and activates network routing with priority tags.',
  },
  {
    step: '03',
    title: 'Supply Team Responds',
    text: 'Fulfilling hospital accepts viable request and aligns appointment or handover flow.',
  },
  {
    step: '04',
    title: 'Case Closes Transparently',
    text: 'Every action is logged and visible for governance, safety, and audit readiness.',
  },
];

function LandingPage() {
  const { auth } = useAuth();
  const startRoute = auth?.token ? '/dashboard' : '/auth';

  return (
    <div className="landing-pro">
      <section className="section-wrap landing-pro-hero">
        <div className="landing-pro-copy">
          <p className="eyebrow">National Donation Coordination Platform</p>
          <h1>One intelligent network for urgent blood and organ coordination.</h1>
          <p>
            CareFlow unifies requesting hospitals, fulfilling hospitals, and command teams
            into one high-clarity workflow built for speed, safety, and accountability.
          </p>
          <div className="landing-actions">
            <Link to={startRoute} className="btn-solid">Enter Portal</Link>
            <Link to="/how-it-works" className="btn-ghost">View Workflow</Link>
          </div>
          <div className="landing-pro-tags" aria-label="Platform highlights">
            <span>Verified Access</span>
            <span>Live Routing</span>
            <span>Audit Ready</span>
          </div>
        </div>
        <div className="landing-pro-visual">
          <img src={heroNetwork} alt="CareFlow visual network of hospitals and coordination signals" className="hero-visual" />
        </div>
      </section>

      <section className="section-wrap landing-pro-metrics">
        {impactItems.map((item) => (
          <article key={item.label} className="landing-pro-metric">
            <h3>{item.value}</h3>
            <p>{item.label}</p>
          </article>
        ))}
      </section>

      <section className="section-wrap landing-pro-capabilities">
        <div className="section-heading">
          <p className="eyebrow">Core Capabilities</p>
          <h2>Everything needed for hospital-to-hospital fulfillment</h2>
        </div>
        <div className="landing-pro-grid">
          {capabilityItems.map((item) => (
            <article key={item.title} className="landing-pro-card">
              <h3>{item.title}</h3>
              <p>{item.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section-wrap landing-pro-process">
        <div className="section-heading">
          <p className="eyebrow">Operational Flow</p>
          <h2>How a critical case moves from request to fulfillment</h2>
        </div>
        <div className="landing-pro-timeline">
          {processItems.map((item) => (
            <article key={item.step} className="landing-pro-step">
              <span>{item.step}</span>
              <div>
                <h3>{item.title}</h3>
                <p>{item.text}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="section-wrap landing-pro-final">
        <div>
          <p className="eyebrow">Ready To Demonstrate Impact?</p>
          <h2>Present a modern, real-world coordination portal with confidence.</h2>
          <p>
            Clean UI, strong process narrative, and measurable operations design in one platform experience.
          </p>
        </div>
        <div className="landing-actions">
          <Link to={startRoute} className="btn-solid">Start Live Demo</Link>
          <Link to="/contact" className="btn-ghost">Contact Team</Link>
        </div>
      </section>
    </div>
  );
}

export default LandingPage;
