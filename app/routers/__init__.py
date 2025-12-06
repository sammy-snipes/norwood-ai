from app.routers.auth import router as auth_router
from app.routers.certification import router as certification_router
from app.routers.counseling import router as counseling_router

__all__ = ["auth_router", "counseling_router", "certification_router"]
