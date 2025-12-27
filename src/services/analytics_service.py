"""
Analytics Service - Microservice for analytics and reporting
Handles: User stats, history, trends, aggregations
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import DatabaseManager

app = FastAPI(
    title="ToastyAnalytics - Analytics Service",
    description="Microservice for analytics and reporting",
    version="3.0.0",
)

db_manager = DatabaseManager()


class UserStatsResponse(BaseModel):
    """User statistics"""

    user_id: str
    total_submissions: int
    average_score: float
    recent_scores: List[Dict[str, Any]]
    improvement_trend: str


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "analytics-service", "version": "3.0.0"}


@app.get("/analytics/{user_id}", response_model=UserStatsResponse)
async def get_user_analytics(user_id: str, limit: int = Query(default=10, le=100)):
    """Get analytics for a user"""

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
            .limit(limit)
            .all()
        )

        # Calculate stats
        scores_over_time = [
            {"timestamp": h.timestamp.isoformat(), "score": float(h.score)}
            for h in reversed(history)
        ]

        avg_score = (
            sum(float(h.score) for h in history) / len(history) if history else 0.0
        )

        # Calculate trend
        first_score = float(history[0].score) if len(history) > 0 else 0.0
        last_score = float(history[-1].score) if len(history) > 0 else 0.0

        return UserStatsResponse(
            user_id=user_id,
            total_submissions=len(history),
            average_score=round(avg_score, 2),
            recent_scores=scores_over_time,
            improvement_trend=(
                "improving"
                if len(history) > 1 and first_score > last_score
                else "stable"
            ),
        )

    finally:
        session.close()


@app.get("/history/{user_id}")
async def get_user_history(
    user_id: str,
    limit: int = Query(default=20, le=100),
    dimension: Optional[str] = None,
):
    """Get grading history for a user"""

    session = db_manager.get_session()
    try:
        from database.models import GradingHistory, User

        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        query = session.query(GradingHistory).filter_by(user_id=user.id)

        if dimension:
            query = query.filter_by(dimension=dimension)

        history = query.order_by(GradingHistory.timestamp.desc()).limit(limit).all()

        return {
            "user_id": user_id,
            "total_records": len(history),
            "history": [
                {
                    "id": h.id,
                    "code_snippet": h.code_snippet[:100],
                    "language": h.language,
                    "score": float(h.score),
                    "dimension": h.dimension,
                    "timestamp": h.timestamp.isoformat(),
                }
                for h in history
            ],
        }

    finally:
        session.close()


@app.get("/aggregated-stats")
async def get_aggregated_stats():
    """Get aggregated platform statistics"""

    session = db_manager.get_session()
    try:
        from database.models import GradingHistory, User
        from sqlalchemy import func

        total_users = session.query(func.count(User.id)).scalar()
        total_gradings = session.query(func.count(GradingHistory.id)).scalar()
        avg_platform_score = session.query(func.avg(GradingHistory.score)).scalar()

        # Get dimension breakdown
        dimension_stats = (
            session.query(
                GradingHistory.dimension,
                func.avg(GradingHistory.score).label("avg_score"),
                func.count(GradingHistory.id).label("count"),
            )
            .group_by(GradingHistory.dimension)
            .all()
        )

        return {
            "total_users": total_users or 0,
            "total_gradings": total_gradings or 0,
            "average_score": round(float(avg_platform_score or 0), 2),
            "by_dimension": [
                {
                    "dimension": d.dimension,
                    "average_score": round(float(d.avg_score), 2),
                    "total_gradings": d.count,
                }
                for d in dimension_stats
            ],
        }

    finally:
        session.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
