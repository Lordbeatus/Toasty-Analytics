"""
Event Sourcing - Command Handlers (Write Side of CQRS)

Handles commands and generates events.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .event_store import Event, EventStore, EventType, get_event_store

logger = logging.getLogger(__name__)


@dataclass
class Command:
    """Base command class"""

    command_id: str
    user_id: str
    metadata: Dict[str, Any]


@dataclass
class GradeCodeCommand(Command):
    """Command to grade code"""

    code: str
    language: str
    dimensions: List[str]


@dataclass
class SubmitFeedbackCommand(Command):
    """Command to submit feedback"""

    grading_id: str
    rating: int
    comment: Optional[str] = None


@dataclass
class CreateUserCommand(Command):
    """Command to create a user"""

    username: str
    email: str


class CommandHandler:
    """
    Handles commands and generates events.

    This is the "write side" of CQRS.
    """

    def __init__(self, event_store: EventStore):
        """
        Initialize command handler.

        Args:
            event_store: Event store instance
        """
        self.event_store = event_store

    def handle_grade_code(self, command: GradeCodeCommand) -> str:
        """
        Handle grade code command.

        Args:
            command: GradeCodeCommand

        Returns:
            Grading ID
        """
        grading_id = str(uuid.uuid4())

        # Append GRADING_REQUESTED event
        self.event_store.append(
            event_type=EventType.GRADING_REQUESTED,
            aggregate_id=grading_id,
            aggregate_type="grading",
            data={
                "user_id": command.user_id,
                "code": command.code,
                "language": command.language,
                "dimensions": command.dimensions,
            },
            metadata=command.metadata,
        )

        logger.info(f"Grading requested: {grading_id} for user {command.user_id}")

        # Simulate grading completion (in real system, this would be async)
        # For now, immediately complete with a mock score
        score = 85.0  # Mock score

        self.event_store.append(
            event_type=EventType.GRADING_COMPLETED,
            aggregate_id=grading_id,
            aggregate_type="grading",
            data={
                "user_id": command.user_id,
                "score": score,
                "dimensions": command.dimensions,
                "breakdown": {"code_quality": 90, "reliability": 80},
            },
            metadata={"processing_time_ms": 150},
        )

        logger.info(f"Grading completed: {grading_id} with score {score}")

        return grading_id

    def handle_submit_feedback(self, command: SubmitFeedbackCommand) -> str:
        """
        Handle submit feedback command.

        Args:
            command: SubmitFeedbackCommand

        Returns:
            Feedback ID
        """
        feedback_id = str(uuid.uuid4())

        # Append FEEDBACK_SUBMITTED event
        self.event_store.append(
            event_type=EventType.FEEDBACK_SUBMITTED,
            aggregate_id=command.grading_id,
            aggregate_type="grading",
            data={
                "user_id": command.user_id,
                "grading_id": command.grading_id,
                "rating": command.rating,
                "comment": command.comment,
            },
            metadata=command.metadata,
        )

        logger.info(
            f"Feedback submitted: {feedback_id} for grading {command.grading_id}"
        )

        # If positive feedback, learn strategy
        if command.rating >= 4:
            self.event_store.append(
                event_type=EventType.STRATEGY_LEARNED,
                aggregate_id=command.user_id,
                aggregate_type="user",
                data={
                    "user_id": command.user_id,
                    "grading_id": command.grading_id,
                    "strategy": "positive_feedback_pattern",
                },
                metadata={},
            )

        return feedback_id

    def handle_create_user(self, command: CreateUserCommand) -> str:
        """
        Handle create user command.

        Args:
            command: CreateUserCommand

        Returns:
            User ID
        """
        user_id = command.user_id or str(uuid.uuid4())

        # Append USER_CREATED event
        self.event_store.append(
            event_type=EventType.USER_CREATED,
            aggregate_id=user_id,
            aggregate_type="user",
            data={
                "user_id": user_id,
                "username": command.username,
                "email": command.email,
            },
            metadata=command.metadata,
        )

        logger.info(f"User created: {user_id} ({command.username})")

        return user_id


# Global command handler
_command_handler: Optional[CommandHandler] = None


def get_command_handler() -> CommandHandler:
    """Get or create global command handler"""
    global _command_handler

    if _command_handler is None:
        event_store = get_event_store()
        _command_handler = CommandHandler(event_store)

    return _command_handler
