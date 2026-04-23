"""Blood & Organ Donation Portal API V1 - Comprehensive Quick Reference"""

# ==================== QUICK START COMMANDS ====================

# Docker Setup (Fastest Way)
"""
cd c:\est full stack
docker-compose up -d
docker-compose exec api alembic upgrade head
# Visit: http://localhost:3000
"""

# Local Setup
"""
# Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm start

# Celery (new terminal)
cd backend
celery -A app.celery_tasks worker --loglevel=info
"""

# ==================== KEY FILES ====================

"""
README.md                   ← Start here! Project overview
ARCHITECTURE.md            ← System design & components
DATABASE_SCHEMA.md         ← 9 tables with ERD
API_SPECIFICATION.md       ← 50+ endpoints with examples
IMPLEMENTATION_PLAN.md     ← 12-week development roadmap
SETUP_GUIDE.md            ← Detailed setup instructions
DEPLOYMENT_GUIDE.md       ← AWS/K8s deployment

backend/app/
├── main.py               ← FastAPI app
├── config.py            ← Configuration
├── models/              ← 9 SQLAlchemy models
├── schemas/             ← Pydantic validation
├── services/matching_engine.py  ← CORE ALGORITHM ⭐
├── api/v1/              ← All endpoints
└── celery_tasks/        ← Async jobs
"""

# ==================== CRITICAL FEATURES ====================

"""
1. MATCHING ALGORITHM (services/matching_engine.py)
   - Blood compatibility checking
   - Haversine distance calculation
   - Multi-factor scoring (0-100)
   - Top 5 matches ranked by score

2. AUTHENTICATION (core/security.py)
   - JWT tokens (access + refresh)
   - Password hashing (bcrypt)
   - OTP generation & verification
   - Role-based access control

3. REAL-TIME NOTIFICATIONS (celery_tasks/notification_tasks.py)
   - WebSocket events
   - Email delivery
   - SMS (Twilio)
   - Background processing

4. ADMIN PANEL
   - User verification workflow
   - Request approval/rejection
   - Fraud detection
   - Analytics dashboards
"""

# ==================== DATABASE SCHEMA ====================

"""
USER (2M records)
├─ Authentication: email, phone, password_hash
├─ Verification: email_verified, phone_verified, id_verified
├─ Account: role (DONOR/RECIPIENT/ADMIN), is_blocked
└─ Relationships: Profile (1:1), Donor (1:1), Recipient (1:1)

PROFILE (2M records)
├─ Personal: name, age, gender
├─ Location: city, latitude, longitude
├─ Medical: blood_group, allergies, chronic_diseases
└─ Emergency: contact_name, contact_phone

DONOR (200K records)
├─ Status: is_available, availability_updated_at
├─ Blood: can_donate_blood, blood_donation_last_date, eligible_date
├─ Organ: organ_types, organ_donation_registered
└─ History: blood_donations_count, lives_saved, medical_clearance

RECIPIENT (50K records)
├─ Medical: primary_disease, diagnosis_date, surgery_needed_date
├─ Hospital: hospital_name, doctor_name, doctor_phone
├─ Verification: is_verified_by_hospital, verification_document
└─ Matching: matching_criteria (JSON), urgency_level, hla_typing

REQUEST (10K active)
├─ Type: request_type (BLOOD/ORGAN/PLASMA)
├─ Details: blood_group_needed, organ_type_needed, quantity_needed
├─ Urgency: urgency_level, needed_by
├─ Status: status (OPEN/MATCHED/IN_PROGRESS/FULFILLED/CANCELLED/EXPIRED)
└─ Location: hospital_location, hospital_name, receiving_doctor

MATCH (50K records)
├─ Compatibility: compatibility_score (0-100), distance_km
├─ Status: status (SUGGESTED/NOTIFIED/ACCEPTED/REJECTED/COMPLETED)
├─ Responses: donor_response, donor_response_at, recipient_response
└─ Execution: appointment_scheduled_at, donation_completed_at

NOTIFICATION (1M records)
├─ Type: notification_type (REQUEST_MATCHED/NEW_REQUEST_NEARBY/etc)
├─ Content: title, message
├─ Delivery: deliver_via (IN_APP/EMAIL/SMS), is_read
└─ Status: delivery_attempts, last_delivery_attempt

ADMIN_ACTION (100K audit records)
├─ Action: action_type (VERIFY_ID/BLOCK_USER/REJECT_REQUEST/etc)
├─ Target: target_entity_type, target_entity_id
├─ Decision: decision, reason, evidence_urls
└─ Status: status (PENDING/APPROVED/REJECTED)

ANALYTICS (365 records, 1 per day)
├─ Users: total_donors, total_recipients, active_donors, active_recipients
├─ Requests: new_requests, fulfilled_requests, pending_requests
├─ Matches: total_matches, successful_matches, match_success_rate
└─ Performance: avg_response_time_minutes, avg_matching_time_minutes
"""

