"""Versioned API router composition."""

from fastapi import APIRouter

from app.api.routes.reports import admin_router as admin_reports_router
from app.api.routes.reports import router as reports_router
from app.api.routes.interventions import router as interventions_router
from app.api.routes.impact import router as impact_router
from app.api.routes.duplicates import router as duplicates_router
from app.api.routes.hotspots import router as hotspots_router
from app.api.routes.temporal import router as temporal_router
from app.api.routes.recurrence import router as recurrence_router
from app.api.routes.trend import router as trend_router
from app.api.routes.severity import router as severity_router
from app.api.routes.risk import router as risk_router
from app.api.routes.recommendations import router as recommendations_router
from app.api.routes.ai import router as ai_router
from app.api.routes.auth import router as auth_router
from app.api.routes.auth import notifications_router


api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(notifications_router)
api_router.include_router(reports_router)
api_router.include_router(admin_reports_router)
api_router.include_router(interventions_router)
api_router.include_router(impact_router)
api_router.include_router(duplicates_router)
api_router.include_router(hotspots_router)
api_router.include_router(temporal_router)
api_router.include_router(recurrence_router)
api_router.include_router(trend_router)
api_router.include_router(severity_router)
api_router.include_router(risk_router)
api_router.include_router(recommendations_router)
api_router.include_router(ai_router)
