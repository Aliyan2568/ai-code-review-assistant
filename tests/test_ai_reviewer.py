"""Tests for the AI reviewer and /review endpoint. Groq is always mocked."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from groq import APIConnectionError

from app.schemas.review import Issue
from app.services.ai_reviewer import AIReviewError, parse_ai_response, review_with_ai


def fake_client(content: str) -> MagicMock:
    client = MagicMock()
    message = SimpleNamespace(content=content)
    client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(message=message)])
    return client


GOOD_JSON = json.dumps({
    "summary": "Mostly fine.",
    "issues": [{"line": 2, "severity": "medium", "category": "bug", "rule": "off-by-one", "message": "Loop skips last item."}],
})


def test_parse_valid_response():
    summary, issues = parse_ai_response(GOOD_JSON)
    assert summary == "Mostly fine."
    assert issues[0].rule == "off-by-one"
    assert issues[0].source == "ai"


def test_parse_drops_malformed_issues():
    content = json.dumps({"summary": "x", "issues": [
        {"severity": "critical", "category": "bug", "rule": "r", "message": "bad severity"},
        "not a dict",
        {"line": None, "severity": "low", "category": "style", "rule": "ok", "message": "kept"},
    ]})
    _, issues = parse_ai_response(content)
    assert [i.rule for i in issues] == ["ok"]


@pytest.mark.parametrize("content", ["not json", "[1, 2]"])
def test_parse_rejects_non_object(content):
    with pytest.raises(AIReviewError):
        parse_ai_response(content)


def test_review_with_ai_sends_static_issues_to_model():
    client = fake_client(GOOD_JSON)
    static = [Issue(line=1, severity="high", category="security", rule="eval-usage", message="m")]
    summary, issues = review_with_ai("eval(x)\n", static, client=client)

    assert summary == "Mostly fine."
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["response_format"] == {"type": "json_object"}
    assert "eval-usage" in kwargs["messages"][1]["content"]


def test_review_with_ai_wraps_groq_errors():
    client = MagicMock()
    client.chat.completions.create.side_effect = APIConnectionError(request=MagicMock())
    with pytest.raises(AIReviewError):
        review_with_ai("x = 1\n", [], client=client)


def test_review_endpoint_combines_static_and_ai(client):
    ai_issue = Issue(line=1, severity="low", category="style", rule="naming", message="m", source="ai")
    with patch("app.routes.review.ai_reviewer.review_with_ai", return_value=("Looks ok.", [ai_issue])):
        response = client.post("/review", json={"code": "x = eval('1')\n"})

    body = response.json()
    assert response.status_code == 200
    assert body["ai_status"] == "ok"
    assert body["ai_summary"] == "Looks ok."
    assert {i["source"] for i in body["issues"]} == {"static", "ai"}
    assert body["summary"]["total"] == 2


def test_review_endpoint_without_api_key_returns_static_only(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "groq_api_key", "")
    response = client.post("/review", json={"code": "x = eval('1')\n"})
    body = response.json()
    assert body["ai_status"] == "disabled"
    assert [i["rule"] for i in body["issues"]] == ["eval-usage"]


def test_review_endpoint_when_ai_fails(client):
    with patch("app.routes.review.ai_reviewer.review_with_ai", side_effect=AIReviewError("boom")):
        response = client.post("/review", json={"code": "x = 1\n"})
    assert response.status_code == 200
    assert response.json()["ai_status"] == "failed"


def test_review_endpoint_skips_ai_on_syntax_error(client):
    with patch("app.routes.review.ai_reviewer.review_with_ai") as mock_ai:
        response = client.post("/review", json={"code": "def f(:\n"})
    mock_ai.assert_not_called()
    assert response.json()["issues"][0]["rule"] == "syntax-error"
