import ast
import re

from app.schemas.review import Issue

SECRET_NAME = re.compile(r"(password|passwd|secret|api_?key|token)", re.IGNORECASE)
DANGEROUS_CALLS = {"eval", "exec"}
WEAK_HASHES = {"md5", "sha1"}
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "request"}


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
        self._check_deserialization(node)
        self._check_weak_hash(node)
        self._check_request_timeout(node)
        self.generic_visit(node)

    def _check_weak_hash(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "hashlib":
            algo = func.attr
            if algo == "new" and node.args and isinstance(node.args[0], ast.Constant):
                algo = str(node.args[0].value).lower()
            if algo in WEAK_HASHES:
                self._add(node, "medium", "security", "weak-hash",
                          f"{algo.upper()} is broken for security use; use hashlib.sha256 (or bcrypt/argon2 for passwords).")

    def _check_request_timeout(self, node: ast.Call) -> None:
        func = node.func
        if (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                and func.value.id == "requests" and func.attr in HTTP_METHODS
                and not any(kw.arg == "timeout" for kw in node.keywords)):
            self._add(node, "medium", "bug", "request-without-timeout",
                      f"requests.{func.attr}() has no timeout and can hang forever; pass timeout=<seconds>.")

    def _check_deserialization(self, node: ast.Call) -> None:
        func = node.func
        if not (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)):
            return
        module, method = func.value.id, func.attr
        if module == "pickle" and method in {"load", "loads"}:
            self._add(node, "high", "security", "unsafe-deserialization",
                      "pickle can execute arbitrary code when loading untrusted data; use json instead.")
        elif module == "yaml" and method == "load" and not any(kw.arg == "Loader" for kw in node.keywords):
            self._add(node, "high", "security", "unsafe-deserialization",
                      "yaml.load without a Loader is unsafe; use yaml.safe_load instead.")

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
