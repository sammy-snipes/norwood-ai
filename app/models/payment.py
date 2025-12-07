from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship
from ulid import ULID

from app.models.base import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(26), primary_key=True, default=lambda: str(ULID()))
    user_id = Column(
        String(26), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stripe_payment_id = Column(String(255), unique=True, nullable=False, index=True)
    amount_cents = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)  # pending, succeeded, failed
    type = Column(String(20), nullable=False, default="premium")  # premium, donation
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment {self.id} status={self.status}>"
