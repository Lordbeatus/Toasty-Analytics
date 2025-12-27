"""
ToastyAnalytics - Production MCP Server with Event-Driven Architecture
Includes: WebSocket support, GraphQL, Neural graders, Event streaming
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Fix Python path to allow absolute imports
root_path = Path(__file__).parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from src.core.types import FeedbackLevel, GradingDimension

# Now use absolute imports
from src.database.models import Agent, DatabaseManager, GradingHistory, User
from src.graders import get_grader_for_dimension
from src.meta_learning.engine import MetaLearner

# Import production features
try:
    from cache import CacheManager
    from config import get_settings
    from metrics import GRADING_DURATION, GRADING_REQUESTS, metrics_middleware
    from sentry_integration import init_sentry

    settings = get_settings()
    PRODUCTION_MODE = True
except ImportError:
    PRODUCTION_MODE = False
    settings = None

# Create FastAPI app with enhanced features
app = FastAPI(
    title="ToastyAnalytics MCP Server v2.0",
    description="AI Agent Self-Improvement with Meta-Learning & Event-Driven Architecture",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add metrics middleware if in production
if (
    PRODUCTION_MODE
    and settings
    and hasattr(settings, "ENABLE_METRICS")
    and settings.ENABLE_METRICS
):
    app.middleware("http")(metrics_middleware)

# Initialize components
db_manager = DatabaseManager()
meta_learner = MetaLearner(db_manager)

# Cache manager (optional)
cache_manager = None
if PRODUCTION_MODE:
    try:
        cache_manager = CacheManager()
    except:
        pass


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
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass

    async def broadcast(self, message: dict):
        for user_connections in self.active_connections.values():
            for connection in user_connections:
                try:
                    await connection.send_json(message)
                except:
                    pass


manager = ConnectionManager()

# Event queue for event-driven architecture
event_queue: asyncio.Queue = asyncio.Queue()


# Pydantic models
class GradeRequest(BaseModel):
    user_id: str
    agent_id: Optional[str] = None
    code: str
    language: str
    context: Optional[Dict[str, Any]] = {}
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
    if PRODUCTION_MODE:
        try:
            init_sentry()
        except:
            pass

    # Start event processor
    asyncio.create_task(process_events())

    print("🚀 ToastyAnalytics MCP Server v2.0 started")
    print(f"📊 Production mode: {PRODUCTION_MODE}")
    print(f"💾 Database: {db_manager.engine.url}")


# Health check
@app.get("/")
async def root():
    return {
        "service": "ToastyAnalytics MCP Server",
        "version": "2.0.0",
        "status": "running",
        "features": {
            "grading": True,
            "meta_learning": True,
            "websocket": True,
            "event_driven": True,
            "caching": cache_manager is not None,
            "metrics": PRODUCTION_MODE,
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
            "cache": "connected" if cache_manager else "not configured",
            "websocket": "active",
        },
    }


# Main grading endpoint with caching and event streaming
@app.post("/grade", response_model=GradeResponse)
async def grade_code(request: GradeRequest, background_tasks: BackgroundTasks):
    """
    Grade code with personalized meta-learning strategies
    Includes caching and real-time event streaming
    """
    grading_id = f"grade_{uuid.uuid4()}"

    # Track metrics
    if PRODUCTION_MODE:
        GRADING_REQUESTS.inc()

    # Check cache first
    cached = False
    if cache_manager:
        cached_result = await cache_manager.get_grade(
            request.user_id, request.code, request.dimensions
        )
        if cached_result:
            cached_result["cached"] = True
            return GradeResponse(**cached_result)

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

        # Cache the result
        if cache_manager:
            background_tasks.add_task(
                cache_manager.set_grade,
                request.user_id,
                request.code,
                request.dimensions,
                response.dict(),
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
async def submit_feedback(request: FeedbackRequest):
    """Submit feedback to improve future gradings"""
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
    """Real-time event streaming for a specific user"""
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive and receive client messages
            data = await websocket.receive_text()
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
async def get_user_strategies(user_id: str):
    """Get all learned strategies for a user"""
    strategies = meta_learner.get_user_strategies(user_id)
    return {
        "user_id": user_id,
        "strategies": strategies,
        "total_strategies": len(strategies),
    }


# Analytics endpoint
@app.get("/analytics/user/{user_id}")
async def get_user_analytics(user_id: str, limit: int = 100):
    """Get analytics and improvement trends for a user"""
    session = db_manager.get_session()
    user = session.query(User).filter_by(user_id=user_id).first()

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
            "improving" if len(history) > 1 and first_score > last_score else "stable"
        ),
    }


# List available grading dimensions
@app.get("/dimensions")
async def list_dimensions():
    """List all available grading dimensions"""
    return {
        "dimensions": [
            {
                "name": dim.value,
                "description": _get_dimension_description(dim),
                "available": True,
            }
            for dim in GradingDimension
        ]
    }


def _get_dimension_description(dim: GradingDimension) -> str:
    descriptions = {
        GradingDimension.CODE_QUALITY: "Code structure, readability, and best practices",
        GradingDimension.SPEED: "Generation and execution performance",
        GradingDimension.RELIABILITY: "Consistency and success rates",
    }
    return descriptions.get(dim, "Custom grading dimension")


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics endpoint"""
    if PRODUCTION_MODE:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
        from starlette.responses import Response

        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    else:
        return {"message": "Metrics not enabled in development mode"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
