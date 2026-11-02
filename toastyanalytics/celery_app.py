"""
Celery application and scheduled tasks.

Tasks are queued on the broker configured by CELERY_BROKER_URL, with results
stored in CELERY_RESULT_BACKEND. Start a worker with:

    celery -A toastyanalytics.celery_app worker --loglevel=info
"""

import logging

from celery import Celery
from celery.schedules import crontab

from toastyanalytics.config import config

# Setup logging
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "toastyanalytics",
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND,
)

# Configuration
celery_app.conf.update(
    # How long to keep results
    result_expires=3600,  # 1 hour
    # Task routing
    task_routes={
        "grading.*": {"queue": "grading"},
        "analytics.*": {"queue": "analytics"},
    },
    # Serialization (how data is stored)
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Performance
    worker_prefetch_multiplier=4,  # How many tasks to grab at once
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (prevent memory leaks)
)


@celery_app.task(name="grading.grade_code", bind=True)
def grade_code_task(self, user_id: str, code: str, language: str, dimensions: list):
    """
    Background task to grade code.

    This runs in a separate worker process, not blocking the API.

    Args:
        self: Celery task instance (gives us task_id, retry, etc.)
        user_id: Who's AI wrote this code
        code: The code to grade
        language: Programming language
        dimensions: What to grade (code_quality, speed, etc.)

    Returns:
        Grading results dictionary
    """
    from toastyanalytics import DatabaseManager, MetaLearner, get_grader_for_dimension
    from toastyanalytics.core.types import GradingDimension

    try:
        # Update task state
        self.update_state(state="GRADING", meta={"status": "Analyzing code..."})

        # Initialize
        db = DatabaseManager()
        meta_learner = MetaLearner(db)

        results = []

        # Grade each dimension
        for dim_str in dimensions:
            dim = GradingDimension(dim_str)

            # Get grader with learned strategies
            grader = get_grader_for_dimension(dim)
            meta_learner.apply_strategies_to_grader(grader, user_id)

            # Grade!
            result = grader.grade(code=code, language=language)

            results.append(
                {
                    "dimension": dim.value,
                    "score": result.score,
                    "max_score": result.max_score,
                    "percentage": result.percentage,
                    "feedback": result.feedback,
                    "suggestions": [
                        {
                            "description": s.description,
                            "category": s.category,
                            "expected_impact": s.expected_impact,
                        }
                        for s in result.suggestions
                    ],
                }
            )

        # Return results
        return {"status": "completed", "user_id": user_id, "results": results}

    except Exception as e:
        # Retry on failure (max 3 times)
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise self.retry(exc=e, countdown=5, max_retries=3)


@celery_app.task(name="analytics.update_collective_learning")
def update_collective_learning_task(user_id: str):
    """
    Background task to update collective learning patterns.

    This analyzes patterns across all users and updates global insights.
    Runs periodically or after significant new data.
    """
    try:
        # Analyze patterns (this is expensive, hence background)
        # ... pattern analysis logic ...

        return {"status": "updated", "user_id": user_id}

    except Exception as e:
        logger.error(f"Collective learning update failed: {e}")
        raise


# Periodic tasks (scheduled jobs)
celery_app.conf.beat_schedule = {
    # Run collective learning update every hour
    "update-collective-learning": {
        "task": "analytics.update_collective_learning_task",
        "schedule": crontab(minute=0),  # Every hour at :00
    },
}
