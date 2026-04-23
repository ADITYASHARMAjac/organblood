import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { apiRequest, buildWebSocketUrl } from '../api/client';

const initialDonor = {
  donation_type: 'BOTH',
  organ_types: 'KIDNEY',
  preferred_donation_time: 'MORNING',
  profile: {
    first_name: '',
    last_name: '',
    date_of_birth: '1990-01-01',
    gender: 'OTHER',
    address: '',
    city: '',
    state: '',
    postal_code: '',
    country: 'India',
    latitude: '19.0760',
    longitude: '72.8777',
    blood_group: 'O+',
    emergency_contact_name: '',
    emergency_contact_phone: '',
  },
};

const initialFilters = {
  radiusKm: '50',
  maxDistanceKm: '100',
  urgency: '',
  bloodGroup: '',
  requestType: '',
  organType: '',
};

const defaultProfileExtras = {
  headline: '',
  occupation: '',
  language: 'English',
  contact_preference: 'PHONE',
  timezone: 'Asia/Kolkata',
  bio: '',
};

const DONOR_FORM_STORAGE_KEY = 'donor_form_state';
const APPLIED_REQUEST_IDS_STORAGE_KEY = 'donor_applied_request_ids';
const APPLIED_REQUESTS_STORAGE_KEY = 'donor_applied_requests';
const APPLIED_MATCH_REASON = 'Applied from nearby requests';

function getStoredObject(key, fallback) {
  const raw = localStorage.getItem(key);
  if (!raw) return fallback;
  try {
    return { ...fallback, ...JSON.parse(raw) };
  } catch (error) {
    return fallback;
  }
}

function getStoredDonorForm() {
  const raw = localStorage.getItem(DONOR_FORM_STORAGE_KEY);
  if (!raw) return initialDonor;

  try {
    const parsed = JSON.parse(raw);
    return {
      ...initialDonor,
      ...parsed,
      profile: {
        ...initialDonor.profile,
        ...(parsed?.profile || {}),
      },
    };
  } catch (error) {
    return initialDonor;
  }
}

function getStoredArray(key) {
  const raw = localStorage.getItem(key);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    return [];
  }
}

function normalizeAppliedRequestRecord(item) {
  if (!item || !item.request_id) return null;
  return {
    ...item,
    donor_response_reason: item.donor_response_reason || APPLIED_MATCH_REASON,
    approval_status: item.approval_status || 'PENDING_APPROVAL',
  };
}

function getStoredAppliedRequests() {
  const raw = localStorage.getItem(APPLIED_REQUESTS_STORAGE_KEY);
  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed.map(normalizeAppliedRequestRecord).filter(Boolean);
    } catch (error) {
      // fallback below
    }
  }

  const legacyIds = getStoredArray(APPLIED_REQUEST_IDS_STORAGE_KEY);
  return legacyIds.map((requestId) => ({
    request_id: requestId,
    match_id: null,
    request_type: 'UNKNOWN',
    urgency_level: 'PENDING',
    hospital_name: 'Pending details',
    distance_km: 0,
    blood_group_needed: '-',
    organ_type_needed: '-',
    clinical_notes: 'Applied request',
    compatibility_score: null,
    match_status: 'PENDING',
    donor_response: 'ACCEPTED',
    donor_response_reason: APPLIED_MATCH_REASON,
    approval_status: 'PENDING_APPROVAL',
  }));
}

function deriveDonationType(donor) {
  const blood = Boolean(donor?.can_donate_blood);
  const organ = Boolean(donor?.organ_types?.length) || Boolean(donor?.organ_donation_registered);
  if (blood && organ) return 'BOTH';
  if (blood) return 'BLOOD';
  if (organ) return 'ORGAN';
  return 'BLOOD';
}

function addDays(days) {
  const dt = new Date();
  dt.setDate(dt.getDate() + days);
  return dt.toISOString().slice(0, 10);
}

function normalizeFilterValue(value) {
  return String(value || '').trim().toUpperCase();
}

function getApprovalLabel(match) {
  const status = String(match?.approval_status || match?.recipient_response || '').toUpperCase();
  if (status === 'APPROVED' || status === 'ACCEPTED') return 'Accepted';
  if (status === 'REJECTED') return 'Rejected';
  return 'Pending Approval';
}

function getApprovalTone(match) {
  const status = String(match?.approval_status || match?.recipient_response || '').toUpperCase();
  if (status === 'APPROVED' || status === 'ACCEPTED') return 'good';
  if (status === 'REJECTED') return 'bad';
  return 'warn';
}

function isAppliedRequestRecord(match) {
  const donorResponse = String(match?.donor_response || '').toUpperCase();
  const matchStatus = String(match?.match_status || '').toUpperCase();
  return (
    donorResponse === 'ACCEPTED' ||
    matchStatus === 'ACCEPTED' ||
    String(match?.donor_response_reason || '').trim() === APPLIED_MATCH_REASON
  );
}

function isActiveHandover(match) {
  const donorResponse = String(match?.donor_response || '').toUpperCase();
  const approvalStatus = String(match?.approval_status || match?.recipient_response || '').toUpperCase();
  const matchStatus = String(match?.match_status || '').toUpperCase();
  const requestStatus = String(match?.request_status || '').toUpperCase();

  if (donorResponse !== 'ACCEPTED' && matchStatus !== 'ACCEPTED') return false;
  if (approvalStatus === 'REJECTED') return false;
  if (['REJECTED', 'FAILED', 'COMPLETED'].includes(matchStatus)) return false;
  if (['CANCELLED', 'EXPIRED', 'FULFILLED'].includes(requestStatus)) return false;
  return true;
}

function getDonationHistoryStatus(match) {
  return getApprovalLabel(match);
}

function getDonationHistoryTone(match) {
  return getApprovalTone(match);
}

function getDonationHistoryStatusLabel(match) {
  const status = getApprovalLabel(match);
  if (status === 'Accepted') return 'Accepted';
  if (status === 'Rejected') return 'Rejected';
  return 'Pending Approval';
}

function formatDateTime(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}

function getVerification(item) {
  return item?.verification || item?.request_verification || null;
}

function getVerificationRiskLabel(item) {
  const risk = String(getVerification(item)?.risk_level || '').toUpperCase();
  if (risk === 'HIGH') return 'High Risk';
  if (risk === 'MEDIUM') return 'Needs Review';
  return 'Verified';
}

