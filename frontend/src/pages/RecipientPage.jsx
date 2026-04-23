import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { apiRequest, buildWebSocketUrl } from '../api/client';

const initialRecipient = {
  primary_disease: '',
  diagnosis_date: '2022-01-01',
  surgery_needed_date: '2026-05-01',
  hospital_name: '',
  hospital_contact_phone: '',
  doctor_name: '',
  doctor_phone: '',
  doctor_registration_number: '',
  hospital_verification_document_url: '',
  matching_criteria: {
    urgency: 'CRITICAL',
  },
  profile: {
    first_name: '',
    last_name: '',
    date_of_birth: '1995-01-01',
    gender: 'OTHER',
    address: '',
    city: '',
    state: '',
    postal_code: '',
    country: 'India',
    latitude: '19.0596',
    longitude: '72.8295',
    blood_group: 'AB+',
    emergency_contact_name: '',
    emergency_contact_phone: '',
  },
};

const initialRequest = {
  request_type: 'BLOOD',
  blood_group_needed: 'AB+',
  organ_type_needed: 'KIDNEY',
  quantity_needed: '1',
  urgency_level: 'CRITICAL',
  needed_by: '',
  hospital_name: '',
  receiving_doctor_name: '',
  receiving_doctor_phone: '',
  hospital_location: {
    latitude: '19.0596',
    longitude: '72.8295',
    address: '',
  },
  clinical_notes: '',
  required_tests: 'CBC',
  is_public: true,
};

const pageMeta = {
  profile: {
    title: 'Requesting Hospital Profile',
    blurb: 'Set up the hospital identity, clinical owner, and case intake details.',
  },
  request: {
    title: 'Raise New Requirement',
    blurb: 'Create a blood or organ requirement and send it into the central hospital network.',
  },
  history: {
    title: 'Case History',
    blurb: 'Track every requirement, command-center decision, and fulfillment status.',
  },
};

function formatDate(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}

function getRequestStatusLabel(status) {
  const value = String(status || '').toUpperCase();
  if (value === 'OPEN') return 'Pending Admin Review';
  if (value === 'IN_PROGRESS' || value === 'MATCHED') return 'Approved For Network Fulfillment';
  if (value === 'CANCELLED') return 'Declined By Command Center';
  if (value === 'FULFILLED') return 'Completed';
  if (value === 'EXPIRED') return 'Expired';
  return value || '-';
}

function getRequestStatusTone(status) {
  const value = String(status || '').toUpperCase();
  if (value === 'IN_PROGRESS' || value === 'MATCHED') return 'good';
  if (value === 'CANCELLED' || value === 'EXPIRED') return 'bad';
  return 'warn';
}

