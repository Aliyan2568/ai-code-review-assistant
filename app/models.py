"""SQLAlchemy ORM models: a review and the issues found in it."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str | None] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(Text)
    ai_status: Mapped[str] = mapped_column(String(16))
    ai_summary: Mapped[str | None] = mapped_column(Text)

    # Counts are stored so listing reviews doesn't need to load every issue.
    total_issues: Mapped[int] = mapped_column(Integer, default=0)
    high_count: Mapped[int] = mapped_column(Integer, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, default=0)
    low_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    issues: Mapped[list["ReviewIssue"]] = relationship(
        back_populates="review", cascade="all, delete-orphan", order_by="ReviewIssue.id"
    )


class ReviewIssue(Base):
    __tablename__ = "review_issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), index=True)
    line: Mapped[int | None] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(32))
    rule: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(16))

    review: Mapped[Review] = relationship(back_populates="issues")
