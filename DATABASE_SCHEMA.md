# Blood & Organ Donation Portal - Database Schema

## 📊 Entity-Relationship Diagram (Conceptual)

```
┌─────────────────┐          ┌──────────────────┐
│     USERS       │◄─────────│   PROFILES       │
│  (Auth & Login) │          │  (Personal Info) │
└────────┬────────┘          └──────────────────┘
         │
         ├─────┬──────────┬──────────┐
         │     │          │          │
         ▼     ▼          ▼          ▼
      ┌──────────────┐  ┌──────────────────┐
      │   DONORS     │  │  RECIPIENTS      │
      │   (Blood,    │  │  (Requests,      │
      │   Organs)    │  │   Medical Need)  │
      └──────┬───────┘  └────────┬─────────┘
             │                   │
             │                   ▼
             │          ┌──────────────────┐
             │          │  REQUESTS        │
             │          │  (Blood/Organ)   │
             │          └────────┬─────────┘
             │                   │
             └───────────┬───────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │      MATCHES             │
              │ (Donor-Request Pairing)  │
              └──────────────────────────┘

          ┌──────────────────┐          ┌──────────────────┐
          │   NOTIFICATIONS  │          │  ADMIN_ACTIONS   │
          │  (Real-time      │          │  (Approvals,     │
          │   Alerts)        │          │   Fraud Checks)  │
          └──────────────────┘          └──────────────────┘
```

---

## 📋 Database Tables (PostgreSQL)

