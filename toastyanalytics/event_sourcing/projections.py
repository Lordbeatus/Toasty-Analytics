"""
Event Sourcing - Projections (Read Models)

Implements the CQRS pattern with event-driven projections.
Projections create materialized views from event streams.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .event_store import Event, EventStore, EventType, get_event_store

logger = logging.getLogger(__name__)


@dataclass
class UserProjection:
    """User read model projection"""

    user_id: str
    username: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[datetime] = None
    total_gradings: int = 0
    average_score: float = 0.0
    feedback_count: int = 0
    strategies_learned: int = 0
    last_activity: Optional[datetime] = None

    def apply_event(self, event: Event):
        """Apply event to update projection"""
        if event.event_type == EventType.USER_CREATED:
            self.username = event.data.get("username")
            self.email = event.data.get("email")
            self.created_at = event.timestamp

        elif event.event_type == EventType.GRADING_COMPLETED:
            self.total_gradings += 1
            score = event.data.get("score", 0)
            # Update running average
            self.average_score = (
                self.average_score * (self.total_gradings - 1) + score
            ) / self.total_gradings
            self.last_activity = event.timestamp

        elif event.event_type == EventType.FEEDBACK_SUBMITTED:
            self.feedback_count += 1
            self.last_activity = event.timestamp

        elif event.event_type == EventType.STRATEGY_LEARNED:
            self.strategies_learned += 1


@dataclass
class GradingProjection:
    """Grading session read model projection"""

    grading_id: str
    user_id: str
    code_language: Optional[str] = None
    dimensions: List[str] = field(default_factory=list)
    score: Optional[float] = None
    status: str = "pending"  # pending, completed, failed
    requested_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    feedback_received: bool = False

    def apply_event(self, event: Event):
        """Apply event to update projection"""
        if event.event_type == EventType.GRADING_REQUESTED:
            self.code_language = event.data.get("language")
            self.dimensions = event.data.get("dimensions", [])
            self.requested_at = event.timestamp
            self.status = "pending"

        elif event.event_type == EventType.GRADING_COMPLETED:
            self.score = event.data.get("score")
            self.completed_at = event.timestamp
            self.status = "completed"
            if self.requested_at:
                self.duration_ms = int(
                    (self.completed_at - self.requested_at).total_seconds() * 1000
                )

        elif event.event_type == EventType.FEEDBACK_SUBMITTED:
            self.feedback_received = True


class ProjectionManager:
    """
    Manages projections and keeps them up-to-date with events.

    Features:
    - Event subscription and replay
    - Projection rebuilding
    - Materialized view management
    """

    def __init__(self, event_store: EventStore):
        """
        Initialize projection manager.

        Args:
            event_store: Event store instance
        """
        self.event_store = event_store
        self.user_projections: Dict[str, UserProjection] = {}
        self.grading_projections: Dict[str, GradingProjection] = {}

        # Register event handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register event handlers for projections"""
        # User projection handlers
        self.event_store.register_handler(
            EventType.USER_CREATED, self._handle_user_event
        )
        self.event_store.register_handler(
            EventType.GRADING_COMPLETED, self._handle_user_event
        )
        self.event_store.register_handler(
            EventType.FEEDBACK_SUBMITTED, self._handle_user_event
        )
        self.event_store.register_handler(
            EventType.STRATEGY_LEARNED, self._handle_user_event
        )

        # Grading projection handlers
        self.event_store.register_handler(
            EventType.GRADING_REQUESTED, self._handle_grading_event
        )
        self.event_store.register_handler(
            EventType.GRADING_COMPLETED, self._handle_grading_event
        )
        self.event_store.register_handler(
            EventType.FEEDBACK_SUBMITTED, self._handle_grading_event
        )

    def _handle_user_event(self, event: Event):
        """Handle events for user projection"""
        user_id = event.data.get("user_id") or event.aggregate_id

        if user_id not in self.user_projections:
            self.user_projections[user_id] = UserProjection(user_id=user_id)

        self.user_projections[user_id].apply_event(event)
        logger.debug(f"Updated user projection for {user_id}")

    def _handle_grading_event(self, event: Event):
        """Handle events for grading projection"""
        grading_id = event.aggregate_id
        user_id = event.data.get("user_id", "unknown")

        if grading_id not in self.grading_projections:
            self.grading_projections[grading_id] = GradingProjection(
                grading_id=grading_id, user_id=user_id
            )

        self.grading_projections[grading_id].apply_event(event)
        logger.debug(f"Updated grading projection for {grading_id}")

    def get_user_projection(self, user_id: str) -> Optional[UserProjection]:
        """Get user projection"""
        return self.user_projections.get(user_id)

    def get_grading_projection(self, grading_id: str) -> Optional[GradingProjection]:
        """Get grading projection"""
        return self.grading_projections.get(grading_id)

    def rebuild_user_projection(self, user_id: str) -> UserProjection:
        """
        Rebuild user projection from events.

        Args:
            user_id: User ID

        Returns:
            Rebuilt UserProjection
        """
        projection = UserProjection(user_id=user_id)

        # Get all events for user
        events = self.event_store.get_all_events()

        # Filter events related to this user
        user_events = [
            e
            for e in events
            if e.data.get("user_id") == user_id or e.aggregate_id == user_id
        ]

        # Apply all events
        for event in user_events:
            projection.apply_event(event)

        self.user_projections[user_id] = projection
        logger.info(
            f"Rebuilt user projection for {user_id} from {len(user_events)} events"
        )

        return projection

    def rebuild_all_projections(self):
        """Rebuild all projections from event store"""
        logger.info("Rebuilding all projections...")

        # Clear existing projections
        self.user_projections.clear()
        self.grading_projections.clear()

        # Get all events
        events = self.event_store.get_all_events(limit=10000)

        # Apply all events
        for event in events:
            if event.event_type in [
                EventType.USER_CREATED,
                EventType.GRADING_COMPLETED,
                EventType.FEEDBACK_SUBMITTED,
                EventType.STRATEGY_LEARNED,
            ]:
                self._handle_user_event(event)

            if event.event_type in [
                EventType.GRADING_REQUESTED,
                EventType.GRADING_COMPLETED,
                EventType.FEEDBACK_SUBMITTED,
            ]:
                self._handle_grading_event(event)

        logger.info(
            f"Rebuilt {len(self.user_projections)} user projections and "
            f"{len(self.grading_projections)} grading projections"
        )

    def get_user_statistics(self) -> Dict[str, Any]:
        """Get aggregated user statistics"""
        total_users = len(self.user_projections)
        total_gradings = sum(p.total_gradings for p in self.user_projections.values())
        avg_score = (
            sum(p.average_score for p in self.user_projections.values()) / total_users
            if total_users > 0
            else 0
        )

        return {
            "total_users": total_users,
            "total_gradings": total_gradings,
            "average_score": avg_score,
            "active_users": len(
                [
                    p
                    for p in self.user_projections.values()
                    if p.last_activity
                    and (datetime.utcnow() - p.last_activity).days < 7
                ]
            ),
        }


# Global projection manager
_projection_manager: Optional[ProjectionManager] = None


def get_projection_manager() -> ProjectionManager:
    """Get or create global projection manager"""
    global _projection_manager

    if _projection_manager is None:
        event_store = get_event_store()
        _projection_manager = ProjectionManager(event_store)

    return _projection_manager
