# ToastyAnalytics

> **Enterprise AI-Powered Code Grading Engine with Advanced Microservices Architecture**

ToastyAnalytics is a production-ready code analysis and grading system that uses meta-learning to continuously improve its assessment accuracy. Features include JWT authentication, rate limiting, distributed tracing, neural network graders, and full microservices support.

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/toastyanalytics.git
cd toastyanalytics

# Install dependencies
pip install -r requirements.txt

# Start infrastructure (databases, Redis, Jaeger)
cd deployment/docker
docker-compose -f docker-compose.split-db.yml up -d

# Run server
cd ../..
uvicorn src.server_v2:app --reload

# API available at: http://localhost:8000/docs
# Jaeger UI at: http://localhost:16686
```

## ✨ Feature Highlights

### 🔐 Security & Performance
- **JWT Authentication**: Token-based API security with RBAC
- **Rate Limiting**: Redis-based request throttling (tiered limits)
- **Distributed Tracing**: OpenTelemetry with Jaeger/Zipkin
- **API Keys**: Service-to-service authentication

### 🧠 Advanced AI Features
- **Neural Network Graders**: CodeBERT-based ML grading
- **Meta-Learning**: Adaptive thresholds from user feedback
- **Federated Learning**: Privacy-preserving distributed training
- **Custom Plugins**: Python & YAML-based extensibility

### 🏗️ Enterprise Architecture
- **Microservices**: 4 independent services + API gateway
- **Service Mesh**: Istio with canary deployments & circuit breaking
- **Database Splitting**: Per-service PostgreSQL databases
- **Event Streaming**: Kafka/RabbitMQ integration
- **GraphQL API**: Flexible queries alongside REST

### 📊 Observability
- **Distributed Tracing**: End-to-end request tracking
- **Metrics**: Prometheus + Grafana dashboards
- **Structured Logging**: JSON logs with Sentry integration
- **Health Checks**: Readiness/liveness probes

## 📖 Documentation

- **[Complete Documentation](docs/README.md)** - System overview, features, and tech stack
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment for all platforms
- **[Architecture Reference](docs/ARCHITECTURE.md)** - Technical architecture details
- **[Quick Commands](quickCommandsHelp.md)** - Quick reference for development
- **[Code Examples](examples/README.md)** - Usage examples and patterns

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              API Gateway (JWT + Rate Limiting)          │
│                   http://localhost:8080                 │
└────────────┬────────────────────────────────────────────┘
             │ (Distributed Tracing)
    ┌────────┼────────┬────────────┬────────────┐
    │        │        │            │            │
┌───▼──┐ ┌──▼───┐ ┌──▼──────┐ ┌──▼────────┐ ┌─▼────┐
│User  │ │Grade │ │Meta-Lrn │ │Analytics │ │Events│
│Svc   │ │Svc   │ │Svc      │ │Svc       │ │Broker│
└──┬───┘ └──┬───┘ └───┬─────┘ └───┬──────┘ └──┬───┘
   │        │         │            │           │
┌──▼────┐ ┌▼─────┐ ┌─▼────┐ ┌────▼───┐  ┌───▼──┐
│User DB│ │Grade │ │Meta  │ │Analytics│ │Kafka │
│:5433  │ │DB    │ │DB    │ │DB       │ │/RMQ  │
│       │ │:5434 │ │:5435 │ │:5436    │ │      │
└───────┘ └──────┘ └──────┘ └─────────┘ └──────┘
```

## 🔧 API Examples

### Grade Code
```python
import requests

response = requests.post("http://localhost:8000/grade", json={
    "code": "def hello(): print('Hello')",
    "language": "python",
    "user_id": "user-123",
    "dimensions": ["code_quality", "reliability"]
})

print(response.json())
```

### WebSocket Events
```python
import asyncio
import websockets

async def listen():
    async with websockets.connect("ws://localhost:8000/ws/user-123") as ws:
        async for message in ws:
            print(f"Event: {message}")

asyncio.run(listen())
```

## 📦 Project Structure

```
toastyanalytics/
├── core/              # Base graders and types
├── graders/           # Dimension-specific graders
├── meta_learning/     # Self-improvement engine
├── database/          # ORM models
├── mcp_server/        # MCP protocol server
├── scripts/           # Utility scripts
├── tests/             # Test suite
│   └── integration/   # Integration tests
├── docs/              # Documentation
├── servers/           # Server implementations
└── server_v2.py       # Production server (v2)
```

## 🧪 Testing

```bash
# Run unit tests
pytest tests/

# Test WebSocket connection
python tests/integration/test_websocket.py

# Test full grading pipeline
python tests/integration/test_v2.py
```

## 🔌 Services

The Docker Compose stack includes:

| Service    | Port | Description                    |
|------------|------|--------------------------------|
| API        | 8000 | FastAPI application            |
| PostgreSQL | 5432 | Database                       |
| Redis      | 6379 | Cache layer                    |
| Prometheus | 9090 | Metrics collection             |
| Grafana    | 3000 | Dashboards (admin/admin)       |
| Worker     | -    | Celery background tasks        |
| Beat       | -    | Celery scheduler               |

## 🛠️ Development

```bash
# Install dependencies
pip install -r requirements-prod.txt

# Run locally (without Docker)
uvicorn server_v2:app --reload

# Run tests with coverage
pytest --cov=. tests/
```

## 📊 Monitoring

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (login: admin/admin)
- **API Metrics**: http://localhost:8000/metrics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details

## 🎯 Roadmap

- [x] Multi-dimensional grading
- [x] Meta-learning engine
- [x] WebSocket support
- [x] Event-driven architecture
- [x] Neural network graders
- [x] GraphQL API
- [x] Kafka integration
- [x] Federated learning
- [x] VS Code extension
- [ ] Efficiency enhancements and improved model

---

**Built with ❤️ for vibecoding and AI agent self-improvement**

