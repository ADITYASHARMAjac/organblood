# Render Deploy Guide

## What Was Added

- `render.yaml` to create:
  - Render Postgres database
  - FastAPI backend web service
  - React static frontend
- `backend/.python-version` to pin Python on Render
- backend config support for:
  - reliable `DEBUG` parsing
  - `CORS_ORIGINS` from env as JSON array or comma-separated list

## Deploy Steps

1. Push this repo to GitHub.
2. In Render, create a new Blueprint and point it to this repo.
3. Render will create:
   - `donation-portal-db`
   - `donation-portal-api`
   - `donation-portal-web`

## Required Manual Environment Values After Blueprint Creation

### Backend: `donation-portal-api`

Set these values in Render:

- `CORS_ORIGINS`
  - Recommended format:
  ```env
  ["https://your-frontend-name.onrender.com"]
  ```
- Or set:
  ```env
  CORS_ORIGIN_REGEX=^https://.*\.onrender\.com$
  ```

Optional if you use these features:

- `ADMIN_EMAIL`
- `ADMIN_PHONE`
- `SMTP_SERVER`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_S3_BUCKET_NAME`
- `AWS_REGION`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`

### Frontend: `donation-portal-web`

Set:

```env
REACT_APP_API_URL=https://your-backend-name.onrender.com
```

This is required because the frontend is deployed as a separate static site and must know the backend's public URL.

## Render Services

### Backend

- Root directory: `backend`
- Build command:
```bash
pip install -r requirements.txt
```
- Pre-deploy command:
```bash
python scripts/prepare_railway_db.py
```
- Start command:
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
- Health check:
```text
/health
```

### Frontend

- Root directory: `frontend`
- Build command:
```bash
npm ci && npm run build
```
- Publish directory:
```text
build
```
- Rewrite rule:
```text
/* -> /index.html
```

## Notes

- The backend startup already calls `Base.metadata.create_all(...)`, but the pre-deploy bootstrap makes the first deploy more reliable.
- Demo seed users and dummy workflow data do not run in production when `DEBUG=false` and `ENVIRONMENT=production`.
- Render Postgres private connection is wired automatically through the Blueprint using `fromDatabase.connectionString`.

## One-Time Production Bootstrap (Users + Starter Requests)

If login returns `401 Invalid email or password` right after deploy, your production DB likely has no demo users yet.

### If Render Shell is unavailable (free instance)

Use deploy-time bootstrap toggle:

1. In backend service env vars, set:
```env
RUN_BOOTSTRAP_ON_DEPLOY=true
BOOTSTRAP_USER_PASSWORD=YourStrongPassword@123
```
2. Trigger a manual deploy.
3. After deploy succeeds, set:
```env
RUN_BOOTSTRAP_ON_DEPLOY=false
```

The `render.yaml` pre-deploy command will run schema prep and then run bootstrap only when `RUN_BOOTSTRAP_ON_DEPLOY=true`.

### If Render Shell is available

Run this once from your Render backend service shell:

```bash
cd /opt/render/project/src/backend
python scripts/bootstrap_production_data.py --yes
```

What it creates/updates (idempotent):
- `admin@blooddonation.com`
- `donor@blooddonation.com`
- `recipient@blooddonation.com`
- donor/recipient profile records
- donor capability flags
- starter `OPEN` requests that are visible in donor queues

Default password for all bootstrap users:

```text
SecurePass@123
```

To set a custom password instead:

```bash
python scripts/bootstrap_production_data.py --yes --password "YourStrongPassword@123"
```

To bootstrap only users (no starter requests):

```bash
python scripts/bootstrap_production_data.py --yes --without-requests
```
