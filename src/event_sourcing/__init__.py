"""
Event Sourcing - __init__.py

Makes event sourcing module easily importable.
"""

from .commands import (
    CommandHandler,
    CreateUserCommand,
    GradeCodeCommand,
    SubmitFeedbackCommand,
    get_command_handler,
)
from .event_store import Event, EventStore, EventType, get_event_store
from .integration import add_event_sourcing_routes, init_event_sourcing
from .projections import (
    GradingProjection,
    ProjectionManager,
    UserProjection,
    get_projection_manager,
)

__all__ = [
    # Event Store
    "EventStore",
    "Event",
    "EventType",
    "get_event_store",
    # Projections
    "ProjectionManager",
    "UserProjection",
    "GradingProjection",
    "get_projection_manager",
    # Commands
    "CommandHandler",
    "GradeCodeCommand",
    "SubmitFeedbackCommand",
    "CreateUserCommand",
    "get_command_handler",
    # Integration
    "init_event_sourcing",
    "add_event_sourcing_routes",
]
