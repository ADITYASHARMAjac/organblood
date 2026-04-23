# Deployment & Production Readiness Guide

## 🌐 Deployment Environments

### Development
- Single-node Docker Compose setup
- SQLite or local PostgreSQL
- In-memory Redis
- Debug mode enabled

### Staging
- Multi-container on staging server
- PostgreSQL with backups
- Redis cluster
- SSL certificates
- Monitoring enabled

### Production
- Kubernetes cluster (minimum 3 nodes)
- Managed database (RDS/Cloud SQL)
- Redis cluster with sentinel
- CDN for static assets
- Load balancer with SSL
- Monitoring & alerting
- Auto-scaling based on metrics

---

## 🏗️ AWS Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Route 53 (DNS)                      │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│            CloudFront + WAF                             │
│  (Static assets, DDoS protection)                       │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│        Application Load Balancer (ALB)                  │
│     (SSL Termination, Route Distribution)              │
└────────────┬──────────────┬──────────────┬──────────────┘
             │              │              │
    ┌────────▼──┐   ┌───────▼──┐   ┌──────▼────┐
    │ ECS Task 1│   │ ECS Task 2│   │ ECS Task 3│
    │(FastAPI)  │   │(FastAPI)  │   │(FastAPI)  │
    └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
          │               │               │
          └───────────────┼───────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐   ┌──────────┐
    │ RDS      │    │ ElastiC  │   │ S3       │
    │PostgreSQL│   │Cache     │   │(Storage) │
    │(Primary) │   │(Redis)   │   │          │
    └────┬─────┘    └──────────┘   └──────────┘
         │
         ▼
    ┌──────────┐
    │ RDS      │
    │PostgreSQL│
    │(Replica) │
    └──────────┘
```

---

## 📋 Pre-Deployment Checklist

### Code & Quality
- [ ] All tests passing (>80% coverage)
- [ ] Code review completed
- [ ] Security scan passed (Snyk/Trivy)
- [ ] Load testing done (target: 1000 concurrent users)
- [ ] Performance baselines set

### Infrastructure
- [ ] SSL certificates configured
- [ ] Database backups tested
- [ ] Cache layer operational
- [ ] Load balancer configured
- [ ] Auto-scaling policies set (scale up at 70% CPU, down at 30%)

### Security
- [ ] Environment variables configured
- [ ] Secrets stored in vault (AWS Secrets Manager)
- [ ] API rate limiting enabled
- [ ] CORS configured for production domain
- [ ] WAF rules configured
- [ ] DDoS protection enabled

### Monitoring & Logging
- [ ] CloudWatch dashboards created
- [ ] Alarms configured (high memory, high latency, errors)
- [ ] Centralized logging setup (ELK/CloudWatch Logs)
- [ ] Error tracking (Sentry) configured
- [ ] Performance monitoring (NewRelic/DataDog) configured

---

## 🚀 AWS ECS Deployment Steps

### Step 1: Create RDS PostgreSQL Instance
```bash
aws rds create-db-instance \
  --db-instance-identifier donation-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --allocated-storage 20 \
  --storage-type gp2 \
  --master-username donation_user \
  --master-user-password <secure-password> \
  --publicly-accessible false \
  --backup-retention-period 7
```

### Step 2: Create ElastiCache Redis Cluster
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id donation-cache \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1 \
  --auto-minor-version-upgrade \
  --publicly-accessible false
```

### Step 3: Create ECR Repositories
```bash
# Backend
aws ecr create-repository \
  --repository-name donation-api \
  --region us-east-1

# Frontend
aws ecr create-repository \
  --repository-name donation-frontend \
  --region us-east-1
```

### Step 4: Build & Push Images
```bash
# Backend
docker build -t donation-api:latest backend/
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

docker tag donation-api:latest <account>.dkr.ecr.us-east-1.amazonaws.com/donation-api:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/donation-api:latest

# Frontend
docker build -t donation-frontend:latest frontend/
docker tag donation-frontend:latest <account>.dkr.ecr.us-east-1.amazonaws.com/donation-frontend:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/donation-frontend:latest
```

### Step 5: Create ECS Task Definitions
See `k8s/ecs-task-definitions.json`

### Step 6: Create ECS Service
```bash
aws ecs create-service \
  --cluster donation-cluster \
  --service-name donation-api-service \
  --task-definition donation-api:1 \
  --desired-count 3 \
  --launch-type EC2 \
  --load-balancers targetGroupArn=<arn>,containerName=api,containerPort=8000
```

---

## 🐳 Kubernetes Deployment (GCP GKE)

### Step 1: Create GKE Cluster
```bash
gcloud container clusters create donation-cluster \
  --num-nodes 3 \
  --enable-autoscaling \
  --min-nodes 2 \
  --max-nodes 10 \
  --region us-central1
```

### Step 2: Create Docker Images
See AWS section above (steps 4)

