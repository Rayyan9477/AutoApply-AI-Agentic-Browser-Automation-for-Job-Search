"""API v1 router aggregating all sub-routers."""

from fastapi import APIRouter

from app.api.v1.analytics import router as analytics_router
from app.api.v1.applications import router as applications_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.resumes import router as resumes_router
from app.api.v1.settings import router as settings_router

v1_router = APIRouter()

v1_router.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])
v1_router.include_router(applications_router, prefix="/applications", tags=["Applications"])
v1_router.include_router(resumes_router, prefix="/resumes", tags=["Resumes"])
v1_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
v1_router.include_router(settings_router, prefix="/settings", tags=["Settings"])