function RecipientPage({ view = 'request' }) {
  const { token, setFlash } = useAuth();

  const [recipient, setRecipient] = useState(initialRecipient);
  const [requestForm, setRequestForm] = useState(initialRequest);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [submittingRequest, setSubmittingRequest] = useState(false);
  const [profileExists, setProfileExists] = useState(false);

  const notificationsWsUrl = useMemo(
    () => (token ? buildWebSocketUrl('/ws/notifications', token) : ''),
    [token]
  );

  const activeMeta = pageMeta[view] || pageMeta.request;
  const showProfile = view === 'profile';
  const showRequest = view === 'request';
  const showHistory = view === 'history';
  function updateRecipientProfile(field, value) {
    setRecipient((prev) => ({
      ...prev,
      profile: {
        ...prev.profile,
        [field]: value,
      },
    }));
  }

  function updateRequestForm(field, value) {
    setRequestForm((prev) => ({ ...prev, [field]: value }));
  }

  function updateRequestLocation(field, value) {
    setRequestForm((prev) => ({
      ...prev,
      hospital_location: {
        ...prev.hospital_location,
        [field]: value,
      },
    }));
  }

  async function loadRecipientProfile(silent = false) {
    try {
      const data = await apiRequest('/recipients/me', { token });
      setProfileExists(true);
      setRecipient((prev) => ({
        ...prev,
        primary_disease: data.primary_disease || prev.primary_disease,
        hospital_name: data.hospital_name || prev.hospital_name,
        hospital_contact_phone: data.hospital_contact_phone || prev.hospital_contact_phone,
        doctor_name: data.doctor_name || prev.doctor_name,
        doctor_phone: data.doctor_phone || prev.doctor_phone,
        doctor_registration_number: data.doctor_registration_number || prev.doctor_registration_number,
        hospital_verification_document_url: data.hospital_verification_document_url || prev.hospital_verification_document_url,
        matching_criteria: {
          ...prev.matching_criteria,
          ...(data.matching_criteria || {}),
        },
      }));
      if (!silent) {
        setFlash({ type: 'success', text: 'Requesting hospital profile loaded.' });
      }
    } catch (error) {
      if (error?.status === 404) {
        setProfileExists(false);
        return;
      }
      if (!silent) setFlash({ type: 'error', text: error.message });
    }
  }

  async function loadRequests(silent = false) {
    setLoading(true);
    try {
      const data = await apiRequest('/requests', { token });
      setRequests((data.items || []).sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)));
      if (!silent) {
        setFlash({ type: 'success', text: `Loaded ${data.count || 0} requests.` });
      }
    } catch (error) {
      setFlash({ type: 'error', text: error.message });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!token) return;
    loadRecipientProfile(true);
    loadRequests(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (!token) return undefined;

    const ws = new WebSocket(notificationsWsUrl);
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'SYSTEM_ALERT' || payload.type === 'REQUEST_MATCHED') {
          loadRequests(true);
        }
      } catch (error) {
        // Ignore malformed websocket payloads.
      }
    };

    return () => ws.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, notificationsWsUrl]);

  async function saveRecipientProfile(event) {
    event.preventDefault();
    setSavingProfile(true);

    try {
      const payload = {
        ...recipient,
        profile: {
          ...recipient.profile,
          latitude: Number(recipient.profile.latitude),
          longitude: Number(recipient.profile.longitude),
        },
      };

      await apiRequest('/recipients/register', {
        method: 'POST',
        token,
        body: payload,
      });

      setProfileExists(true);
      setFlash({ type: 'success', text: 'Requesting hospital profile saved.' });
      await loadRecipientProfile(true);
    } catch (error) {
      setFlash({ type: 'error', text: error.message });
    } finally {
      setSavingProfile(false);
    }
  }

  async function submitRequest(event) {
    event.preventDefault();
    setSubmittingRequest(true);

    try {
      const payload = {
        request_type: requestForm.request_type,
        blood_group_needed: requestForm.request_type === 'BLOOD'
          ? requestForm.blood_group_needed
          : requestForm.request_type === 'ORGAN'
            ? requestForm.blood_group_needed
            : undefined,
        organ_type_needed: requestForm.request_type === 'ORGAN' ? requestForm.organ_type_needed : undefined,
        quantity_needed: Number(requestForm.quantity_needed || 1),
        urgency_level: requestForm.urgency_level,
        needed_by: new Date(requestForm.needed_by).toISOString(),
        hospital_name: requestForm.hospital_name,
        receiving_doctor_name: requestForm.receiving_doctor_name,
        receiving_doctor_phone: requestForm.receiving_doctor_phone,
        hospital_location: {
          latitude: Number(requestForm.hospital_location.latitude),
          longitude: Number(requestForm.hospital_location.longitude),
          address: requestForm.hospital_location.address,
        },
        clinical_notes: requestForm.clinical_notes,
        required_tests: requestForm.required_tests
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
        is_public: requestForm.is_public,
      };

      const data = await apiRequest('/requests', {
        method: 'POST',
        token,
        body: payload,
      });

      setFlash({
        type: 'success',
        text: `Requirement sent to command center and matching hospitals. Current status: ${getRequestStatusLabel(data.request?.status)}`,
      });
      await loadRequests(true);
    } catch (error) {
      setFlash({ type: 'error', text: error.message });
    } finally {
      setSubmittingRequest(false);
    }
  }

  const profileFields = (
    <>
      <label className="recipient-field">
        <span>Primary Condition</span>
        <input value={recipient.primary_disease} onChange={(e) => setRecipient((prev) => ({ ...prev, primary_disease: e.target.value }))} required />
      </label>
      <label className="recipient-field">
        <span>Requesting Hospital</span>
        <input value={recipient.hospital_name} onChange={(e) => setRecipient((prev) => ({ ...prev, hospital_name: e.target.value }))} required />
      </label>
      <label className="recipient-field">
        <span>Hospital Contact Phone</span>
        <input value={recipient.hospital_contact_phone} onChange={(e) => setRecipient((prev) => ({ ...prev, hospital_contact_phone: e.target.value }))} required />
      </label>
      <label className="recipient-field">
        <span>Clinical Lead</span>
        <input value={recipient.doctor_name} onChange={(e) => setRecipient((prev) => ({ ...prev, doctor_name: e.target.value }))} required />
      </label>
      <label className="recipient-field">
        <span>Clinical Lead Phone</span>
        <input value={recipient.doctor_phone} onChange={(e) => setRecipient((prev) => ({ ...prev, doctor_phone: e.target.value }))} required />
      </label>
      <label className="recipient-field">
        <span>Doctor Registration Number</span>
        <input value={recipient.doctor_registration_number} onChange={(e) => setRecipient((prev) => ({ ...prev, doctor_registration_number: e.target.value }))} required />
      </label>
      <label className="recipient-field recipient-field-wide">
        <span>Hospital Verification Document URL</span>
        <input
          value={recipient.hospital_verification_document_url}
          onChange={(e) => setRecipient((prev) => ({ ...prev, hospital_verification_document_url: e.target.value }))}
          placeholder="https://hospital.example/verification-doc.pdf"
        />
      </label>
      <label className="recipient-field">
        <span>First Name</span>
        <input value={recipient.profile.first_name} onChange={(e) => updateRecipientProfile('first_name', e.target.value)} required />
      </label>
      <label className="recipient-field">
        <span>Last Name</span>
        <input value={recipient.profile.last_name} onChange={(e) => updateRecipientProfile('last_name', e.target.value)} required />
      </label>
      <label className="recipient-field">
        <span>City</span>
        <input value={recipient.profile.city} onChange={(e) => updateRecipientProfile('city', e.target.value)} required />
      </label>
      <label className="recipient-field">
        <span>State</span>
        <input value={recipient.profile.state} onChange={(e) => updateRecipientProfile('state', e.target.value)} required />
      </label>
      <label className="recipient-field">
        <span>Address</span>
        <input value={recipient.profile.address} onChange={(e) => updateRecipientProfile('address', e.target.value)} required />
      </label>
      <label className="recipient-field">
        <span>Blood Group</span>
        <select value={recipient.profile.blood_group} onChange={(e) => updateRecipientProfile('blood_group', e.target.value)}>
          <option value="O+">O+</option>
          <option value="O-">O-</option>
          <option value="A+">A+</option>
          <option value="A-">A-</option>
          <option value="B+">B+</option>
          <option value="B-">B-</option>
          <option value="AB+">AB+</option>
          <option value="AB-">AB-</option>
        </select>
      </label>
    </>
  );

  const requestFields = (
    <>
      <label className="recipient-field">
        <span>Request Type</span>
        <select value={requestForm.request_type} onChange={(e) => updateRequestForm('request_type', e.target.value)}>
          <option value="BLOOD">Blood</option>
          <option value="ORGAN">Organ</option>
        </select>
      </label>
      {['BLOOD', 'ORGAN'].includes(requestForm.request_type) && (
        <label className="recipient-field">
          <span>Blood Group Needed</span>
          <select value={requestForm.blood_group_needed} onChange={(e) => updateRequestForm('blood_group_needed', e.target.value)}>
            {requestForm.request_type === 'ORGAN' && <option value="ANY">ANY (Emergency Flexible)</option>}
            <option value="O+">O+</option>
            <option value="O-">O-</option>
            <option value="A+">A+</option>
            <option value="A-">A-</option>
            <option value="B+">B+</option>
            <option value="B-">B-</option>
            <option value="AB+">AB+</option>
            <option value="AB-">AB-</option>
          </select>
        </label>
      )}
      {requestForm.request_type === 'ORGAN' && (
        <label className="recipient-field">
          <span>Organ Needed</span>
          <select value={requestForm.organ_type_needed} onChange={(e) => updateRequestForm('organ_type_needed', e.target.value)}>
            <option value="ANY">ANY (Emergency)</option>
            <option value="KIDNEY">Kidney</option>
            <option value="LIVER">Liver</option>
            <option value="HEART">Heart</option>
            <option value="LUNG">Lung</option>
            <option value="PANCREAS">Pancreas</option>
            <option value="CORNEA">Cornea</option>
          </select>
        </label>
      )}
      <label className="recipient-field">
        <span>Units / Quantity Needed</span>
        <input type="number" min="1" value={requestForm.quantity_needed} onChange={(e) => updateRequestForm('quantity_needed', e.target.value)} />
      </label>
      <label className="recipient-field">
        <span>Urgency</span>
        <select value={requestForm.urgency_level} onChange={(e) => updateRequestForm('urgency_level', e.target.value)}>
          <option value="LOW">Low</option>
          <option value="MEDIUM">Medium</option>
          <option value="CRITICAL">Critical</option>
        </select>
      </label>
      <label className="recipient-field">
        <span>Need By</span>
        <input type="datetime-local" value={requestForm.needed_by} onChange={(e) => updateRequestForm('needed_by', e.target.value)} required />
      </label>
      <label className="recipient-field">
        <span>Receiving Hospital</span>
        <input value={requestForm.hospital_name} onChange={(e) => updateRequestForm('hospital_name', e.target.value)} required />
      </label>
      <label className="recipient-field">
        <span>Receiving Doctor</span>
        <input value={requestForm.receiving_doctor_name} onChange={(e) => updateRequestForm('receiving_doctor_name', e.target.value)} required />
      </label>
      <label className="recipient-field">
        <span>Receiving Doctor Phone</span>
        <input value={requestForm.receiving_doctor_phone} onChange={(e) => updateRequestForm('receiving_doctor_phone', e.target.value)} required />
      </label>
      <label className="recipient-field recipient-field-wide">
        <span>Receiving Hospital Address</span>
        <input value={requestForm.hospital_location.address} onChange={(e) => updateRequestLocation('address', e.target.value)} required />
      </label>
      <label className="recipient-field recipient-field-wide">
        <span>Clinical Notes And Transfer Context</span>
        <textarea rows={3} value={requestForm.clinical_notes} onChange={(e) => updateRequestForm('clinical_notes', e.target.value)} />
      </label>
      <label className="recipient-field recipient-field-wide">
        <span>Required Tests / Compatibility Checks</span>
        <input
          value={requestForm.required_tests}
          onChange={(e) => updateRequestForm('required_tests', e.target.value)}
          placeholder="CBC, Crossmatch"
        />
      </label>
      <div className="recipient-field recipient-field-wide">
        <span>Location Coordinates</span>
        <div className="recipient-inline-grid">
          <input value={requestForm.hospital_location.latitude} onChange={(e) => updateRequestLocation('latitude', e.target.value)} placeholder="Latitude" required />
          <input value={requestForm.hospital_location.longitude} onChange={(e) => updateRequestLocation('longitude', e.target.value)} placeholder="Longitude" required />
        </div>
      </div>
    </>
  );

  return (
    <section className="recipient-page">
      {showProfile && (
        <article className="recipient-panel">
          <div className="recipient-panel-head">
            <div>
              <p className="eyebrow">Requesting Hospital Workspace</p>
              <h2>{activeMeta.title}</h2>
              <p className="muted-text">{activeMeta.blurb}</p>
            </div>
            {!profileExists && (
              <div className="recipient-hero-chips">
                <span className="status-chip warn">Profile not set</span>
              </div>
            )}
          </div>

          <form onSubmit={saveRecipientProfile} className="recipient-form-grid recipient-form-grid-two">
            {profileFields}
            <div className="recipient-actions recipient-field-wide">
              <button type="submit" className="recipient-primary-btn" disabled={savingProfile}>
                {savingProfile ? 'Saving...' : 'Save Hospital Profile'}
              </button>
            </div>
          </form>
        </article>
      )}

      {showRequest && (
        <article className="recipient-panel">
          <div className="recipient-panel-head">
            <div>
              <p className="eyebrow">Requesting Hospital Workspace</p>
              <h2>{activeMeta.title}</h2>
              <p className="muted-text">{activeMeta.blurb}</p>
            </div>
            <div className="tab-row">
              <button type="button" onClick={() => loadRequests(false)} disabled={loading}>Refresh Cases</button>
            </div>
          </div>

          {!profileExists && (
            <div className="recipient-notice">
              <strong>Requesting hospital profile missing.</strong>
              <span>Create the hospital profile first to submit a requirement.</span>
              <Link to="/recipient/profile">Go to Hospital Profile</Link>
            </div>
          )}

          <form onSubmit={submitRequest} className="recipient-form-grid recipient-form-grid-two">
            {requestFields}
            <div className="recipient-actions recipient-field-wide">
              <button type="submit" className="recipient-primary-btn" disabled={submittingRequest}>
                {submittingRequest ? 'Sending...' : 'Send Requirement To Command Center'}
              </button>
            </div>
          </form>
        </article>
      )}

      {showHistory && (
        <article className="recipient-panel recipient-history-panel">
          <div className="recipient-panel-head recipient-history-head">
            <div>
              <p className="eyebrow">Requesting Hospital Workspace</p>
              <h2>{activeMeta.title}</h2>
              <p className="muted-text">{activeMeta.blurb}</p>
            </div>

            <div className="recipient-history-summary">
              <span className="status-chip warn">Open: {requests.filter((item) => String(item.status).toUpperCase() === 'OPEN').length}</span>
              <span className="status-chip good">Reviewed: {requests.filter((item) => ['IN_PROGRESS', 'MATCHED', 'CANCELLED', 'FULFILLED'].includes(String(item.status).toUpperCase())).length}</span>
              <button type="button" onClick={() => loadRequests(false)} disabled={loading}>Reload</button>
            </div>
          </div>

          {requests.length === 0 ? (
            <div className="recipient-empty-state">
              <strong>No requirements yet.</strong>
              <span>Raise one using the request page.</span>
            </div>
          ) : (
            <div className="recipient-history-table-shell table-shell">
              <table className="data-table recipient-table recipient-history-table">
                <thead>
                  <tr>
                    <th>Case ID</th>
                    <th>Requirement Details</th>
                    <th>Hospital</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Needed By</th>
                  </tr>
                </thead>
                <tbody>
                  {requests.map((item) => (
                    <tr key={item.id}>
                      <td className="history-id-cell">{item.id}</td>
                      <td className="history-details-cell">
                        <strong>{item.request_type}</strong>
                        <span>
                          {item.request_type === 'BLOOD'
                            ? `Blood group: ${item.blood_group_needed || '-'}`
                            : `Organ: ${item.organ_type_needed || '-'} | Blood: ${item.blood_group_needed || '-'}`
                          }
                        </span>
                        <span>Urgency: {item.urgency_level}</span>
                      </td>
                      <td>{item.hospital_name || '-'}</td>
                      <td>
                        <span className={`status-chip ${getRequestStatusTone(item.status)}`}>
                          {getRequestStatusLabel(item.status)}
                        </span>
                      </td>
                      <td>{formatDate(item.created_at)}</td>
                      <td>{formatDate(item.needed_by)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>
      )}
    </section>
  );
}

export default RecipientPage;
