# Blood & Organ Donation Portal - API Specification

## 🔌 Base URL
```
https://api.blooddonation.com/v1
```

## 🔐 Authentication Header
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

---

## 📋 API ENDPOINTS SPECIFICATION

### **1. AUTHENTICATION ENDPOINTS** (`/auth`)

#### POST `/auth/register`
**Register a new user (Donor/Recipient)**

```
Request:
{
  "email": "john@example.com",
  "phone": "+918765432109",
  "username": "john_donor",
  "password": "SecurePass@123",
  "role": "DONOR"  // DONOR or RECIPIENT
}

Response (201):
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "john@example.com",
  "phone": "+918765432109",
  "role": "DONOR",
  "message": "Registration successful. Check email for verification.",
  "verification_sent": true
}
```

#### POST `/auth/login`
**Authenticate user and get JWT tokens**

```
Request:
{
  "email": "john@example.com",
  "password": "SecurePass@123"
}

Response (200):
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "john@example.com",
    "role": "DONOR",
    "email_verified": false
  }
}

Errors:
- 401: Invalid credentials
- 429: Too many login attempts
```

#### POST `/auth/refresh`
**Refresh access token**

```
Request:
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}

Response (200):
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 900
}
```

#### POST `/auth/logout`
**Invalidate tokens**

```
Request: (authenticated)
{}

Response (200):
{
  "message": "Logged out successfully"
}
```

#### POST `/auth/verify-email`
**Confirm email with OTP**

```
Request:
{
  "email": "john@example.com",
  "otp": "123456"
}

Response (200):
{
  "message": "Email verified successfully",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### POST `/auth/verify-phone`
**Confirm phone with OTP**

```
Request:
{
  "phone": "+918765432109",
  "otp": "654321"
}

Response (200):
{
  "message": "Phone verified successfully"
}
```

#### POST `/auth/send-verification-otp`
**Resend verification OTP**

```
Request:
{
  "type": "EMAIL",  // EMAIL or PHONE
  "destination": "john@example.com"
}

Response (200):
{
  "message": "OTP sent successfully",
  "resend_available_after": 60
}
```

#### POST `/auth/forgot-password`
**Initiate password reset**

```
Request:
{
  "email": "john@example.com"
}

Response (200):
{
  "message": "Password reset link sent to email",
  "reset_token_expires_in": 3600
}
```

#### POST `/auth/reset-password`
**Reset password with token**

```
Request:
{
  "reset_token": "abc123xyz...",
  "new_password": "NewSecurePass@123"
}

Response (200):
{
  "message": "Password reset successfully"
}
```

---

### **2. USER PROFILE ENDPOINTS** (`/users`)

#### GET `/users/me`
**Get own profile (authenticated)**

```
Response (200):
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "john@example.com",
    "phone": "+918765432109",
    "role": "DONOR",
    "email_verified": true,
    "phone_verified": true,
    "id_verified": false,
    "created_at": "2026-04-01T10:30:00Z"
  },
  "profile": {
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1990-05-15",
    "gender": "MALE",
    "city": "Mumbai",
    "state": "Maharashtra",
    "blood_group": "O+",
    "latitude": 19.0760,
    "longitude": 72.8777,
    "profile_photo_url": "https://cdn.example.com/photos/...",
    "allergies": "Penicillin",
    "emergency_contact_name": "Jane Doe",
    "emergency_contact_phone": "+918765432100"
  }
}
```

#### PUT `/users/me`
**Update own profile**

```
Request:
{
  "first_name": "John",
  "city": "Bangalore",
  "latitude": 12.9716,
  "longitude": 77.5946,
  "allergies": "Penicillin, Aspirin"
}

Response (200):
{
  "message": "Profile updated successfully",
  "profile": {...}
}
```

#### POST `/users/me/upload-id`
**Upload Aadhaar-like verification document**

```
Request: (multipart/form-data)
{
  "document": <FILE>,
  "document_type": "AADHAAR"  // AADHAAR, PASSPORT, VOTER_ID
}

