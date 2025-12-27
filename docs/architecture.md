# ToastyAnalytics Architecture Guide

## System Overview

ToastyAnalytics is a meta-learning platform designed to improve AI agents through adaptive grading and personalized feedback. The system consists of several interconnected components that work together to enable continuous improvement.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User/Agent Layer                         │
│  (CLI, REST API, Python SDK, VS Code Extension)                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────┼─────────────────────────────────┐
│                        MCP Server (FastAPI)                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Endpoints: /grade, /feedback, /strategies, /analytics   │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────┬──────────────────┬──────────────────┬──────────────┘
            │                  │                  │
    ┌───────▼──────┐  ┌───────▼────────┐  ┌─────▼──────┐
    │   Graders    │  │  Meta-Learner  │  │  Database  │
    │              │  │                │  │            │
    │ • Code       │  │ • Parameter    │  │ • Users    │
    │   Quality    │  │   Adaptation   │  │ • Sessions │
    │ • Speed      │  │ • Feedback     │  │ • History  │
    │ • Reliability│  │   Personalize  │  │ • Strategies│
    │ • Custom     │  │ • Threshold    │  │ • Learning │
    │              │  │   Tuning       │  │            │
    └──────────────┘  └────────────────┘  └────────────┘
```

## Core Components

### 1. Core Layer (`core/`)

**Purpose**: Provides base abstractions and type definitions.

- `base_grader.py`: Abstract base class for all graders
  - Defines standard grading interface
  - Manages weights and thresholds
  - Enables meta-learning updates

- `types.py`: Type definitions and enums
  - `GradingDimension`: Available grading dimensions
  - `FeedbackLevel`: Detail levels for feedback
  - `ScoreBreakdown`: Detailed score rationale
  - `ImprovementSuggestion`: Actionable suggestions

**Key Abstractions**:
```python
class BaseGrader(ABC):
    def grade(**kwargs) -> GraderResult
    def update_weights(weights)
    def update_thresholds(thresholds)
```

### 2. Database Layer (`database/`)

**Purpose**: Persistent storage for all learning data.

**Models**:
- `User`: User profiles and preferences
- `Agent`: Agent profiles for multi-agent systems
- `GradingHistory`: All grading records
- `LearningStrategy`: Learned improvement strategies
- `CollectiveLearning`: Global patterns across users

**Technology**: SQLAlchemy ORM
- Development: SQLite
- Production: PostgreSQL

**Relationships**:
```
User (1) ──< (N) GradingHistory
User (1) ──< (N) LearningStrategy
Agent (1) ──< (N) GradingHistory
```

### 3. Graders (`graders/`)

**Purpose**: Implement specific grading dimensions.

**Current Graders**:
- `CodeQualityGraderV2`: Evaluates code structure, readability, best practices
- `SpeedGrader`: Measures generation/execution time
- `ReliabilityGrader`: Assesses consistency and success rates

**Grader Pattern**:
```python
class CustomGrader(BaseGrader):
    @property
    def dimension(self) -> GradingDimension:
        return GradingDimension.CUSTOM
    
    def _get_default_weights(self) -> Dict[str, float]:
        return {'component1': 0.5, 'component2': 0.5}
    
    def _get_default_thresholds(self) -> Dict[str, float]:
        return {'excellent': 85, 'good': 75}
    
    def grade(self, **kwargs) -> GraderResult:
        # Implement grading logic
        return GraderResult(...)
```

**Extensibility**: New graders can be added by:
1. Inheriting from `BaseGrader`
2. Implementing required methods
3. Registering in `get_grader_for_dimension()`

### 4. Meta-Learning Engine (`meta_learning/`)

**Purpose**: Enables self-improvement through strategy adaptation.

**Key Algorithms**:

#### Parameter Adaptation
- Analyzes improvement trends per dimension
- Adjusts grading weights to focus on weak areas
- Uses exponential moving average for smooth updates

```python
# If user struggles with structure, increase its weight
if improvement_rate < threshold:
    new_weight = current_weight + adaptation_rate * delta
