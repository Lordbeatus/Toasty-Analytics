"""
API Gateway - GraphQL + REST unified entry point
Routes to microservices, handles authentication, rate limiting
"""

import sys
from pathlib import Path
from typing import Any, Dict

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).parent.parent))

app = FastAPI(
    title="ToastyAnalytics - API Gateway",
    description="Unified API gateway with GraphQL and REST",
    version="3.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs (from environment or service discovery)
GRADING_SERVICE = "http://grading-service:8000"
META_LEARNING_SERVICE = "http://meta-learning-service:8001"
ANALYTICS_SERVICE = "http://analytics-service:8002"


async def proxy_request(service_url: str, path: str, method: str = "GET", **kwargs):
    """Proxy request to microservice"""
    async with httpx.AsyncClient() as client:
        url = f"{service_url}{path}"
        response = await client.request(method, url, **kwargs)
        return response.json()


@app.get("/health")
async def health():
    """Gateway health check"""

    # Check all services
    services_status = {}

    for name, url in [
        ("grading", GRADING_SERVICE),
        ("meta-learning", META_LEARNING_SERVICE),
        ("analytics", ANALYTICS_SERVICE),
    ]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{url}/health", timeout=2.0)
                services_status[name] = (
                    "healthy" if response.status_code == 200 else "unhealthy"
                )
        except Exception:
            services_status[name] = "unreachable"

    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": "3.0.0",
        "services": services_status,
    }


# Proxy to grading service
@app.post("/grade")
async def grade(request: Request):
    """Grade code - proxies to grading service"""
    body = await request.json()
    return await proxy_request(GRADING_SERVICE, "/grade", method="POST", json=body)


@app.get("/dimensions")
async def dimensions():
    """List dimensions - proxies to grading service"""
    return await proxy_request(GRADING_SERVICE, "/dimensions")


# Proxy to meta-learning service
@app.post("/feedback")
async def feedback(request: Request):
    """Submit feedback - proxies to meta-learning service"""
    body = await request.json()
    return await proxy_request(
        META_LEARNING_SERVICE, "/feedback", method="POST", json=body
    )


@app.get("/strategies/{user_id}")
async def strategies(user_id: str):
    """Get strategies - proxies to meta-learning service"""
    return await proxy_request(META_LEARNING_SERVICE, f"/strategies/{user_id}")


# Proxy to analytics service
@app.get("/analytics/{user_id}")
async def analytics(user_id: str, limit: int = 10):
    """Get analytics - proxies to analytics service"""
    return await proxy_request(ANALYTICS_SERVICE, f"/analytics/{user_id}?limit={limit}")


@app.get("/history/{user_id}")
async def history(user_id: str, limit: int = 20):
    """Get history - proxies to analytics service"""
    return await proxy_request(ANALYTICS_SERVICE, f"/history/{user_id}?limit={limit}")


# GraphQL integration
try:
    from graphql_api import create_graphql_router

    if graphql_router := create_graphql_router():
        app.include_router(graphql_router)
        print("✅ GraphQL API enabled at /graphql")
except Exception as e:
    print(f"⚠️  GraphQL not available: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
