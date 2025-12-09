"""Leaderboard router - premium only rankings."""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.routers.auth import decode_token
from app.services import leaderboard as leaderboard_service

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


class NorwoodEntry(BaseModel):
    username: str
    norwood_stage: int
    avatar_url: str | None = None


class InsecurityEntry(BaseModel):
    username: str
    score: int
    avatar_url: str | None = None


class CockPleasureEntry(BaseModel):
    username: str
    pleasure_zone: str
    pleasure_zone_label: str
    avatar_url: str | None = None


class CockSizeEntry(BaseModel):
    username: str
    length_inches: float
    girth_inches: float
    size_category: str
    avatar_url: str | None = None


class LeaderboardResponse(BaseModel):
    best_norwood: list[NorwoodEntry]
    worst_norwood: list[NorwoodEntry]
    insecurity_index: list[InsecurityEntry]
    cock_pleasure: list[CockPleasureEntry]
    cock_size: list[CockSizeEntry]


def require_premium(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Require premium or admin user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_premium and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Leaderboard requires Sage Mode",
        )

    return user


@router.get("", response_model=LeaderboardResponse)
def get_leaderboard(
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get leaderboard data (premium only)."""
    best = leaderboard_service.get_best_norwood(db)
    worst = leaderboard_service.get_worst_norwood(db)
    insecurity = leaderboard_service.get_insecurity_index(db)
    pleasure = leaderboard_service.get_cock_pleasure_rankings(db)
    size = leaderboard_service.get_cock_size_rankings(db)

    return LeaderboardResponse(
        best_norwood=[NorwoodEntry(**e) for e in best],
        worst_norwood=[NorwoodEntry(**e) for e in worst],
        insecurity_index=[InsecurityEntry(**e) for e in insecurity],
        cock_pleasure=[CockPleasureEntry(**e) for e in pleasure],
        cock_size=[CockSizeEntry(**e) for e in size],
    )