```

#### Feedback Personalization
- Tracks which feedback styles lead to improvement
- Learns user preferences from explicit feedback
- Adapts between minimal, standard, detailed, expert levels

#### Threshold Tuning
- Adjusts scoring thresholds based on user skill level
- Growth mindset: keeps user challenged but not frustrated
- Gradual progression as user improves

#### Pattern Recognition
- Identifies common mistakes across users
- Builds collective knowledge base
- Privacy-preserving (no code storage)

**Learning Cycle**:
```
1. Grade Code → 2. User Feedback → 3. Analyze Patterns →
4. Update Strategies → 5. Apply to Next Session → (repeat)
```

### 5. MCP Server (`mcp_server/`)

**Purpose**: Orchestrates multiple agents and coordinates learning.

**Technology**: FastAPI + Uvicorn
- Async/await for performance
- Pydantic for request/response validation
- OpenAPI docs auto-generated

**Key Endpoints**:
- `POST /grade`: Grade code with personalized strategies
- `POST /feedback`: Submit feedback to trigger learning
- `GET /strategies/{user_id}`: Retrieve learned strategies
- `GET /analytics/user/{user_id}`: Get user analytics
- `POST /agents`: Register agents
- `GET /collective-learning`: Global insights

**Multi-Agent Coordination**:
- Each agent has unique ID and profile
- Agents can specialize (coding, review, testing)
- Shared learning within user context
- Conflict resolution for parallel grading

### 6. CLI Tool (`cli/`)

**Purpose**: Command-line interface for developers.

**Commands**:
- `grade <file>`: Grade a single file
- `grade-all <dir>`: Grade entire directory
- `show-strategies`: View learned strategies
- `feedback`: Submit feedback on session
- `serve`: Start MCP server
- `stats`: View analytics

**Technology**: Click framework
- Intuitive command structure
- Auto-generated help
- Tab completion support

## Data Flow

### Grading Flow

```
1. User submits code
   ↓
2. MCP Server receives request
   ↓
3. Load user's learned strategies
   ↓
4. Get appropriate grader
   ↓
5. Apply strategies to grader
   ↓
6. Grade code
   ↓
7. Store result in database
   ↓
8. Return personalized feedback
```

### Learning Flow

```
1. User submits feedback (score + comments)
   ↓
2. Meta-learner retrieves session data
   ↓