# ==================== API ENDPOINTS ====================

"""
AUTH (8 endpoints)
POST   /auth/register              ← Create user
POST   /auth/login                 ← Get JWT
POST   /auth/refresh               ← New access token
POST   /auth/logout                ← Logout
POST   /auth/verify-email          ← Email OTP
POST   /auth/verify-phone          ← Phone OTP
POST   /auth/forgot-password       ← Reset flow
POST   /auth/reset-password        ← New password

USERS (1 endpoint)
GET    /users/me                   ← Own profile
PUT    /users/me                   ← Update profile

DONORS (6 endpoints)
POST   /donors/register            ← Become donor
GET    /donors/me                  ← Donor profile
PUT    /donors/me                  ← Update profile
PUT    /donors/me/availability     ← Toggle availability
GET    /donors/nearby              ← Find nearby donors
GET    /donors/available-by-type   ← Filter by blood/organ

RECIPIENTS (3 endpoints)
POST   /recipients/register        ← Register as recipient
GET    /recipients/me              ← Recipient profile
PUT    /recipients/me              ← Update profile

REQUESTS (6 endpoints)
POST   /requests                   ← Create request
GET    /requests                   ← List requests
GET    /requests/{id}              ← Get details
PUT    /requests/{id}              ← Update
POST   /requests/{id}/cancel       ← Cancel
GET    /requests/{id}/matches      ← Get all matches

MATCHES (4 endpoints)
GET    /matches/for-request/{id}   ← All matches
POST   /matches/{id}/accept        ← Donor accept
POST   /matches/{id}/reject        ← Donor reject
POST   /matches/{id}/complete      ← Mark done

ADMIN (6 endpoints)
GET    /admin/users                ← User list
POST   /admin/verify-user/{id}     ← Verify user
POST   /admin/block-user/{id}      ← Block user
GET    /admin/requests             ← Flagged requests
GET    /admin/requests/{id}/approve ← Approve
GET    /admin/analytics            ← View metrics
"""

# ==================== MATCHING ALGORITHM CORE ====================

"""
BLOOD COMPATIBILITY:
O+ can give to: O+, O-, A+, A-, B+, B-, AB+, AB- (universal)
O- can give to: O+, O-, A+, A-, B+, B-, AB+, AB- (universal)
A+ can give to: A+, A-, AB+, AB-
A- can give to: A+, A-, AB+, AB-
B+ can give to: B+, B-, AB+, AB-
B- can give to: B+, B-, AB+, AB-
AB+ can give to: AB+, AB- (universal recipient)
AB- can give to: AB+, AB-

SCORING FORMULA:
1. Blood Match Score (0-100):
   - Perfect match (same type) = 100
   - Compatible = 90
   - Incompatible = 0

2. Distance Factor (0-1):
   - Using Haversine formula
   - Exponential decay: e^(-distance/radius)
   - Max radius: 100km (configurable)

3. Urgency Weight (0.4-1.0):
   - CRITICAL = 1.0 (highest priority)
   - MEDIUM = 0.7
   - LOW = 0.4

FINAL SCORE = (blood_match × 0.4 + distance_factor × 100 × 0.4) × urgency_weight × 100
Result: 0-100 score, sorted descending (98 = near-perfect match)

MATCHING PROCESS:
1. Query: Get all available donors with blood type match
2. Filter: Keep only within 100km radius
3. Score: Calculate compatibility for each donor
4. Rank: Sort by score descending
5. Return: Top 5 matches with notification
"""

# ==================== IMPORTANT CONFIGURATIONS ====================

"""
backend/.env.example
├─ DATABASE_URL=postgresql://user:pass@localhost:5432/db
├─ REDIS_URL=redis://localhost:6379/0
├─ JWT_SECRET_KEY=your-secret-key (CHANGE IN PRODUCTION!)
├─ SMTP settings (Gmail/SendGrid)
├─ JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
├─ JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
├─ DATABASE_URL (PostgreSQL connection)
├─ CELERY_BROKER_URL (Redis for Celery)
└─ AWS credentials for S3 uploads

Match Configuration:
├─ MATCH_SEARCH_RADIUS_KM=100
├─ TOP_MATCHES_RETURNED=5
├─ URGENCY_WEIGHT_CRITICAL=1.0
├─ URGENCY_WEIGHT_MEDIUM=0.7
└─ URGENCY_WEIGHT_LOW=0.4
"""

