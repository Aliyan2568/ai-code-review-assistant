"""Static analysis endpoint (no AI, no database)."""

from fastapi import APIRouter

from app.schemas.review import AnalyzeResponse, CodeRequest, summarize
from app.services.static_analyzer import analyze_code

router = APIRouter(tags=["Analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: CodeRequest) -> AnalyzeResponse:
    issues = analyze_code(request.code)
    return AnalyzeResponse(issues=issues, summary=summarize(issues))
