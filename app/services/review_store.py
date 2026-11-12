"""Database access for saved reviews."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Review, ReviewIssue
from app.schemas.review import AnalysisSummary, Issue


def save_review(
    db: Session,
    *,
    code: str,
    filename: str | None,
    issues: list[Issue],
    summary: AnalysisSummary,
    ai_status: str,
    ai_summary: str | None,
) -> Review:
    review = Review(
        code=code,
        filename=filename,
        ai_status=ai_status,
        ai_summary=ai_summary,
        total_issues=summary.total,
        high_count=summary.high,
        medium_count=summary.medium,
        low_count=summary.low,
        issues=[ReviewIssue(**issue.model_dump()) for issue in issues],
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def list_reviews(db: Session, limit: int, offset: int) -> list[Review]:
    stmt = select(Review).order_by(Review.created_at.desc(), Review.id.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def get_review(db: Session, review_id: int) -> Review | None:
    stmt = select(Review).where(Review.id == review_id).options(selectinload(Review.issues))
    return db.scalar(stmt)
