"""
ToastyAnalytics HTTP API

Exposes grading, feedback, analytics, and WebSocket endpoints.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from toastyanalytics.auth.jwt_auth import (
    KNOWN_SCOPES,
    SCOPE_ANALYTICS_READ,
    SCOPE_GRADE_READ,
    SCOPE_GRADE_WRITE,
    SCOPE_TOKEN_ISSUE,
    Token,
    TokenData,
    api_key_scheme,
    auth_manager,
    authenticate_headers,
    get_principal,
    is_auth_configured,
    principal_from_api_key,
    require_scope,
)
from toastyanalytics.config import config
from toastyanalytics.core.types import GradingDimension
from toastyanalytics.database.models import DatabaseManager, GradingHistory, User
from toastyanalytics.graders import SUPPORTED_DIMENSIONS, get_grader_for_dimension
from toastyanalytics.meta_learning.engine import MetaLearner
from toastyanalytics.middleware.rate_limiter import RateLimiter, RateLimitMiddleware

# Optional integration: enabled when `sentry-sdk` is installed.
try:
    from toastyanalytics.sentry_integration import init_sentry
except ImportError:
    init_sentry = None

# Create FastAPI app with enhanced features
app = FastAPI(
    title="ToastyAnalytics API",
    description="Multi-dimensional code grading with meta-learning",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiting is registered before CORS so CORS also wraps 429 responses.
rate_limiter = RateLimiter(
    redis_url=config.REDIS_URL if config.RATE_LIMIT_ENABLED else None,
    default_limit=config.RATE_LIMIT_PER_MINUTE,
)
app.state.rate_limiter = rate_limiter


def _request_tier(request: Request) -> str:
    """Resolve the caller's role tier before route dependencies run."""
    principal = authenticate_headers(
        request.headers.get("authorization"),
        request.headers.get(config.API_KEY_HEADER),
    )
    if principal:
        request.state.user_id = principal.user_id
        if config.AUTH_ENABLED and "admin" in principal.roles:
            return "admin"
    return "free"


if config.RATE_LIMIT_ENABLED:
    app.add_middleware(
        RateLimitMiddleware,
        rate_limiter=rate_limiter,
        tier_resolver=_request_tier,
        tier_limits={
            "free": (config.RATE_LIMIT_PER_MINUTE, 60),
            "admin": (config.RATE_LIMIT_ADMIN_PER_MINUTE or None, 60),
        },
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
db_manager = DatabaseManager()
meta_learner = MetaLearner(db_manager)


# WebSocket connection manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            for connection in list(self.active_connections[user_id]):
                try:
                    await connection.send_json(message)
                except Exception:
                    self.disconnect(connection, user_id)

    async def broadcast(self, message: dict):
        failed_connections = []
        for user_id, user_connections in list(self.active_connections.items()):
            for connection in list(user_connections):
                try:
                    await connection.send_json(message)
                except Exception:
                    failed_connections.append((user_id, connection))
        for user_id, connection in failed_connections:
            self.disconnect(connection, user_id)


manager = ConnectionManager()

# Event queue for event-driven architecture
event_queue: asyncio.Queue = asyncio.Queue()


# Pydantic models
class GradeRequest(BaseModel):
    user_id: str
    agent_id: Optional[str] = None
    code: str
    language: str
    context: Dict[str, Any] = Field(default_factory=dict)
    dimensions: List[str] = Field(default_factory=lambda: ["code_quality"])
    feedback_level: str = "standard"


class GradeResponse(BaseModel):
    grading_id: str
    user_id: str
    timestamp: str
    scores: Dict[str, float]
    feedback: Dict[str, Any]
    overall_score: float
    improvement_suggestions: List[Dict[str, Any]]
    learning_applied: bool
    cached: bool = False


class FeedbackRequest(BaseModel):
    grading_id: str
    user_id: str
    rating: Optional[int] = Field(None, ge=1, le=5)
    comments: Optional[str] = None
    helpful_suggestions: Optional[List[str]] = None


class TokenRequest(BaseModel):
    """Mint a JWT for a user, authorized by an API key."""

    user_id: str
    scopes: Optional[List[str]] = None
    roles: Optional[List[str]] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class LearningEvent(BaseModel):
    event_type: str
    user_id: str
    data: Dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# Event processor (background task)
async def process_events():
    """Process events from the queue for event-driven architecture"""
    while True:
        try:
            event: LearningEvent = await event_queue.get()

            # Broadcast to connected WebSocket clients
            await manager.send_personal_message(
                {
                    "type": event.event_type,
                    "data": event.data,
                    "timestamp": event.timestamp,
                },
                event.user_id,
            )

            # Process based on event type
            if event.event_type == "learning_update":
                # Trigger meta-learning update
                pass
            elif event.event_type == "grading_complete":
                # Update analytics
                pass

            event_queue.task_done()
        except Exception as e:
            print(f"Event processing error: {e}")
            await asyncio.sleep(1)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # Initialize Sentry if configured
    if init_sentry is not None:
        try:
            init_sentry()
        except Exception as exc:
            print(f"Sentry disabled: {exc}")

    # Start event processor
    asyncio.create_task(process_events())

    print(f"ToastyAnalytics API {app.version} started")
    print(f"Database: {db_manager.engine.url}")
    print(f"Error tracking: {'enabled' if init_sentry is not None else 'disabled'}")
    print(f"Authentication: {'enabled' if config.AUTH_ENABLED else 'disabled'}")
    print(
        f"Rate limiting: {config.RATE_LIMIT_ENABLED} ({rate_limiter.backend} backend)"
    )
    if config.AUTH_ENABLED and not is_auth_configured():
        print(
            "WARNING: authentication is enabled but neither JWT_SECRET_KEY nor "
            "TOASTY_API_KEYS is set; protected endpoints will return 503."
        )


# Health check
@app.get("/")
async def root():
    return {
        "service": "ToastyAnalytics API",
        "version": "2.0.0",
        "status": "running",
        "features": {
            "grading": True,
            "meta_learning": True,
            "websocket": True,
            "event_driven": True,
            "authentication": config.AUTH_ENABLED,
            "rate_limiting": config.RATE_LIMIT_ENABLED,
        },
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "up",
            "database": "connected" if db_manager else "down",
            "websocket": "active",
            "auth": "enabled" if config.AUTH_ENABLED else "disabled",
            "rate_limiter": rate_limiter.backend,
        },
    }


