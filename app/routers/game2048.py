"""Game 2048 router."""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Game2048Score, User
from app.routers.auth import decode_token

router = APIRouter(prefix="/api/2048", tags=["game2048"])


class SubmitScoreRequest(BaseModel):
    score: int
    highest_tile: int
    is_win: bool = False


class ScoreResponse(BaseModel):
    id: str
    score: int
    highest_tile: int
    is_win: bool


class HighScoreResponse(BaseModel):
    score: int
    highest_tile: int


def require_auth(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Require authenticated user."""
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

    return user


@router.post("/scores", response_model=ScoreResponse)
def submit_score(
    request: SubmitScoreRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Submit a 2048 game score."""
    score = Game2048Score(
        user_id=user.id,
        score=request.score,
        highest_tile=request.highest_tile,
        is_win=request.is_win,
    )
    db.add(score)
    db.commit()
    db.refresh(score)

    return ScoreResponse(
        id=score.id,
        score=score.score,
        highest_tile=score.highest_tile,
        is_win=score.is_win,
    )


@router.get("/high-score", response_model=HighScoreResponse | None)
def get_high_score(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get the user's highest 2048 score."""
    best = (
        db.query(Game2048Score)
        .filter(Game2048Score.user_id == user.id)
        .order_by(Game2048Score.score.desc())
        .first()
    )

    if not best:
        return None

    return HighScoreResponse(
        score=best.score,
        highest_tile=best.highest_tile,
    )
