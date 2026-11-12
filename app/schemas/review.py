"""Request/response models for code analysis and review."""

from typing import Literal

from pydantic import BaseModel, Field

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


class ReviewResponse(AnalyzeResponse):
    ai_status: Literal["ok", "disabled", "failed"]
    ai_summary: str | None = None


def summarize(issues: list[Issue]) -> AnalysisSummary:
    return AnalysisSummary(
        total=len(issues),
        high=sum(i.severity == "high" for i in issues),
        medium=sum(i.severity == "medium" for i in issues),
        low=sum(i.severity == "low" for i in issues),
    )
