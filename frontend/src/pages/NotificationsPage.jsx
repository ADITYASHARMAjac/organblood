import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { apiRequest, buildWebSocketUrl } from '../api/client';

function NotificationsPage() {
  const { token, setFlash } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [events, setEvents] = useState([]);
  const [socketState, setSocketState] = useState('Connecting...');

  const wsUrl = useMemo(() => buildWebSocketUrl('/ws/notifications', token), [token]);

  useEffect(() => {
    if (!token) {
      return undefined;
    }

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => setSocketState('Connected');
    ws.onclose = () => setSocketState('Disconnected');
    ws.onerror = () => setSocketState('Connection Error');

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type !== 'INIT_UNREAD') {
          setEvents((prev) => [payload, ...prev].slice(0, 20));
        }
      } catch (error) {
        // Ignore malformed websocket payloads.
      }
    };

    const timer = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 20000);

    return () => {
      clearInterval(timer);
      ws.close();
    };
  }, [token, wsUrl]);

  async function loadNotifications(unreadOnly) {
    try {
      const data = await apiRequest(`/notifications/me?unread_only=${unreadOnly}`, { token });
      setNotifications(data.items || []);
    } catch (error) {
      setFlash({ type: 'error', text: error.message });
    }
  }

  async function markRead(notificationId) {
    try {
      await apiRequest(`/notifications/${notificationId}/read`, {
        method: 'POST',
        token,
      });
      await loadNotifications(true);
    } catch (error) {
      setFlash({ type: 'error', text: error.message });
    }
  }

  return (
    <section className="panel full">
      <h2>Notifications Center</h2>
      <p className="muted-text">WebSocket status: {socketState}</p>

      <div className="tab-row">
        <button onClick={() => loadNotifications(true)}>Load Unread</button>
        <button onClick={() => loadNotifications(false)}>Load All</button>
      </div>

      <div className="split-grid">
        <div className="list-block">
          <h3>Inbox</h3>
          {notifications.length === 0 && <p className="muted-text">No notifications loaded yet.</p>}
          {notifications.map((item) => (
            <div key={item.notification_id} className="list-item multi">
              <div>
                {item.notification_type} | {item.title} | Read: {String(item.is_read)}
              </div>
              {!item.is_read && <button onClick={() => markRead(item.notification_id)}>Mark Read</button>}
            </div>
          ))}
        </div>

        <div className="list-block">
          <h3>Live Feed (WebSocket)</h3>
          {events.length === 0 && <p className="muted-text">No live events received yet.</p>}
          {events.map((event, idx) => (
            <div key={`${idx}-${event.type || 'evt'}`} className="list-item">
              {JSON.stringify(event)}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default NotificationsPage;