3. Analyze patterns (what helped, what didn't)
   ↓
4. Calculate improvement rates per dimension
   ↓
5. Update/create learning strategies
   ↓
6. Persist strategies to database
   ↓
7. Apply to next grading session
```

### Multi-Agent Flow

```
Agent 1 (Coding)        Agent 2 (Review)       Agent 3 (Testing)
      ↓                        ↓                       ↓
   Generate Code            Review Code          Write Tests
      ↓                        ↓                       ↓
   Grade (quality)         Grade (reliability)   Grade (coverage)
      ↓                        ↓                       ↓
      └─────────────┬──────────┴───────────────────────┘
                    ↓
         Collective Learning Update
                    ↓
         Shared Strategies (User-Scoped)
```

## Scalability Considerations

### Performance

**Current**:
- Synchronous grading (fast for single requests)
- In-memory processing
- SQLite for development

**Future Optimizations**:
- Async grading for parallel requests
- Caching frequently graded code patterns
- PostgreSQL with connection pooling
- Redis for session state
- Background workers (Celery/RQ)

### Storage

**Current Scale**: 
- ~1KB per grading record
- 1M gradings = ~1GB

**Optimization Strategies**:
- Partition tables by date
- Archive old sessions
- Compress code snippets
- Index frequently queried fields

### Deployment

**Development**:
```bash
# Single container
docker run -p 8000:8000 toastyanalytics
```

**Production**:
```yaml
# Docker Compose with separate DB
services:
  api:
    image: toastyanalytics:latest
    replicas: 3
  db:
    image: postgres:15
  redis:
    image: redis:7
```

**Kubernetes**:
```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
```

## Security

### Authentication
- JWT tokens for API access
- API keys for programmatic access
- OAuth2 for third-party integrations

### Data Privacy
- User code never stored (only metadata)
- Anonymized collective learning
- GDPR compliance (right to deletion)
- Encryption at rest

### Rate Limiting
- Per-user quotas
- IP-based throttling
- Graceful degradation

## Testing Strategy

### Unit Tests
- Each grader independently tested
- Meta-learning algorithms verified
- Database models validated

### Integration Tests
- API endpoints tested end-to-end
- Database transactions verified
- Multi-agent scenarios tested

### Performance Tests
- Load testing with locust/k6
- Database query optimization
- Memory profiling

## Monitoring & Observability

### Metrics
- Grading request rate
- Average response time
- Learning strategy effectiveness
- User satisfaction scores

### Logging
- Structured JSON logs
- Request/response tracing
- Error tracking (Sentry)

### Dashboards
- Grafana for metrics
- Kibana for logs
- Custom analytics dashboard

## Extension Points

### Custom Graders
Implement `BaseGrader` to add new dimensions:
```python
class SecurityGrader(BaseGrader):
    @property
    def dimension(self):
        return GradingDimension.SECURITY
    
    def grade(self, code, **kwargs):
        # Run security analysis
        return GraderResult(...)
```

**Plugin System**: ToastyAnalytics supports dynamic plugin loading:
- **Python Plugins**: Create `.py` files in `src/plugins/custom/` that inherit from `BaseGrader`
- **YAML Rules**: Define regex-based rules in `.yaml` files for quick custom graders
- **Auto-Discovery**: Plugins are automatically loaded on startup
- **Example**: See `src/plugins/custom/security_grader.py`

### Custom Learning Strategies
Extend `MetaLearner`:
```python
class AdvancedMetaLearner(MetaLearner):
    def _custom_strategy(self, ...):
        # Implement new learning algorithm
        pass
```

### External Integrations
- GitHub Actions for PR grading
- VS Code extension
- Jupyter notebook magic commands
- Slack/Discord bots

## Advanced Features (Implemented)

### 1. Neural Network Graders
**Location**: `src/graders/neural_grader.py`

Uses CodeBERT (microsoft/codebert-base) for ML-based code quality assessment:
- PyTorch neural network with quality prediction head
- Tokenization and embedding of source code
- Fallback to AST grading when ML libraries unavailable

**Installation**:
```bash
pip install torch transformers
```

### 2. GraphQL API
**Location**: `src/graphql_api.py`

Provides flexible query language alongside REST:
- **Queries**: `user`, `grading_history`, `learning_strategies`, `search_code`
- **Mutations**: `grade_code`, `submit_feedback`, `reload_plugins`
- **Subscriptions**: `grading_updates` (real-time via WebSocket)
- **Technology**: Strawberry GraphQL

### 3. Event Streaming
**Location**: `src/messaging/event_broker.py`

Production-grade event streaming with auto-detection:
- **Primary**: Apache Kafka (JSON serialization)
- **Fallback**: RabbitMQ (pika)
- **Auto-detection**: Attempts Kafka, falls back to RabbitMQ, then in-memory
- **Events**: Grading results, feedback submissions, meta-learning updates

### 4. Federated Learning
**Location**: `src/federated_learning.py`

Privacy-preserving distributed learning across agents:
- **Framework**: Flower (flwr)
- **Algorithm**: Federated Averaging (FedAvg)
- **Privacy**: Model weights only, no raw data sharing
- **Benefits**: Collective learning without centralizing sensitive data

### 5. Microservices Architecture
**Location**: `src/services/`, `deployment/kubernetes/`

Decomposed into independent services:
- **API Gateway** (`:8080`): Unified entry point, routing, GraphQL
- **Grading Service** (`:8000`): Code quality grading, AST analysis
- **Meta-Learning Service** (`:8001`): Feedback processing, pattern detection
- **Analytics Service** (`:8002`): Data aggregation, trend analysis

**Deployment**:
- Docker Compose: `deployment/docker/docker-compose.microservices.yml`
- Kubernetes: `deployment/kubernetes/deployments.yaml`
- Istio Service Mesh: `deployment/kubernetes/istio-config.yaml`

### 6. Service Mesh (Istio)
**Location**: `deployment/kubernetes/istio-config.yaml`

Production traffic management and security:
- **Canary Deployments**: 90/10 traffic split
- **Circuit Breaking**: Max 10 connections, max 100 requests
- **mTLS**: Encrypted service-to-service communication
- **Retries**: Automatic retry on 5xx errors
- **Timeouts**: 10s per request

---

## Folder Structure

```
toastyanalytics/
├── src/                          # All Python source code
│   ├── server_v2.py             # Main FastAPI server
│   ├── graphql_api.py           # GraphQL layer
│   ├── federated_learning.py   # Federated learning
│   ├── core/                    # Base abstractions
│   ├── graders/                 # Grading implementations
│   │   └── neural_grader.py    # ML-based grader
│   ├── database/                # Database models
│   ├── meta_learning/           # Adaptive learning
│   ├── plugins/                 # Plugin system
│   │   └── custom/             # User plugins
│   ├── messaging/               # Event streaming
│   └── services/                # Microservices
├── deployment/                  # All deployment configs
│   ├── docker/                 # Docker Compose
│   └── kubernetes/             # K8s + Istio
├── docs/                        # Documentation
├── tests/                       # Test suite
├── examples/                    # Usage examples
└── README.md                    # Main documentation
```

---

**Version**: 2.0.0  
**Last Updated**: 2025-12-26
