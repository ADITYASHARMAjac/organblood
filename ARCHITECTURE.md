# Blood & Organ Donation Portal - System Architecture

## 🏗️ High-Level Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND LAYER                         │
│        React SPA with Maps Integration (Mapbox)             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │• Donation Dashboard    • Request Matching View       │   │
│  │• User Profile          • Notifications Center        │   │
│  │• Map View              • Analytics Dashboard         │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │ REST API + WebSocket
┌────────────────────▼────────────────────────────────────────┐
│                    API GATEWAY LAYER                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │• Rate Limiting (Redis)      • Request Validation    │   │
│  │• CORS Handling              • Logging & Monitoring  │   │
│  │• Authentication Middleware  • Error Handling        │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                   APPLICATION LAYER (FastAPI)              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ AUTH Module         │ USER Module                    │   │
│  │ ├─ JWT Generation   │ ├─ Profile Management         │   │
│  │ ├─ OAuth Providers  │ ├─ ID Verification           │   │
│  │ └─ 2FA Support      │ └─ Location Updates           │   │
│  │                                                      │   │
│  │ DONOR Module        │ RECIPIENT Module              │   │
│  │ ├─ Availability     │ ├─ Request Creation          │   │
│  │ ├─ Blood Group Mgmt │ ├─ Urgency Levels            │   │
│  │ └─ Organ Types      │ └─ Medical Details            │   │
│  │                                                      │   │
│  │ MATCHING Module     │ NOTIFICATION Module           │   │
│  │ ├─ Algorithm        │ ├─ Real-time Alerts (Socket) │   │
│  │ ├─ Compatibility    │ ├─ Email/SMS Integration     │   │
│  │ └─ Distance Calc    │ └─ Queue Management (Celery)  │   │
│  │                                                      │   │
│  │ ADMIN Module        │ ANALYTICS Module              │   │
│  │ ├─ Approvals        │ ├─ Dashboards                │   │
│  │ ├─ Spam Detection   │ ├─ Reports                   │   │
│  │ └─ User Management  │ └─ Metrics                    │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                 DATA LAYER (Repositories)                   │
│         SQL ORM (SQLAlchemy) with Connection Pooling       │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                    DATABASE LAYER                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │• PostgreSQL (Primary Data)                           │   │
│  │• Redis Cache (Sessions, Rate Limiting, Notifications)│   │
│  │• Elasticsearch (Future: Request Search & Analytics)  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

Cache Layer:
┌─────────────────────────────────────┐
│ Redis Clusters                      │
│ • Sessions      • Rate Limits       │
│ • User Cache    • Notification Queue│
│ • Donor Index   • Match Results     │
└─────────────────────────────────────┘

Message Queue:
┌─────────────────────────────────────┐
│ Celery + RabbitMQ/Redis             │
│ • Async Notifications               │
│ • Email/SMS Sending                 │
│ • Analytics Processing              │
│ • Matching Algorithm Jobs           │
└─────────────────────────────────────┘
```

---

## 🔐 Security Architecture

```
CLIENT REQUEST
      │
      ▼
┌─────────────────────────────┐
│ SSL/TLS (HTTPS)             │
│ API Rate Limiting (200 req/min) │
└──────────────┬──────────────┘
               │
      ▼
┌─────────────────────────────┐
│ Input Validation & Sanitization │
│ • Regex Patterns            │
│ • Length Validation         │
│ • Type Checking             │
└──────────────┬──────────────┘
               │
      ▼
┌─────────────────────────────┐
│ JWT Authentication          │
│ • Access Token (15 min)     │
│ • Refresh Token (7 days)    │
│ • Email Verification Badge  │
└──────────────┬──────────────┘
               │
      ▼
┌─────────────────────────────┐
│ Role-Based Access Control   │
│ • DONOR, RECIPIENT, ADMIN   │
│ • Scope-based Permissions   │
└──────────────┬──────────────┘
               │
      ▼