Response (201):
{
  "message": "Document uploaded successfully",
  "document_url": "https://cdn.example.com/docs/...",
  "verification_pending": true,
  "admin_review_required": true
}
```

#### GET `/users/{user_id}`
**Get public profile of another user (limited info)**

```
Response (200):
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "first_name": "John",
  "last_name": "Doe",
  "city": "Mumbai",
  "rating": 4.8,
  "donations_count": 5,
  "profile_photo_url": "https://cdn.example.com/photos/..."
}
```

#### GET `/users/me/stats`
**Get personal donation statistics**

```
Response (200):
{
  "total_donations": 5,
  "total_lives_saved": 2,
  "blood_donations": 3,
  "organ_donations": 0,
  "last_donation_date": "2026-03-15",
  "next_eligible_date": "2026-04-12",
  "rating": 4.8,
  "badges": ["5x Donor", "Verified", "Active"]
}
```

---

### **3. DONOR ENDPOINTS** (`/donors`)

#### POST `/donors/register`
**Register as a blood/organ donor**

```
Request: (authenticated, user must have DONOR role)
{
  "can_donate_blood": true,
  "blood_donation_last_date": "2026-03-15",
  "organ_types": ["KIDNEY", "HEART"],
  "organ_donation_registered": true,
  "organ_registration_certificate_url": "https://cdn.example.com/certs/...",
  "willing_hospital_list": ["HOSP_001", "HOSP_002"],
  "preferred_donation_time": "MORNING",
  "medical_clearance_report_url": "https://cdn.example.com/reports/..."
}

Response (201):
{
  "donor_id": "550e8400-e29b-41d4-a716-446655440001",
  "message": "Donor profile created successfully",
  "medical_clearance_pending": false
}
```

#### GET `/donors/me`
**Get own donor profile (authenticated)**

```
Response (200):
{
  "donor_id": "550e8400-e29b-41d4-a716-446655440001",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "is_available": true,
  "can_donate_blood": true,
  "blood_donation_eligible_date": "2026-04-12",
  "organ_types": ["KIDNEY", "HEART"],
  "organ_donation_registered": true,
  "medical_clearance": true,
  "blood_donations_count": 5,
  "organ_donations_count": 0,
  "lives_saved": 2
}
```

#### PUT `/donors/me`
**Update donor profile**

```
Request:
{
  "is_available": false,
  "availability_reason": "Sick leave",
  "willing_hospital_list": ["HOSP_001", "HOSP_003"],
  "preferred_donation_time": "AFTERNOON"
}

Response (200):
{
  "message": "Donor profile updated successfully",
  "donor": {...}
}
```

#### PUT `/donors/me/availability`
**Quick toggle availability**

```
Request:
{
  "is_available": true,
  "reason": "Ready to donate"
}

Response (200):
{
  "message": "Availability updated",
  "is_available": true,
  "updated_at": "2026-04-12T14:30:00Z"
}
```

#### GET `/donors/nearby?latitude=19.0760&longitude=72.8777&radius=50`
**Get nearby available donors (for Admin/Hospital)**

```
Response (200):
{
  "donors": [
    {
      "donor_id": "...",
      "first_name": "John",
      "blood_group": "O+",
      "distance_km": 2.5,
      "is_available": true,
      "organ_types": ["KIDNEY"],
      "rating": 4.8
    }
  ],
  "total_count": 5
}
```

#### GET `/donors/available-by-type?organ_type=KIDNEY&blood_group=O+`
**Filter donors by organ/blood type**

```
Response (200):
{
  "donors": [
    {
      "donor_id": "...",
      "city": "Mumbai",
      "distance_km": 5.0
    }
  ],
  "count": 10
}
```

---

### **4. RECIPIENT ENDPOINTS** (`/recipients`)

#### POST `/recipients/register`
**Register as a blood/organ recipient**

```
Request: (authenticated, user must have RECIPIENT role)
{
  "primary_disease": "End-stage renal disease",
  "diagnosis_date": "2025-06-01",
  "surgery_needed_date": "2026-05-15",
  "hospital_name": "Apollo Hospitals, Mumbai",
  "hospital_contact_phone": "+919876543210",
  "doctor_name": "Dr. Ramesh Kumar",
  "doctor_phone": "+919876543211",
  "doctor_registration_number": "MCI_123456",
  "is_verified_by_hospital": false,
  "matching_criteria": {
    "blood_group": "O+",
    "organ_type": "KIDNEY",
    "hla_compatibility": false
  }
}