### 1️⃣ **USERS** - Core Login & Authentication
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    
    -- Authentication
    password_hash VARCHAR(255) NOT NULL,
    
    -- Verification
    email_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMP,
    phone_verified BOOLEAN DEFAULT FALSE,
    phone_verified_at TIMESTAMP,
    
    -- Aadhaar-like ID verification
    id_verified BOOLEAN DEFAULT FALSE,
    id_document_path VARCHAR(500),
    id_verified_at TIMESTAMP,
    
    -- Account Status
    role ENUM('DONOR', 'RECIPIENT', 'ADMIN') NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_blocked BOOLEAN DEFAULT FALSE,
    block_reason VARCHAR(500),
    
    -- JWT
    refresh_token_hash VARCHAR(255),
    last_login TIMESTAMP,
    last_ip_address INET,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    
    -- Indexing
    INDEX idx_email,
    INDEX idx_phone,
    INDEX idx_role,
    INDEX idx_is_active,
    UNIQUE(id, deleted_at)
);
```

### 2️⃣ **PROFILES** - User Personal Information
```sql
CREATE TABLE profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    
    -- Basic Info
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender ENUM('MALE', 'FEMALE', 'OTHER'),
    
    -- Contact & Location
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20),
    country VARCHAR(100) DEFAULT 'India',
    
    -- Geolocation (for distance calculation)
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    
    -- Medical History
    blood_group ENUM('O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-'),
    allergies TEXT,
    chronic_diseases TEXT,
    current_medications TEXT,
    
    -- Emergency Contact
    emergency_contact_name VARCHAR(100),
    emergency_contact_phone VARCHAR(20),
    emergency_contact_relation VARCHAR(50),
    
    -- Media
    profile_photo_url VARCHAR(500),
    id_photo_url VARCHAR(500),
    medical_report_url VARCHAR(500),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_user_id,
    INDEX idx_location(latitude, longitude),
    INDEX idx_blood_group,
    INDEX idx_city
);
```

### 3️⃣ **DONORS** - Donor Profile & Availability
```sql
CREATE TABLE donors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES profiles(id),
    
    -- Donor Status
    is_available BOOLEAN DEFAULT TRUE,
    availability_updated_at TIMESTAMP,
    
    -- Blood Donation
    can_donate_blood BOOLEAN DEFAULT FALSE,
    blood_donation_last_date DATE,
    blood_donation_eligible_date DATE,
    
    -- Organ Donation (stored as JSONB array)
    organ_types JSONB DEFAULT '[]', -- ['KIDNEY', 'HEART', 'LIVER', 'PANCREAS', 'CORNEA']
    organ_donation_registered BOOLEAN DEFAULT FALSE,
    organ_registration_certificate_url VARCHAR(500),
    
    -- Donation History
    blood_donations_count INTEGER DEFAULT 0,
    organ_donations_count INTEGER DEFAULT 0,
    lives_saved INTEGER DEFAULT 0,
    
    -- Preferences
    preferred_donation_time VARCHAR(50),
    willing_hospital_list JSONB DEFAULT '[]', -- Hospital IDs
    
    -- Verification
    medical_clearance BOOLEAN DEFAULT FALSE,
    medical_clearance_date DATE,
    medical_report_url VARCHAR(500),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_user_id,
    INDEX idx_is_available,
    INDEX idx_blood_donation_eligible,
    INDEX idx_organ_types
);
```

### 4️⃣ **RECIPIENTS** - Recipient Profile & Medical History
```sql
CREATE TABLE recipients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES profiles(id),
    
    -- Recipient Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Medical History
    primary_disease VARCHAR(255),
    diagnosis_date DATE,
    surgery_needed_date DATE,
    
    -- Hospital & Doctor Info
    hospital_name VARCHAR(255),
    hospital_contact_phone VARCHAR(20),
    doctor_name VARCHAR(100),
    doctor_phone VARCHAR(20),
    doctor_registration_number VARCHAR(50),
    
    -- Priority Verification
    is_verified_by_hospital BOOLEAN DEFAULT FALSE,
    hospital_verification_date DATE,
    hospital_verification_document_url VARCHAR(500),
    
    -- Medical Needs (stored as JSONB for flexibility)
    matching_criteria JSONB NOT NULL, -- Blood group, organ type, etc.
    
    -- Urgency
    urgency_level ENUM('LOW', 'MEDIUM', 'CRITICAL') DEFAULT 'MEDIUM',
    urgency_reason TEXT,
    
    -- HLA Typing (for organ matching)
    hla_typing JSONB DEFAULT NULL, -- Advanced compatibility data
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_user_id,
    INDEX idx_urgency_level,
    INDEX idx_is_verified,
    INDEX idx_disease_type
);
```

### 5️⃣ **REQUESTS** - Blood/Organ Requests
```sql
CREATE TABLE requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_id UUID NOT NULL REFERENCES recipients(id),
    
    -- Request Details
    request_type ENUM('BLOOD', 'ORGAN', 'PLASMA') NOT NULL,
    blood_group_needed VARCHAR(5),
    organ_type_needed VARCHAR(50), -- 'KIDNEY', 'HEART', etc.
    quantity_needed INTEGER, -- For blood: units, For organ: 1
    
    -- Urgency & Timeline
    urgency_level ENUM('LOW', 'MEDIUM', 'CRITICAL') NOT NULL,
    needed_by TIMESTAMP NOT NULL,
    
    -- Status Tracking
    status ENUM('OPEN', 'MATCHED', 'IN_PROGRESS', 'FULFILLED', 'CANCELLED', 'EXPIRED') DEFAULT 'OPEN',
    matched_donor_id UUID REFERENCES donors(id),
    matched_at TIMESTAMP,
    
    -- Hospital Details
    hospital_location JSONB NOT NULL, -- {latitude, longitude, address}
    hospital_name VARCHAR(255),
    receiving_doctor_name VARCHAR(100),
    receiving_doctor_phone VARCHAR(20),
    
    -- Additional Info
    clinical_notes TEXT,
    required_tests JSONB DEFAULT '[]', -- ['COVID', 'HIV', 'HBsAg']
    additional_requirements TEXT,
    
    -- Visibility & Sharing
    is_public BOOLEAN DEFAULT FALSE,
    shared_with_hospitals JSONB DEFAULT '[]', -- Hospital IDs
    
    -- Timestamps & TTL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    fulfilled_at TIMESTAMP,
    
    INDEX idx_recipient_id,
    INDEX idx_request_type,
    INDEX idx_status,
    INDEX idx_urgency_level,
    INDEX idx_created_at,
    INDEX idx_blood_organ_status(blood_group_needed, organ_type_needed, status)
);
```

### 6️⃣ **MATCHES** - Donor-Request Pairings
```sql
CREATE TABLE matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    donor_id UUID NOT NULL REFERENCES donors(id) ON DELETE CASCADE,
    
    -- Match Score
    compatibility_score DECIMAL(5, 2) NOT NULL, -- 0-100
    distance_km DECIMAL(10, 2) NOT NULL,
    score_components JSONB NOT NULL, -- {blood_match: 100, urgency_weight: 0.8, distance_factor: 0.9}
    
    -- Status
    status ENUM('SUGGESTED', 'NOTIFIED', 'ACCEPTED', 'REJECTED', 'COMPLETED', 'FAILED') DEFAULT 'SUGGESTED',
    
    -- Donor Response
    donor_response ENUM('PENDING', 'ACCEPTED', 'REJECTED', 'UNAVAILABLE') DEFAULT 'PENDING',
    donor_response_at TIMESTAMP,
    donor_response_reason TEXT,
    
    -- Recipient Response
    recipient_response ENUM('PENDING', 'ACCEPTED', 'REJECTED') DEFAULT 'PENDING',
    recipient_response_at TIMESTAMP,
    
    -- Donation Execution
    appointment_scheduled_at TIMESTAMP,
    donation_completed_at TIMESTAMP,
    donation_failed_reason TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_request_id,
    INDEX idx_donor_id,
    INDEX idx_status,
    INDEX idx_compatibility_score DESC,
    UNIQUE(request_id, donor_id)
);
```

### 7️⃣ **NOTIFICATIONS** - Real-Time Alerts
```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Notification Type
    type ENUM('REQUEST_MATCHED', 'NEW_REQUEST_NEARBY', 'DONATION_REMINDER', 'VERIFICATION_NEEDED', 'SYSTEM_ALERT') NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    
    -- Related Entity
    related_entity_type VARCHAR(50), -- 'REQUEST', 'MATCH', 'USER'
    related_entity_id UUID,
    
    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    
    -- Delivery Channels
    deliver_via JSONB DEFAULT '["IN_APP"]', -- ['IN_APP', 'EMAIL', 'SMS', 'PUSH']
    email_sent BOOLEAN DEFAULT FALSE,
    sms_sent BOOLEAN DEFAULT FALSE,
    push_sent BOOLEAN DEFAULT FALSE,
    
    -- Retry Logic
    delivery_attempts INTEGER DEFAULT 0,
    last_delivery_attempt TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '7 days'),
    
    INDEX idx_user_id,
    INDEX idx_type,
    INDEX idx_is_read,
    INDEX idx_created_at
);
```

### 8️⃣ **ADMIN_ACTIONS** - Audit Trail & Approvals
```sql
CREATE TABLE admin_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID NOT NULL REFERENCES users(id),
    
    -- Action Details
    action_type ENUM('APPROVE_USER', 'BLOCK_USER', 'REJECT_REQUEST', 'VERIFY_ID', 'REMOVE_SPAM', 'SUSPEND_ACCOUNT') NOT NULL,
    target_entity_type VARCHAR(50), -- 'USER', 'REQUEST', 'MATCH'
    target_entity_id UUID NOT NULL,
    
    -- Decision
    decision TEXT,
    reason TEXT,
    evidence_urls JSONB DEFAULT '[]',
    
    -- Status
    status ENUM('PENDING', 'APPROVED', 'REJECTED') DEFAULT 'APPROVED',
    status_updated_by UUID REFERENCES users(id),
    status_updated_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ACTION_at TIMESTAMP,
    
    INDEX idx_admin_id,
    INDEX idx_action_type,
    INDEX idx_target_entity
);
```

### 9️⃣ **ANALYTICS** - Metrics & Dashboard Data
```sql
CREATE TABLE analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Date
    date DATE NOT NULL,
    
    -- Metrics
    total_donors INTEGER DEFAULT 0,
    total_recipients INTEGER DEFAULT 0,
    active_donors INTEGER DEFAULT 0,
    active_recipients INTEGER DEFAULT 0,
    
    -- Requests
    new_requests INTEGER DEFAULT 0,
    fulfilled_requests INTEGER DEFAULT 0,
    pending_requests INTEGER DEFAULT 0,
    
    -- Matches
    total_matches INTEGER DEFAULT 0,
    successful_matches INTEGER DEFAULT 0,
    match_success_rate DECIMAL(5, 2),
    
    -- Blood Metrics
    blood_requests INTEGER DEFAULT 0,
    blood_fulfilled INTEGER DEFAULT 0,
    
    -- Organ Metrics
    organ_requests INTEGER DEFAULT 0,
    organ_fulfilled INTEGER DEFAULT 0,
    
    -- Response Times
    avg_response_time_minutes INTEGER,
    avg_matching_time_minutes INTEGER,
    
    -- Geographic
    top_requesting_city VARCHAR(100),
    top_donor_city VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(date),
    INDEX idx_date
);
```

---

## 🔑 Key Relationships & Constraints

| Relationship | Type | Constraint |
|--------------|------|-----------|
| Users → Profiles | 1:1 | CASCADE DELETE |
| Users → Donors | 1:1 | CASCADE DELETE |
| Users → Recipients | 1:1 | CASCADE DELETE |
| Donors ← → Matches | 1:N | RESTRICT(can't delete donor if matches exist) |
| Recipients → Requests | 1:N | CASCADE DELETE |
| Requests → Matches | 1:N | CASCADE DELETE |
| Donors → Profiles | 1:1 | FK Constraint |

---

## 📑 Indexes for Performance

```sql
-- Geospatial Index for faster location queries
CREATE INDEX idx_location_gist ON profiles USING GIST (
    ll_to_earth(latitude, longitude)
);

-- Full-text search on medical conditions
CREATE INDEX idx_medical_conditions ON recipients 
USING GIN(to_tsvector('english', primary_disease));

-- Composite index for fast request filtering
CREATE INDEX idx_requests_status_urgency_date ON requests(status, urgency_level, created_at DESC);

-- Composite index for donor availability
CREATE INDEX idx_donors_available_bloodtype ON donors(is_available, user_id);
```

---

## 🛡️ Data Privacy & Security

1. **Sensitive Field Encryption**
   - Aadhaar-like ID: AES-256-CBC
   - Medical records: AES-256-GCM
   - Personal phone: Tokenized + Encrypted

2. **Data Retention Policy**
   - Active accounts: Indefinite
   - Deleted accounts: Soft delete + purge after 90 days
   - Request history: 2 years
   - Logs: 6 months (with external archival)

3. **Audit Logging**
   - All admin actions tracked in `admin_actions`
   - User login attempts tracked
   - Data access logged for sensitive records
