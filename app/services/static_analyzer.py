"""Rule-based static analysis of Python code using the standard-library `ast` module.

The code is parsed, never executed.
"""

import ast
import re

from app.schemas.review import Issue

SECRET_NAME = re.compile(r"(password|passwd|secret|api_?key|token)", re.IGNORECASE)
DANGEROUS_CALLS = {"eval", "exec"}


class _Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.issues: list[Issue] = []

    def _add(self, node: ast.AST, severity, category, rule, message) -> None:
        self.issues.append(
            Issue(line=getattr(node, "lineno", None), severity=severity, category=category, rule=rule, message=message)
        )

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self._add(node, "medium", "bug", "bare-except",
                      "Bare 'except:' also catches KeyboardInterrupt and SystemExit; catch a specific exception.")
        self.generic_visit(node)

    def _check_defaults(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for default in node.args.defaults + [d for d in node.args.kw_defaults if d is not None]:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self._add(default, "medium", "bug", "mutable-default",
                          f"Function '{node.name}' uses a mutable default argument; it is shared between calls. "
                          "Use None and create the value inside the function.")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_defaults(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_defaults(node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_CALLS:
            self._add(node, "high", "security", f"{node.func.id}-usage",
                      f"'{node.func.id}()' can execute arbitrary code; avoid it on untrusted input.")
        for kw in node.keywords:
            if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                self._add(node, "high", "security", "shell-true",
                          "shell=True enables shell injection; pass a list of arguments instead.")
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        for op, comparator in zip(node.ops, node.comparators):
            if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(comparator, ast.Constant) and comparator.value is None:
                self._add(node, "low", "style", "none-comparison",
                          "Compare to None with 'is' / 'is not' instead of '==' / '!='.")
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) and node.value.value:
            for target in node.targets:
                name = target.id if isinstance(target, ast.Name) else getattr(target, "attr", None)
                if name and SECRET_NAME.search(name):
                    self._add(node, "high", "security", "hardcoded-secret",
                              f"'{name}' looks like a hardcoded secret; load it from an environment variable.")
        self.generic_visit(node)


def analyze_code(code: str) -> list[Issue]:
    """Return the issues found in `code`, sorted by line number."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [Issue(line=exc.lineno, severity="high", category="syntax", rule="syntax-error",
                      message=f"Syntax error: {exc.msg}")]

    visitor = _Visitor()
    visitor.visit(tree)
    return sorted(visitor.issues, key=lambda i: (i.line or 0, i.rule))