Response (201):
{
  "recipient_id": "550e8400-e29b-41d4-a716-446655440002",
  "message": "Recipient profile created successfully",
  "verification_pending": true
}
```

#### GET `/recipients/me`
**Get own recipient profile**

```
Response (200):
{
  "recipient_id": "550e8400-e29b-41d4-a716-446655440002",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "primary_disease": "End-stage renal disease",
  "urgency_level": "CRITICAL",
  "hospital_name": "Apollo Hospitals, Mumbai",
  "doctor_name": "Dr. Ramesh Kumar",
  "is_verified_by_hospital": false,
  "matching_criteria": {...}
}
```

#### PUT `/recipients/me`
**Update recipient profile**

```
Request:
{
  "surgery_needed_date": "2026-06-01",
  "urgency_level": "CRITICAL"
}

Response (200):
{
  "message": "Recipient profile updated successfully"
}
```

---

### **5. REQUEST ENDPOINTS** (`/requests`)

#### POST `/requests`
**Create a new blood/organ request (authenticated as recipient)**

```
Request:
{
  "request_type": "BLOOD",
  "blood_group_needed": "O+",
  "quantity_needed": 4,
  "urgency_level": "CRITICAL",
  "needed_by": "2026-04-13T12:00:00Z",
  "hospital_location": {
    "latitude": 19.0760,
    "longitude": 72.8777,
    "address": "Apollo Hospitals, Bandra, Mumbai"
  },
  "hospital_name": "Apollo Hospitals",
  "receiving_doctor_name": "Dr. Ramesh",
  "receiving_doctor_phone": "+919876543211",
  "clinical_notes": "Emergency blood transfusion needed",
  "required_tests": ["COVID", "HIV", "HBsAg"],
  "is_public": true
}

Response (201):
{
  "request_id": "550e8400-e29b-41d4-a716-446655440003",
  "status": "OPEN",
  "message": "Request created successfully. Searching for matches...",
  "matching_in_progress": true
}
```

#### GET `/requests/{request_id}`
**Get request details**

```
Response (200):
{
  "request_id": "550e8400-e29b-41d4-a716-446655440003",
  "request_type": "BLOOD",
  "blood_group_needed": "O+",
  "urgency_level": "CRITICAL",
  "status": "MATCHED",
  "hospital_name": "Apollo Hospitals",
  "created_at": "2026-04-12T10:00:00Z",
  "needed_by": "2026-04-13T12:00:00Z",
  "matched_donor": {
    "donor_id": "...",
    "first_name": "John",
    "distance_km": 2.5
  },
  "matches": [
    {
      "match_id": "...",
      "donor_id": "...",
      "compatibility_score": 95.0,
      "status": "NOTIFIED"
    }
  ]
}
```

#### GET `/requests?status=OPEN&urgency_level=CRITICAL&limit=20&offset=0`
**List requests with filters**

```
Response (200):
{
  "requests": [
    {
      "request_id": "...",
      "request_type": "BLOOD",
      "blood_group_needed": "O+",
      "urgency_level": "CRITICAL",
      "status": "OPEN",
      "hospital_location": {...},
      "created_at": "2026-04-12T10:00:00Z",
      "matches_found": 3
    }
  ],
  "total_count": 50,
  "limit": 20,
  "offset": 0
}
```

#### PUT `/requests/{request_id}`
**Update request (recipient only)**

```
Request:
{
  "urgency_level": "CRITICAL",
  "quantity_needed": 5
}

