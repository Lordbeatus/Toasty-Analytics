"""
Event Sourcing Example Integration

Shows how to integrate event sourcing with existing FastAPI application.
"""

import uuid
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from src.event_sourcing.commands import (
    CreateUserCommand,
    GradeCodeCommand,
    SubmitFeedbackCommand,
    get_command_handler,
)
from src.event_sourcing.event_store import EventType, get_event_store
from src.event_sourcing.projections import get_projection_manager


# Pydantic models for API
class GradeRequest(BaseModel):
    code: str
    language: str
    dimensions: List[str]
    user_id: str


class FeedbackRequest(BaseModel):
    grading_id: str
    rating: int
    comment: Optional[str] = None


class UserCreateRequest(BaseModel):
    username: str
    email: str


# Initialize event sourcing
def init_event_sourcing(app: FastAPI):
    """
    Initialize event sourcing for FastAPI app.

    Call this during app startup:
        @app.on_event("startup")
        async def startup():
            init_event_sourcing(app)
    """
    # Get instances
    event_store = get_event_store()
    projection_manager = get_projection_manager()

    # Rebuild projections from events (on startup)
    projection_manager.rebuild_all_projections()

    # Store in app state
    app.state.event_store = event_store
    app.state.projection_manager = projection_manager
    app.state.command_handler = get_command_handler()


# API endpoints
def add_event_sourcing_routes(app: FastAPI):
    """Add event sourcing routes to FastAPI app"""

    @app.post("/api/v2/grade", tags=["Event Sourcing"])
    async def grade_code_with_events(request: GradeRequest):
        """
        Grade code using event sourcing.

        This creates GRADING_REQUESTED and GRADING_COMPLETED events.
        """
        command = GradeCodeCommand(
            command_id=str(uuid.uuid4()),
            user_id=request.user_id,
            code=request.code,
            language=request.language,
            dimensions=request.dimensions,
            metadata={"source": "api"},
        )

        grading_id = app.state.command_handler.handle_grade_code(command)

        # Get projection
        projection = app.state.projection_manager.get_grading_projection(grading_id)

        return {
            "grading_id": grading_id,
            "status": projection.status if projection else "pending",
            "score": projection.score if projection else None,
        }

    @app.post("/api/v2/feedback", tags=["Event Sourcing"])
    async def submit_feedback_with_events(request: FeedbackRequest, user_id: str):
        """
        Submit feedback using event sourcing.

        This creates FEEDBACK_SUBMITTED event and may trigger STRATEGY_LEARNED.
        """
        command = SubmitFeedbackCommand(
            command_id=str(uuid.uuid4()),
            user_id=user_id,
            grading_id=request.grading_id,
            rating=request.rating,
            comment=request.comment,
            metadata={"source": "api"},
        )

        feedback_id = app.state.command_handler.handle_submit_feedback(command)

        return {"feedback_id": feedback_id, "status": "submitted"}

    @app.post("/api/v2/users", tags=["Event Sourcing"])
    async def create_user_with_events(request: UserCreateRequest):
        """
        Create user using event sourcing.

        This creates USER_CREATED event.
        """
        command = CreateUserCommand(
            command_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            username=request.username,
            email=request.email,
            metadata={"source": "api"},
        )

        user_id = app.state.command_handler.handle_create_user(command)

        return {"user_id": user_id, "username": request.username}

    @app.get("/api/v2/users/{user_id}/stats", tags=["Event Sourcing"])
    async def get_user_stats(user_id: str):
        """
        Get user statistics from projection (read model).

        This queries the materialized view, not the event store.
        """
        projection = app.state.projection_manager.get_user_projection(user_id)

        if not projection:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "user_id": projection.user_id,
            "username": projection.username,
            "total_gradings": projection.total_gradings,
            "average_score": projection.average_score,
            "feedback_count": projection.feedback_count,
            "strategies_learned": projection.strategies_learned,
            "last_activity": (
                projection.last_activity.isoformat()
                if projection.last_activity
                else None
            ),
        }

    @app.get("/api/v2/gradings/{grading_id}", tags=["Event Sourcing"])
    async def get_grading_details(grading_id: str):
        """Get grading details from projection"""
        projection = app.state.projection_manager.get_grading_projection(grading_id)

        if not projection:
            raise HTTPException(status_code=404, detail="Grading not found")

        return {
            "grading_id": projection.grading_id,
            "user_id": projection.user_id,
            "language": projection.code_language,
            "dimensions": projection.dimensions,
            "score": projection.score,
            "status": projection.status,
            "duration_ms": projection.duration_ms,
            "feedback_received": projection.feedback_received,
        }

    @app.get("/api/v2/events/{aggregate_id}", tags=["Event Sourcing"])
    async def get_event_stream(aggregate_id: str):
        """
        Get event stream for an aggregate.

        Useful for debugging and auditing.
        """
        events = app.state.event_store.get_events(aggregate_id)

        return {
            "aggregate_id": aggregate_id,
            "event_count": len(events),
            "events": [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type,
                    "timestamp": e.timestamp.isoformat(),
                    "version": e.version,
                    "data": e.data,
                }
                for e in events
            ],
        }

    @app.post("/api/v2/projections/rebuild", tags=["Event Sourcing"])
    async def rebuild_projections():
        """
        Rebuild all projections from event store.

        Use this if projections get out of sync.
        """
        app.state.projection_manager.rebuild_all_projections()

        stats = app.state.projection_manager.get_user_statistics()

        return {"status": "rebuilt", "statistics": stats}

    @app.get("/api/v2/statistics", tags=["Event Sourcing"])
    async def get_platform_statistics():
        """Get aggregated platform statistics from projections"""
        stats = app.state.projection_manager.get_user_statistics()

        return stats


# Example usage in main app
"""
from fastapi import FastAPI
from src.event_sourcing.integration import init_event_sourcing, add_event_sourcing_routes

app = FastAPI()

# Add event sourcing routes
add_event_sourcing_routes(app)

@app.on_event("startup")
async def startup():
    # Initialize event sourcing
    init_event_sourcing(app)

# Now you can use event sourcing endpoints:
# POST /api/v2/grade
# POST /api/v2/feedback
# GET /api/v2/users/{user_id}/stats
# GET /api/v2/events/{aggregate_id}
"""
