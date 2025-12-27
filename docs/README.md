# ToastyAnalytics Documentation

## What is ToastyAnalytics?

**ToastyAnalytics** is a production-ready AI-powered code grading and analysis platform with meta-learning capabilities. It evaluates code quality across multiple dimensions, learns from user feedback to improve accuracy, and provides actionable improvement suggestions.

### Core Capabilities
- **Multi-dimensional Code Analysis**: AST-based grading for code quality, readability, complexity, speed, and reliability
- **Meta-Learning**: Adapts grading thresholds and strategies based on user feedback patterns
- **Neural Network Grading**: ML-based code quality assessment using CodeBERT
- **Plugin System**: Extensible architecture for custom graders (Python and YAML-based)
- **Real-time Analysis**: Fast grading with Redis caching for repeated code patterns

---

## Technology Stack

### Core Application
- **Language**: Python 3.11+
- **Web Framework**: FastAPI (async REST API)
- **Database**: PostgreSQL (production) / SQLite (development)
- **Cache/Queue**: Redis (caching + Celery broker)
- **Task Queue**: Celery (async grading tasks)
- **ORM**: SQLAlchemy

### Advanced Features
- **Authentication**: JWT with role-based access control (RBAC)
- **Tracing**: OpenTelemetry + Jaeger/Zipkin
- **Rate Limiting**: Redis-based request throttling
- **GraphQL**: Strawberry GraphQL (alternative to REST)
- **Service Mesh**: Istio (Kubernetes deployments)
- **Monitoring**: Prometheus + Grafana

### AI/ML Components
- **Code Analysis**: Python AST module for parsing
- **Complexity Metrics**: McCabe cyclomatic complexity
- **Neural Graders**: PyTorch + Transformers (CodeBERT)
- **Federated Learning**: Privacy-preserving distributed training

### Deployment Options
- **Docker Compose**: Monolith or microservices architecture
- **Kubernetes**: Production-grade orchestration with Istio
- **Cloud Platforms**: AWS (ECS/EKS), Azure (AKS/Container Apps), GCP (GKE/Cloud Run), DigitalOcean

---

## Architecture

### Monolith Architecture (Default)
```
┌─────────────┐
│  FastAPI    │  ← Main API Server (port 8000)
│  Server     │
└──────┬──────┘
       │
   ┌───┴────┬──────────┬──────────┐
   │        │          │          │
┌──▼───┐ ┌─▼──┐ ┌────▼────┐ ┌───▼────┐
│ Post │ │Redis│ │ Celery  │ │ Prom/  │
│greSQL│ │     │ │ Workers │ │ Grafana│
└──────┘ └────┘ └─────────┘ └────────┘
```

### Microservices Architecture (Optional)
```
┌──────────────────┐
│   API Gateway    │ ← GraphQL + REST (port 8080)
└────────┬─────────┘
         │
    ┌────┴────┬──────────┬────────────┐
    │         │          │            │
┌───▼───┐ ┌──▼──┐ ┌─────▼─────┐ ┌───▼────┐
│Grading│ │Meta │ │ Analytics │ │Database│
│Service│ │Learn│ │  Service  │ │        │
│:8000  │ │:8001│ │   :8002   │ │ :5432  │
└───────┘ └─────┘ └───────────┘ └────────┘
```

### Core Components

#### 1. Grading Engine (`src/graders/`)
- **CodeQualityGraderV2**: AST-based code analysis (structure, readability, best practices)
- **NeuralGrader**: ML-based quality assessment
- **SpeedGrader**: Performance metrics
- **ReliabilityGrader**: Consistency and success rate tracking
- **Plugin System**: Custom graders via Python classes or YAML rules

#### 2. Meta-Learning Engine (`src/meta_learning/`)
- Tracks user feedback on grading results
- Identifies patterns in code improvements
- Adapts grading weights and thresholds per user
- Learns personalized strategies
- Collective learning across users

#### 3. Database Layer (`src/database/`)
- **User**: User profiles and preferences
- **Agent**: AI agent profiles for multi-agent systems
- **GradingHistory**: Complete grading records with scores and feedback
- **LearningStrategy**: Learned improvement patterns per user
- **CollectiveLearning**: Aggregated patterns across all users

#### 4. Authentication (`src/auth/`)
- JWT access tokens (30-minute expiry)
- JWT refresh tokens (7-day expiry)
- Role-based access control (RBAC)
- Scope-based permissions
- API key management for services

#### 5. Observability
- **Tracing**: OpenTelemetry integration with Jaeger
- **Metrics**: Prometheus exporters for request rates, latencies, error rates
- **Logging**: Structured JSON logs with contextual metadata
- **Monitoring**: Grafana dashboards for visualization

---

## Key Features

### 1. AST-Based Code Analysis
Real parsing of code structure (not regex) for accurate quality assessment:
- Function/class extraction with line numbers
- McCabe cyclomatic complexity calculation
- Docstring detection
- Import analysis
- Line-specific feedback with function names

