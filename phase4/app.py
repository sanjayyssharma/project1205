"""FastAPI ASGI application (Phase 4 backend)."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from phase4 import metrics
from phase4.errors import RateLimitedError, ServiceError
from phase4.rate_limit import allow as rate_limit_allow
from phase4.repository import RestaurantRepository
from phase4.schemas import RecommendationRequest, RecommendationResponse
from phase4.service import RecommendationService
from restaurant_recs.config import Settings, get_settings

logger = logging.getLogger(__name__)


def _effective_settings(request: Request) -> Settings:
    """Respect ``app.dependency_overrides[get_settings]`` (used in tests)."""
    ov = request.app.dependency_overrides.get(get_settings)
    if ov is not None:
        return ov()
    return get_settings()


def get_service(settings: Settings = Depends(get_settings)) -> RecommendationService:
    return RecommendationService(settings)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Restaurant recommendations API",
        version="0.1.0",
        description="Phase 4 HTTP backend: filter (Phase 2) + Groq rank (Phase 3). Phase 6: metrics, limits, structured access logs.",
    )

    @app.middleware("http")
    async def observability_middleware(request: Request, call_next: Callable):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = rid
        settings = _effective_settings(request)

        if (
            settings.api_rate_limit_per_minute > 0
            and request.method == "POST"
            and request.url.path == "/v1/recommendations"
        ):
            client = request.client.host if request.client else "unknown"
            forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
            key = forwarded or client
            if not rate_limit_allow(key, settings.api_rate_limit_per_minute):
                metrics.inc("recommendations_rate_limited_total")
                return JSONResponse(
                    status_code=429,
                    content=RateLimitedError(limit_per_minute=settings.api_rate_limit_per_minute).as_body(),
                    headers={"X-Request-ID": rid},
                )

        t0 = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            logger.exception(
                "request_id=%s method=%s path=%s duration_ms=%.2f status=exception",
                rid,
                request.method,
                request.url.path,
                duration_ms,
            )
            raise
        duration_ms = (time.perf_counter() - t0) * 1000.0
        response.headers["X-Request-ID"] = rid
        logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
            rid,
            request.method,
            request.url.path,
            getattr(response, "status_code", "?"),
            duration_ms,
        )
        return response

    @app.exception_handler(ServiceError)
    async def service_error_handler(_request: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.as_body())

    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    async def health(settings_dep: Settings = Depends(get_settings)) -> dict[str, object]:
        repo = RestaurantRepository(settings_dep)
        path = repo.snapshot_path()
        return {
            "status": "ok",
            "snapshot_path": str(path.resolve()),
            "snapshot_exists": path.exists(),
            "groq_configured": bool((settings_dep.groq_api_key or "").strip()),
            "rate_limit_per_minute": settings_dep.api_rate_limit_per_minute,
            "groq_timeout_seconds": settings_dep.groq_timeout_seconds,
            "groq_max_retries": settings_dep.groq_max_retries,
            "llm_max_prompt_chars": settings_dep.llm_max_prompt_chars,
        }

    @app.get("/metrics", tags=["meta"])
    async def prometheus_metrics() -> PlainTextResponse:
        """Prometheus-style text metrics (in-process counters; Phase 6)."""
        return PlainTextResponse(metrics.prometheus_text(), media_type="text/plain; version=0.0.4")

    @app.post(
        "/v1/recommendations",
        response_model=RecommendationResponse,
        tags=["recommendations"],
    )
    async def create_recommendations(
        body: RecommendationRequest,
        request: Request,
        service: RecommendationService = Depends(get_service),
    ) -> RecommendationResponse:
        rid = getattr(request.state, "request_id", "")
        try:
            return service.recommend(body, request_id=rid)
        except ServiceError:
            raise
        except Exception as exc:  # noqa: BLE001
            metrics.inc("recommendations_errors_total")
            logger.exception("request_id=%s recommend failed: %s", rid, exc)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "internal_error",
                    "message": "An unexpected error occurred.",
                },
            ) from exc

    return app


app = create_app()