Response (200):
{
  "message": "Request updated successfully"
}
```

#### POST `/requests/{request_id}/cancel`
**Cancel a request**

```
Response (200):
{
  "message": "Request cancelled successfully",
  "status": "CANCELLED"
}
```

#### GET `/requests/{request_id}/matches`
**Get all matches for a request**

```
Response (200):
{
  "matches": [
    {
      "match_id": "...",
      "donor_id": "...",
      "donor_name": "John Doe",
      "distance_km": 2.5,
      "compatibility_score": 98.0,
      "status": "NOTIFIED",
      "donor_response": "PENDING"
    }
  ],
  "total_matches": 5
}
```

---

### **6. MATCHING ENDPOINTS** (`/matches`)

#### GET `/matches/for-request/{request_id}`
**Get all matches for a specific request**

```
Response (200):
{
  "matches": [
    {
      "match_id": "...",
      "donor_id": "...",
      "donor_name": "John",
      "distance_km": 2.5,
      "compatibility_score": 95.5,
      "score_breakdown": {
        "blood_match": 100.0,
        "urgency_weight": 0.8,
        "distance_factor": 0.9
      },
      "status": "NOTIFIED",
      "created_at": "2026-04-12T10:05:00Z"
    }
  ],
  "total": 5
}
```

#### POST `/matches/{match_id}/accept`
**Donor accepts a match**

```
Request: (authenticated as donor)
{
  "appointment_preferred_date": "2026-04-13",
  "appointment_preferred_time": "10:00",
  "notes": "Can donate in the morning"
}

Response (200):
{
  "message": "Match accepted",
  "match_id": "...",
  "status": "ACCEPTED",
  "appointment_details": {...}
}
```

#### POST `/matches/{match_id}/reject`
**Donor rejects a match**

```
Request:
{
  "reason": "Currently unavailable",
  "details": "Have flu symptoms"
}

Response (200):
{
  "message": "Match rejected",
  "status": "REJECTED"
}
```

#### POST `/matches/{match_id}/complete`
**Mark a match as completed (admin)**

```
Request:
{
  "donation_date": "2026-04-13",
  "actual_units_donated": 4,
  "notes": "Successful donation",
  "verification_document_url": "https://..."
}

Response (200):
{
  "message": "Match marked as completed",
  "match_id": "...",
  "status": "COMPLETED"
}
```

---

### **7. NOTIFICATION ENDPOINTS** (`/notifications`)

#### GET `/notifications?limit=20&offset=0`
**Get notifications for authenticated user**

```
Response (200):
{
  "notifications": [
    {
      "notification_id": "...",
      "type": "REQUEST_MATCHED",
      "title": "New Donation Request Nearby",
      "message": "A CRITICAL blood request for O+ is 2km away",
      "is_read": false,
      "related_entity_type": "REQUEST",
      "related_entity_id": "...",
      "created_at": "2026-04-12T14:30:00Z",
      "expires_at": "2026-04-19T14:30:00Z"
    }
  ],
  "unread_count": 3
}
```

#### PUT `/notifications/{notification_id}/read`
**Mark notification as read**

```
Response (200):
{
  "message": "Notification marked as read"
}
```

#### POST `/notifications/mark-all-read`
**Mark all notifications as read**

```
Response (200):
{
  "message": "All notifications marked as read",
  "updated_count": 5
}
```

#### DELETE `/notifications/{notification_id}`
**Delete a notification**

```
Response (204): No Content
```

---

### **8. ADMIN ENDPOINTS** (`/admin`)

#### GET `/admin/users?role=DONOR&is_verified=false&limit=20`
**List users for verification**

```
Response (200):
{
  "users": [
    {
      "user_id": "...",
      "email": "john@example.com",
      "role": "DONOR",
      "email_verified": true,
      "id_verified": false,
      "id_document_url": "https://...",
      "created_at": "2026-04-01",
      "registration_status": "PENDING_ID_VERIFICATION"
    }
  ],
  "total_count": 45
}
```

#### POST `/admin/verify-user/{user_id}`
**Verify user's identity**

```
Request: (admin only)
{
  "verified": true,
  "notes": "Documents verified successfully"
}

