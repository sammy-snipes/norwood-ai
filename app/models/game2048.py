"""Game 2048 score models."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from ulid import ULID

from app.models.base import Base, TimestampMixin


class Game2048Score(Base, TimestampMixin):
    """2048 game score record."""

    __tablename__ = "game_2048_scores"

    id = Column(String(26), primary_key=True, default=lambda: str(ULID()))
    user_id = Column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score = Column(Integer, nullable=False)
    highest_tile = Column(Integer, nullable=False)  # 0-7 for Norwood levels
    is_win = Column(Boolean, nullable=False, default=False)

    # Relationships
    user = relationship("User", back_populates="game_2048_scores")

    def __repr__(self) -> str:
        return f"<Game2048Score {self.id} - {self.score}>"
