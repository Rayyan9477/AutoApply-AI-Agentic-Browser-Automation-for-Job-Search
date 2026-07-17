"""API v1 router aggregating all sub-routers."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, require_superuser
from app.api.v1.admin import router as admin_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.applications import router as applications_router
from app.api.v1.auth import router as auth_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.platform_sessions import router as platform_sessions_router
from app.api.v1.resumes import router as resumes_router
from app.api.v1.settings import router as settings_router

v1_router = APIRouter()

# Auth routes are public (no guard).
v1_router.include_router(auth_router, prefix="/auth", tags=["Auth"])

# All other routers require an authenticated user (router-level guard).
_auth = [Depends(get_current_user)]
v1_router.include_router(jobs_router, prefix="/jobs", tags=["Jobs"], dependencies=_auth)
v1_router.include_router(
    applications_router, prefix="/applications", tags=["Applications"], dependencies=_auth
)
v1_router.include_router(resumes_router, prefix="/resumes", tags=["Resumes"], dependencies=_auth)
v1_router.include_router(
    analytics_router, prefix="/analytics", tags=["Analytics"], dependencies=_auth
)
v1_router.include_router(settings_router, prefix="/settings", tags=["Settings"], dependencies=_auth)
v1_router.include_router(
    platform_sessions_router,
    prefix="/platform-sessions",
    tags=["Platform Sessions"],
    dependencies=_auth,
)

# Admin/health routes require a superuser.
v1_router.include_router(
    admin_router, prefix="/admin", tags=["Admin"], dependencies=[Depends(require_superuser)]
)
