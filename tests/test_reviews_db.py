"""Tests for saving reviews and the review history endpoints (SQLite in-memory)."""

from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.models import Review, ReviewIssue
from app.schemas.review import Issue

AI_ISSUE = Issue(line=2, severity="low", category="style", rule="naming", message="Use snake_case.", source="ai")


def post_review(client, code="x = eval('1')\n", filename="demo.py", ai=("Needs work.", [AI_ISSUE])):
    with patch("app.routes.review.ai_reviewer.review_with_ai", return_value=ai):
        return client.post("/review", json={"code": code, "filename": filename})


def test_review_is_saved_with_issues(client, db_session):
    response = post_review(client)
    body = response.json()
    assert body["id"] is not None

    saved = db_session.get(Review, body["id"])
    assert saved.filename == "demo.py"
    assert saved.ai_summary == "Needs work."
    assert (saved.total_issues, saved.high_count, saved.low_count) == (2, 1, 1)
    assert {i.source for i in saved.issues} == {"static", "ai"}


def test_list_reviews_newest_first(client):
    first = post_review(client, filename="a.py").json()["id"]
    second = post_review(client, filename="b.py").json()["id"]

    rows = client.get("/reviews").json()
    assert [r["id"] for r in rows] == [second, first]
    assert rows[0]["summary"] == {"total": 2, "high": 1, "medium": 0, "low": 1}
    assert "code" not in rows[0]


def test_list_reviews_pagination(client):
    ids = [post_review(client).json()["id"] for _ in range(3)]
    rows = client.get("/reviews", params={"limit": 1, "offset": 1}).json()
    assert [r["id"] for r in rows] == [ids[1]]


def test_list_reviews_rejects_bad_limit(client):
    assert client.get("/reviews", params={"limit": 0}).status_code == 422


def test_get_review_detail(client):
    review_id = post_review(client).json()["id"]
    body = client.get(f"/reviews/{review_id}").json()
    assert body["code"] == "x = eval('1')\n"
    assert body["ai_status"] == "ok"
    assert [i["rule"] for i in body["issues"]] == ["eval-usage", "naming"]


def test_get_missing_review_returns_404(client):
    assert client.get("/reviews/999").status_code == 404


def test_deleting_review_deletes_issues(client, db_session):
    review_id = post_review(client).json()["id"]
    db_session.delete(db_session.get(Review, review_id))
    db_session.commit()
    assert db_session.scalars(select(ReviewIssue)).all() == []


def test_review_still_returned_when_save_fails(client):
    error = OperationalError("INSERT", {}, Exception("db down"))
    with patch("app.routes.review.review_store.save_review", side_effect=error):
        response = post_review(client)
    assert response.status_code == 200
    assert response.json()["id"] is None
    assert response.json()["summary"]["total"] == 2
