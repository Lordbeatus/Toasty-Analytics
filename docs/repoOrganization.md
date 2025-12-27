# ToastyAnalytics - Folder Structure

## Current Organization 

```
toastyanalytics/
├── src/                              # All source code
│   ├── server_v2.py                  # Main FastAPI server
│   ├── config.py                     # Configuration
│   ├── cache.py                      # Redis caching
│   ├── celery_app.py                 # Celery tasks
│   ├── graphql_api.py                # GraphQL API layer
│   ├── federated_learning.py         # FL framework
│   │
│   ├── core/                         # Core abstractions
│   │   ├── base_grader.py
│   │   └── types.py
│   │
│   ├── graders/                      # Grading implementations
│   │   ├── __init__.py
│   │   ├── code_quality_grader.py
│   │   ├── speed_grader.py
│   │   ├── reliability_grader.py
│   │   └── neural_grader.py
│   │
│   ├── plugins/                      # Plugin system
│   │   ├── plugin_loader.py
│   │   └── custom/
│   │       ├── security_grader.py
│   │       └── example_rules.yaml
│   │
│   ├── messaging/                    # Event streaming
│   │   └── event_broker.py
│   │
│   ├── database/                     # Database layer
│   │   ├── models.py
│   │   └── migrations/
│   │
│   ├── meta_learning/                # Adaptive learning
│   │   └── engine.py
│   │
│   ├── services/                     # Microservices
│   │   ├── grading_service.py
│   │   ├── meta_learning_service.py
│   │   ├── analytics_service.py
│   │   └── api_gateway.py
│   │
│   └── cli/                          # CLI tools
│       └── main.py
│
├── deployment/                       # All deployment configs
│   ├── docker/
│   │   ├── docker-compose.yml        # Monolith deployment
│   │   ├── docker-compose.microservices.yml
│   │   ├── Dockerfile
│   │   ├── Dockerfile.grading
│   │   ├── Dockerfile.meta
│   │   ├── Dockerfile.analytics
│   │   └── Dockerfile.gateway
│   │
│   ├── kubernetes/
│   │   ├── deployments.yaml
│   │   └── istio-config.yaml
│   │
│   ├── grafana-dashboards/
│   └── grafana-provisioning/
│
├── docs/                             # Documentation
│   ├── README.md                     # Main documentation (system overview, features, tech stack)
│   ├── DEPLOYMENT.md                 # Production deployment guide
│   └── ARCHITECTURE.md               # Technical architecture reference
│
├── tests/                            # Test suite
│   ├── conftest.py
│   ├── test_graders.py
│   ├── test_meta_learning.py
│   └── test_integration.py
│
├── examples/                         # Usage examples
│   ├── README.md
│   ├── api_usage.py
│   ├── basic_usage.py
│   └── comprehensive_proof.py
│
├── scripts/                          # Utility scripts
│   └── fix_imports.py
│
├── mcp-server/                       # MCP server (Node.js)
│   ├── package.json
│   └── index.js
│
├── vscode-extension/                 # VS Code extension
│   └── ...
│
├── config_files/                     # Config templates
│   └── prometheus.yml
│
├── .env                              # Environment variables
├── .env.example                      # Example environment
├── .gitignore
├── requirements.txt                  # Python dependencies
├── requirements-prod.txt             # Production dependencies
├── setup.py                          # Package setup
├── __init__.py                       # Root init
└── README.md                         # Main readme
```

## Import Paths

All source code imports use the `src.` prefix:
```python
from src.graders import get_grader_for_dimension
from src.config import config
from src.cache import CacheManager
```

## Running Commands

### Docker Compose (Monolith):
```bash
cd deployment/docker
docker-compose up -d
```

### Docker Compose (Microservices):
```bash
cd deployment/docker
docker-compose -f docker-compose.microservices.yml up -d
```

### Kubernetes:
```bash
kubectl apply -f deployment/kubernetes/deployments.yaml
kubectl apply -f deployment/kubernetes/istio-config.yaml
```

### Development Server:
```bash
uvicorn src.server_v2:app --reload
```

### Celery Worker:
```bash
celery -A src.celery_app worker --loglevel=info
```
