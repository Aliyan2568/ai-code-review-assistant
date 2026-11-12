"""Review endpoints: run a full review (static + AI) and browse saved reviews.

If the AI step is disabled or fails, the static results are still returned.
If saving to the database fails, the review is still returned with id=null.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.review import CodeRequest, ReviewDetail, ReviewListItem, ReviewResponse, summarize
from app.services import ai_reviewer, review_store
from app.services.static_analyzer import analyze_code
from app.utils.logger import get_logger

router = APIRouter(tags=["Review"])
logger = get_logger(__name__)


@router.post("/review", response_model=ReviewResponse)
def review(request: CodeRequest, db: Session = Depends(get_db)) -> ReviewResponse:
    static_issues = analyze_code(request.code)
    issues = list(static_issues)
    ai_summary = None

    if static_issues and static_issues[0].rule == "syntax-error":
        ai_status = "failed"
        ai_summary = "AI review skipped: fix the syntax error first."
    else:
        try:
            ai_summary, ai_issues = ai_reviewer.review_with_ai(request.code, static_issues)
            issues += ai_issues
            ai_status = "ok"
        except ai_reviewer.AIReviewDisabled:
            ai_status = "disabled"
        except ai_reviewer.AIReviewError:
            ai_status = "failed"

    issues.sort(key=lambda i: (i.line or 0, i.rule))
    summary = summarize(issues)

    review_id = None
    try:
        saved = review_store.save_review(
            db, code=request.code, filename=request.filename, issues=issues,
            summary=summary, ai_status=ai_status, ai_summary=ai_summary,
        )
        review_id = saved.id
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Could not save review: %s", exc)

    return ReviewResponse(id=review_id, issues=issues, summary=summary, ai_status=ai_status, ai_summary=ai_summary)


@router.get("/reviews", response_model=list[ReviewListItem])
def list_reviews(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[ReviewListItem]:
    return [ReviewListItem.from_model(r) for r in review_store.list_reviews(db, limit, offset)]


@router.get("/reviews/{review_id}", response_model=ReviewDetail)
def get_review(review_id: int, db: Session = Depends(get_db)) -> ReviewDetail:
    saved = review_store.get_review(db, review_id)
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return ReviewDetail.from_model(saved)
