"""
Meta-Learning Service - Microservice for adaptive learning
Handles: User strategies, feedback processing, pattern learning
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import DatabaseManager
from src.meta_learning.engine import MetaLearner

app = FastAPI(
    title="ToastyAnalytics - Meta-Learning Service",
    description="Microservice for adaptive learning and feedback",
    version="3.0.0",
)

# Initialize components
db_manager = DatabaseManager()
meta_learner = MetaLearner(db_manager)


class FeedbackRequest(BaseModel):
    """Feedback submission"""

    user_id: str
    session_id: str
    feedback_score: Optional[float] = None
    explicit_feedback: Optional[Dict[str, Any]] = None
    code_snippet: Optional[str] = None
    dimension: Optional[str] = None


class StrategyResponse(BaseModel):
    """Learning strategy response"""

    user_id: str
    strategies: Dict[str, Any]
    total_strategies: int
    last_updated: datetime


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "meta-learning-service",
        "version": "3.0.0",
        "database": "connected" if db_manager else "disconnected",
    }


@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit feedback on grading quality"""

    try:
        # Process feedback through meta-learner
        meta_learner.process_feedback(
            user_id=request.user_id,
            session_id=request.session_id,
            feedback_score=request.feedback_score,
            explicit_feedback=request.explicit_feedback or {},
        )

        # If code and dimension provided, record grading session
        if request.code_snippet and request.dimension:
            session = db_manager.get_session()
            try:
                from database.models import GradingHistory, User

                user = session.query(User).filter_by(user_id=request.user_id).first()
                if not user:
                    user = User(user_id=request.user_id)
                    session.add(user)
                    session.commit()

                history = GradingHistory(
                    user_id=user.id,
                    code_snippet=request.code_snippet[:500],
                    language="python",
                    score=request.feedback_score or 0,
                    dimension=request.dimension,
                    session_id=request.session_id,
                )
                session.add(history)
                session.commit()
            finally:
                session.close()

        return {
            "status": "success",
            "message": "Feedback processed",
            "user_id": request.user_id,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/strategies/{user_id}", response_model=StrategyResponse)
async def get_user_strategies(user_id: str):
    """Get learned strategies for a user"""

    try:
        strategies = meta_learner.get_user_strategies(user_id)

        return StrategyResponse(
            user_id=user_id,
            strategies=strategies,
            total_strategies=len(strategies),
            last_updated=datetime.utcnow(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/strategies/{user_id}/update")
async def update_strategies(user_id: str, strategies: Dict[str, Any]):
    """Update learning strategies for a user"""

    try:
        # Update strategies in meta-learner
        meta_learner.update_user_strategies(user_id, strategies)

        return {
            "status": "success",
            "user_id": user_id,
            "updated_strategies": len(strategies),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/patterns/{user_id}")
async def get_learning_patterns(user_id: str):
    """Get learning patterns for a user"""

    session = db_manager.get_session()
    try:
        from database.models import GradingHistory, User

        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get recent history
        history = (
            session.query(GradingHistory)
            .filter_by(user_id=user.id)
            .order_by(GradingHistory.timestamp.desc())
            .limit(50)
            .all()
        )

        # Analyze patterns
        patterns = {"common_mistakes": [], "improvement_areas": [], "strengths": []}

        if history:
            avg_score = sum(float(h.score) for h in history) / len(history)

            if avg_score < 70:
                patterns["improvement_areas"].append(
                    "Overall code quality needs improvement"
                )

            # Group by dimension
            by_dimension = {}
            for h in history:
                dim = h.dimension
                if dim not in by_dimension:
                    by_dimension[dim] = []
                by_dimension[dim].append(float(h.score))

            for dim, scores in by_dimension.items():
                avg = sum(scores) / len(scores)
                if avg > 80:
                    patterns["strengths"].append(f"Strong {dim} performance")
                elif avg < 60:
                    patterns["improvement_areas"].append(f"{dim} needs work")

        return {
            "user_id": user_id,
            "patterns": patterns,
            "total_sessions": len(history),
        }

    finally:
        session.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
