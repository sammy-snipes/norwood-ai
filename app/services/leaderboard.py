"""Leaderboard calculation service."""

import logging
import statistics

from sqlalchemy.orm import Session

from app.models import (
    Analysis,
    Certification,
    CertificationStatus,
    CockCertification,
    CockCertificationStatus,
    CounselingSession,
    User,
)

logger = logging.getLogger(__name__)

# Insecurity scoring weights
CERT_WEIGHT = 50
ANALYSIS_WEIGHT = 10
COUNSELING_WEIGHT = 5
COCK_CERT_WEIGHT = 100  # Rating your cock is peak insecurity

# Pleasure zone ranking (lower is better)
PLEASURE_ZONE_ORDER = {
    "ideal": 0,
    "very_satisfying": 1,
    "satisfying": 2,
    "enjoyable": 3,
    "not_satisfying": 4,
}


def _user_visible_on_leaderboard(user: User) -> bool:
    """Check if user has opted to appear on leaderboard (default True)."""
    opts = user.options or {}
    return opts.get("show_on_leaderboard", True)


def _get_user_median_norwood(user_id: str, db: Session) -> float | None:
    """Calculate median norwood stage for a user."""
    stages = (
        db.query(Analysis.norwood_stage)
        .filter(Analysis.user_id == user_id, Analysis.norwood_stage > 0)
        .all()
    )
    if not stages:
        return None
    return statistics.median([s[0] for s in stages])


def get_best_norwood(db: Session, limit: int = 5) -> list[dict]:
    """Get users with lowest median Norwood stage."""
    users_with_analyses = (
        db.query(User)
        .join(Analysis, Analysis.user_id == User.id)
        .filter(Analysis.norwood_stage > 0)
        .distinct()
        .all()
    )

    user_medians = []
    for u in users_with_analyses:
        if not _user_visible_on_leaderboard(u):
            continue
        median = _get_user_median_norwood(u.id, db)
        if median is not None:
            user_medians.append(
                {
                    "username": u.name or "Anonymous",
                    "avatar_url": u.avatar_url,
                    "norwood_stage": round(median),
                }
            )

    return sorted(user_medians, key=lambda x: x["norwood_stage"])[:limit]


def get_worst_norwood(db: Session, limit: int = 5) -> list[dict]:
    """Get users with highest median Norwood stage."""
    users_with_analyses = (
        db.query(User)
        .join(Analysis, Analysis.user_id == User.id)
        .filter(Analysis.norwood_stage > 0)
        .distinct()
        .all()
    )

    user_medians = []
    for u in users_with_analyses:
        if not _user_visible_on_leaderboard(u):
            continue
        median = _get_user_median_norwood(u.id, db)
        if median is not None:
            user_medians.append(
                {
                    "username": u.name or "Anonymous",
                    "avatar_url": u.avatar_url,
                    "norwood_stage": round(median),
                }
            )

    return sorted(user_medians, key=lambda x: x["norwood_stage"], reverse=True)[:limit]


def get_insecurity_index(db: Session, limit: int = 10) -> list[dict]:
    """Get users ranked by insecurity score (based on platform usage)."""
    all_users = db.query(User).all()

    scores = []
    for u in all_users:
        if not _user_visible_on_leaderboard(u):
            continue

        cert_count = (
            db.query(Certification)
            .filter(
                Certification.user_id == u.id,
                Certification.status == CertificationStatus.completed,
            )
            .count()
        )

        analysis_count = db.query(Analysis).filter(Analysis.user_id == u.id).count()

        counseling_count = (
            db.query(CounselingSession).filter(CounselingSession.user_id == u.id).count()
        )

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
            scores.append(
                {
                    "username": u.name or "Anonymous",
                    "score": score,
                    "avatar_url": u.avatar_url,
                }
            )

    return sorted(scores, key=lambda x: x["score"], reverse=True)[:limit]


def get_cock_pleasure_rankings(db: Session, limit: int = 5) -> list[dict]:
    """Get users ranked by cock pleasure zone (best first)."""
    cock_certs = (
        db.query(CockCertification)
        .join(User, CockCertification.user_id == User.id)
        .filter(CockCertification.status == CockCertificationStatus.completed)
        .all()
    )

    visible_certs = [c for c in cock_certs if _user_visible_on_leaderboard(c.user)]

    sorted_certs = sorted(
        visible_certs,
        key=lambda c: PLEASURE_ZONE_ORDER.get(
            c.pleasure_zone.value if c.pleasure_zone else "not_satisfying", 5
        ),
    )[:limit]

    return [
        {
            "username": c.user.name or "Anonymous",
            "pleasure_zone": c.pleasure_zone.name if c.pleasure_zone else "unknown",
            "pleasure_zone_label": c.pleasure_zone_label or "Unknown",
            "avatar_url": c.user.avatar_url,
        }
        for c in sorted_certs
    ]


def get_cock_size_rankings(db: Session, limit: int = 5) -> list[dict]:
    """Get users ranked by cock size (volume approximation)."""
    cock_certs = (
        db.query(CockCertification)
        .join(User, CockCertification.user_id == User.id)
        .filter(CockCertification.status == CockCertificationStatus.completed)
        .all()
    )

    visible_certs = [c for c in cock_certs if _user_visible_on_leaderboard(c.user)]

    # Sort by volume: length * girth^2
    sorted_certs = sorted(
        visible_certs,
        key=lambda c: (c.length_inches or 0) * ((c.girth_inches or 0) ** 2),
        reverse=True,
    )[:limit]

    return [
        {
            "username": c.user.name or "Anonymous",
            "length_inches": c.length_inches or 0,
            "girth_inches": c.girth_inches or 0,
            "size_category": c.size_category.value if c.size_category else "unknown",
            "avatar_url": c.user.avatar_url,
        }
        for c in sorted_certs
    ]
