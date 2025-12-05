from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship
from ulid import ULID

from app.models.base import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(String(26), primary_key=True, default=lambda: str(ULID()))
    user_id = Column(String(26), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url = Column(Text, nullable=True)  # S3 path
    norwood_stage = Column(Integer, nullable=False)
    confidence = Column(String(20), nullable=False)  # high, medium, low
    roast = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="analyses")

    def __repr__(self) -> str:
        return f"<Analysis {self.id} stage={self.norwood_stage}>"
