import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { apiRequest, buildWebSocketUrl } from '../api/client';

const bloodGroupOptions = ['ALL', 'O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-'];
const organTypeOptions = ['ALL', 'KIDNEY', 'LIVER', 'HEART', 'LUNG', 'PANCREAS', 'CORNEA'];

function byCreatedDesc(a, b) {
  return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
}

function formatDate(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}

function getRiskLabel(verification) {
  const risk = String(verification?.risk_level || '').toUpperCase();
  if (risk === 'HIGH') return 'High Risk';
  if (risk === 'MEDIUM') return 'Needs Review';
  return 'Low Risk';
}

function getRiskTone(verification) {
  const risk = String(verification?.risk_level || '').toUpperCase();
  if (risk === 'HIGH') return 'bad';
  if (risk === 'MEDIUM') return 'warn';
  return 'good';
}

function AdminPage({ view = 'recipient-requests' }) {
  const { token, setFlash } = useAuth();
  const navigate = useNavigate();
  const adminNotificationsWsUrl = useMemo(
    () => (token ? buildWebSocketUrl('/ws/notifications', token) : ''),
    [token]
  );

  const [loading, setLoading] = useState(false);
  const [requests, setRequests] = useState([]);
  const [donorRequests, setDonorRequests] = useState([]);
  const [scheduleRequests, setScheduleRequests] = useState([]);
  const [requestStatus, setRequestStatus] = useState('OPEN');
  const [requestType, setRequestType] = useState('ALL');
  const [requestUrgency, setRequestUrgency] = useState('ALL');
  const [requestSearch, setRequestSearch] = useState('');
  const [donorRequestType, setDonorRequestType] = useState('ALL');
  const [donorBloodGroup, setDonorBloodGroup] = useState('ALL');
  const [donorOrganType, setDonorOrganType] = useState('ALL');
  const [donorRequestSearch, setDonorRequestSearch] = useState('');
  const [scheduleSearch, setScheduleSearch] = useState('');
  const [notifications, setNotifications] = useState([]);

  const pageMeta = {
    'recipient-requests': {
      title: 'Requesting Hospital Cases',
      blurb: 'Review inbound hospital requirements and decide whether they should enter the network workflow.',
    },
    'donor-requests': {
      title: 'Fulfilling Hospital Responses',
      blurb: 'Review hospital-side fulfillment responses and approve or reject the handover.',
    },
    schedules: {
      title: 'Transfer Schedules',
      blurb: 'Track approved inter-hospital handovers and scheduling details.',
    },
  };

  const activeMeta = pageMeta[view] || pageMeta['recipient-requests'];
  const showRecipientRequests = view === 'recipient-requests';
  const showDonorRequests = view === 'donor-requests';
  const showSchedules = view === 'schedules';

  useEffect(() => {
    refreshForView(view);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view]);

  useEffect(() => {
    if (!token) return undefined;

    const ws = new WebSocket(adminNotificationsWsUrl);
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'SYSTEM_ALERT' || payload.type === 'REQUEST_MATCHED') {
          if (view === 'recipient-requests') {
            loadRecipientRequests(true);
          }
          if (view === 'donor-requests') {
            loadDonorRequests(true);
          }
          if (view === 'schedules') {
            loadSchedules(true);
          }
          loadNotifications(true);
        }
      } catch (error) {
        // Ignore malformed websocket payloads.
      }
    };

    return () => ws.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, view, adminNotificationsWsUrl]);

  async function refreshForView(nextView) {
    setLoading(true);
    try {
      if (nextView === 'recipient-requests') {
        await loadRecipientRequests(true);
        return;
      }
      if (nextView === 'donor-requests') {
        await loadDonorRequests(true);
        return;
      }
      if (nextView === 'schedules') {
        await loadSchedules(true);
        return;
      }
      await loadNotifications(true);
    } catch (error) {
      setFlash({ type: 'error', text: error.message });
    } finally {
      setLoading(false);
    }
  }

  async function loadRecipientRequests(silent = false) {
    const data = await apiRequest('/admin/requests?limit=250', { token });
    const sorted = [...(data.items || [])].sort(byCreatedDesc);
    setRequests(sorted);
    if (!silent) setFlash({ type: 'success', text: `Loaded ${sorted.length} requesting hospital cases.` });
  }

  async function loadDonorRequests(silent = false) {
    const data = await apiRequest('/admin/donor-requests?limit=250', { token });
    const sorted = [...(data.items || [])].sort(byCreatedDesc);
    setDonorRequests(sorted);
    if (!silent) setFlash({ type: 'success', text: `Loaded ${sorted.length} fulfilling hospital responses.` });
  }

  async function loadSchedules(silent = false) {
    const data = await apiRequest('/admin/schedules?limit=250', { token });
    const sorted = [...(data.items || [])].sort(byCreatedDesc);
    setScheduleRequests(sorted);
    if (!silent) setFlash({ type: 'success', text: `Loaded ${sorted.length} transfer schedules.` });
  }

  async function loadNotifications(silent = false) {
    const data = await apiRequest('/notifications/me?unread_only=true&limit=50', { token });
    setNotifications(data.items || []);
    if (!silent) setFlash({ type: 'success', text: `Loaded ${data.count || 0} unread notifications.` });
  }

  async function acceptRequestByAdmin(requestId) {
    if (!requestId) return;
    const reason = 'Requirement reviewed and approved for network processing.';
    const data = await apiRequest(`/admin/requests/${requestId}/accept`, {
      method: 'POST',
      token,
      body: { reason, details: reason },
    });
    setFlash({ type: 'success', text: `Case approved. Generated ${data.matches_found || 0} network matches.` });
    await loadRecipientRequests(true);
    navigate('/admin/schedules');
  }

  async function rejectRequestByAdmin(requestId) {
    if (!requestId) return;
    const reason = 'Requirement rejected by command center.';
    await apiRequest(`/admin/requests/${requestId}/block`, {
      method: 'POST',
      token,
      body: { reason, details: reason },
    });
    setFlash({ type: 'success', text: 'Case rejected successfully.' });
    await loadRecipientRequests(true);
  }

  async function reviewDonorRequest(matchId, decision) {
    if (!matchId) return;
    const reason = decision === 'accept'
      ? 'Fulfilling hospital response approved by command center.'
      : 'Fulfilling hospital response rejected by command center.';
    await apiRequest(`/admin/donor-requests/${matchId}/${decision}`, {
      method: 'POST',
      token,
      body: { reason, details: reason },
    });
    setFlash({ type: 'success', text: decision === 'accept' ? 'Fulfilling hospital response approved.' : 'Fulfilling hospital response rejected.' });
    await loadDonorRequests(true);
    if (decision === 'accept') {
      await loadSchedules(true);
      navigate('/admin/schedules');
    }
  }

  const filteredRequests = useMemo(() => {
    const needle = requestSearch.trim().toLowerCase();
    return requests.filter((item) => {
      const status = String(item.status || '').toUpperCase();
      const type = String(item.request_type || '').toUpperCase();
      const urgency = String(item.urgency_level || '').toUpperCase();

      if (requestStatus !== 'ALL' && status !== requestStatus) return false;
      if (requestType !== 'ALL' && type !== requestType) return false;
      if (requestUrgency !== 'ALL' && urgency !== requestUrgency) return false;
      if (!needle) return true;

      const haystack = [
        item.request_id,
        item.recipient_name,
        item.request_type,
        item.hospital_name,
        item.urgency_level,
        item.status,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return haystack.includes(needle);
    });
  }, [requestSearch, requestStatus, requestType, requestUrgency, requests]);

  const filteredDonorRequests = useMemo(() => {
    const needle = donorRequestSearch.trim().toLowerCase();
    return donorRequests.filter((item) => {
      const requestType = String(item.request_type || '').toUpperCase();
      const bloodGroup = String(item.blood_group_needed || '').toUpperCase();
      const organType = String(item.organ_type_needed || '').toUpperCase();

      if (donorRequestType !== 'ALL' && requestType !== donorRequestType) return false;
      if (donorBloodGroup !== 'ALL' && bloodGroup !== donorBloodGroup) return false;
      if (donorOrganType !== 'ALL' && organType !== donorOrganType) return false;
      if (!needle) return true;
      const haystack = [
        item.match_id,
        item.request_id,
        item.request_type,
        item.donor_name,
        item.hospital_name,
        item.admin_review_status,
        item.donor_response,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return haystack.includes(needle);
    });
  }, [donorBloodGroup, donorOrganType, donorRequestSearch, donorRequestType, donorRequests]);

  const filteredSchedules = useMemo(() => {
    const needle = scheduleSearch.trim().toLowerCase();
    return scheduleRequests.filter((item) => {
      if (!needle) return true;
      const haystack = [
        item.match_id,
        item.request_id,
        item.request_type,
        item.donor_name,
        item.hospital_name,
        item.request_status,
        item.admin_review_status,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return haystack.includes(needle);
    });
  }, [scheduleRequests, scheduleSearch]);

  return (
    <section className="admin-page">
      {showRecipientRequests && (
        <article className="admin-section recipient-request-table-page">
          <div className="admin-section-head">
            <div>
              <p className="eyebrow">Central Command Workspace</p>
              <h3>{activeMeta.title}</h3>
            </div>
            <div className="tab-row">
              <button onClick={() => loadRecipientRequests(false)} disabled={loading}>Refresh Cases</button>
            </div>
          </div>

          <div className="admin-filter-grid recipient-filter-grid">
            <label className="filter-field">
              <span>Status</span>
              <select value={requestStatus} onChange={(e) => setRequestStatus(e.target.value)}>
                <option value="ALL">All Status</option>
                <option value="OPEN">Open</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="MATCHED">Matched</option>
                <option value="FULFILLED">Fulfilled</option>
                <option value="CANCELLED">Cancelled</option>
                <option value="EXPIRED">Expired</option>
              </select>
            </label>
            <label className="filter-field">
              <span>Type</span>
              <select value={requestType} onChange={(e) => setRequestType(e.target.value)}>
                <option value="ALL">All Types</option>
                <option value="BLOOD">Blood</option>
                <option value="ORGAN">Organ</option>
                <option value="PLASMA">Plasma</option>
              </select>
            </label>
            <label className="filter-field">
              <span>Urgency</span>
              <select value={requestUrgency} onChange={(e) => setRequestUrgency(e.target.value)}>
                <option value="ALL">All Urgency</option>
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </label>
            <label className="filter-field filter-field-search">
              <span>Search</span>
              <input
                placeholder="Case id, hospital, request type"
                value={requestSearch}
                onChange={(e) => setRequestSearch(e.target.value)}
              />
            </label>
          </div>

          <div className="table-shell edge-to-edge-table-shell">
            <table className="data-table admin-table recipient-request-table">
              <thead>
                <tr>
                  <th>Case ID</th>
                  <th>Requesting Hospital</th>
                  <th>Type</th>
                  <th>Hospital</th>
                  <th>Urgency</th>
                  <th>Verification</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredRequests.map((item) => (
                  <tr key={item.request_id}>
                    <td>{item.request_id}</td>
                    <td>{item.recipient_name || '-'}</td>
                    <td>{item.request_type}</td>
                    <td>{item.hospital_name || 'Unknown Hospital'}</td>
                    <td>{item.urgency_level}</td>
                    <td>
                      <span className={`status-chip ${getRiskTone(item.verification)}`}>
                        {getRiskLabel(item.verification)}
                      </span>
                    </td>
                    <td>{item.status}</td>
                    <td>{formatDate(item.created_at)}</td>
                    <td>
                      <div className="tab-row">
                        <button
                          onClick={() => acceptRequestByAdmin(item.request_id)}
                          disabled={
                            String(item.status).toUpperCase() !== 'OPEN' ||
                            String(item?.verification?.risk_level || '').toUpperCase() === 'HIGH'
                          }
                        >
                          Approve
                        </button>
                        <button
                          className="danger"
                          onClick={() => rejectRequestByAdmin(item.request_id)}
                          disabled={String(item.status).toUpperCase() !== 'OPEN'}
                        >
                          Decline
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {filteredRequests.length === 0 && <p className="muted-text">No requesting hospital cases available.</p>}
        </article>
      )}

      {showDonorRequests && (
        <article className="admin-section donor-request-page">
          <div className="admin-section-head">
            <h3>Fulfilling Hospital Responses</h3>
            <div className="tab-row">
              <button onClick={() => loadDonorRequests(false)} disabled={loading}>Refresh Responses</button>
            </div>
          </div>

          <div className="admin-filter-grid donor-filter-grid">
            <label className="filter-field">
              <span>Request Type</span>
              <select value={donorRequestType} onChange={(e) => setDonorRequestType(e.target.value)}>
                <option value="ALL">All Types</option>
                <option value="BLOOD">Blood</option>
                <option value="ORGAN">Organ</option>
                <option value="PLASMA">Plasma</option>
              </select>
            </label>
            <label className="filter-field">
              <span>Blood Group</span>
              <select
                value={donorBloodGroup}
                onChange={(e) => setDonorBloodGroup(e.target.value)}
                disabled={donorRequestType === 'ORGAN'}
              >
                {bloodGroupOptions.map((item) => <option key={item} value={item}>{item === 'ALL' ? 'All Blood Groups' : item}</option>)}
              </select>
            </label>
            <label className="filter-field">
              <span>Organ Type</span>
              <select
                value={donorOrganType}
                onChange={(e) => setDonorOrganType(e.target.value)}
                disabled={donorRequestType === 'BLOOD' || donorRequestType === 'PLASMA'}
              >
                {organTypeOptions.map((item) => <option key={item} value={item}>{item === 'ALL' ? 'All Organs' : item}</option>)}
              </select>
            </label>
            <label className="filter-field filter-field-search">
              <span>Search</span>
              <input
                placeholder="Hospital, case id, location"
                value={donorRequestSearch}
                onChange={(e) => setDonorRequestSearch(e.target.value)}
              />
            </label>
          </div>

          <div className="section-divider" />

          {filteredDonorRequests.length > 0 && (
            <div className="table-shell">
              <table className="data-table admin-table">
                <thead>
                  <tr>
                    <th>Case ID</th>
                    <th>Fulfilling Hospital</th>
                    <th>Hospital</th>
                    <th>Type</th>
                    <th>Score</th>
                    <th>Donor Trust</th>
                    <th>Request Trust</th>
                    <th>Command Review</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDonorRequests.map((item) => {
                    const reviewStatus = String(item.admin_review_status || 'PENDING').toUpperCase();
                    return (
                    <tr key={item.match_id}>
                      <td>{item.request_id}</td>
                      <td>{item.donor_name}</td>
                      <td>{item.hospital_name || '-'}</td>
                      <td>{item.request_type}</td>
                      <td>{Number(item.compatibility_score || 0).toFixed(2)}</td>
                      <td>
                        <span className={`status-chip ${getRiskTone(item.donor_verification)}`}>
                          {getRiskLabel(item.donor_verification)}
                        </span>
                      </td>
                      <td>
                        <span className={`status-chip ${getRiskTone(item.request_verification)}`}>
                          {getRiskLabel(item.request_verification)}
                        </span>
                      </td>
                      <td>{reviewStatus}</td>
                      <td>
                        <div className="tab-row">
                          <button
                            onClick={() => reviewDonorRequest(item.match_id, 'accept')}
                            disabled={reviewStatus !== 'PENDING'}
                          >
                            Approve
                          </button>
                          <button
                            className="danger"
                            onClick={() => reviewDonorRequest(item.match_id, 'reject')}
                            disabled={reviewStatus !== 'PENDING'}
                          >
                            Decline
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {filteredDonorRequests.length === 0 && <p className="muted-text">No fulfilling hospital responses match current filters.</p>}
        </article>
      )}

      {showSchedules && (
        <article className="admin-section donor-request-page">
          <div className="admin-section-head">
            <h3>Transfer Schedules</h3>
            <div className="tab-row">
              <button onClick={() => loadSchedules(false)} disabled={loading}>Refresh Schedules</button>
            </div>
          </div>

          <div className="admin-filter-grid donor-filter-grid">
            <label className="filter-field filter-field-search">
              <span>Search</span>
              <input
                placeholder="Case id, hospital, doctor"
                value={scheduleSearch}
                onChange={(e) => setScheduleSearch(e.target.value)}
              />
            </label>
          </div>

          <div className="section-divider" />

          {filteredSchedules.length > 0 ? (
            <div className="table-shell">
              <table className="data-table admin-table">
                <thead>
                  <tr>
                    <th>Case ID</th>
                    <th>Fulfilling Hospital</th>
                    <th>Hospital</th>
                    <th>Doctor</th>
                    <th>Type</th>
                    <th>Score</th>
                    <th>Distance</th>
                    <th>Trust</th>
                    <th>Approval</th>
                    <th>Approved At</th>
                    <th>Scheduled At</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSchedules.map((item) => (
                    <tr key={item.match_id}>
                      <td>{item.request_id}</td>
                      <td>
                        <div>{item.donor_name}</div>
                        <div className="muted-cell">{item.donor_blood_group || '-'}</div>
                      </td>
                      <td>{item.hospital_name || '-'}</td>
                      <td>
                        <div>{item.receiving_doctor_name || '-'}</div>
                        <div className="muted-cell">{item.receiving_doctor_phone || '-'}</div>
                      </td>
                      <td>{item.request_type || '-'}</td>
                      <td>{Number(item.compatibility_score || 0).toFixed(2)}</td>
                      <td>{Number(item.distance_km || 0).toFixed(2)} km</td>
                      <td>
                        <span className={`status-chip ${getRiskTone(item.request_verification)}`}>
                          {getRiskLabel(item.request_verification)}
                        </span>
                      </td>
                      <td>
                        <span className="status-chip good">{item.admin_review_status || 'ACCEPTED'}</span>
                      </td>
                      <td>{formatDate(item.recipient_response_at)}</td>
                      <td>{formatDate(item.appointment_scheduled_at)}</td>
                      <td>{item.request_status || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted-text">No transfer schedules yet.</p>
          )}
        </article>
      )}

    </section>
  );
}

export default AdminPage;