┌─────────────────────────────┐
│ Data Encryption             │
│ • At Rest: AES-256          │
│ • In Transit: TLS 1.3       │
│ • Sensitive Fields Hashed   │
└─────────────────────────────┘
```

---

## 📊 Data Flow: Matching Request

```
┌────────────────────┐
│ Recipient Creates  │
│ Request (Blood/    │
│ Organ Type)        │
└──────────┬─────────┘
           │
           ▼
┌──────────────────────────────┐
│ Input Validation & Auth      │
│ • Verify User Status         │
│ • Validate Medical Details   │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ Store Request in Database    │
│ • Set Status: OPEN           │
│ • Generate Unique ID         │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ Trigger Matching Algorithm   │
│ (Async via Celery)           │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ MATCHING ALGORITHM                   │
│ 1. Query Donors by Blood Type Match  │
│ 2. Filter by Availability (True)     │
│ 3. Calculate Distance (Haversine)    │
│ 4. Apply Urgency Weights             │
│ 5. Rank by Score                     │
│ 6. Return Top 5 Matches              │
└──────────┬──────────────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ Send Real-Time Notifications │
│ • WebSocket Alert to Donors  │
│ • Email/SMS Backup           │
│ • In-App Push Notification   │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ Update UI Dashboard          │
│ • Show Matched Donors        │
│ • Display Maps & Routes      │
│ • Contact Options            │
└──────────────────────────────┘
```

---

## 🔄 Technology Stack Justification

| Component | Technology | Why |
|-----------|-----------|-----|
| Backend | FastAPI | Async support, auto-docs, performance, Python |
| Frontend | React | SPA efficiency, map integration, real-time updates |
| Database | PostgreSQL | ACID compliance, JSON support, geospatial queries, reliability |
| Caching | Redis | Fast session management, rate limiting, pub/sub for notifications |
| Queue | Celery + RabbitMQ | Async task processing, scalable notifications |
| Auth | JWT | Stateless, scalable, mobile-friendly |
| Maps | Mapbox | Distance calculations, real-time geolocation |
| Search | Elasticsearch | Fast donor discovery (future enhancement) |

---

## 🚀 Deployment Architecture

```
┌─────────────────────────────────────────────────────┐
│ PRODUCTION ENVIRONMENT (Cloud: AWS/GCP/Azure)      │
├─────────────────────────────────────────────────────┤
│ Load Balancer (SSL Termination)                     │
│             │                                       │
├─────────────┼──────────────────────────────────────┤
│             │                                       │
│ Docker Container 1    Docker Container 2   Docker 3│
│ (FastAPI App)        (FastAPI App)       (FastAPI) │
│                                                     │
├─────────────────────────────────────────────────────┤
│ PostgreSQL Instance         Redis Cluster           │
│ • 2x Replication            • Master-Slave Setup    │
│ • Automated Backups         • 99.99% Uptime         │
│ • Point-in-time Recovery    • Sharded Storage       │
│                                                     │
├─────────────────────────────────────────────────────┤
│ Celery Workers (for async tasks)                    │
│ • 5 workers in production                           │
│ • Auto-scaling based on queue depth                 │
│                                                     │
├─────────────────────────────────────────────────────┤
│ Monitoring & Logging                                │
│ • Prometheus (Metrics)                              │
│ • ELK Stack (Logs)                                  │
│ • Grafana (Dashboards)                              │
│ • Sentry (Error Tracking)                           │
│                                                     │
├─────────────────────────────────────────────────────┤
│ Static Content & CDN                                │
│ • CloudFront/CloudFlare                             │
│ • React SPA Hosting                                 │
│ • Asset Caching                                     │
└─────────────────────────────────────────────────────┘
```

---

## 🎨 Design Principles

1. **Modularity**: Each feature is a separate service module
2. **Scalability**: Async processing with Celery, horizontal scaling with containers
3. **Security**: JWT + email verification, encrypted sensitive data, rate limiting
4. **Performance**: Redis caching, database indexing, query optimization
5. **Reliability**: PostgreSQL ACID guarantees, error handling, retries
6. **Maintainability**: Clean code, separation of concerns (MVC), comprehensive logging
