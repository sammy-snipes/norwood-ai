"""Leaderboard router - premium only rankings."""

import statistics

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    Analysis,
    Certification,
    CertificationStatus,
    CockCertification,
    CockCertificationStatus,
    CounselingSession,
    Game2048Score,
    User,
)
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


class Game2048Entry(BaseModel):
    username: str
    score: int
    highest_tile: int
    avatar_url: str | None = None


class LeaderboardResponse(BaseModel):
    best_norwood: list[NorwoodEntry]
    worst_norwood: list[NorwoodEntry]
    insecurity_index: list[InsecurityEntry]
    cock_pleasure: list[CockPleasureEntry]
    cock_size: list[CockSizeEntry]
    game_2048_high_scores: list[Game2048Entry]


# Insecurity scoring weights
CERT_WEIGHT = 50
ANALYSIS_WEIGHT = 10
COUNSELING_WEIGHT = 5
COCK_CERT_WEIGHT = 100  # Rating your cock is peak insecurity


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


def user_visible_on_leaderboard(user: User) -> bool:
    """Check if user has opted to appear on leaderboard (default True)."""
    opts = user.options or {}
    return opts.get("show_on_leaderboard", True)


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

    # Calculate median for each user (only if they opted in)
    user_medians = []
    for u in users_with_analyses:
        if not user_visible_on_leaderboard(u):
            continue
        median = get_user_median_norwood(u.id, db)
        if median is not None:
            user_medians.append(
                {
                    "username": u.name or "Anonymous",
                    "avatar_url": u.avatar_url,
                    "median": median,
                }
            )

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
    all_users = db.query(User).all()

    insecurity_scores = []
    for u in all_users:
        if not user_visible_on_leaderboard(u):
            continue

        # Count certifications
        cert_count = (
            db.query(Certification)
            .filter(
                Certification.user_id == u.id,
                Certification.status == CertificationStatus.completed,
            )
            .count()
        )

        # Count analyses
        analysis_count = db.query(Analysis).filter(Analysis.user_id == u.id).count()

        # Count counseling sessions
        counseling_count = (
            db.query(CounselingSession).filter(CounselingSession.user_id == u.id).count()
        )

        # Count cock certifications
        cock_cert_count = (
            db.query(CockCertification)
            .filter(
                CockCertification.user_id == u.id,
                CockCertification.status == CockCertificationStatus.completed,
            )
            .count()
        )

        score = (
            cert_count * CERT_WEIGHT
            + analysis_count * ANALYSIS_WEIGHT
            + counseling_count * COUNSELING_WEIGHT
            + cock_cert_count * COCK_CERT_WEIGHT
        )

        if score > 0:
            insecurity_scores.append(
                InsecurityEntry(
                    username=u.name or "Anonymous",
                    score=score,
                    avatar_url=u.avatar_url,
                )
            )

    # Sort by score descending and take top entries
    insecurity_scores.sort(key=lambda x: x.score, reverse=True)
    insecurity_index = insecurity_scores[:10]

    # Cock rankings
    # Pleasure zone ranking (A > B > C > D > E)
    pleasure_zone_order = {
        "ideal": 0,
        "very_satisfying": 1,
        "satisfying": 2,
        "enjoyable": 3,
        "not_satisfying": 4,
    }

    cock_certs = (
        db.query(CockCertification)
        .join(User, CockCertification.user_id == User.id)
        .filter(CockCertification.status == CockCertificationStatus.completed)
        .all()
    )

    # Filter by users who opted in
    visible_cock_certs = [c for c in cock_certs if user_visible_on_leaderboard(c.user)]

    # Best pleasure zones
    pleasure_sorted = sorted(
        visible_cock_certs,
        key=lambda c: pleasure_zone_order.get(
            c.pleasure_zone.value if c.pleasure_zone else "not_satisfying", 5
        ),
    )[:5]

    cock_pleasure = [
        CockPleasureEntry(
            username=c.user.name or "Anonymous",
            pleasure_zone=c.pleasure_zone.name if c.pleasure_zone else "unknown",
            pleasure_zone_label=c.pleasure_zone_label or "Unknown",
            avatar_url=c.user.avatar_url,
        )
        for c in pleasure_sorted
    ]

    # Biggest cocks (by volume approximation: length * girth^2)
    size_sorted = sorted(
        visible_cock_certs,
        key=lambda c: (c.length_inches or 0) * ((c.girth_inches or 0) ** 2),
        reverse=True,
    )[:5]

    cock_size = [
        CockSizeEntry(
            username=c.user.name or "Anonymous",
            length_inches=c.length_inches or 0,
            girth_inches=c.girth_inches or 0,
            size_category=c.size_category.value if c.size_category else "unknown",
            avatar_url=c.user.avatar_url,
        )
        for c in size_sorted
    ]

    # 2048 High Scores - get best score per user
    game_scores = (
        db.query(Game2048Score)
        .join(User, Game2048Score.user_id == User.id)
        .order_by(Game2048Score.score.desc())
        .all()
    )

    # Get best score per visible user
    seen_users = set()
    game_2048_high_scores = []
    for g in game_scores:
        if g.user_id in seen_users:
            continue
        if not user_visible_on_leaderboard(g.user):
            continue
        seen_users.add(g.user_id)
        game_2048_high_scores.append(
            Game2048Entry(
                username=g.user.name or "Anonymous",
                score=g.score,
                highest_tile=g.highest_tile,
                avatar_url=g.user.avatar_url,
            )
        )
        if len(game_2048_high_scores) >= 10:
            break

    return LeaderboardResponse(
        best_norwood=best_norwood,
        worst_norwood=worst_norwood,
        insecurity_index=insecurity_index,
        cock_pleasure=cock_pleasure,
        cock_size=cock_size,
        game_2048_high_scores=game_2048_high_scores,
    )
