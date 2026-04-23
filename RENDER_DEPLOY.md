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
