from app.routers.auth import router as auth_router
from app.routers.certification import router as certification_router
from app.routers.cock import router as cock_router
from app.routers.counseling import router as counseling_router
from app.routers.forum import router as forum_router
from app.routers.game2048 import router as game2048_router
from app.routers.leaderboard import router as leaderboard_router

__all__ = [
    "auth_router",
    "counseling_router",
    "certification_router",
    "cock_router",
    "forum_router",
    "game2048_router",
    "leaderboard_router",
]
