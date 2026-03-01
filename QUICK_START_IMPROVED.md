# Quick Start Guide - TravelAI

This guide will help you get TravelAI running with all the latest improvements.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (optional, for containerized deployment)
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (optional, for caching)

## Option 1: Docker Compose (Recommended)

### 1. Clone and Setup

```bash
cd travel_ai_app

# Copy environment template
cp backend/.env.example backend/.env
```

### 2. Configure Environment

Edit `backend/.env` and set:

```bash
# REQUIRED - Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=your-super-secret-key-at-least-32-characters-long

# Database (Docker PostgreSQL)
DATABASE_URL=postgresql://travelai:travelai@postgres:5432/travelai

# Redis (optional but recommended)
REDIS_URL=redis://redis:6379

# API Keys (get from respective providers)
OPENAI_API_KEY=sk-your-key
OPENWEATHER_API_KEY=your-key
AMADEUS_API_KEY=your-key
AMADEUS_SECRET_KEY=your-key
```

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Verify Health

```bash
# Check all services
docker-compose ps

# View logs
docker-compose logs -f backend

# Test endpoints
curl http://localhost:8000/api/v1/health
curl http://localhost:3000/api/health
```

### 5. Access Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Option 2: Local Development

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your values
```

### 2. Database Setup

```bash
# Start PostgreSQL (example with Docker)
docker run -d --name postgres \
  -e POSTGRES_USER=travelai \
  -e POSTGRES_PASSWORD=travelai \
  -e POSTGRES_DB=travelai \
  -p 5432:5432 \
  postgres:15-alpine

# Run migrations
alembic upgrade head
```

### 3. Start Backend

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure (optional)
# Create .env.local with:
# NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 5. Start Frontend

```bash
# Development mode
npm run dev

# Production build
npm run build
npm start
```

## Running Tests

### Backend Tests

```bash
cd backend

# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v

# Run specific test
pytest tests/test_auth.py::TestUserLogin::test_login_success -v
```

### Frontend Tests

```bash
cd frontend

# Run tests (if configured)
npm test

# Lint
npm run lint
```

## Database Migrations

### Create New Migration

```bash
cd backend

# Auto-generate from model changes
alembic revision --autogenerate -m "Description of changes"

# Or create empty migration
alembic revision -m "Add new table"
```

### Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade <revision_id>

# Downgrade one revision
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade <revision_id>
```

### Check Migration Status

```bash
# Show current revision
alembic current

# Show all revisions
alembic history

# Show pending migrations
alembic history --verbose
```

## Redis Caching (Optional)

### Start Redis

```bash
# Using Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Or install locally and run
redis-server
```

### Configure

Add to `backend/.env`:

```bash
REDIS_URL=redis://localhost:6379
```

The cache service will automatically connect and start caching.

## Troubleshooting

### Backend Won't Start

**Error: SECRET_KEY not set**
```bash
# Generate a new key
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Add to .env
SECRET_KEY=<generated-key>
```

**Error: Database connection failed**
```bash
# Check PostgreSQL is running
docker ps | grep postgres
# or
pg_isready -h localhost -p 5432

# Check DATABASE_URL in .env
echo $DATABASE_URL
```

### Frontend Won't Start

**Error: Module not found**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Error: API connection failed**
```bash
# Check backend is running
curl http://localhost:8000/api/v1/health

# Check NEXT_PUBLIC_API_URL
echo $NEXT_PUBLIC_API_URL
```

### Tests Failing

```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Clear pytest cache
pytest --cache-clear

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Docker Issues

```bash
# Clean up Docker
docker-compose down -v  # Remove volumes
docker system prune -a  # Remove all unused data

# Rebuild
docker-compose up -d --build

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Performance Tips

### 1. Enable Redis Caching

Significantly reduces API calls and improves response times.

### 2. Use Connection Pooling

Already configured in `backend/app/database/connection.py`.

### 3. Enable Production Mode

```bash
# Backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Frontend
npm run build
npm start
```

### 4. Use Docker in Production

Multi-stage builds optimize image size and security.

## Security Checklist

Before deploying to production:

- [ ] SECRET_KEY is at least 32 characters and randomly generated
- [ ] Using PostgreSQL, not SQLite
- [ ] All API keys are set and valid
- [ ] DEBUG=false in .env
- [ ] ALLOWED_ORIGINS configured for your domain
- [ ] HTTPS enabled
- [ ] Database backups configured
- [ ] Health checks passing
- [ ] Rate limiting working (test with multiple requests)

## Common API Calls

### Get Recommendations

```bash
curl -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "New York",
    "travel_start": "2024-06-01",
    "travel_end": "2024-06-10",
    "num_travelers": 2,
    "num_recommendations": 5,
    "user_preferences": {
      "budget_daily": 200,
      "budget_total": 4000,
      "travel_style": "moderate",
      "interests": ["nature", "food"],
      "passport_country": "US",
      "visa_preference": "visa_free",
      "traveling_with": "couple"
    }
  }'
```

### List Destinations

```bash
curl http://localhost:8000/api/v1/destinations
curl "http://localhost:8000/api/v1/destinations?query=Paris"
curl "http://localhost:8000/api/v1/destinations?country=JP"
```

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

## Environment Variables Reference

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key (min 32 chars) | `your-secret-key` |
| `DATABASE_URL` | Database connection URL | `postgresql://...` |

### Recommended

| Variable | Description | Example |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `OPENWEATHER_API_KEY` | Weather API key | `...` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `ALLOWED_ORIGINS` | CORS origins | `localhost:3000,localhost:5173` |
| `LLM_PROVIDER` | AI provider | `openai` |

## Getting Help

1. **Check logs**: `docker-compose logs -f`
2. **Run tests**: `pytest -v`
3. **Check docs**: http://localhost:8000/docs
4. **Review code**: See `IMPROVEMENTS_SUMMARY.md`

---

**Happy Coding! ✈️🌍**
