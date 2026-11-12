"""Request/response models for code analysis and review."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["low", "medium", "high"]
Category = Literal["bug", "security", "performance", "style", "syntax"]

MAX_CODE_LENGTH = 50_000


class CodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=MAX_CODE_LENGTH, description="Python source code")
    filename: str | None = Field(default=None, max_length=255)


class Issue(BaseModel):
    line: int | None = None
    severity: Severity
    category: Category
    rule: str
    message: str
    source: Literal["static", "ai"] = "static"


class AnalysisSummary(BaseModel):
    total: int
    high: int
    medium: int
    low: int


class AnalyzeResponse(BaseModel):
    issues: list[Issue]
    summary: AnalysisSummary


AIStatus = Literal["ok", "disabled", "failed"]


class ReviewResponse(AnalyzeResponse):
    id: int | None = Field(default=None, description="Saved review id; null if saving failed")
    ai_status: AIStatus
    ai_summary: str | None = None


class ReviewListItem(BaseModel):
    """One row in the review history (no code or issues)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str | None
    created_at: datetime
    ai_status: AIStatus
    summary: AnalysisSummary

    @classmethod
    def from_model(cls, review) -> "ReviewListItem":
        return cls(
            id=review.id,
            filename=review.filename,
            created_at=review.created_at,
            ai_status=review.ai_status,
            summary=AnalysisSummary(
                total=review.total_issues, high=review.high_count, medium=review.medium_count, low=review.low_count
            ),
        )


class ReviewDetail(ReviewListItem):
    code: str
    ai_summary: str | None
    issues: list[Issue]

    @classmethod
    def from_model(cls, review) -> "ReviewDetail":
        base = ReviewListItem.from_model(review).model_dump()
        return cls(
            **base,
            code=review.code,
            ai_summary=review.ai_summary,
            issues=[Issue.model_validate(issue, from_attributes=True) for issue in review.issues],
        )


def summarize(issues: list[Issue]) -> AnalysisSummary:
    return AnalysisSummary(
        total=len(issues),
        high=sum(i.severity == "high" for i in issues),
        medium=sum(i.severity == "medium" for i in issues),
        low=sum(i.severity == "low" for i in issues),
    )