### 2. Meta-Learning
System improves over time by learning from feedback:
- **Adaptive Thresholds**: Adjusts scoring based on user expectations
- **Pattern Recognition**: Identifies common improvement patterns
- **Personalization**: Each user gets customized grading criteria
- **Strategy Learning**: Discovers what advice leads to improvements

### 3. Plugin System
Extend grading capabilities without modifying core:
- **Python Plugins**: Full grader implementation with custom logic
- **YAML Rules**: Simple regex-based pattern matching
- **Auto-Discovery**: Plugins loaded automatically from `src/plugins/`
- **Example**: Security grader included

### 4. Microservices Support
Optional decomposition for production scalability:
- **Grading Service**: Code analysis and scoring
- **Meta-Learning Service**: Feedback processing and adaptation
- **Analytics Service**: Historical data and reporting
- **API Gateway**: Unified GraphQL/REST interface

### 5. JWT Authentication
Production-ready security:
- Token-based authentication
- Role-based access control (admin, user, service)
- Scope-based permissions (grade:read, grade:write)
- API key support for service-to-service communication

### 6. Rate Limiting
Prevent abuse and manage resources:
- Tiered limits (free: 10/min, premium: 100/min, admin: unlimited)
- Redis-based distributed rate limiting
- Per-user and per-IP tracking
- Configurable limits via API

---

## Deployment

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run API server
uvicorn src.server_v2:app --reload --port 8000

# Run Celery worker (separate terminal)
celery -A src.celery_app worker --loglevel=info
```

### Docker (Recommended)
```bash
# Monolith architecture
cd deployment/docker
docker-compose up -d

# Microservices architecture
docker-compose -f docker-compose.microservices.yml up -d

# With split databases per service
docker-compose -f docker-compose.split-db.yml up -d
```

### Kubernetes (Production)
```bash
# Create namespace
kubectl create namespace toastyanalytics

# Deploy services
kubectl apply -f deployment/kubernetes/deployments.yaml

# Optional: Install Istio service mesh
istioctl install --set profile=default -y
kubectl apply -f deployment/kubernetes/istio-config.yaml
```

### Access Points
- **API Docs**: http://localhost:8000/docs
- **GraphQL Playground**: http://localhost:8080/graphql
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **Jaeger UI**: http://localhost:16686

---

## API Usage

### Grade Code (REST)
```bash
curl -X POST http://localhost:8000/grade \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def add(a, b):\n    return a + b",
    "language": "python",
    "user_id": "user123",
    "dimensions": ["code_quality"]
  }'
```

### Submit Feedback
```bash
curl -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "grading_id": "abc-123",
    "dimension": "code_quality",
    "was_helpful": true,
    "comment": "Good suggestions"
  }'
```

### GraphQL Query
```graphql
query {
  gradeCode(input: {
    code: "def greet(name):\n    return f\"Hello, {name}!\""
    language: "python"
    userId: "user123"
    dimensions: ["code_quality"]
  }) {
    overallScore
    feedback {
      dimension
      score
      feedback
    }
    improvementSuggestions {
      category
      description
      priority
    }
  }
}
```

---

## Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/toastyanalytics

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret
ALLOWED_HOSTS=localhost,yourdomain.com

# Observability (Optional)
SENTRY_DSN=https://...@sentry.io/project
OTEL_EXPORTER_JAEGER_ENDPOINT=http://jaeger:14268/api/traces

# Features
ENABLE_NEURAL_GRADING=false  # Requires PyTorch
ENABLE_GRAPHQL=true
ENABLE_RATE_LIMITING=true
```

---

## Performance

### Benchmarks
- **Simple grading**: ~50ms (AST parsing + scoring)
- **Neural grading**: ~200ms (includes ML model inference)
- **With caching**: ~5ms (Redis cache hit)
- **Throughput**: 500+ requests/second (with Celery workers)

### Optimization
- **Redis caching**: Identical code returns cached results
- **Async processing**: Celery for background grading
- **Connection pooling**: SQLAlchemy pooling for database
- **Rate limiting**: Prevents resource exhaustion

---

## Monitoring

### Prometheus Metrics
- `grading_requests_total`: Total grading requests
- `grading_duration_seconds`: Request latency histogram
- `grading_errors_total`: Error count by type
- `cache_hit_rate`: Redis cache effectiveness
- `celery_task_duration_seconds`: Background task performance

### Grafana Dashboards
Pre-configured dashboards available in `deployment/grafana-dashboards/`:
- Request rate and latency
- Error rates by endpoint
- Cache hit rates
- Celery queue depth and processing time
- Database query performance

### Distributed Tracing
OpenTelemetry integration provides:
- End-to-end request tracing
- Service dependency mapping
- Performance bottleneck identification
- Error propagation tracking

---

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_graders.py

# With coverage
pytest --cov=src tests/

# Integration tests only
pytest tests/test_integration.py -v
```

---

## License

[Your License Here]

---

## Support

For issues, questions, or contributions, see the main repository README.
