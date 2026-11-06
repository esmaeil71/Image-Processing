from fastapi import APIRouter

from app.api.v1 import auth, jobs, models_api, studies, studies_extra, users

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(studies.router, prefix="/studies", tags=["studies"])
router.include_router(studies_extra.router, prefix="/studies", tags=["studies"])
router.include_router(models_api.router, prefix="/models", tags=["models"])
router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
