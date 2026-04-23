import React from 'react';
import { Link } from 'react-router-dom';
import aboutOperations from '../assets/about-operations.svg';

const principles = [
  {
    title: 'Safety First',
    text: 'User verification, role boundaries, and controlled actions are built into each operational workflow.',
  },
  {
    title: 'Clinical Urgency',
    text: 'We design around emergency timelines so requests and matches move faster when minutes matter.',
  },
  {
    title: 'Data Visibility',
    text: 'Teams get a single source of truth for requests, status changes, notifications, and governance decisions.',
  },
  {
    title: 'Scalable Operations',
    text: 'CareFlow supports local teams while remaining extensible for district and state-level coordination.',
  },
];

function AboutPage() {
  return (
    <>
      <section className="section-wrap content-page">
        <p className="eyebrow">About CareFlow</p>
        <h1>Built for trust, urgency, and medical coordination</h1>
        <p>
          CareFlow improves how donation ecosystems operate. The platform gives donors,
          recipients, hospitals, and administrators a structured process with clear actions,
          transparent statuses, and live communication.
        </p>
      </section>

      <section className="section-wrap image-band">
        <img src={aboutOperations} alt="Operational workflow showing verification, matching, and governance" className="about-image" />
      </section>

      <section className="section-wrap">
        <div className="section-heading">
          <p className="eyebrow">Our Mission</p>
          <h2>Reduce friction in life-critical donation journeys</h2>
        </div>
        <div className="content-grid">
          <article className="content-card">
            <h3>Why this platform exists</h3>
            <p>
              Donation cases are time-sensitive and often fragmented across calls, spreadsheets,
              and manual follow-ups. We centralize those steps into one workflow-driven portal.
            </p>
          </article>
          <article className="content-card">
            <h3>Who can use it</h3>
            <p>
              Donors register and update availability, recipients submit urgent requests,
              and administrators verify users while monitoring platform health and analytics.
            </p>
          </article>
          <article className="content-card">
            <h3>What makes it reliable</h3>
            <p>
              Identity checks, role-based access, audit-friendly actions, and controlled admin tools
              help teams make decisions with confidence.
            </p>
          </article>
        </div>
      </section>

      <section className="section-wrap">
        <div className="section-heading">
          <p className="eyebrow">Core Principles</p>
          <h2>How we design and operate</h2>
        </div>
        <div className="feature-grid">
          {principles.map((item) => (
            <article key={item.title} className="feature-card">
              <h3>{item.title}</h3>
              <p>{item.text}</p>
            </article>
          ))}
        </div>
        <div className="landing-actions top-space">
          <Link to="/how-it-works" className="btn-ghost">View Full Workflow</Link>
          <Link to="/contact" className="btn-solid">Contact Our Team</Link>
        </div>
      </section>
    </>
  );
}

export default AboutPage;
