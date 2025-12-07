"""Leaderboard router - premium only rankings."""

import statistics

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Analysis, Certification, CertificationStatus, CounselingSession, User
from app.routers.auth import decode_token

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


class NorwoodEntry(BaseModel):
    username: str
    norwood_stage: int
    avatar_url: str | None = None


class InsecurityEntry(BaseModel):
    username: str
    score: int
    avatar_url: str | None = None


class LeaderboardResponse(BaseModel):
    best_norwood: list[NorwoodEntry]
    worst_norwood: list[NorwoodEntry]
    insecurity_index: list[InsecurityEntry]


# Insecurity scoring weights
CERT_WEIGHT = 50
ANALYSIS_WEIGHT = 10
COUNSELING_WEIGHT = 5


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


def get_user_median_norwood(user_id: str, db: Session) -> float | None:
    """Calculate median norwood stage for a user."""
    stages = (
        db.query(Analysis.norwood_stage)
        .filter(Analysis.user_id == user_id, Analysis.norwood_stage > 0)
        .all()
    )
    if not stages:
        return None
    return statistics.median([s[0] for s in stages])


@router.get("", response_model=LeaderboardResponse)
def get_leaderboard(
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get leaderboard data (premium only)."""

    # Get all users with analyses
    users_with_analyses = (
        db.query(User)
        .join(Analysis, Analysis.user_id == User.id)
        .filter(Analysis.norwood_stage > 0)
        .distinct()
        .all()
    )

    # Calculate median for each user
    user_medians = []
    for u in users_with_analyses:
        median = get_user_median_norwood(u.id, db)
        if median is not None:
            user_medians.append({
                "username": u.name or "Anonymous",
                "avatar_url": u.avatar_url,
                "median": median,
            })

    # Best Norwood: lowest median (round for display)
    best_sorted = sorted(user_medians, key=lambda x: x["median"])[:5]
    best_norwood = [
        NorwoodEntry(
            username=u["username"],
            norwood_stage=round(u["median"]),
            avatar_url=u["avatar_url"],
        )
        for u in best_sorted
    ]

    # Worst Norwood: highest median
    worst_sorted = sorted(user_medians, key=lambda x: x["median"], reverse=True)[:5]
    worst_norwood = [
        NorwoodEntry(
            username=u["username"],
            norwood_stage=round(u["median"]),
            avatar_url=u["avatar_url"],
        )
        for u in worst_sorted
    ]

    # Insecurity Index: score based on total interactions
    # Get all users with their interaction counts
    users = db.query(User).all()

    insecurity_scores = []
    for user in users:
        # Count certifications
        cert_count = (
            db.query(Certification)
            .filter(
                Certification.user_id == user.id,
                Certification.status == CertificationStatus.completed,
            )
            .count()
        )

        # Count analyses
        analysis_count = db.query(Analysis).filter(Analysis.user_id == user.id).count()

        # Count counseling sessions
        counseling_count = (
            db.query(CounselingSession).filter(CounselingSession.user_id == user.id).count()
        )

        score = (
            cert_count * CERT_WEIGHT
            + analysis_count * ANALYSIS_WEIGHT
            + counseling_count * COUNSELING_WEIGHT
        )

        if score > 0:
            insecurity_scores.append(
                InsecurityEntry(
                    username=user.name or "Anonymous",
                    score=score,
                    avatar_url=user.avatar_url,
                )
            )

    # Sort by score descending and take top entries
    insecurity_scores.sort(key=lambda x: x.score, reverse=True)
    insecurity_index = insecurity_scores[:10]

    return LeaderboardResponse(
        best_norwood=best_norwood,
        worst_norwood=worst_norwood,
        insecurity_index=insecurity_index,
    )
