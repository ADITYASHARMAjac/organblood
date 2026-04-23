import React from 'react';

const workflowSteps = [
  {
    title: '1. Register and Verify',
    detail: 'Users sign up, complete OTP checks, and gain role-specific access to secure workflows.',
  },
  {
    title: '2. Build Medical Profile',
    detail: 'Donors and recipients enter profile details used for accurate compatibility and routing.',
  },
  {
    title: '3. Create and Match Requests',
    detail: 'Recipients create urgent blood or organ requests. Matching services identify potential donors.',
  },
  {
    title: '4. Notify and Coordinate',
    detail: 'Notifications and live events keep stakeholders informed through every critical update.',
  },
  {
    title: '5. Govern and Improve',
    detail: 'Admins verify users, review analytics, and enforce platform safety and policy actions.',
  },
];

function HowItWorksPage() {
  return (
    <section className="section-wrap content-page">
      <p className="eyebrow">How It Works</p>
      <h1>Purpose-built journeys for every role</h1>
      <p>
        The portal is not a static website. It is an operational system with clear role-based tracks
        for donors, recipients, and administrators.
      </p>

      <div className="timeline-grid">
        {workflowSteps.map((step) => (
          <article key={step.title} className="timeline-card">
            <h3>{step.title}</h3>
            <p>{step.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export default HowItWorksPage;
