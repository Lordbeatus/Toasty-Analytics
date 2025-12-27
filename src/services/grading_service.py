"""
Grading Service - Microservice for code grading
Handles: AST analysis, neural grading, custom plugins
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.types import GradingDimension
from src.graders import get_grader_for_dimension

app = FastAPI(
    title="ToastyAnalytics - Grading Service",
    description="Microservice for code quality grading",
    version="3.0.0",
)


class GradeRequest(BaseModel):
    """Request to grade code"""

    code: str
    language: str = "python"
    dimensions: Optional[List[str]] = None
    user_id: Optional[str] = None
    use_neural: bool = False
    custom_grader: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class GradeResponse(BaseModel):
    """Response from grading"""

    user_id: Optional[str]
    scores: Dict[str, float]
    feedback: Dict[str, Any]
    suggestions: List[str]
    timestamp: datetime
    service: str = "grading-service"


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "grading-service",
        "version": "3.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/grade", response_model=GradeResponse)
async def grade_code(request: GradeRequest):
    """Grade code across specified dimensions"""

    # Default to code_quality if no dimensions specified
    if not request.dimensions:
        request.dimensions = ["code_quality"]

    scores = {}
    feedback = {}
    all_suggestions = []

    for dim_str in request.dimensions:
        try:
            # Convert string to GradingDimension enum
            dimension = GradingDimension(dim_str)

            # Get appropriate grader
            grader = get_grader_for_dimension(
                dimension,
                use_neural=request.use_neural,
                custom_grader=request.custom_grader,
            )

            # Perform grading
            context_data = request.context or {}

            if dim_str == "speed":
                generation_time = context_data.get("generation_time", 1.0)
                result = grader.grade(generation_time=generation_time)
            elif dim_str == "reliability":
                task_attempts = context_data.get(
                    "task_attempts", [{"success": True, "score": 90}]
                )
                result = grader.grade(task_attempts=task_attempts)
            else:
                result = grader.grade(
                    code=request.code, language=request.language, **context_data
                )

            scores[dim_str] = result.score

            # Extract component scores from metadata
            component_breakdown = {}
            if hasattr(result, "metadata") and result.metadata:
                component_breakdown = result.metadata.get("component_scores", {})

            # Build breakdown
            if hasattr(result.breakdown, "__dict__"):
                breakdown_dict = result.breakdown.__dict__.copy()
            elif isinstance(result.breakdown, dict):
                breakdown_dict = result.breakdown.copy()
            else:
                breakdown_dict = {}
            breakdown_dict.update(component_breakdown)

            feedback[dim_str] = {
                "score": result.score,
                "breakdown": breakdown_dict,
                "feedback": result.feedback,
                "suggestions": result.suggestions,
            }

            all_suggestions.extend(
                [
                    s.description if hasattr(s, "description") else str(s)
                    for s in result.suggestions
                ]
            )

        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid dimension: {dim_str}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Grading error: {str(e)}")

    return GradeResponse(
        user_id=request.user_id,
        scores=scores,
        feedback=feedback,
        suggestions=all_suggestions,
        timestamp=datetime.utcnow(),
    )


@app.get("/dimensions")
async def list_dimensions():
    """List available grading dimensions"""
    return {
        "dimensions": [
            {
                "name": "code_quality",
                "description": "Overall code quality including structure, readability, and best practices",
                "available": True,
            },
            {
                "name": "readability",
                "description": "Code readability and documentation quality",
                "available": True,
            },
            {
                "name": "speed",
                "description": "Code generation speed and efficiency",
                "available": True,
            },
            {
                "name": "reliability",
                "description": "Task completion reliability and success rate",
                "available": True,
            },
        ]
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    # TODO: Implement actual Prometheus metrics
    return {
        "grading_requests_total": 0,
        "grading_duration_seconds": 0.0,
        "active_grading_requests": 0,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
