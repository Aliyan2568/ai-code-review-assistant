"""Full review endpoint: static analysis plus AI review.

If the AI step is disabled or fails, the static results are still returned.
"""

from fastapi import APIRouter

from app.schemas.review import CodeRequest, ReviewResponse, summarize
from app.services import ai_reviewer
from app.services.static_analyzer import analyze_code

router = APIRouter(tags=["Review"])


@router.post("/review", response_model=ReviewResponse)
def review(request: CodeRequest) -> ReviewResponse:
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
    return ReviewResponse(issues=issues, summary=summarize(issues), ai_status=ai_status, ai_summary=ai_summary)