### Step 3: Push to Google Container Registry
```bash
docker tag donation-api:latest gcr.io/<project>/donation-api:latest
gcloud docker -- push gcr.io/<project>/donation-api:latest
```

### Step 4: Create Kubernetes ConfigMaps & Secrets
```bash
kubectl create configmap app-config \
  --from-literal=APP_ENV=production \
  --from-literal=DEBUG=false

kubectl create secret generic app-secrets \
  --from-literal=JWT_SECRET_KEY=<secret> \
  --from-literal=DATABASE_URL=<url>
```

### Step 5: Deploy Services
```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

### Step 6: Configure Autoscaling
```bash
kubectl autoscale deployment donation-api \
  --min=3 --max=10 \
  --cpu-percent=70
```

---

## 📊 Monitoring Setup

### CloudWatch Dashboards
```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/ApplicationELB", "TargetResponseTime"],
          ["AWS/ApplicationELB", "RequestCount"],
          ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count"],
          ["AWS/RDS", "DatabaseConnections"],
          ["AWS/RDS", "CPUUtilization"]
        ],
        "period": 60,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Donation Portal Metrics"
      }
    }
  ]
}
```

### Alarms to Configure
```bash
# High API Response Time
aws cloudwatch put-metric-alarm \
  --alarm-name donation-api-slow-response \
  --alarm-description "Alert when API response time > 500ms" \
  --metric-name TargetResponseTime \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 300 \
  --threshold 0.5 \
  --comparison-operator GreaterThanThreshold

# Database Connection Issues
aws cloudwatch put-metric-alarm \
  --alarm-name donation-db-connection-count \
  --alarm-description "Alert when DB connections > 80" \
  --metric-name DatabaseConnections \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold
```

---

## 🔄 CI/CD Pipeline (GitHub Actions)

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          pip install -r backend/requirements.txt
          pytest backend/tests -v --cov

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build backend image
        run: docker build -t donation-api:${{ github.sha }} backend/
      - name: Push to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY
          docker push $ECR_REGISTRY/donation-api:${{ github.sha }}

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster donation-cluster \
            --service donation-api-service \
            --force-new-deployment
```

---

## 🔐 Security Hardening

### SSL/TLS Configuration
```nginx
server {
    listen 443 ssl http2;
    server_name api.blooddonation.com;
    
    ssl_certificate /etc/ssl/certs/api.crt;
    ssl_certificate_key /etc/ssl/private/api.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    location / {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Database Backup Strategy
```bash
# Automated daily backup
0 2 * * * /usr/local/bin/backup-postgres.sh

# Backup script
#!/bin/bash
BACKUP_DIR="/backups/postgres"
DB_NAME="donation_db"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
pg_dump -U donation_user $DB_NAME | gzip > $BACKUP_DIR/donation_db_$TIMESTAMP.sql.gz
```

---

## 📈 Scaling Strategies

### Horizontal Scaling
- Add more FastAPI instances behind load balancer
- Use ECS auto-scaling or Kubernetes HPA
- Target: 100 req/s per instance

### Vertical Scaling
- Increase instance type for CPU-bound operations
- Increase memory for caching layer
- Use read replicas for database

### Caching Strategy
- Redis cluster for session management
- Cache API responses (5-15 min TTL)
- Use CDN for frontend assets

### Database Optimization
- Add database indexes
- Use connection pooling (pgBouncer)
- Archive old data to separate storage

---

## 📝 Runbooks

### Incident: API Down
1. Check load balancer health
2. Check ECS task logs
3. Check database connectivity
4. Check Redis connectivity
5. Rollback to last known good version
6. Page on-call engineer

### Incident: High Latency
1. Check database query performance
2. Check cache hit rate
3. Check CPU/memory usage
4. Trigger manual scaling
5. Investigate slow queries
6. Optimize or add indexes

### Incident: Database Corruption
1. Stop writes to database
2. Restore from backup
3. Verify data integrity
4. Resume writes
5. Run reconciliation checks
6. Post-mortem analysis

---

## ✅ Post-Deployment Validation

1. **Health Checks**
   ```bash
   curl https://api.blooddonation.com/health
   ```

2. **API Smoke Tests**
   ```bash
   pytest tests/smoke/ -v
   ```

3. **Load Test (10 min)**
   ```bash
   locust -f tests/load_test.py --host=https://api.blooddonation.com -u 100 -r 10 -t 10m
   ```

4. **End-to-End Flow**
   - Register user
   - Create donor profile
   - Create request
   - Verify matching
   - Check notifications

5. **Monitoring Review**
   - Dashboard OK
   - No error spikes
   - Latency baseline met
   - Cache hit rate >80%

---

## 📞 Rollback Procedure

```bash
# If deployment goes wrong:
aws ecs update-service \
  --cluster donation-cluster \
  --service donation-api-service \
  --task-definition donation-api:previous-version \
  --force-new-deployment

# Verify rollback
aws ecs describe-services \
  --cluster donation-cluster \
  --services donation-api-service
```