function getVerificationTone(item) {
  const risk = String(getVerification(item)?.risk_level || '').toUpperCase();
  if (risk === 'HIGH') return 'bad';
  if (risk === 'MEDIUM') return 'warn';
  return 'good';
}

function DonorPage({ view = 'medical-profile' }) {
  const { token, setFlash } = useAuth();

  const [form, setForm] = useState(() => getStoredDonorForm());
  const [authMe, setAuthMe] = useState(null);
  const [donorMe, setDonorMe] = useState(null);
  const [recipientRequests, setRecipientRequests] = useState([]);
  const [nearbyRequests, setNearbyRequests] = useState([]);
  const [topMatches, setTopMatches] = useState([]);
  const [filters, setFilters] = useState(initialFilters);
  const [profilePhoto, setProfilePhoto] = useState(() => localStorage.getItem('donor_profile_photo') || '');
  const [profileExtras, setProfileExtras] = useState(() => getStoredObject('donor_profile_extras', defaultProfileExtras));
  const [savingProfile, setSavingProfile] = useState(false);
  const [loading, setLoading] = useState(false);
  const [applyingRequestId, setApplyingRequestId] = useState('');
  const [cancellingRequestId, setCancellingRequestId] = useState('');
  const [respondingAppointmentId, setRespondingAppointmentId] = useState('');
  const [appliedRequests, setAppliedRequests] = useState(() => getStoredAppliedRequests());
  const [appointmentRequests, setAppointmentRequests] = useState([]);
  const [appointmentPreference, setAppointmentPreference] = useState({
    date: addDays(1),
    time: '10:00',
    notes: 'Scheduled from donor dashboard.',
  });
  const [acceptToast, setAcceptToast] = useState('');

  const verificationSummary = useMemo(() => {
    if (!authMe) return { complete: false, label: 'Pending' };
    const complete = Boolean(authMe.email_verified && authMe.phone_verified && authMe.id_verified);
    return { complete, label: complete ? 'Verified' : 'Pending' };
  }, [authMe]);

  const notificationsWsUrl = useMemo(() => {
    if (!token) return '';
    return buildWebSocketUrl('/ws/notifications', token);
  }, [token]);

  const donationHistory = useMemo(() => appliedRequests, [appliedRequests]);
  const matchingPageMatches = useMemo(
    () => appliedRequests.filter(isActiveHandover),
    [appliedRequests]
  );

  const pageMeta = {
    'medical-profile': {
      title: 'Fulfillment Profile',
      blurb: '',
    },
    'donation-history': {
      title: 'Fulfillment History',
      blurb: '',
    },
    'nearby-requests': {
      title: 'Approved Cases',
      blurb: '',
    },
    'recipient-requests': {
      title: 'Network Requests',
      blurb: '',
    },
    'appointment-scheduling': {
      title: 'Donor Appointment',
      blurb: '',
    },
    'donor-appointment': {
      title: 'Transfer Scheduling',
      blurb: '',
    },
    'matching-system': {
      title: 'Active Handovers',
      blurb: '',
    },
  };

  const activeMeta = pageMeta[view] || pageMeta['medical-profile'];
  const showIdentity = view === 'medical-profile';
  const showFilters = view === 'nearby-requests' || view === 'recipient-requests';
  const showNearby = view === 'nearby-requests';
  const showRecipientRequests = view === 'recipient-requests';
  const showTopMatches = view === 'matching-system';
  const showDonationHistory = view === 'donation-history';
  const showDonorAppointment = view === 'appointment-scheduling' || view === 'donor-appointment';

  useEffect(() => {
    if (!acceptToast) return undefined;
    const timeoutId = window.setTimeout(() => setAcceptToast(''), 3200);
    return () => window.clearTimeout(timeoutId);
  }, [acceptToast]);

  useEffect(() => {
    loadIdentity(true);
    loadDonorProfile(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    localStorage.setItem(DONOR_FORM_STORAGE_KEY, JSON.stringify(form));
  }, [form]);

  useEffect(() => {
    localStorage.setItem(APPLIED_REQUESTS_STORAGE_KEY, JSON.stringify(appliedRequests));
    localStorage.setItem(
      APPLIED_REQUEST_IDS_STORAGE_KEY,
      JSON.stringify(appliedRequests.map((item) => item.request_id).filter(Boolean))
    );
  }, [appliedRequests]);

  function syncFormFromDonor(data) {
    if (!data) return;

    setForm((prev) => ({
      ...prev,
      donation_type: deriveDonationType(data),
      organ_types: (data.organ_types || []).join(', '),
      preferred_donation_time: data.preferred_donation_time || prev.preferred_donation_time,
      profile: {
        ...prev.profile,
        first_name: data.profile?.first_name || prev.profile.first_name,
        last_name: data.profile?.last_name || prev.profile.last_name,
        date_of_birth: data.profile?.date_of_birth || prev.profile.date_of_birth,
        gender: data.profile?.gender || prev.profile.gender,
        address: data.profile?.address || prev.profile.address,
        city: data.profile?.city || prev.profile.city,
        state: data.profile?.state || prev.profile.state,
        postal_code: data.profile?.postal_code || prev.profile.postal_code,
        country: data.profile?.country || prev.profile.country,
        blood_group: data.profile?.blood_group || prev.profile.blood_group,
        emergency_contact_name: data.profile?.emergency_contact_name || prev.profile.emergency_contact_name,
        emergency_contact_phone: data.profile?.emergency_contact_phone || prev.profile.emergency_contact_phone,
        latitude: data.profile?.latitude !== null && data.profile?.latitude !== undefined
          ? String(data.profile.latitude)
          : prev.profile.latitude,
        longitude: data.profile?.longitude !== null && data.profile?.longitude !== undefined
          ? String(data.profile.longitude)
          : prev.profile.longitude,
      },
    }));
  }

  function updateProfileField(field, value) {
    setForm((prev) => ({
      ...prev,
      profile: {
        ...prev.profile,
        [field]: value,
      },
    }));
  }

  function updateFormField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function updateFilter(field, value) {
    setFilters((prev) => ({ ...prev, [field]: value }));
  }

  function updateRequestTypeFilter(value) {
    setFilters((prev) => ({
      ...prev,
      requestType: value,
      organType: value === 'ORGAN' ? prev.organType : '',
    }));
  }

  function updateAppointmentPreference(field, value) {
    setAppointmentPreference((prev) => ({ ...prev, [field]: value }));
  }

  function updateProfileExtra(field, value) {
    setProfileExtras((prev) => ({ ...prev, [field]: value }));
  }

  function onProfilePhotoSelected(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setFlash({ type: 'error', text: 'Please upload a valid image file.' });
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const photo = String(reader.result || '');
      setProfilePhoto(photo);
      localStorage.setItem('donor_profile_photo', photo);
      window.dispatchEvent(new CustomEvent('donor-photo-updated', { detail: photo }));
      setFlash({ type: 'success', text: 'Profile photo updated.' });
    };
    reader.readAsDataURL(file);
  }

  function parseDonationPreferences() {
    const donationType = (form.donation_type || '').toUpperCase();
    const organTypes = form.organ_types
      .split(',')
      .map((x) => x.trim().toUpperCase())
      .filter(Boolean);

    if (donationType === 'BLOOD') {
      return { canDonateBlood: true, organDonationRegistered: false, organTypes: [] };
    }
    if (donationType === 'ORGAN') {
      return { canDonateBlood: false, organDonationRegistered: true, organTypes };
    }
    return { canDonateBlood: true, organDonationRegistered: true, organTypes };
  }

  function applyNearbyClientFilters(items) {
    const urgencyFilter = normalizeFilterValue(filters.urgency);
    const requestTypeFilter = normalizeFilterValue(filters.requestType);
    const bloodGroupFilter = normalizeFilterValue(filters.bloodGroup);
    const organTypeFilter = normalizeFilterValue(filters.organType);

    return items.filter((item) => {
      const urgency = normalizeFilterValue(item?.urgency_level);
      const requestType = normalizeFilterValue(item?.request_type);
      const bloodGroup = normalizeFilterValue(item?.blood_group_needed);
      const organType = normalizeFilterValue(item?.organ_type_needed);

      if (urgencyFilter && urgency !== urgencyFilter) return false;
      if (requestTypeFilter && requestType !== requestTypeFilter) return false;
      if (bloodGroupFilter && bloodGroup !== bloodGroupFilter) return false;
      if (organTypeFilter && organType !== organTypeFilter) return false;
      return true;
    });
  }

  function markRequestAsApplied(item) {
    const requestId = item?.request_id;
    if (!requestId) return;

    const snapshot = {
      request_id: requestId,
      match_id: item.match_id || null,
      request_type: item.request_type || 'UNKNOWN',
      urgency_level: item.urgency_level || 'PENDING',
      hospital_name: item.hospital_name || 'N/A',
      distance_km: Number(item.distance_km || 0),
      blood_group_needed: item.blood_group_needed || '-',
      organ_type_needed: item.organ_type_needed || '-',
      clinical_notes: item.clinical_notes || 'Applied request',
      compatibility_score: item.compatibility_score ?? null,
      match_status: item.match_status || 'PENDING',
      donor_response: item.donor_response || 'ACCEPTED',
      donor_response_reason: item.donor_response_reason || APPLIED_MATCH_REASON,
      approval_status: item.approval_status || 'PENDING_APPROVAL',
    };

    setAppliedRequests((prev) => {
      const idx = prev.findIndex((x) => x.request_id === requestId);
      if (idx === -1) return [snapshot, ...prev];
      const next = [...prev];
      next[idx] = { ...next[idx], ...snapshot };
      return next;
    });
  }

  async function loadIdentity(silent = false) {
    try {
      const data = await apiRequest('/auth/me', { token });
      setAuthMe(data);
    } catch (error) {
      if (!silent) setFlash({ type: 'error', text: error.message });
    }
  }

  async function loadDonorProfile(silent = false) {
    try {
      const data = await apiRequest('/donors/me', { token });
      setDonorMe(data);
      syncFormFromDonor(data);
    } catch (error) {
      if (error?.status === 404) {
        setDonorMe(null);
        return;
      }
      if (!silent) setFlash({ type: 'error', text: error.message });
    }
  }

  async function saveProfile(event) {
    event.preventDefault();
    setSavingProfile(true);

    try {
      const prefs = parseDonationPreferences();
      const basePayload = {
        can_donate_blood: prefs.canDonateBlood,
        organ_types: prefs.organTypes,
        organ_donation_registered: prefs.organDonationRegistered,
        preferred_donation_time: form.preferred_donation_time,
        profile: {
          ...form.profile,
          latitude: Number(form.profile.latitude),
          longitude: Number(form.profile.longitude),
        },
      };

      if (!donorMe) {
        await apiRequest('/donors/register', {
          method: 'POST',
          token,
          body: basePayload,
        });
      } else {
        await apiRequest('/donors/me/profile', {
          method: 'PUT',
          token,
          body: {
            donation_type: form.donation_type,
            ...basePayload,
          },
        });
      }

      localStorage.setItem('donor_profile_extras', JSON.stringify(profileExtras));
      if (profilePhoto) {
        localStorage.setItem('donor_profile_photo', profilePhoto);
      }

      setFlash({ type: 'success', text: 'Fulfilling hospital profile saved successfully.' });
      await loadIdentity(true);
      await loadDonorProfile(true);
    } catch (error) {
      setFlash({ type: 'error', text: error.message });
    } finally {
      setSavingProfile(false);
    }
  }

  async function toggleAvailability() {
    if (!donorMe) {
      setFlash({ type: 'error', text: 'Create your fulfillment profile first.' });
      return;
    }

    try {
      await apiRequest('/donors/me/availability', {
        method: 'PUT',
        token,
        body: { is_available: !donorMe.is_available },
      });
      setFlash({ type: 'success', text: `Availability updated to ${!donorMe.is_available}.` });
      await loadDonorProfile(true);
    } catch (error) {
      setFlash({ type: 'error', text: error.message });
    }
  }

  function captureLiveLocation() {
    if (!navigator.geolocation) {
      setFlash({ type: 'error', text: 'Geolocation is not supported by your browser.' });
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        updateProfileField('latitude', String(position.coords.latitude));
        updateProfileField('longitude', String(position.coords.longitude));
        setFlash({ type: 'success', text: 'Live location captured. Click "Save Location" to persist.' });
      },
      () => {
        setFlash({ type: 'error', text: 'Unable to capture location. Check browser permissions.' });
      }
    );
  }

  async function saveLocationOnly() {
    if (!donorMe) {
      setFlash({ type: 'error', text: 'Create the fulfillment profile first to persist location.' });
      return;
    }

    try {
      await apiRequest('/donors/me/profile', {
        method: 'PUT',
        token,
        body: {
          profile: {
            latitude: Number(form.profile.latitude),
            longitude: Number(form.profile.longitude),
          },
        },
      });
      setFlash({ type: 'success', text: 'Location updated successfully.' });
      await loadDonorProfile(true);
    } catch (error) {
      setFlash({ type: 'error', text: error.message });
    }
  }

  async function loadNearbyRequests(silent = false) {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('radius_km', filters.radiusKm || '50');
      if (filters.urgency) params.set('urgency', filters.urgency);
      if (filters.bloodGroup) params.set('blood_group', filters.bloodGroup);
      if (filters.requestType) params.set('request_type', filters.requestType);
      if (filters.organType) params.set('organ_type', filters.organType);

      const data = await apiRequest(`/donors/me/nearby-requests?${params.toString()}`, { token });
      const filteredItems = applyNearbyClientFilters(data.items || []);
      setNearbyRequests(filteredItems);
      if (!silent) {
        setFlash({ type: 'success', text: `Loaded ${filteredItems.length} approved cases.` });
      }
    } catch (error) {
      setNearbyRequests([]);
      setFlash({ type: 'error', text: error.message });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!showNearby || !token) {
      return;
    }
    loadNearbyRequests(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showNearby, token]);

  async function loadRecipientRequests(silent = false) {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('radius_km', filters.radiusKm || '50');
      if (filters.urgency) params.set('urgency', filters.urgency);
      if (filters.bloodGroup) params.set('blood_group', filters.bloodGroup);
      if (filters.requestType) params.set('request_type', filters.requestType);
      if (filters.organType) params.set('organ_type', filters.organType);

      const data = await apiRequest(`/donors/me/recipient-requests?${params.toString()}`, { token });
      const filteredItems = applyNearbyClientFilters(data.items || []);
      setRecipientRequests(filteredItems);
      if (!silent) {
        setFlash({ type: 'success', text: `Loaded ${filteredItems.length} network requests.` });
      }
    } catch (error) {
      setRecipientRequests([]);
      setFlash({ type: 'error', text: error.message });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!showRecipientRequests || !token) {
      return;
    }
    loadRecipientRequests(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showRecipientRequests, token]);

  async function loadTopMatches(silent = false) {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('limit', '100');
      params.set('max_distance_km', '500');

      const data = await apiRequest(`/donors/me/top-matches?${params.toString()}`, { token });
      const items = data.items || [];
      setTopMatches(items);
      setAppliedRequests((prev) => {
        const liveByRequestId = new Map(items.map((entry) => [entry.request_id, entry]));
        const merged = prev.map((entry) => {
          const live = liveByRequestId.get(entry.request_id);
          if (!live) return entry;
          const liveRecipientStatus = String(live.recipient_response || '').toUpperCase();
          const liveApprovalStatus = liveRecipientStatus === 'ACCEPTED'
            ? 'APPROVED'
            : liveRecipientStatus === 'REJECTED'
              ? 'REJECTED'
              : String(live.match_status || '').toUpperCase() === 'COMPLETED'
                ? 'APPROVED'
                : 'PENDING_APPROVAL';
          return {
            ...entry,
            ...live,
            donor_response_reason: entry.donor_response_reason || live.donor_response_reason || APPLIED_MATCH_REASON,
            recipient_response: live.recipient_response || entry.recipient_response,
            recipient_response_at: live.recipient_response_at || entry.recipient_response_at,
            appointment_scheduled_at: live.appointment_scheduled_at || entry.appointment_scheduled_at,
            approval_status: liveApprovalStatus === 'PENDING_APPROVAL'
              ? (entry.approval_status || liveApprovalStatus)
              : liveApprovalStatus,
          };
        });

        const known = new Set(merged.map((entry) => entry.request_id));
        items.forEach((entry) => {
          if (!known.has(entry.request_id) && isAppliedRequestRecord(entry)) {
            const liveRecipientStatus = String(entry.recipient_response || '').toUpperCase();
            merged.push({
              ...entry,
              approval_status: entry.approval_status || (
                liveRecipientStatus === 'ACCEPTED'
                  ? 'APPROVED'
                  : liveRecipientStatus === 'REJECTED'
                    ? 'REJECTED'
                    : String(entry.match_status || '').toUpperCase() === 'COMPLETED'
                      ? 'APPROVED'
                      : 'PENDING_APPROVAL'
              ),
            });
            known.add(entry.request_id);
          }
        });

        return merged;
      });
      if (!silent) {
        setFlash({ type: 'success', text: `Loaded ${items.length} top matches.` });
      }
    } catch (error) {
      setTopMatches([]);
      setFlash({ type: 'error', text: error.message });
    } finally {
      setLoading(false);
    }
  }

  async function loadDonorAppointments(silent = false) {
    setLoading(true);
    try {
      const data = await apiRequest('/donors/me/appointments?limit=200', { token });
      const items = data.items || [];
      setAppointmentRequests(items);
      if (!silent) {
        setFlash({ type: 'success', text: `Loaded ${items.length} transfer schedules.` });
      }
    } catch (error) {
      setAppointmentRequests([]);
      setFlash({ type: 'error', text: error.message });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if ((!showTopMatches && !showDonationHistory) || !token) {
      return;
    }
    loadTopMatches(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showTopMatches, showDonationHistory, token]);

  useEffect(() => {
    if (!showDonorAppointment || !token) {
      return;
    }
    loadDonorAppointments(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showDonorAppointment, token]);

  useEffect(() => {
    if (!token) {
      return undefined;
    }

    const ws = new WebSocket(notificationsWsUrl);

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'REQUEST_MATCHED' || payload.type === 'SYSTEM_ALERT') {
          loadTopMatches(true);
          if (showDonorAppointment) {
            loadDonorAppointments(true);
          }
        }
        if (payload.type === 'NEW_REQUEST_NEARBY' && showRecipientRequests) {
          loadRecipientRequests(true);
        }
      } catch (error) {
        // Ignore malformed websocket payloads.
      }
    };

    return () => {
      ws.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, notificationsWsUrl, showDonorAppointment, showRecipientRequests]);

  async function acceptRequest(matchId, notesOverride) {
    try {
      await apiRequest(`/matches/${matchId}/accept`, {
        method: 'POST',
        token,
        body: {
          appointment_preferred_date: appointmentPreference.date || addDays(1),
          appointment_preferred_time: appointmentPreference.time || '10:00',
          notes: notesOverride || appointmentPreference.notes || 'Scheduled from donor dashboard.',
        },
      });
      const acceptedMessage = 'Case accepted. It is now visible in Active Handovers and sent for admin review.';
      setFlash({ type: 'success', text: acceptedMessage });
      setAcceptToast(acceptedMessage);
      await loadNearbyRequests();
      await loadTopMatches();
    } catch (error) {
      setFlash({ type: 'error', text: error.message });
    }
  }

  async function applyForRequest(item) {
    setApplyingRequestId(item.request_id);
    try {
      const riskLevel = String(item?.verification?.risk_level || '').toUpperCase();
      if (riskLevel === 'HIGH') {
        throw new Error('This request is flagged high-risk and is blocked for donor applications.');
      }

      if (item.match_id) {
        await acceptRequest(item.match_id, APPLIED_MATCH_REASON);
        markRequestAsApplied({
          ...item,
          donor_response_reason: APPLIED_MATCH_REASON,
          donor_response: 'ACCEPTED',
          match_status: 'ACCEPTED',
        });
      } else {
        const response = await apiRequest(`/requests/${item.request_id}/apply`, {
          method: 'POST',
          token,
        });
        const appliedSnapshot = {
          ...item,
          match_id: response?.match_id || null,
          compatibility_score: response?.compatibility_score ?? item.compatibility_score,
          distance_km: response?.distance_km ?? item.distance_km,
          donor_response_reason: APPLIED_MATCH_REASON,
          donor_response: 'ACCEPTED',
          match_status: 'ACCEPTED',
        };
        markRequestAsApplied(appliedSnapshot);
        setTopMatches((prev) => {
          const next = prev.filter((entry) => entry.request_id !== appliedSnapshot.request_id);
          return [appliedSnapshot, ...next];
        });
        const acceptedMessage = 'Case accepted. It is now visible in Active Handovers and sent for admin review.';
        setFlash({ type: 'success', text: acceptedMessage });
        setAcceptToast(acceptedMessage);
        await loadNearbyRequests();
        await loadTopMatches();
      }
    } catch (error) {
      setFlash({ type: 'error', text: error.message });
    } finally {
      setApplyingRequestId('');
    }
  }

  async function cancelAppliedRequest(item) {
    setCancellingRequestId(item.request_id);
    try {
      if (item.match_id) {
        await apiRequest(`/matches/${item.match_id}/reject`, {
          method: 'POST',
          token,
          body: {
            reason: 'CANCELLED_BY_DONOR',
            details: 'Cancelled by donor from matching system.',
          },
        });
      }
      setAppliedRequests((prev) => prev.filter((entry) => entry.request_id !== item.request_id));
      setTopMatches((prev) => prev.filter((entry) => entry.request_id !== item.request_id));
      setFlash({ type: 'success', text: 'Request cancelled.' });
      await loadTopMatches(true);
    } catch (error) {
      setFlash({ type: 'error', text: error.message });
    } finally {
      setCancellingRequestId('');
    }
  }

  async function acceptAppointment(item) {
    setRespondingAppointmentId(item.match_id);
    try {
      await apiRequest(`/matches/${item.match_id}/accept`, {
        method: 'POST',
        token,
        body: {
          appointment_preferred_date: appointmentPreference.date || addDays(1),
          appointment_preferred_time: appointmentPreference.time || '10:00',
          notes: appointmentPreference.notes || 'Scheduled from donor appointment page.',
        },
      });
      setFlash({ type: 'success', text: 'Appointment accepted.' });
      await loadDonorAppointments(true);
      await loadTopMatches(true);
    } catch (error) {
      setFlash({ type: 'error', text: error.message });
    } finally {
      setRespondingAppointmentId('');
    }
  }

  async function rejectAppointment(item) {
    const reason = window.prompt('Rejection reason', 'Appointment rejected by donor.');
    if (!reason) return;

    setRespondingAppointmentId(item.match_id);
    try {
      await apiRequest(`/matches/${item.match_id}/reject`, {
        method: 'POST',
        token,
        body: {
          reason,
          details: reason,
        },
      });
      setFlash({ type: 'success', text: 'Appointment rejected.' });
      await loadDonorAppointments(true);
      await loadTopMatches(true);
    } catch (error) {
      setFlash({ type: 'error', text: error.message });
    } finally {
      setRespondingAppointmentId('');
    }
  }

  return (
    <section className={`full donor-page ${showNearby ? 'nearby-page' : ''} ${showIdentity ? 'medical-page' : ''} ${!showNearby && !showIdentity ? 'plain-page' : ''}`}>
      {acceptToast && <div className="donor-accept-toast">{acceptToast}</div>}
      {showIdentity && (
        <div className="donor-grid single-col">
          {showIdentity && (
            <article className="donor-section medical-profile-section">
              <div className="medical-profile-header">
                <div>
                  <p className="eyebrow">Donor Workspace</p>
                  <h3>Fulfillment Profile</h3>
                  <p className="muted-text">Keep your profile complete so urgent requests can reach you faster.</p>
                </div>
                <div className="medical-profile-status">
                  <span className={`status-chip ${verificationSummary.complete ? 'good' : 'warn'}`}>
                    Verification: {verificationSummary.label}
                  </span>
                  <span className={`status-chip ${donorMe?.is_available ? 'good' : 'warn'}`}>
                    Availability: {donorMe ? (donorMe.is_available ? 'Available' : 'Not Available') : 'Not Set'}
                  </span>
                </div>
              </div>

              <form onSubmit={saveProfile} className="donor-profile-layout">
                <aside className="donor-profile-photo-card">
                  <div className="donor-profile-photo-preview">
                    {profilePhoto ? (
                      <img src={profilePhoto} alt="Donor profile" />
                    ) : (
                      <span>{form.profile.first_name?.[0] || 'D'}</span>
                    )}
                  </div>
                  <label className="btn-ghost donor-upload-btn">
                    Upload Photo
                    <input type="file" accept="image/*" onChange={onProfilePhotoSelected} hidden />
                  </label>
                </aside>

                <div className="donor-profile-fields">
                  <div className="medical-profile-card">
                    <h4>Personal Information</h4>
                    <div className="donor-form-grid">
                      <label className="medical-field">
                        <span>First Name</span>
                        <input value={form.profile.first_name} onChange={(e) => updateProfileField('first_name', e.target.value)} required />
                      </label>
                      <label className="medical-field">
                        <span>Last Name</span>
                        <input value={form.profile.last_name} onChange={(e) => updateProfileField('last_name', e.target.value)} required />
                      </label>
                      <label className="medical-field">
                        <span>Date of Birth</span>
                        <input type="date" value={form.profile.date_of_birth} onChange={(e) => updateProfileField('date_of_birth', e.target.value)} required />
                      </label>
                      <label className="medical-field">
                        <span>Gender</span>
                        <select value={form.profile.gender} onChange={(e) => updateProfileField('gender', e.target.value)}>
                          <option value="MALE">Male</option>
                          <option value="FEMALE">Female</option>
                          <option value="OTHER">Other</option>
                        </select>
                      </label>
                      <label className="medical-field">
                        <span>Address</span>
                        <input value={form.profile.address} onChange={(e) => updateProfileField('address', e.target.value)} required />
                      </label>
                      <label className="medical-field">
                        <span>City</span>
                        <input value={form.profile.city} onChange={(e) => updateProfileField('city', e.target.value)} required />
                      </label>
                      <label className="medical-field">
                        <span>State</span>
                        <input value={form.profile.state} onChange={(e) => updateProfileField('state', e.target.value)} required />
                      </label>
                      <label className="medical-field">
                        <span>Postal Code</span>
                        <input value={form.profile.postal_code} onChange={(e) => updateProfileField('postal_code', e.target.value)} />
                      </label>
                      <label className="medical-field">
                        <span>Blood Group</span>
                        <select value={form.profile.blood_group} onChange={(e) => updateProfileField('blood_group', e.target.value)}>
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
                    </div>
                  </div>

                  <div className="medical-profile-card">
                    <h4>Donation Preferences</h4>
                    <div className="donor-form-grid">
                      <label className="medical-field">
                        <span>Donation Type</span>
                        <select value={form.donation_type} onChange={(e) => updateFormField('donation_type', e.target.value)}>
                          <option value="BLOOD">Blood</option>
                          <option value="ORGAN">Organ</option>
                          <option value="BOTH">Both</option>
                        </select>
                      </label>
                      <label className="medical-field">
                        <span>Organs</span>
                        <input placeholder="comma separated" value={form.organ_types} onChange={(e) => updateFormField('organ_types', e.target.value)} />
                      </label>
                      <label className="medical-field">
                        <span>Preferred Donation Time</span>
                        <select value={form.preferred_donation_time} onChange={(e) => updateFormField('preferred_donation_time', e.target.value)}>
                          <option value="MORNING">Morning</option>
                          <option value="AFTERNOON">Afternoon</option>
                          <option value="EVENING">Evening</option>
                          <option value="ANYTIME">Anytime</option>
                        </select>
                      </label>
                    </div>
                  </div>

                  <div className="medical-profile-card">
                    <h4>Additional Details</h4>
                    <div className="donor-profile-extra-grid">
                      <label className="medical-field">
                        <span>Headline</span>
                        <input value={profileExtras.headline} onChange={(e) => updateProfileExtra('headline', e.target.value)} />
                      </label>
                      <label className="medical-field">
                        <span>Occupation</span>
                        <input value={profileExtras.occupation} onChange={(e) => updateProfileExtra('occupation', e.target.value)} />
                      </label>
                      <label className="medical-field">
                        <span>Language</span>
                        <select value={profileExtras.language} onChange={(e) => updateProfileExtra('language', e.target.value)}>
                          <option value="English">English</option>
                          <option value="Hindi">Hindi</option>
                          <option value="Other">Other</option>
                        </select>
                      </label>
                      <label className="medical-field">
                        <span>Contact Preference</span>
                        <select value={profileExtras.contact_preference} onChange={(e) => updateProfileExtra('contact_preference', e.target.value)}>
                          <option value="PHONE">Phone</option>
                          <option value="EMAIL">Email</option>
                          <option value="ANY">Any</option>
                        </select>
                      </label>
                      <label className="medical-field">
                        <span>Timezone</span>
                        <input value={profileExtras.timezone} onChange={(e) => updateProfileExtra('timezone', e.target.value)} />
                      </label>
                      <label className="medical-field medical-field-wide">
                        <span>Short Bio</span>
                        <textarea value={profileExtras.bio} onChange={(e) => updateProfileExtra('bio', e.target.value)} rows={4} />
                      </label>
                      <label className="medical-field">
                        <span>Emergency Contact Name</span>
                        <input value={form.profile.emergency_contact_name} onChange={(e) => updateProfileField('emergency_contact_name', e.target.value)} />
                      </label>
                      <label className="medical-field">
                        <span>Emergency Contact Phone</span>
                        <input value={form.profile.emergency_contact_phone} onChange={(e) => updateProfileField('emergency_contact_phone', e.target.value)} />
                      </label>
                    </div>
                  </div>

                  <button type="submit" className="medical-save-btn" disabled={savingProfile}>
                    {savingProfile ? 'Saving...' : donorMe ? 'Save Fulfillment Profile' : 'Register And Save Fulfillment Profile'}
                  </button>
                </div>
              </form>
            </article>
          )}
        </div>
      )}

      {showDonorAppointment && (
        <article className="donor-section plain-section appointment-section">
          <div className="admin-section-head">
            <h3>{activeMeta.title}</h3>
            <div className="tab-row">
              <button onClick={() => loadDonorAppointments(false)} disabled={loading}>Refresh Schedules</button>
            </div>
          </div>

          <div className="appointment-toolbar">
            <label className="appointment-field">
              <span>Preferred Date</span>
              <input
                type="date"
                value={appointmentPreference.date}
                onChange={(e) => updateAppointmentPreference('date', e.target.value)}
              />
            </label>
            <label className="appointment-field">
              <span>Preferred Time</span>
              <input
                type="time"
                value={appointmentPreference.time}
                onChange={(e) => updateAppointmentPreference('time', e.target.value)}
              />
            </label>
            <label className="appointment-field appointment-field-wide">
              <span>Transfer Notes</span>
              <input
                value={appointmentPreference.notes}
                onChange={(e) => updateAppointmentPreference('notes', e.target.value)}
                placeholder="Add a short note for the appointment"
              />
            </label>
          </div>

          <div className="section-divider" />

          {appointmentRequests.length === 0 ? (
            <p className="muted-text">No approved transfer schedules yet.</p>
          ) : (
            <div className="table-shell">
              <table className="data-table appointment-table">
                <thead>
                  <tr>
                    <th>Request ID</th>
                    <th>Hospital</th>
                    <th>Doctor</th>
                    <th>Type</th>
                    <th>Blood Group</th>
                    <th>Organ</th>
                    <th>Urgency</th>
                    <th>Status</th>
                    <th>Donor Response</th>
                    <th>Score</th>
                    <th>Distance</th>
                    <th>Approved At</th>
                    <th>Scheduled At</th>
                    <th>Scheduled Request Created</th>
                    <th>Notes</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {appointmentRequests.map((item) => (
                    <tr key={item.match_id}>
                      <td>{item.request_id}</td>
                      <td>
                        <strong>{item.hospital_name || 'N/A'}</strong>
                        <div className="muted-cell">{item.request_status || '-'}</div>
                      </td>
                      <td>
                        <div>{item.receiving_doctor_name || '-'}</div>
                        <div className="muted-cell">{item.receiving_doctor_phone || '-'}</div>
                      </td>
                      <td>{item.request_type || '-'}</td>
                      <td>{item.blood_group_needed || '-'}</td>
                      <td>{item.organ_type_needed || '-'}</td>
                      <td>{item.urgency_level || '-'}</td>
                      <td>
                        <span className={`status-chip ${String(item.recipient_response || '').toUpperCase() === 'ACCEPTED' ? 'good' : 'warn'}`}>
                          {item.recipient_response || '-'}
                        </span>
                      </td>
                      <td>{item.donor_response || '-'}</td>
                      <td>{Number(item.compatibility_score || 0).toFixed(2)}</td>
                      <td>{Number(item.distance_km || 0).toFixed(2)} km</td>
                      <td>{formatDateTime(item.recipient_response_at)}</td>
                      <td>{formatDateTime(item.appointment_scheduled_at)}</td>
                      <td>{formatDateTime(item.created_at)}</td>
                      <td>
                        <div>{item.clinical_notes || 'No notes provided.'}</div>
                        <div className="muted-cell">
                          {Array.isArray(item.required_tests) && item.required_tests.length > 0
                            ? item.required_tests.join(', ')
                            : 'No tests listed'}
                        </div>
                      </td>
                      <td>
                        <div className="tab-row appointment-actions">
                          <button
                            onClick={() => acceptAppointment(item)}
                            disabled={respondingAppointmentId === item.match_id}
                          >
                            {respondingAppointmentId === item.match_id ? 'Saving...' : 'Accept'}
                          </button>
                          <button
                            className="danger"
                            onClick={() => rejectAppointment(item)}
                            disabled={respondingAppointmentId === item.match_id}
                          >
                            Reject
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>
      )}

      {showFilters && (
        <article className={`${showNearby ? 'donor-section nearby-plain-section' : 'panel donor-section'}`}>
          <h3>Case Filters</h3>

          <div className="donor-filter-grid">
            <label className="donor-filter-field">
              <span>Search Radius (km)</span>
              <input type="number" min="0.1" step="0.1" value={filters.radiusKm} onChange={(e) => updateFilter('radiusKm', e.target.value)} />
            </label>
            <label className="donor-filter-field">
              <span>Maximum Match Distance (km)</span>
              <input type="number" min="0.1" step="0.1" value={filters.maxDistanceKm} onChange={(e) => updateFilter('maxDistanceKm', e.target.value)} />
            </label>
            <label className="donor-filter-field">
              <span>Urgency Level</span>
              <select value={filters.urgency} onChange={(e) => updateFilter('urgency', e.target.value)}>
                <option value="">All Urgency</option>
                <option value="LOW">LOW</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="CRITICAL">CRITICAL</option>
              </select>
            </label>
            <label className="donor-filter-field">
              <span>Request Type</span>
              <select value={filters.requestType} onChange={(e) => updateRequestTypeFilter(e.target.value)}>
                <option value="">All Types</option>
                <option value="BLOOD">BLOOD</option>
                <option value="ORGAN">ORGAN</option>
                <option value="PLASMA">PLASMA</option>
              </select>
            </label>
            <label className="donor-filter-field">
              <span>Blood Group Needed</span>
              <select value={filters.bloodGroup} onChange={(e) => updateFilter('bloodGroup', e.target.value)}>
                <option value="">All Blood Groups</option>
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
            <label className="donor-filter-field">
              <span>Organ Needed</span>
              <select
                value={filters.organType}
                onChange={(e) => updateFilter('organType', e.target.value)}
                disabled={Boolean(filters.requestType) && filters.requestType !== 'ORGAN'}
              >
                <option value="">All Organs</option>
                <option value="KIDNEY">KIDNEY</option>
                <option value="LIVER">LIVER</option>
                <option value="HEART">HEART</option>
                <option value="LUNG">LUNG</option>
                <option value="PANCREAS">PANCREAS</option>
                <option value="CORNEA">CORNEA</option>
              </select>
            </label>
          </div>

          <div className="tab-row top-space">
            {showNearby && <button onClick={loadNearbyRequests} disabled={loading}>View Approved Cases</button>}
            {showRecipientRequests && <button onClick={loadRecipientRequests} disabled={loading}>View Network Requests</button>}
          </div>
        </article>
      )}

      {showDonationHistory && (
        <article className="donor-section plain-section">
          <h3>Fulfillment History</h3>
          {donationHistory.length === 0 && <p className="muted-text">No fulfillment history found.</p>}

          {donationHistory.length > 0 && (
            <div className="table-shell">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Hospital</th>
                    <th>Distance (km)</th>
                    <th>Blood Group</th>
                    <th>Organ</th>
                    <th>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {donationHistory.map((item) => (
                    <tr key={item.match_id || item.request_id}>
                      <td>{item.request_type || '-'}</td>
                      <td>
                        <span className={`status-chip ${getDonationHistoryTone(item)}`}>
                          {getDonationHistoryStatusLabel(item)}
                        </span>
                      </td>
                      <td>{item.hospital_name || 'N/A'}</td>
                      <td>{Number(item.distance_km || 0).toFixed(2)}</td>
                      <td>{item.blood_group_needed || '-'}</td>
                      <td>{item.organ_type_needed || '-'}</td>
                      <td>{item.compatibility_score !== null && item.compatibility_score !== undefined ? Number(item.compatibility_score).toFixed(2) : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>
      )}

      {(showNearby || showRecipientRequests || showTopMatches) && (
        <div className={`donor-results-grid ${showNearby || showRecipientRequests || showTopMatches ? 'single-col' : ''}`}>
          {showRecipientRequests && (
            <article className="donor-section nearby-plain-section nearby-results-section">
              <h3>Requesting Hospital Cases Awaiting Review</h3>
              {recipientRequests.length === 0 && <p className="muted-text">No matching network requests found.</p>}

              <div className="nearby-results-list">
                {recipientRequests.map((item) => (
                  <div key={item.request_id} className="nearby-request-item">
                    <div className="donor-card-head">
                      <strong>{item.request_type}</strong>
                      <span>{item.urgency_level}</span>
                    </div>
                    <p><strong>Recipient:</strong> {item.recipient_name || 'Recipient'}</p>
                    <p><strong>Hospital:</strong> {item.hospital_name || 'N/A'}</p>
                    <p><strong>Distance:</strong> {Number(item.distance_km).toFixed(2)} km</p>
                    <p><strong>Blood Group Needed:</strong> {item.blood_group_needed || '-'}</p>
                    <p><strong>Organ Needed:</strong> {item.organ_type_needed || '-'}</p>
                    <p><strong>Doctor:</strong> {item.receiving_doctor_name || '-'} {item.receiving_doctor_phone ? `(${item.receiving_doctor_phone})` : ''}</p>
                    <p><strong>Notes:</strong> {item.clinical_notes || 'No additional notes.'}</p>
                    <p><strong>Match Score:</strong> {item.compatibility_score !== null && item.compatibility_score !== undefined ? Number(item.compatibility_score).toFixed(2) : '-'}</p>
                    <p>
                      <strong>Verification:</strong>{' '}
                      <span className={`status-chip ${getVerificationTone(item)}`}>
                        {getVerificationRiskLabel(item)}
                      </span>
                    </p>
                    <p><strong>Status:</strong> Waiting for central command review</p>
                  </div>
                ))}
              </div>
            </article>
          )}

          {showNearby && (
            <article className="donor-section nearby-plain-section nearby-results-section">
              <h3>Approved Cases Ready For Fulfillment</h3>
              {nearbyRequests.length === 0 && <p className="muted-text">No approved cases loaded yet.</p>}

              <div className="nearby-results-list">
                {nearbyRequests.map((item) => (
                  <div key={item.request_id} className="nearby-request-item">
                    {String(item.status || '').toUpperCase() === 'OPEN' && (
                      <p>
                        <strong>Status:</strong>{' '}
                        <span className="status-chip warn">Pending central command approval</span>
                      </p>
                    )}
                    <div className="donor-card-head">
                      <strong>{item.request_type}</strong>
                      <span>{item.urgency_level}</span>
                    </div>
                    <p><strong>Hospital:</strong> {item.hospital_name || 'N/A'}</p>
                    <p><strong>Distance:</strong> {Number(item.distance_km).toFixed(2)} km</p>
                    <p><strong>Blood Group Needed:</strong> {item.blood_group_needed || '-'}</p>
                    <p><strong>Organ Needed:</strong> {item.organ_type_needed || '-'}</p>
                    <p><strong>Notes:</strong> {item.clinical_notes || 'No additional notes.'}</p>
                    <p><strong>Match Score:</strong> {item.compatibility_score !== null && item.compatibility_score !== undefined ? Number(item.compatibility_score).toFixed(2) : 'Auto-calculated on apply'}</p>
                    <p>
                      <strong>Verification:</strong>{' '}
                      <span className={`status-chip ${getVerificationTone(item)}`}>
                        {getVerificationRiskLabel(item)}
                      </span>
                    </p>

                    <div className="tab-row nearby-request-actions">
                      {(() => {
                        const isPendingAdminApproval = String(item?.status || '').toUpperCase() === 'OPEN';
                        return (
                      <button
                        onClick={() => applyForRequest(item)}
                        disabled={
                          applyingRequestId === item.request_id ||
                          String(item?.verification?.risk_level || '').toUpperCase() === 'HIGH' ||
                          isPendingAdminApproval
                        }
                        title={isPendingAdminApproval ? 'This case is waiting for admin approval.' : ''}
                      >
                        {applyingRequestId === item.request_id
                          ? 'Responding...'
                          : isPendingAdminApproval
                            ? 'Waiting Approval'
                            : 'Accept Case'}
                      </button>
                        );
                      })()}
                    </div>
                  </div>
                ))}
              </div>
            </article>
          )}

          {showTopMatches && (
            <article className="donor-section plain-section matching-list-section">
              <h3>Active Handovers</h3>
              {matchingPageMatches.length === 0 && <p className="muted-text">No active handovers yet. Accept a case from Approved Cases.</p>}

              {matchingPageMatches.length > 0 && (
                <div className="table-shell">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Type</th>
                        <th>Hospital</th>
                        <th>Distance (km)</th>
                        <th>Blood Group</th>
                        <th>Organ</th>
                        <th>Urgency</th>
                        <th>Score</th>
                        <th>Approval</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {matchingPageMatches.map((match, index) => (
                        <tr key={match.match_id || match.request_id || `${index}`}>
                          <td>{index + 1}</td>
                          <td>{match.request_type || 'UNKNOWN'}</td>
                          <td>{match.hospital_name || 'N/A'}</td>
                          <td>{Number(match.distance_km || 0).toFixed(2)}</td>
                          <td>{match.blood_group_needed || '-'}</td>
                          <td>{match.organ_type_needed || '-'}</td>
                          <td>{match.urgency_level || 'PENDING'}</td>
                          <td>{match.compatibility_score !== null && match.compatibility_score !== undefined ? Number(match.compatibility_score).toFixed(2) : 'Pending'}</td>
                          <td>
                            <span className={`matching-status-chip ${getApprovalTone(match)}`}>
                              {getApprovalLabel(match)}
                            </span>
                          </td>
                          <td>
                            <button
                              type="button"
                              className="matching-cancel-btn"
                              onClick={() => cancelAppliedRequest(match)}
                              disabled={cancellingRequestId === match.request_id}
                            >
                              {cancellingRequestId === match.request_id ? 'Cancelling...' : 'Cancel Request'}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </article>
          )}
        </div>
      )}
    </section>
  );
}

export default DonorPage;
