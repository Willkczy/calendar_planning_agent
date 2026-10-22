"""Run with: uvicorn src.api.app:app --host 127.0.0.1 --port 8000."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from config.settings import settings
from src.domain.models import (
    ApprovalRequest,
    CreatePlan,
    DraftUpdate,
    Plan,
    RevisionRequest,
)
from src.planning.service import PlanningService
from src.planning.store import ConflictError, PlanStore

ROOT = Path(__file__).resolve().parents[2]


def create_app(service: PlanningService | None = None) -> FastAPI:
    api = FastAPI(title="Calendar Planning Agent", version="0.2.0")
    service = service or PlanningService(
        PlanStore(os.getenv("PLANNER_DB_PATH", str(ROOT / ".data/planner.sqlite3")))
    )
    api.state.planner = service
    # This release shares one local user's calendar and database. Do not expose
    # it publicly; multi-user authentication/OAuth are a separate deployment.
    api.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"],
    )

    @api.middleware("http")
    async def same_origin(request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            allowed = {
                f"http://{request.headers.get('host')}",
                f"https://{request.headers.get('host')}",
                "http://127.0.0.1:5173",
                "http://localhost:5173",
            }
            if origin and origin not in allowed:
                return JSONResponse(
                    {"detail": "Cross-origin mutation is not allowed"}, status_code=403
                )
        return await call_next(request)

    @api.exception_handler(ConflictError)
    async def conflict(_request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @api.exception_handler(KeyError)
    async def missing(_request, _exc):
        return JSONResponse({"detail": "Plan not found"}, status_code=404)

    @api.exception_handler(ValueError)
    async def invalid(_request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @api.exception_handler(Exception)
    async def failure(_request, exc):
        logging.getLogger(__name__).error(
            "Planning operation failed: %s", type(exc).__name__
        )
        return JSONResponse(
            {
                "detail": "The operation could not be completed. Your saved plan is retained; reload and retry."
            },
            status_code=502,
        )

    @api.get("/api/config")
    def config():
        return {
            "calendar_mode": settings.CALENDAR_MODE,
            "calendar_id": settings.GOOGLE_CALENDAR_ID,
            "timezone": settings.APP_TIMEZONE,
            "llm_provider": settings.LLM_PROVIDER,
            "deployment": "local-single-user",
        }

    @api.get("/api/plans")
    def plans():
        return [
            {
                "id": p.id,
                "goal": p.goal,
                "status": p.status,
                "revision": p.revision,
                "updated_at": p.updated_at,
            }
            for p in service.store.list()
        ]

    @api.post("/api/plans", response_model=Plan, status_code=201)
    def create(request: CreatePlan):
        return service.create(request)

    @api.get("/api/plans/{plan_id}", response_model=Plan)
    def get(plan_id: str):
        return service.get(plan_id)

    @api.post("/api/plans/{plan_id}/decompose", response_model=Plan)
    def decompose(plan_id: str, request: RevisionRequest):
        return service.decompose(plan_id, request.revision)

    @api.put("/api/plans/{plan_id}/draft", response_model=Plan)
    def update(plan_id: str, request: DraftUpdate):
        return service.update(plan_id, request)

    @api.post("/api/plans/{plan_id}/generate", response_model=Plan)
    def generate(plan_id: str, request: RevisionRequest):
        return service.generate(plan_id, request.revision)

    @api.post("/api/plans/{plan_id}/approve", response_model=Plan)
    def approve(plan_id: str, request: ApprovalRequest):
        return service.approve(plan_id, request)

    @api.post("/api/plans/{plan_id}/reject", response_model=Plan)
    def reject(plan_id: str, request: RevisionRequest):
        return service.reject(plan_id, request.revision)

    dist = ROOT / "web/dist"
    if dist.is_dir():
        api.mount("/", StaticFiles(directory=dist, html=True), name="workspace")
    return api


app = create_app()
