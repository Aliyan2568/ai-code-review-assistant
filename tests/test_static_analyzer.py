"""Tests for the rule-based static analyzer and the /analyze endpoint."""

import pytest

from app.services.static_analyzer import analyze_code


def rules(code: str) -> list[str]:
    return [issue.rule for issue in analyze_code(code)]


def test_clean_code_has_no_issues():
    assert analyze_code("def add(a, b):\n    return a + b\n") == []


def test_syntax_error_is_reported():
    issues = analyze_code("def broken(:\n    pass\n")
    assert len(issues) == 1
    assert issues[0].rule == "syntax-error"
    assert issues[0].severity == "high"


def test_bare_except():
    assert rules("try:\n    x = 1\nexcept:\n    pass\n") == ["bare-except"]


def test_specific_except_is_fine():
    assert rules("try:\n    x = 1\nexcept ValueError:\n    pass\n") == []


@pytest.mark.parametrize("default", ["[]", "{}", "{1}"])
def test_mutable_default(default):
    assert rules(f"def f(x={default}):\n    return x\n") == ["mutable-default"]


def test_mutable_kwonly_default_in_async_function():
    assert rules("async def f(*, x=[]):\n    return x\n") == ["mutable-default"]


@pytest.mark.parametrize("call", ["eval", "exec"])
def test_eval_and_exec(call):
    assert rules(f"{call}(user_input)\n") == [f"{call}-usage"]


def test_shell_true():
    assert rules("import subprocess\nsubprocess.run(cmd, shell=True)\n") == ["shell-true"]


def test_none_comparison():
    assert rules("if x == None:\n    pass\n") == ["none-comparison"]


def test_hardcoded_secret():
    issues = analyze_code('API_KEY = "abc123"\n')
    assert [i.rule for i in issues] == ["hardcoded-secret"]
    assert issues[0].line == 1


def test_empty_secret_string_not_flagged():
    assert rules('password = ""\n') == []


def test_issues_sorted_by_line():
    code = "x = eval('1')\ntry:\n    pass\nexcept:\n    pass\n"
    assert [i.line for i in analyze_code(code)] == [1, 4]


def test_analyze_endpoint(client):
    response = client.post("/analyze", json={"code": "x = eval('1')\n"})
    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == {"total": 1, "high": 1, "medium": 0, "low": 0}
    assert body["issues"][0]["rule"] == "eval-usage"


def test_analyze_endpoint_rejects_empty_code(client):
    response = client.post("/analyze", json={"code": ""})
    assert response.status_code == 422
