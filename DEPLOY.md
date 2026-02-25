# TravelAI Deployment Guide

## Quick Start - Docker (Recommended)

### Prerequisites
- Docker & Docker Compose installed
- At least 4GB RAM available

### Deploy with Docker Compose

```bash
cd travel_ai_app

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

**Services:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

---

## Deploy to Railway (Easiest)

1. **Push to GitHub**
```bash
git init
git add .
git commit -m "Initial commit"
git push origin main
```

2. **Connect to Railway**
- Go to https://railway.app
- Click "New Project" → "Deploy from GitHub repo"
- Select your repository

3. **Add Services**
- Add PostgreSQL database
- Add Redis
- Deploy backend (Dockerfile in /backend)
- Deploy frontend (Dockerfile in /frontend)

4. **Set Environment Variables**
```
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
SECRET_KEY=your-secret-key-here
```

---

## Deploy to Render

### Backend (Web Service)
1. Go to https://dashboard.render.com
2. Click "New" → "Web Service"
3. Connect your GitHub repo
4. Settings:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port 8000`
5. Add PostgreSQL database
6. Set environment variables

### Frontend (Static Site)
1. Click "New" → "Static Site"
2. Connect your GitHub repo
3. Settings:
   - **Root Directory:** `frontend`
   - **Build Command:** `npm install && npm run build`
   - **Publish Directory:** `out` (or `dist`)

---

## Deploy to Vercel (Frontend Only)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy frontend
cd frontend
vercel --prod
```

---

## Deploy to AWS (Production Scale)

### Using ECS (Elastic Container Service)

1. **Create ECR Repositories**
```bash
aws ecr create-repository --repository-name travelai-backend
aws ecr create-repository --repository-name travelai-frontend
```

2. **Build & Push Images**
```bash
# Backend
cd backend
docker build -t travelai-backend .
docker tag travelai-backend:latest YOUR_ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/travelai-backend:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/travelai-backend:latest

# Frontend
cd ../frontend
docker build -t travelai-frontend .
docker tag travelai-frontend:latest YOUR_ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/travelai-frontend:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/travelai-frontend:latest
```

3. **Deploy with ECS Fargate**
```bash
# Use the CloudFormation template
aws cloudformation create-stack \
  --stack-name travelai \
  --template-body file://aws-ecs-template.yaml \
  --capabilities CAPABILITY_IAM
```

---

## Deploy to Kubernetes

### Prerequisites
- kubectl configured
- A Kubernetes cluster (EKS, GKE, AKS, or local minikube)

### Deploy

```bash
# Apply all configurations
kubectl apply -f k8s-deployment.yaml

# Check status
kubectl get pods
kubectl get services

# View logs
kubectl logs -f deployment/travelai-backend

# Scale up
kubectl scale deployment travelai-backend --replicas=5
```

### Access the App

```bash
# Port forward to access locally
kubectl port-forward service/travelai-backend-service 8000:8000
kubectl port-forward service/travelai-frontend-service 3000:3000
```

---

## Environment Variables

### Required
| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/travelai` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `SECRET_KEY` | JWT signing key | `your-secret-key-here` |

### Optional (API Keys)
| Variable | Service | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` | OpenAI | AI recommendations |
| `ANTHROPIC_API_KEY` | Anthropic | AI recommendations |
| `AMADEUS_API_KEY` | Amadeus | Flight data |
| `OPENWEATHER_API_KEY` | OpenWeather | Weather data |

---

## Health Check Endpoints

- **Backend Health:** `GET /api/v1/health`
- **Frontend:** `GET /`

---

## Troubleshooting

### Backend won't start
```bash
# Check logs
docker-compose logs backend

# Check database connection
docker-compose exec backend python -c "from app.database import engine; print('DB OK')"
```

### Frontend build fails
```bash
# Clear cache
rm -rf frontend/.next
npm run build
```

### Database migrations
```bash
# Auto-create tables (already done on startup)
# Or manually:
docker-compose exec backend python -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

---

## Production Checklist

- [ ] Change `SECRET_KEY` to a secure random string
- [ ] Enable HTTPS (SSL/TLS)
- [ ] Set up database backups
- [ ] Configure monitoring (Prometheus/Grafana)
- [ ] Set up log aggregation
- [ ] Enable rate limiting
- [ ] Configure CORS properly
- [ ] Add API key authentication for external services
- [ ] Set up CI/CD pipeline
