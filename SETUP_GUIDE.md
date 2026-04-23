# Blood & Organ Donation Portal - Setup & Running Guide

## 🚀 Quick Start (Docker)

### Prerequisites
- Docker & Docker Compose installed
- Git installed

### Step 1: Clone/Setup Project
```bash
cd "c:\est full stack"
```

### Step 2: Start Services with Docker Compose
```bash
docker-compose up -d
```

This will start:
- PostgreSQL (port 5432)
- Redis (port 6379)
- FastAPI Backend (port 8000)
- Celery Worker
- Celery Beat
- React Frontend (port 3000)

### Step 3: Initialize Database
```bash
docker-compose exec api alembic upgrade head
```

### Step 4: Access Services
- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/api/v1/docs
- **Health Check:** http://localhost:8000/health

---

## 🛠️ Local Development Setup (Without Docker)

### Backend Setup

#### 1. Create Python Virtual Environment
```bash
cd backend
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

#### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your configuration
```

#### 4. Setup PostgreSQL
```bash
# Create database and user
createuser -P donation_user  # Password: secure_password
createdb -O donation_user donation_db
```

#### 5. Run Migrations
```bash
alembic upgrade head
```

#### 6. Start FastAPI Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 7. Start Redis
```bash
redis-server
```

#### 8. Start Celery Worker (in another terminal)
```bash
celery -A app.celery_tasks worker --loglevel=info
```

#### 9. Start Celery Beat (in another terminal)
```bash
celery -A app.celery_tasks beat --loglevel=info
```

### Frontend Setup

#### 1. Navigate to Frontend Directory
```bash
cd frontend
```

#### 2. Install Dependencies
```bash
npm install
```

#### 3. Configure Environment
```bash
# Create .env file
echo "REACT_APP_API_URL=http://localhost:8000" > .env
echo "REACT_APP_MAPBOX_TOKEN=your-mapbox-token" >> .env
```

#### 4. Start Development Server
```bash
npm start
```

---

## 🧪 Testing

### Running Unit Tests
```bash
# Backend
cd backend
pytest tests/unit -v --cov=app

# Frontend
cd frontend
npm test
```

### Running Integration Tests
```bash
cd backend
pytest tests/integration -v
```

### Load Testing
```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load_test.py --host=http://localhost:8000
```

---

## 📝 API Endpoints Guide

### Authentication
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "phone": "+918765432109",
    "username": "user123",
    "password": "SecurePass@123",
    "role": "DONOR"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass@123"
  }'
```

### Interactive API Documentation
Visit: http://localhost:8000/api/v1/docs

---

## 📚 Project Structure

```
blood-donation-portal/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Configuration
│   │   ├── models/              # Database models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── api/                 # API endpoints
│   │   ├── services/            # Business logic
│   │   ├── core/                # Security, exceptions
│   │   └── utils/               # Utility functions
│   ├── tests/                   # Test suites
│   ├── requirements.txt         # Python dependencies
│   └── Dockerfile              # Backend Docker image
│
├── frontend/
│   ├── src/
│   ├── package.json            # Node dependencies
│   └── Dockerfile              # Frontend Docker image
│
├── docker-compose.yml          # Multi-container setup
├── ARCHITECTURE.md             # System design
├── DATABASE_SCHEMA.md          # DB structure
├── API_SPECIFICATION.md        # API docs
└── IMPLEMENTATION_PLAN.md      # Development roadmap
```

---

## 🐛 Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
psql -U donation_user -d donation_db -c "SELECT 1"

# If connection fails:
# Check .env DATABASE_URL
# Ensure PostgreSQL service is running
```

### Redis Connection Issues
```bash
# Check Redis is running
redis-cli ping

# Should return: PONG
```

### API Port Already in Use
```bash
# On Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# On macOS/Linux
lsof -ti:8000 | xargs kill -9
```

### Frontend Build Issues
```bash
# Clear node modules and reinstall
rm -rf frontend/node_modules
npm install
npm start
```

---

## 📊 Database Migrations

### Create New Migration
```bash
alembic revision --autogenerate -m "Add new table"
```

### Apply Migrations
```bash
alembic upgrade head
```

### Rollback Migration
```bash
alembic downgrade -1
```

---

## 🔐 Security Checklist

- [ ] Change JWT_SECRET_KEY in production
- [ ] Change database password
- [ ] Enable HTTPS/SSL certificates
- [ ] Set DEBUG=False in production
- [ ] Update CORS_ORIGINS for production domain
- [ ] Configure email service credentials
- [ ] Set up SMS provider (Twilio)
- [ ] Configure AWS S3 credentials
- [ ] Enable rate limiting
- [ ] Set up monitoring & alerting

---

## 📈 Performance Optimization

1. **Database Indexing:** Run optimization scripts (in DATABASE_SCHEMA.md)
2. **Redis Caching:** Enabled for frequently accessed data
3. **Async Processing:** Celery handles heavy tasks
4. **Load Balancing:** Deploy multiple API instances
5. **CDN:** Use for static assets (frontend build)

---

## 🚢 Production Deployment

### Using Kubernetes
```bash
# Build images
docker build -t donation-api:latest backend/
docker build -t donation-frontend:latest frontend/

# Apply Kubernetes configs
kubectl apply -f k8s/
```

### Using Cloud Platform (AWS/GCP/Azure)
1. Push images to container registry
2. Configure managed database (RDS/Cloud SQL)
3. Configure managed cache (ElastiCache/Memorystore)
4. Deploy using Cloud Run / App Engine / AKS
5. Configure auto-scaling policies

---

## 📞 Support & Contact

- **Documentation:** See ARCHITECTURE.md, DATABASE_SCHEMA.md
- **API Docs:** http://localhost:8000/api/v1/docs
- **Issues:** Create GitHub issue

---

## 📄 License

This project is proprietary and intended for Blood & Organ Donation purposes.
