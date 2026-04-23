# Railway DB Setup

## Database Type

This project uses PostgreSQL through SQLAlchemy and `psycopg2-binary`.

## Railway Deployment Steps

1. Create a `PostgreSQL` service in Railway.
2. Copy Railway's connection string into the backend `DATABASE_URL` variable.
3. Set the backend environment variables listed below.
4. Run the schema bootstrap command once:

```bash
python backend/scripts/prepare_railway_db.py
```

5. Start the backend normally. The app also calls `Base.metadata.create_all(...)` on startup, but the bootstrap step is the safer first run.

## Required Backend Environment Variables

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DB_NAME
JWT_SECRET_KEY=change-this-in-production
DEBUG=False
ENVIRONMENT=production
```

## Optional But Recommended Environment Variables

```env
REDIS_URL=redis://HOST:6379/0
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@example.com
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET_NAME=
AWS_REGION=us-east-1
CELERY_BROKER_URL=redis://HOST:6379/1
CELERY_RESULT_BACKEND=redis://HOST:6379/2
ADMIN_EMAIL=admin@example.com
ADMIN_PHONE=+919999999999
```

## PostgreSQL Objects Created

### Tables

- `users`
- `profiles`
- `donors`
- `recipients`
- `requests`
- `matches`
- `notifications`
- `admin_actions`
- `analytics`

### PostgreSQL Enums

- `user_role`
- `gender`
- `blood_group`
- `urgency_level_recip`
- `request_type`
- `urgency_level_req`
- `request_status`
- `match_status`
- `donor_response`
- `recipient_response`
- `notification_type_enum`
- `admin_action_type_enum`
- `action_status`

## Table Schema Summary

### `users`

- `id` `varchar(36)` primary key
- `email` `varchar(255)` unique not null
- `phone` `varchar(20)` unique not null
- `username` `varchar(100)` unique not null
- `password_hash` `varchar(255)` not null
- `email_verified` `boolean`
- `email_verified_at` `timestamp`
- `phone_verified` `boolean`
- `phone_verified_at` `timestamp`
- `id_verified` `boolean`
- `id_document_path` `varchar(500)`
- `id_verified_at` `timestamp`
- `role` `user_role` not null
- `is_active` `boolean`
- `is_blocked` `boolean`
- `block_reason` `varchar(500)`
- `refresh_token_hash` `varchar(255)`
- `last_login` `timestamp`
- `last_ip_address` `inet`
- `created_at` `timestamp`
- `updated_at` `timestamp`
- `deleted_at` `timestamp`

Indexes:
- `email`
- `phone`
- `role`
- `is_active`
- composite `idx_email_active`
- composite `idx_role_active`

### `profiles`

- `id` `varchar(36)` primary key
- `user_id` `varchar(36)` unique fk -> `users.id`
- `first_name` `varchar(100)` not null
- `last_name` `varchar(100)` not null
- `date_of_birth` `varchar(10)` not null
- `gender` `gender`
- `address` `text` not null
- `city` `varchar(100)` not null
- `state` `varchar(100)` not null
- `postal_code` `varchar(20)`
- `country` `varchar(100)`
- `latitude` `decimal(10,8)` not null
- `longitude` `decimal(11,8)` not null
- `blood_group` `blood_group`
- `allergies` `text`
- `chronic_diseases` `text`
- `current_medications` `text`
- `emergency_contact_name` `varchar(100)`
- `emergency_contact_phone` `varchar(20)`
- `emergency_contact_relation` `varchar(50)`
- `profile_photo_url` `varchar(500)`
- `id_photo_url` `varchar(500)`
- `medical_report_url` `varchar(500)`
- `created_at` `timestamp`
- `updated_at` `timestamp`

Indexes:
- `city`
- composite `idx_location`
- `idx_city`

### `donors`

- `id` `varchar(36)` primary key
- `user_id` `varchar(36)` unique fk -> `users.id`
- `profile_id` `varchar(36)` fk -> `profiles.id`
- `is_available` `boolean`
- `availability_updated_at` `timestamp`
- `can_donate_blood` `boolean`
- `blood_donation_last_date` `varchar(10)`
- `blood_donation_eligible_date` `varchar(10)`
- `organ_types` `json`
- `organ_donation_registered` `boolean`
- `organ_registration_certificate_url` `varchar(500)`
- `blood_donations_count` `integer`
- `organ_donations_count` `integer`
- `lives_saved` `integer`
- `preferred_donation_time` `varchar(50)`
- `willing_hospital_list` `json`
- `medical_clearance` `boolean`
- `medical_clearance_date` `varchar(10)`
- `medical_report_url` `varchar(500)`
- `created_at` `timestamp`
- `updated_at` `timestamp`

Indexes:
- `is_available`
- `idx_available`
- `idx_blood_eligible`

### `recipients`

- `id` `varchar(36)` primary key
- `user_id` `varchar(36)` unique fk -> `users.id`
- `profile_id` `varchar(36)` fk -> `profiles.id`
- `is_active` `boolean`
- `primary_disease` `varchar(255)`
- `diagnosis_date` `varchar(10)`
- `surgery_needed_date` `varchar(10)`
- `hospital_name` `varchar(255)`
- `hospital_contact_phone` `varchar(20)`
- `doctor_name` `varchar(100)`
- `doctor_phone` `varchar(20)`
- `doctor_registration_number` `varchar(50)`
- `is_verified_by_hospital` `boolean`
- `hospital_verification_date` `varchar(10)`
- `hospital_verification_document_url` `varchar(500)`
- `matching_criteria` `json` not null
- `urgency_level` `urgency_level_recip`
- `urgency_reason` `text`
- `hla_typing` `json`
- `created_at` `timestamp`
- `updated_at` `timestamp`

Indexes:
- `is_verified_by_hospital`
- `urgency_level`
- `idx_verified`

### `requests`

- `id` `varchar(36)` primary key
- `recipient_id` `varchar(36)` fk -> `recipients.id`
- `request_type` `request_type` not null
- `blood_group_needed` `varchar(5)`
- `organ_type_needed` `varchar(50)`
- `quantity_needed` `integer`
- `urgency_level` `urgency_level_req` not null
- `needed_by` `timestamp` not null
- `status` `request_status`
- `matched_donor_id` `varchar(36)`
- `matched_at` `timestamp`
- `hospital_location` `json` not null
- `hospital_name` `varchar(255)`
- `receiving_doctor_name` `varchar(100)`
- `receiving_doctor_phone` `varchar(20)`
- `clinical_notes` `text`
- `required_tests` `json`
- `additional_requirements` `text`
- `is_public` `boolean`
- `shared_with_hospitals` `json`
- `created_at` `timestamp`
- `updated_at` `timestamp`
- `expires_at` `timestamp`
- `fulfilled_at` `timestamp`

Indexes:
- `recipient_id`
- `request_type`
- `urgency_level`
- `status`
- `created_at`
- composite `idx_blood_organ_status`

### `matches`

- `id` `varchar(36)` primary key
- `request_id` `varchar(36)` fk -> `requests.id`
- `donor_id` `varchar(36)` fk -> `donors.id`
- `compatibility_score` `decimal(5,2)` not null
- `distance_km` `decimal(10,2)` not null
- `score_components` `json` not null
- `status` `match_status`
- `donor_response` `donor_response`
- `donor_response_at` `timestamp`
- `donor_response_reason` `text`
- `recipient_response` `recipient_response`
- `recipient_response_at` `timestamp`
- `appointment_scheduled_at` `timestamp`
- `donation_completed_at` `timestamp`
- `donation_failed_reason` `text`
- `created_at` `timestamp`
- `updated_at` `timestamp`

Constraints:
- unique `unique_request_donor` on (`request_id`, `donor_id`)

Indexes:
- `request_id`
- `donor_id`
- `compatibility_score`
- `status`

### `notifications`

- `id` `varchar(36)` primary key
- `user_id` `varchar(36)` fk -> `users.id`
- `notification_type` `notification_type_enum` not null
- `title` `varchar(255)` not null
- `message` `text` not null
- `related_entity_type` `varchar(50)`
- `related_entity_id` `varchar(36)`
- `is_read` `boolean`
- `read_at` `timestamp`
- `deliver_via` `json`
- `email_sent` `boolean`
- `sms_sent` `boolean`
- `push_sent` `boolean`
- `delivery_attempts` `integer`
- `last_delivery_attempt` `timestamp`
- `created_at` `timestamp`
- `expires_at` `timestamp`

Indexes:
- `user_id`
- `notification_type`
- `is_read`
- `created_at`
- composite `idx_user_unread`

### `admin_actions`

- `id` `varchar(36)` primary key
- `admin_id` `varchar(36)` fk -> `users.id`
- `action_type` `admin_action_type_enum` not null
- `target_entity_type` `varchar(50)` not null
- `target_entity_id` `varchar(36)` not null
- `decision` `text`
- `reason` `text`
- `evidence_urls` `json`
- `status` `action_status`
- `status_updated_by` `varchar(36)` fk -> `users.id`
- `status_updated_at` `timestamp`
- `created_at` `timestamp`
- `action_at` `timestamp`

Indexes:
- `admin_id`
- `action_type`
- `target_entity_id`
- composite `idx_admin_action_type`

### `analytics`

- `id` `varchar(36)` primary key
- `date` `varchar(10)` unique not null
- `total_donors` `integer`
- `total_recipients` `integer`
- `active_donors` `integer`
- `active_recipients` `integer`
- `new_requests` `integer`
- `fulfilled_requests` `integer`
- `pending_requests` `integer`
- `total_matches` `integer`
- `successful_matches` `integer`
- `match_success_rate` `decimal(5,2)`
- `blood_requests` `integer`
- `blood_fulfilled` `integer`
- `organ_requests` `integer`
- `organ_fulfilled` `integer`
- `avg_response_time_minutes` `integer`
- `avg_matching_time_minutes` `integer`
- `top_requesting_city` `varchar(100)`
- `top_donor_city` `varchar(100)`
- `created_at` `timestamp`

Indexes:
- `date`

## Required Items For Railway

### Minimum services

- 1 Railway backend service
- 1 Railway PostgreSQL service

### Optional services

- 1 Railway Redis service if you use Celery or Redis-backed features

### Python packages already required by this app

- `sqlalchemy`
- `psycopg2-binary`
- `fastapi`
- `uvicorn`
- `pydantic-settings`

### Runtime notes

- No PostGIS is required.
- No custom PostgreSQL extensions are required for the current schema.
- UUIDs are generated in Python, not by PostgreSQL.
- JSON columns are plain SQLAlchemy `JSON`, which PostgreSQL supports directly.

## Suggested Railway Start And Init Commands

### One-time schema init

```bash
python backend/scripts/prepare_railway_db.py
```

### Backend start

```bash
uvicorn app.main:create_app --factory --host 0.0.0.0 --port $PORT
```

Run the start command from the `backend` directory.
