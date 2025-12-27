# How to Run ToastyAnalytics

## Quick Commands Reference

### Docker (Monolith Architecture)
```bash
# Navigate to docker directory
cd deployment/docker

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up --build -d
```

**Access Points:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

---

### Docker (Microservices Architecture)
```bash
# Navigate to docker directory
cd deployment/docker

# Start microservices
docker-compose -f docker-compose.microservices.yml up -d

# View all services
docker-compose -f docker-compose.microservices.yml ps

# Stop services
docker-compose -f docker-compose.microservices.yml down
```

**Access Points:**
- API Gateway: http://localhost:8080
- GraphQL: http://localhost:8080/graphql

---

### Local Development
```bash
# From project root

# Install dependencies
pip install -r requirements.txt

# Run main API server
uvicorn src.server_v2:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker (separate terminal)
celery -A src.celery_app worker --loglevel=info

# Run Celery beat (separate terminal)
celery -A src.celery_app beat --loglevel=info
```

**Note:** Local development requires PostgreSQL and Redis running separately.

---

### Kubernetes Deployment
```bash
# Navigate to kubernetes directory
cd deployment/kubernetes

# Create namespace
kubectl create namespace toastyanalytics

# Apply deployments
kubectl apply -f deployments.yaml

# Install Istio (if using service mesh)
istioctl install --set profile=default -y
kubectl label namespace toastyanalytics istio-injection=enabled

# Apply Istio config
kubectl apply -f istio-config.yaml

# Check status
kubectl get pods -n toastyanalytics
kubectl get svc -n toastyanalytics

# View logs
kubectl logs -n toastyanalytics deployment/grading-service -f
```

---

### Test Individual Microservices
```bash
# From project root

# Grading service
python -m uvicorn src.services.grading_service:app --port 8000

# Meta-learning service
python -m uvicorn src.services.meta_learning_service:app --port 8001

# Analytics service
python -m uvicorn src.services.analytics_service:app --port 8002

# API Gateway
python -m uvicorn src.services.api_gateway:app --port 8080
```

---

### Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_graders.py

# Run with coverage
pytest --cov=src tests/

# Run integration tests
pytest tests/test_integration.py -v
```

---

### Useful Docker Commands

```bash
# View all containers
docker ps

# View logs for specific container
docker logs toasty-api --tail 50 -f
docker logs toasty-worker --tail 50 -f

# Restart single service
docker-compose -f deployment/docker/docker-compose.yml restart api

# Execute command in container
docker exec -it toasty-api bash

# Clean up everything
docker-compose -f deployment/docker/docker-compose.yml down -v
docker system prune -a --volumes
```

---

### Database Management

```bash
# Access PostgreSQL in Docker
docker exec -it toasty-postgres psql -U toasty -d toastyanalytics

# Run migrations
docker exec -it toasty-api alembic upgrade head

# Create new migration
docker exec -it toasty-api alembic revision --autogenerate -m "description"

# Check Redis
docker exec -it toasty-redis redis-cli
```

---

### MCP Server (Node.js)

```bash
# Navigate to MCP server directory
cd mcp-server

# Install dependencies
npm install

# Run server
node index.js

# Or with environment variables
MCP_PORT=3100 node index.js
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://toasty:password123@localhost:5432/toastyanalytics

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Optional: Sentry
SENTRY_DSN=your-sentry-dsn

# Optional: Feature Flags
ENABLE_NEURAL_GRADING=false
ENABLE_GRAPHQL=false
```

---

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8000
# Windows:
netstat -ano | findstr :8000

# Linux/Mac:
lsof -i :8000

# Kill the process
# Windows:
taskkill /PID <pid> /F

# Linux/Mac:
kill -9 <pid>
```

### Docker Issues
```bash
# Rebuild containers
docker-compose -f deployment/docker/docker-compose.yml up --build --force-recreate -d

# Clean Docker cache
docker system prune -a --volumes
```

### Import Errors
All imports should use `src.` prefix:
```python
# Correct
from src.graders import get_grader_for_dimension
from src.config import config

# Incorrect (old paths)
from graders import get_grader_for_dimension
from config import config
```

---

## Performance Tuning

### Docker Resource Limits
Edit `deployment/docker/docker-compose.yml`:
```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### Celery Workers
```bash
# Increase worker concurrency
celery -A src.celery_app worker --concurrency=8

# Auto-scale workers
celery -A src.celery_app worker --autoscale=10,3
```

---

For more details, see [repoOrganization.md](repoOrganization.md), [prodDeploymentIdeas.md](prodDeploymentIdeas.md), and [architecture.md](architecture.md).
