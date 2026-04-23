const API_PREFIX = '/api/v1';
const REQUEST_TIMEOUT_MS = 12000;
const API_BASE_STORAGE_KEY = 'donation_api_base';

const configuredApiBase = (process.env.REACT_APP_API_URL || '').trim().replace(/\/+$/, '');

function getStoredApiBase() {
  if (typeof window === 'undefined') {
    return '';
  }
  return String(window.localStorage.getItem(API_BASE_STORAGE_KEY) || '').trim();
}

function storeApiBase(base) {
  if (typeof window === 'undefined' || !base) {
    return;
  }
  window.localStorage.setItem(API_BASE_STORAGE_KEY, base);
}

function getApiBaseCandidates() {
  return Array.from(
    new Set(
      [getStoredApiBase(), configuredApiBase, '', 'http://localhost:8000', 'http://localhost:8002']
        .map((item) => item.trim())
        .filter(Boolean)
        .concat([''])
    )
  );
}

function buildApiUrl(base, path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  if (!base) {
    return `${API_PREFIX}${normalizedPath}`;
  }
  return `${base}${API_PREFIX}${normalizedPath}`;
}

export function buildWebSocketUrl(path, token = '') {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const browserFallback = typeof window !== 'undefined'
    ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.hostname}:8002`
    : 'ws://localhost:8002';
  const base = configuredApiBase || browserFallback || getStoredApiBase() || 'ws://localhost:8002';
  const wsBase = base.replace(/^http/i, 'ws').replace(/\/+$/, '');
  const suffix = token ? `?token=${encodeURIComponent(token)}` : '';
  return `${wsBase}${API_PREFIX}${normalizedPath}${suffix}`;
}

async function fetchWithTimeout(url, options) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeoutId);
  }
}

async function parsePayload(response) {
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    return null;
  }

  try {
    return await response.json();
  } catch (error) {
    return null;
  }
}

function isRecoverableHttpStatus(statusCode) {
  return statusCode === 404 || statusCode === 502 || statusCode === 503 || statusCode === 504;
}

function isRetryableProxyFailure(statusCode, payload) {
  // CRA dev proxy commonly returns plain-text 500 when target API is down.
  return statusCode === 500 && !payload;
}

function isNetworkFailure(error) {
  const message = String(error?.message || '');
  return (
    error?.name === 'AbortError' ||
    error?.name === 'TypeError' ||
    /failed to fetch|networkerror|load failed|aborted/i.test(message)
  );
}

function backendUnavailableError() {
  return new Error('Backend API is unreachable. Start backend on http://localhost:8000 (or 8002) and try again.');
}

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

function persistStoredAuth(auth) {
  if (!auth) {
    localStorage.removeItem('donation_auth');
    return;
  }
  localStorage.setItem('donation_auth', JSON.stringify(auth));
}

async function refreshAccessToken(base) {
  const auth = getStoredAuth();
  const refreshToken = auth?.refreshToken;
  if (!refreshToken) {
    return null;
  }

  const response = await fetchWithTimeout(buildApiUrl(base, '/auth/refresh'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    return null;
  }

  const payload = await parsePayload(response);
  const nextAccessToken = payload?.tokens?.access_token;
  const nextRefreshToken = payload?.tokens?.refresh_token;
  if (!nextAccessToken || !nextRefreshToken) {
    return null;
  }

  persistStoredAuth({
    ...(auth || {}),
    token: nextAccessToken,
    refreshToken: nextRefreshToken,
  });

  return nextAccessToken;
}

export async function apiRequest(path, options = {}) {
  const method = options.method || 'GET';
  const resolvedToken = options.token || getStoredAuth()?.token || '';
  const baseHeaders = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  let lastNetworkError = null;

  const apiBaseCandidates = getApiBaseCandidates();

  for (let idx = 0; idx < apiBaseCandidates.length; idx += 1) {
    const base = apiBaseCandidates[idx];
    const url = buildApiUrl(base, path);
    const isLastCandidate = idx === apiBaseCandidates.length - 1;

    try {
      const response = await fetchWithTimeout(url, {
        method,
        headers: {
          ...baseHeaders,
          ...(resolvedToken ? { Authorization: `Bearer ${resolvedToken}` } : {}),
        },
        body: options.body ? JSON.stringify(options.body) : undefined,
      });

      const payload = await parsePayload(response);

      if (!response.ok && response.status === 401 && resolvedToken && !options.skipAuthRefresh) {
        const refreshedToken = await refreshAccessToken(base);
        if (refreshedToken) {
          return apiRequest(path, {
            ...options,
            token: refreshedToken,
            skipAuthRefresh: true,
          });
        }

        persistStoredAuth(null);
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('auth-expired'));
        }
      }

      if (!response.ok) {
        const shouldRetry =
          isRecoverableHttpStatus(response.status) ||
          isRetryableProxyFailure(response.status, payload);

        if (shouldRetry && !isLastCandidate) {
          continue;
        }

        if (isRetryableProxyFailure(response.status, payload) && isLastCandidate) {
          throw backendUnavailableError();
        }

        const message = payload?.error?.message || payload?.detail || `Request failed (${response.status})`;
        const details = payload?.error?.details || null;
        const error = new Error(message);
        error.details = details;
        error.status = response.status;
        throw error;
      }

      if (base) {
        storeApiBase(base);
      }
      return payload;
    } catch (error) {
      if (isNetworkFailure(error) && !isLastCandidate) {
        lastNetworkError = error;
        continue;
      }

      if (isNetworkFailure(error) && isLastCandidate) {
        throw backendUnavailableError();
      }

      throw error;
    }
  }

  if (lastNetworkError) {
    throw backendUnavailableError();
  }

  throw new Error('Request failed');
}

export async function healthCheck() {
  const apiBaseCandidates = getApiBaseCandidates();
  const healthCandidates = apiBaseCandidates.map((base) => (base ? `${base}/health` : '/health'));

  for (let idx = 0; idx < healthCandidates.length; idx += 1) {
    const isLastCandidate = idx === healthCandidates.length - 1;

    try {
      const response = await fetchWithTimeout(healthCandidates[idx], {});
      if (!response.ok) {
        if (!isLastCandidate && isRecoverableHttpStatus(response.status)) {
          continue;
        }
        throw new Error('Backend health check failed');
      }
      if (apiBaseCandidates[idx]) {
        storeApiBase(apiBaseCandidates[idx]);
      }
      return response.json();
    } catch (error) {
      if (isNetworkFailure(error) && !isLastCandidate) {
        continue;
      }
      if (isNetworkFailure(error) && isLastCandidate) {
        throw backendUnavailableError();
      }
      throw error;
    }
  }

  throw new Error('Backend health check failed');
}