Response (200):
{
  "message": "User verified successfully",
  "user_id": "..."
}
```

#### POST `/admin/block-user/{user_id}`
**Block a user account**

```
Request:
{
  "reason": "FRAUD",
  "details": "Multiple false donation claims"
}

Response (200):
{
  "message": "User blocked successfully"
}
```

#### GET `/admin/requests?status=FLAGGED&limit=20`
**Get flagged requests for review**

```
Response (200):
{
  "requests": [
    {
      "request_id": "...",
      "recipient_id": "...",
      "flag_reason": "POTENTIAL_FRAUD",
      "flagged_at": "2026-04-12T12:00:00Z",
      "request_details": {...}
    }
  ],
  "total": 10
}
```

#### POST `/admin/requests/{request_id}/approve`
**Approve a flagged request**

```
Request:
{
  "notes": "Verified with hospital"
}

Response (200):
{
  "message": "Request approved"
}
```

#### POST `/admin/requests/{request_id}/reject`
**Reject a flagged request**

```
Request:
{
  "reason": "FAKE_REQUEST",
  "details": "Hospital confirms no such patient"
}

Response (200):
{
  "message": "Request rejected and removed"
}
```

#### GET `/admin/analytics?date_from=2026-04-01&date_to=2026-04-12`
**Get analytics data**

```
Response (200):
{
  "period": {
    "from": "2026-04-01",
    "to": "2026-04-12"
  },
  "metrics": {
    "total_donors": 1250,
    "total_recipients": 340,
    "new_requests": 125,
    "fulfilled_requests": 95,
    "success_rate": 76.0,
    "avg_matching_time_minutes": 12,
    "total_matches": 450
  },
  "blood_metrics": {
    "requests": 100,
    "fulfilled": 87,
    "success_rate": 87.0
  },
  "organ_metrics": {
    "requests": 25,
    "fulfilled": 8,
    "success_rate": 32.0
  }
}
```

#### GET `/admin/audit-log?limit=50`
**Get audit trail**

```
Response (200):
{
  "actions": [
    {
      "action_id": "...",
      "admin_id": "...",
      "action_type": "VERIFY_ID",
      "target_entity_type": "USER",
      "target_entity_id": "...",
      "decision": "APPROVED",
      "reason": "Documents valid",
      "created_at": "2026-04-12T10:00:00Z"
    }
  ],
  "total": 1540
}
```

---

## 🔍 PAGINATION & FILTERING

All list endpoints support:
```
- limit: 10-100 (default: 20)
- offset: 0 onwards (default: 0)
- sort: ASC/DESC (default varies by endpoint)
- filters: Specific to each endpoint
```

---

## ⚠️ ERROR RESPONSES

### Standard Error Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ],
    "timestamp": "2026-04-12T14:30:00Z",
    "request_id": "req_123456"
  }
}
```

### Common Error Codes
| Code | HTTP | Meaning |
|------|------|---------|
| `AUTH_REQUIRED` | 401 | Missing or invalid token |
| `UNAUTHORIZED` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Invalid input data |
| `DUPLICATE_ENTRY` | 409 | Record already exists |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal server error |

---

## 📡 WEBSOCKET EVENTS (Real-time Notifications)

```javascript
// Client connects
io.connect('wss://api.blooddonation.com/notifications')

// Subscribe to events
Emit: {type: 'subscribe', channel: 'new_requests'}

// Receive real-time updates
On: 'request_matched' -> {
  request_id: '...',
  blood_group: 'O+',
  distance_km: 2.5,
  urgency: 'CRITICAL'
}
```