def _authorize_user(principal: TokenData, user_id: str) -> None:
    """Allow access to the caller's own data; admins may access any user."""
    if principal.auth_type == "disabled" or "admin" in principal.roles:
        return
    if principal.user_id != user_id:
        raise HTTPException(status_code=403, detail="Cannot access another user's data")


@app.post("/auth/token", response_model=Token, tags=["auth"])
async def issue_token(
    payload: TokenRequest,
    api_key: Optional[str] = Depends(api_key_scheme),
):
    """Exchange a service API key for a user-scoped JWT pair."""
    if not config.AUTH_ENABLED:
        raise HTTPException(status_code=503, detail="Authentication is disabled")

    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    principal = principal_from_api_key(api_key)
    if principal is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if "*" not in principal.scopes and SCOPE_TOKEN_ISSUE not in principal.scopes:
        raise HTTPException(status_code=403, detail="Scope 'token:issue' required")

    requested = payload.scopes or list(principal.scopes)
    unknown = set(requested) - {"*"} - KNOWN_SCOPES
    if unknown:
        raise HTTPException(
            status_code=400,
            detail="Unknown scopes: " + ", ".join(sorted(unknown)),
        )
    if "*" not in principal.scopes:
        escalated = [scope for scope in requested if scope not in principal.scopes]
        if escalated:
            raise HTTPException(
                status_code=403,
                detail="API key cannot grant scope(s): " + ", ".join(escalated),
            )

    requested_roles = payload.roles or []
    escalated_roles = [role for role in requested_roles if role not in principal.roles]
    if escalated_roles:
        raise HTTPException(
            status_code=403,
            detail="API key cannot grant role(s): " + ", ".join(escalated_roles),
        )

    return auth_manager.create_token_pair(
        user_id=payload.user_id,
        scopes=requested,
        roles=requested_roles,
    )


@app.post("/auth/refresh", response_model=Token, tags=["auth"])
async def refresh_access_token(payload: RefreshRequest):
    """Mint a new access token from a valid refresh token."""
    data = auth_manager.decode_token(payload.refresh_token, expected_type="refresh")
    return auth_manager.create_token_pair(
        user_id=data["sub"],
        scopes=data.get("scopes", []),
        roles=data.get("roles", []),
    )


@app.get("/auth/me", tags=["auth"])
async def whoami(principal: TokenData = Depends(get_principal)):
    """Return the authenticated caller's identity and grants."""
    return {
        "user_id": principal.user_id,
        "roles": principal.roles,
        "scopes": principal.scopes,
        "auth_type": principal.auth_type,
    }


