import React, { useMemo, useState } from 'react';
import eligibilityIllustration from '../assets/eligibility-check.svg';

const initialState = {
  userType: 'DONOR',
  age: '',
  weight: '',
  hasRecentSurgery: 'no',
  hasInfectionSymptoms: 'no',
  bloodGroup: 'O+',
};

function evaluateEligibility(form) {
  const age = Number(form.age);
  const weight = Number(form.weight);

  if (!Number.isFinite(age) || !Number.isFinite(weight)) {
    return {
      status: 'Incomplete',
      detail: 'Please provide age and weight to get a useful recommendation.',
      tone: 'neutral',
    };
  }

  if (form.userType === 'DONOR') {
    if (age < 18 || age > 65) {
      return {
        status: 'Not Ready Yet',
        detail: 'Typical donor age range is 18-65. Please consult your medical team for exceptions.',
        tone: 'warn',
      };
    }

    if (weight < 50) {
      return {
        status: 'Further Medical Review Needed',
        detail: 'Minimum healthy donor thresholds often require at least 50kg body weight.',
        tone: 'warn',
      };
    }

    if (form.hasRecentSurgery === 'yes' || form.hasInfectionSymptoms === 'yes') {
      return {
        status: 'Temporary Hold Recommended',
        detail: 'Recent surgery or infection symptoms usually require a recovery period and clinician approval.',
        tone: 'warn',
      };
    }

    return {
      status: 'Likely Eligible',
      detail: 'You appear broadly eligible. Complete profile verification and consult medical staff for final clearance.',
      tone: 'good',
    };
  }

  if (form.hasInfectionSymptoms === 'yes') {
    return {
      status: 'Priority Medical Evaluation',
      detail: 'Please consult your treating physician immediately before initiating a request workflow.',
      tone: 'warn',
    };
  }

  return {
    status: 'Ready For Request Intake',
    detail: 'You can proceed to recipient onboarding and create a request for compatibility review.',
    tone: 'good',
  };
}

function EligibilityPage() {
  const [form, setForm] = useState(initialState);

  const result = useMemo(() => evaluateEligibility(form), [form]);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  return (
    <>
      <section className="section-wrap content-page">
        <p className="eyebrow">Eligibility Checker</p>
        <h1>Quick pre-check for donors and recipients</h1>
        <p>
          This assistant helps users understand next steps before they enter full portal workflows.
          It does not replace clinical advice and should be used for orientation only.
        </p>
      </section>

      <section className="section-wrap image-band">
        <img
          src={eligibilityIllustration}
          alt="Eligibility checks for health and compatibility guidance"
          className="about-image"
        />
      </section>

      <section className="section-wrap">
        <div className="contact-grid">
          <form className="panel form-panel" onSubmit={(event) => event.preventDefault()}>
            <label>
              User Type
              <select value={form.userType} onChange={(e) => updateField('userType', e.target.value)}>
                <option value="DONOR">Donor</option>
                <option value="RECIPIENT">Recipient</option>
              </select>
            </label>
            <label>
              Age
              <input
                type="number"
                min="1"
                max="120"
                value={form.age}
                onChange={(e) => updateField('age', e.target.value)}
              />
            </label>
            <label>
              Weight (kg)
              <input
                type="number"
                min="1"
                max="300"
                value={form.weight}
                onChange={(e) => updateField('weight', e.target.value)}
              />
            </label>
            <label>
              Blood Group
              <select value={form.bloodGroup} onChange={(e) => updateField('bloodGroup', e.target.value)}>
                <option>O+</option>
                <option>O-</option>
                <option>A+</option>
                <option>A-</option>
                <option>B+</option>
                <option>B-</option>
                <option>AB+</option>
                <option>AB-</option>
              </select>
            </label>
            <label>
              Recent surgery in last 6 months?
              <select
                value={form.hasRecentSurgery}
                onChange={(e) => updateField('hasRecentSurgery', e.target.value)}
              >
                <option value="no">No</option>
                <option value="yes">Yes</option>
              </select>
            </label>
            <label>
              Infection symptoms right now?
              <select
                value={form.hasInfectionSymptoms}
                onChange={(e) => updateField('hasInfectionSymptoms', e.target.value)}
              >
                <option value="no">No</option>
                <option value="yes">Yes</option>
              </select>
            </label>
          </form>

          <aside className={`panel eligibility-result ${result.tone}`}>
            <h3>{result.status}</h3>
            <p>{result.detail}</p>
            <p className="muted-text">
              Suggested next step: proceed to authentication and complete profile verification for final
              operational readiness.
            </p>
          </aside>
        </div>
      </section>
    </>
  );
}

export default EligibilityPage;
