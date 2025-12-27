"""
Event Sourcing - Event Store Implementation

Provides event storage, retrieval, and replay capabilities.
Implements the Event Store pattern for CQRS architecture.
"""

import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

from sqlalchemy import Column, DateTime, Index, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()


class EventType(str, Enum):
    """Event types in the system"""

    GRADING_REQUESTED = "grading.requested"
    GRADING_COMPLETED = "grading.completed"
    FEEDBACK_SUBMITTED = "feedback.submitted"
    STRATEGY_LEARNED = "strategy.learned"
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    PLUGIN_LOADED = "plugin.loaded"
    THRESHOLD_UPDATED = "threshold.updated"


@dataclass
class Event:
    """Base event class"""

    event_id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime
    version: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "data": self.data,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary"""
        return cls(
            event_id=data["event_id"],
            event_type=data["event_type"],
            aggregate_id=data["aggregate_id"],
            aggregate_type=data["aggregate_type"],
            data=data["data"],
            metadata=data["metadata"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            version=data["version"],
        )


class EventModel(Base):
    """SQLAlchemy model for event storage"""

    __tablename__ = "event_store"

    id = Column(Integer, primary_key=True)
    event_id = Column(String(36), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    aggregate_id = Column(String(100), nullable=False, index=True)
    aggregate_type = Column(String(50), nullable=False, index=True)
    data = Column(Text, nullable=False)
    metadata = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    version = Column(Integer, nullable=False)

    __table_args__ = (
        Index("idx_aggregate", "aggregate_id", "version"),
        Index("idx_type_time", "event_type", "timestamp"),
    )


class EventStore:
    """
    Event Store for storing and retrieving domain events.

    Features:
    - Append-only event log
    - Event versioning
    - Optimistic concurrency control
    - Event replay
    - Snapshot support (future)
    """

    def __init__(self, db_url: str = "sqlite:///event_store.db"):
        """
        Initialize event store.

        Args:
            db_url: Database connection URL
        """
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Event handlers registry
        self.handlers: Dict[str, List[Callable]] = {}

    def append(
        self,
        event_type: str,
        aggregate_id: str,
        aggregate_type: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        expected_version: Optional[int] = None,
    ) -> Event:
        """
        Append an event to the store.

        Args:
            event_type: Type of event
            aggregate_id: ID of the aggregate
            aggregate_type: Type of aggregate
            data: Event data
            metadata: Optional metadata
            expected_version: Expected version for optimistic concurrency

        Returns:
            Created Event object

        Raises:
            ValueError: If version conflict occurs
        """
        session = self.SessionLocal()

        try:
            # Get current version
            current_version = self._get_current_version(session, aggregate_id)

            # Check optimistic concurrency
            if expected_version is not None and current_version != expected_version:
                raise ValueError(
                    f"Version conflict: expected {expected_version}, got {current_version}"
                )

            # Create event
            event = Event(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                aggregate_id=aggregate_id,
                aggregate_type=aggregate_type,
                data=data,
                metadata=metadata or {},
                timestamp=datetime.utcnow(),
                version=current_version + 1,
            )

            # Store event
            event_model = EventModel(
                event_id=event.event_id,
                event_type=event.event_type,
                aggregate_id=event.aggregate_id,
                aggregate_type=event.aggregate_type,
                data=json.dumps(event.data),
                metadata=json.dumps(event.metadata),
                timestamp=event.timestamp,
                version=event.version,
            )

            session.add(event_model)
            session.commit()

            logger.info(
                f"Event appended: {event_type} for {aggregate_id} v{event.version}"
            )

            # Publish to handlers
            self._publish_event(event)

            return event

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to append event: {e}")
            raise
        finally:
            session.close()

    def get_events(
        self, aggregate_id: str, from_version: int = 0, to_version: Optional[int] = None
    ) -> List[Event]:
        """
        Get events for an aggregate.

        Args:
            aggregate_id: ID of the aggregate
            from_version: Starting version (inclusive)
            to_version: Ending version (inclusive)

        Returns:
            List of events
        """
        session = self.SessionLocal()

        try:
            query = session.query(EventModel).filter(
                EventModel.aggregate_id == aggregate_id,
                EventModel.version >= from_version,
            )

            if to_version is not None:
                query = query.filter(EventModel.version <= to_version)

            query = query.order_by(EventModel.version)

            event_models = query.all()

            events = []
            for model in event_models:
                event = Event(
                    event_id=model.event_id,
                    event_type=model.event_type,
                    aggregate_id=model.aggregate_id,
                    aggregate_type=model.aggregate_type,
                    data=json.loads(model.data),
                    metadata=json.loads(model.metadata),
                    timestamp=model.timestamp,
                    version=model.version,
                )
                events.append(event)

            return events

        finally:
            session.close()

    def get_all_events(
        self,
        event_type: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Event]:
        """
        Get all events with optional filtering.

        Args:
            event_type: Filter by event type
            from_time: Filter events after this time
            to_time: Filter events before this time
            limit: Maximum number of events to return

        Returns:
            List of events
        """
        session = self.SessionLocal()

        try:
            query = session.query(EventModel)

            if event_type:
                query = query.filter(EventModel.event_type == event_type)

            if from_time:
                query = query.filter(EventModel.timestamp >= from_time)

            if to_time:
                query = query.filter(EventModel.timestamp <= to_time)

            query = query.order_by(EventModel.timestamp).limit(limit)

            event_models = query.all()

            events = []
            for model in event_models:
                event = Event(
                    event_id=model.event_id,
                    event_type=model.event_type,
                    aggregate_id=model.aggregate_id,
                    aggregate_type=model.aggregate_type,
                    data=json.loads(model.data),
                    metadata=json.loads(model.metadata),
                    timestamp=model.timestamp,
                    version=model.version,
                )
                events.append(event)

            return events

        finally:
            session.close()

    def replay_events(
        self,
        aggregate_id: str,
        apply_func: Callable[[Any, Event], Any],
        initial_state: Any = None,
    ) -> Any:
        """
        Replay events to rebuild aggregate state.

        Args:
            aggregate_id: ID of the aggregate
            apply_func: Function to apply events to state
            initial_state: Initial state before replay

        Returns:
            Final state after replaying all events
        """
        events = self.get_events(aggregate_id)
        state = initial_state

        for event in events:
            state = apply_func(state, event)

        logger.info(f"Replayed {len(events)} events for aggregate {aggregate_id}")

        return state

    def register_handler(self, event_type: str, handler: Callable[[Event], None]):
        """
        Register an event handler.

        Args:
            event_type: Event type to handle
            handler: Handler function
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []

        self.handlers[event_type].append(handler)
        logger.info(f"Registered handler for event type: {event_type}")

    def _publish_event(self, event: Event):
        """Publish event to registered handlers"""
        handlers = self.handlers.get(event.event_type, [])

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler failed for {event.event_type}: {e}")

    def _get_current_version(self, session: Session, aggregate_id: str) -> int:
        """Get current version for an aggregate"""
        result = (
            session.query(EventModel)
            .filter(EventModel.aggregate_id == aggregate_id)
            .order_by(EventModel.version.desc())
            .first()
        )

        return result.version if result else 0


# Global event store instance
_event_store: Optional[EventStore] = None


def get_event_store(db_url: Optional[str] = None) -> EventStore:
    """Get or create global event store instance"""
    global _event_store

    if _event_store is None:
        _event_store = EventStore(db_url or "sqlite:///event_store.db")

    return _event_store