# ==================== TESTING COMMANDS ====================

"""
Unit Tests:
pytest tests/unit/test_matching_engine.py -v  ← Matching algorithm
pytest tests/unit/test_security.py -v         ← JWT & passwords
pytest tests/unit/ -v --cov=app               ← All with coverage

Integration Tests:
pytest tests/integration/test_auth_flow.py -v
pytest tests/integration/test_request_matching.py -v

E2E Tests:
pytest tests/e2e/test_donation_flow.py -v

Load Testing:
locust -f tests/load_test.py --host=http://localhost:8000 -u 1000 -r 100

Coverage Target: >80%
"""

# ==================== COMMON CURL EXAMPLES ====================

"""
# REGISTER
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "donor@example.com",
    "phone": "+918765432109",
    "username": "donor123",
    "password": "SecurePass@123",
    "role": "DONOR"
  }'

# LOGIN
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "donor@example.com", "password": "SecurePass@123"}'

# Use token in header
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/users/me

# CREATE BLOOD REQUEST
curl -X POST http://localhost:8000/api/v1/requests \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "request_type": "BLOOD",
    "blood_group_needed": "O+",
    "quantity_needed": 2,
    "urgency_level": "CRITICAL",
    "needed_by": "2026-04-13T12:00:00Z",
    "hospital_location": {
      "latitude": 19.0760,
      "longitude": 72.8777,
      "address": "Apollo Hospitals, Mumbai"
    },
    "hospital_name": "Apollo Hospitals",
    "receiving_doctor_name": "Dr. Ramesh"
  }'

# GET MATCHES
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/matches/for-request/<request_id>

# DONOR ACCEPT MATCH
curl -X POST http://localhost:8000/api/v1/matches/<match_id>/accept \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "appointment_preferred_date": "2026-04-13",
    "appointment_preferred_time": "10:00",
    "notes": "Can donate in morning"
  }'
"""

# ==================== DEPLOYMENT COMMANDS ====================

"""
DOCKER SETUP:
docker-compose up -d                          ← Start all services
docker-compose logs -f api                    ← View logs
docker-compose down                           ← Stop services
docker-compose exec api alembic upgrade head  ← Migrate DB

AWS DEPLOYMENT:
./scripts/deploy-aws.sh production            ← Deploy to AWS ECS

KUBERNETES:
kubectl apply -f k8s/deployment.yaml          ← Deploy to K8s
kubectl get pods                              ← Check status
kubectl logs <pod-name>                       ← View logs
"""

# ==================== TROUBLESHOOTING ====================

"""
API won't start?
✓ Check DATABASE_URL in .env
✓ Check PostgreSQL is running
✓ Check Redis is running
✓ Check .env file exists

Tests failing?
✓ Run: pytest tests/unit/test_matching_engine.py -v
✓ Check database is clean for tests
✓ Check redis connection

Frontend not connecting?
✓ Check REACT_APP_API_URL in .env
✓ Check CORS_ORIGINS in backend/.env
✓ Check npm packages installed: npm install

Matching not working?
✓ Check donor is marked "available"
✓ Check blood type compatibility
✓ Check request is within 100km radius
✓ See services/matching_engine.py for logic
"""

# ==================== NEXT STEPS ====================

"""
1. READ: README.md (15 min)
2. READ: ARCHITECTURE.md (20 min)
3. SETUP: Follow SETUP_GUIDE.md (30 min)
4. RUN: docker-compose up -d (2 min)
5. EXPLORE: Visit http://localhost:3000 & /api/v1/docs (10 min)
6. CODE: Start with backend/app/main.py (understand structure)
7. TEST: pytest tests/unit/ (verify setup)
8. BUILD: Follow IMPLEMENTATION_PLAN.md for features
"""

if __name__ == "__main__":
    print("""
    🩸💉 BLOOD & ORGAN DONATION PORTAL 🩸💉
    
    Quick reference guide created! 
    
    Start with: README.md
    Then: ARCHITECTURE.md
    Setup: SETUP_GUIDE.md
    
    All business logic in: backend/app/services/matching_engine.py
    All endpoints documented in: API_SPECIFICATION.md
    Database schema in: DATABASE_SCHEMA.md
    
    Happy coding! 🚀
    """)
