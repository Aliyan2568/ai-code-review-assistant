"""AI code review using the Groq chat-completions API.

The model is asked for JSON; its output is validated and anything malformed is dropped,
so a misbehaving model can never break the response shape.
"""

import json

from groq import Groq, GroqError
from pydantic import ValidationError

from app.config import get_settings
from app.schemas.review import Issue
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a senior Python code reviewer. Find real bugs, security problems, \
and performance issues. Do not repeat issues already found by the static analyzer. \
Do not invent problems; an empty list is a fine answer for good code.

Respond with JSON only, in exactly this shape:
{"summary": "<2-3 sentence overall assessment>",
 "issues": [{"line": <int or null>, "severity": "low|medium|high",
             "category": "bug|security|performance|style", "rule": "<short-kebab-case-id>",
             "message": "<what is wrong and how to fix it>"}]}"""


class AIReviewError(Exception):
    """Raised when the AI review cannot be produced."""


class AIReviewDisabled(AIReviewError):
    """Raised when no Groq API key is configured."""


def _build_user_prompt(code: str, static_issues: list[Issue]) -> str:
    already_found = "\n".join(f"- line {i.line}: {i.rule}" for i in static_issues) or "- none"
    return f"Static analyzer already found:\n{already_found}\n\nCode to review:\n```python\n{code}\n```"


def parse_ai_response(content: str) -> tuple[str, list[Issue]]:
    """Turn the model's JSON text into (summary, issues), skipping invalid issues."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AIReviewError("AI response was not valid JSON") from exc
    if not isinstance(data, dict):
        raise AIReviewError("AI response was not a JSON object")

    issues: list[Issue] = []
    for raw in data.get("issues") or []:
        if not isinstance(raw, dict):
            continue
        try:
            issues.append(Issue(**{**raw, "source": "ai"}))
        except (ValidationError, TypeError):
            logger.warning("Dropping malformed AI issue: %r", raw)
    return str(data.get("summary", "")), issues


def review_with_ai(code: str, static_issues: list[Issue], client: Groq | None = None) -> tuple[str, list[Issue]]:
    settings = get_settings()
    if client is None:
        if not settings.groq_api_key:
            raise AIReviewDisabled("GROQ_API_KEY is not set")
        client = Groq(api_key=settings.groq_api_key, timeout=30)

    try:
        completion = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(code, static_issues)},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
    except GroqError as exc:
        logger.error("Groq request failed: %s", exc)
        raise AIReviewError("AI service request failed") from exc

    return parse_ai_response(completion.choices[0].message.content or "")