# Main grading endpoint with event streaming
@app.post("/grade", response_model=GradeResponse)
async def grade_code(
    request: GradeRequest,
    principal: TokenData = Depends(require_scope(SCOPE_GRADE_WRITE)),
):
    """
    Grade code with personalized meta-learning strategies
    and stream the result as a real-time event.
    """
    _authorize_user(principal, request.user_id)
    supported = {dimension.value for dimension in SUPPORTED_DIMENSIONS}
    unsupported = [name for name in request.dimensions if name not in supported]
    if unsupported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported dimensions: {', '.join(unsupported)}",
        )

    grading_id = f"grade_{uuid.uuid4()}"

    try:
        # Get or create user
        session = db_manager.get_session()
        user = session.query(User).filter_by(id=request.user_id).first()
        if not user:
            user = User(id=request.user_id)
            session.add(user)
            session.commit()

        # Load learned strategies for this user
        strategies = meta_learner.get_user_strategies(request.user_id)

        # Grade each dimension
        scores = {}
        feedback = {}
        all_suggestions = []

        for dim_name in request.dimensions:
            try:
                dimension = GradingDimension(dim_name)
                grader = get_grader_for_dimension(dimension)

                # Apply learned strategies
                if (
                    request.user_id in strategies
                    and dim_name in strategies[request.user_id]
                ):
                    strategy = strategies[request.user_id][dim_name]
                    if "weights" in strategy:
                        grader.update_weights(strategy["weights"])
                    if "thresholds" in strategy:
                        grader.update_thresholds(strategy["thresholds"])

                # Perform grading (handle different grader signatures)
                context_data = request.context or {}
                if dim_name == "speed":
                    # SpeedGrader needs generation_time
                    generation_time = context_data.get("generation_time", 1.0)
                    result = grader.grade(generation_time=generation_time)
                elif dim_name == "reliability":
                    # ReliabilityGrader needs task_attempts
                    task_attempts = context_data.get(
                        "task_attempts", [{"success": True, "score": 90}]
                    )
                    result = grader.grade(task_attempts=task_attempts)
                else:
                    # Other graders use code and language
                    result = grader.grade(
                        code=request.code, language=request.language, **context_data
                    )

                scores[dim_name] = result.score

                # Extract component scores from metadata if available
                component_breakdown = {}
                if hasattr(result, "metadata") and result.metadata:
                    component_breakdown = result.metadata.get("component_scores", {})

                # Merge breakdown with component scores
                if hasattr(result.breakdown, "__dict__"):
                    breakdown_dict = result.breakdown.__dict__.copy()
                elif isinstance(result.breakdown, dict):
                    breakdown_dict = result.breakdown.copy()
                else:
                    breakdown_dict = {}
                breakdown_dict.update(component_breakdown)

                feedback[dim_name] = {
                    "score": result.score,
                    "breakdown": breakdown_dict,
                    "feedback": result.feedback,
                    "suggestions": result.suggestions,
                }
                all_suggestions.extend(
                    [
                        {
                            "dimension": dim_name,
                            "category": (
                                sugg.category
                                if hasattr(sugg, "category")
                                else "General"
                            ),
                            "priority": (
                                sugg.priority if hasattr(sugg, "priority") else 1
                            ),
                            "description": (
                                sugg.description
                                if hasattr(sugg, "description")
                                else str(sugg)
                            ),
                            "expected_impact": (
                                sugg.expected_impact
                                if hasattr(sugg, "expected_impact")
                                else ""
                            ),
                            "examples": (
                                sugg.examples if hasattr(sugg, "examples") else []
                            ),
                        }
                        for sugg in result.suggestions
                    ]
                )

            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid dimension: {dim_name}"
                )

        # Calculate overall score
        overall_score = sum(scores.values()) / len(scores) if scores else 0.0

        # Store grading history
        history = GradingHistory(
            session_id=grading_id,
            user_id=user.id,
            agent_id=request.agent_id,
            dimension=",".join(request.dimensions),
            score=overall_score,
            max_score=100.0,
            percentage=overall_score,  # FIX: Set percentage for meta-learning
            grade_metadata={
                "code_length": len(request.code),
                "language": request.language,
                "dimensions": request.dimensions,
                "scores": scores,
            },
        )
        session.add(history)
        session.commit()
        session.close()

        # Prepare response
        response = GradeResponse(
            grading_id=grading_id,
            user_id=request.user_id,
            timestamp=datetime.utcnow().isoformat(),
            scores=scores,
            feedback=feedback,
            overall_score=round(overall_score, 2),
            improvement_suggestions=all_suggestions,
            learning_applied=bool(strategies.get(request.user_id)),
            cached=False,
        )

        # Emit event
        event = LearningEvent(
            event_type="grading_complete",
            user_id=request.user_id,
            data={
                "grading_id": grading_id,
                "overall_score": overall_score,
                "dimensions": request.dimensions,
            },
        )
        await event_queue.put(event)

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Feedback endpoint with meta-learning trigger
@app.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    principal: TokenData = Depends(require_scope(SCOPE_GRADE_WRITE)),
):
    """Submit feedback to improve future gradings"""
    _authorize_user(principal, request.user_id)
    try:
        # Update meta-learning strategies based on feedback
        meta_learner.update_from_feedback(
            user_id=request.user_id,
            grading_id=request.grading_id,
            rating=request.rating,
            comments=request.comments,
            helpful_suggestions=request.helpful_suggestions,
        )

        # Emit learning update event
        event = LearningEvent(
            event_type="learning_update",
            user_id=request.user_id,
            data={
                "grading_id": request.grading_id,
                "rating": request.rating,
                "updated": True,
            },
        )
        await event_queue.put(event)

        return {
            "status": "success",
            "message": "Feedback received and learning strategies updated",
        }
    except Exception as e:
        import traceback

        traceback.print_exc()  # Print full traceback to logs
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time updates
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    Real-time event streaming for a specific user.

    Browsers cannot set headers on WebSocket connections, so ``?token=`` and
    ``?api_key=`` query parameters are accepted as well.
    """
    token = websocket.query_params.get("token")
    query_api_key = websocket.query_params.get("api_key")
    authorization = (
        f"Bearer {token}" if token else websocket.headers.get("authorization")
    )
    principal = authenticate_headers(
        authorization,
        query_api_key or websocket.headers.get(config.API_KEY_HEADER),
    )

    if config.AUTH_ENABLED:
        if principal is None:
            await websocket.close(code=1008)
            return
        if "admin" not in principal.roles and principal.user_id != user_id:
            await websocket.close(code=1008)
            return

    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive and receive client messages
            await websocket.receive_text()
            # Echo back (could process commands here)
            await websocket.send_json(
                {
                    "type": "ack",
                    "message": "Connected to ToastyAnalytics",
                    "user_id": user_id,
                }
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


# Get user's learned strategies
@app.get("/strategies/{user_id}")
async def get_user_strategies(
    user_id: str,
    principal: TokenData = Depends(require_scope(SCOPE_ANALYTICS_READ)),
):
    """Get all learned strategies for a user"""
    _authorize_user(principal, user_id)
    strategies = meta_learner.get_user_strategies(user_id)
    return {
        "user_id": user_id,
        "strategies": strategies,
        "total_strategies": len(strategies),
    }


# Analytics endpoint
@app.get("/analytics/user/{user_id}")
async def get_user_analytics(
    user_id: str,
    limit: int = 100,
    principal: TokenData = Depends(require_scope(SCOPE_ANALYTICS_READ)),
):
    """Get analytics and improvement trends for a user"""
    _authorize_user(principal, user_id)
    session = db_manager.get_session()
    user = session.query(User).filter_by(id=user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get recent grading history
    history = (
        session.query(GradingHistory)
        .filter_by(user_id=user.id)
        .order_by(GradingHistory.timestamp.desc())
        .limit(limit)
        .all()
    )

    session.close()

    # Calculate trends
    scores_over_time = [
        {"timestamp": h.timestamp.isoformat(), "score": float(h.score)}
        for h in reversed(history)
    ]

    avg_score = sum(float(h.score) for h in history) / len(history) if history else 0.0

    # Get first and last scores for trend calculation (already converted to list)
    first_score = float(history[0].score) if len(history) > 0 else 0.0
    last_score = float(history[-1].score) if len(history) > 0 else 0.0

    return {
        "user_id": user_id,
        "total_submissions": len(history),
        "average_score": round(avg_score, 2),
        "recent_scores": scores_over_time,
        "improvement_trend": (
            "improving" if len(history) > 1 and last_score > first_score else "stable"
        ),
    }


# List available grading dimensions
@app.get("/dimensions")
async def list_dimensions(
    principal: TokenData = Depends(require_scope(SCOPE_GRADE_READ)),
):
    """List all available grading dimensions"""
    return {
        "dimensions": [
            {
                "name": dim.value,
                "description": _get_dimension_description(dim),
            }
            for dim in sorted(SUPPORTED_DIMENSIONS, key=lambda d: d.value)
        ]
    }


def _get_dimension_description(dim: GradingDimension) -> str:
    descriptions = {
        GradingDimension.CODE_QUALITY: "Code structure, readability, and best practices",
        GradingDimension.READABILITY: "Readability component of the code-quality analysis",
        GradingDimension.SPEED: "Generation and execution performance",
        GradingDimension.RELIABILITY: "Consistency and success rates across attempts",
        GradingDimension.ACCURACY: "Agreement with a supplied reference answer",
        GradingDimension.PROMPT_UNDERSTANDING: "How well a response addresses its prompt",
        GradingDimension.FOLLOWUP_QUALITY: "Continuity, specificity, and actionability of a follow-up",
        GradingDimension.EFFICIENCY: "Information density and concision of generated text",
        GradingDimension.PROMPT_QUALITY: "Specificity, clarity, and structure of a prompt",
    }
    return descriptions.get(dim, "Custom grading dimension")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)  # nosec B104
