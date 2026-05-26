import ast
import re
import textwrap
from typing import Any


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _max_nesting_depth(node: ast.AST, depth: int = 0) -> int:
    nesting_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try)
    if isinstance(node, nesting_nodes):
        depth += 1
    return max(
        (_max_nesting_depth(child, depth) for child in ast.iter_child_nodes(node)),
        default=depth,
    )


def _cyclomatic_complexity(func_node: ast.FunctionDef) -> int:
    complexity = 1
    for node in ast.walk(func_node):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.Assert)):
            complexity += 1
        elif isinstance(node, ast.comprehension):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1
    return complexity


def _is_in_main_guard(target_node: ast.AST, tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
            and any(
                isinstance(c, ast.Constant) and c.value == "__main__"
                for c in test.comparators
            )
        ):
            for child in ast.walk(node):
                if child is target_node:
                    return True
    return False


def _is_snake_case(name: str) -> bool:
    return bool(re.match(r'^[a-z_][a-z0-9_]*$', name))


def _is_pascal_case(name: str) -> bool:
    return bool(re.match(r'^[A-Z][a-zA-Z0-9]*$', name))


# ──────────────────────────────────────────────────────────────────────────────
# Tool 1: analyze_code_style
# ──────────────────────────────────────────────────────────────────────────────

def analyze_code_style(code: str, strict_mode: bool = False) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    max_line_length = 79 if strict_mode else 100

    lines = code.splitlines()
    for i, line in enumerate(lines, start=1):
        if len(line) > max_line_length:
            violations.append({
                "line": i,
                "rule": "E501",
                "description": f"Line too long ({len(line)} > {max_line_length} characters)",
            })
        if line != line.rstrip():
            violations.append({
                "line": i,
                "rule": "W291",
                "description": "Trailing whitespace",
            })
        stripped = line.lstrip()
        if stripped and not line.startswith("#"):
            indent = len(line) - len(stripped)
            if indent > 0 and indent % 4 != 0:
                violations.append({
                    "line": i,
                    "rule": "E111",
                    "description": f"Indentation is not a multiple of 4 ({indent} spaces)",
                })
        if re.search(r',[^\s,)\]]', line):
            violations.append({
                "line": i,
                "rule": "E231",
                "description": "Missing whitespace after ','",
            })

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        violations.append({
            "line": exc.lineno or 0,
            "rule": "E999",
            "description": f"SyntaxError: {exc.msg}",
        })
        return violations

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not _is_snake_case(node.name) and not node.name.startswith("_"):
                violations.append({
                    "line": node.lineno,
                    "rule": "N802",
                    "description": f"Function name '{node.name}' should be snake_case",
                })
        elif isinstance(node, ast.ClassDef):
            if not _is_pascal_case(node.name):
                violations.append({
                    "line": node.lineno,
                    "rule": "N801",
                    "description": f"Class name '{node.name}' should be PascalCase",
                })

    violations.sort(key=lambda v: v["line"])
    return violations


# ──────────────────────────────────────────────────────────────────────────────
# Tool 2: detect_code_smells
# ──────────────────────────────────────────────────────────────────────────────

def detect_code_smells(code: str, complexity_threshold: int = 10) -> list[dict[str, Any]]:
    smells: list[dict[str, Any]] = []

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [{"smell": "SyntaxError", "severity": "HIGH", "line": exc.lineno or 0, "description": str(exc)}]

    source_lines = code.splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        func_start = node.lineno
        func_end = node.end_lineno or func_start
        func_length = func_end - func_start + 1

        if func_length > 100:
            smells.append({
                "smell": "LongFunction",
                "severity": "HIGH",
                "line": func_start,
                "description": f"Function '{node.name}' is {func_length} lines long (>100)",
            })
        elif func_length > 50:
            smells.append({
                "smell": "LongFunction",
                "severity": "MEDIUM",
                "line": func_start,
                "description": f"Function '{node.name}' is {func_length} lines long (>50)",
            })

        num_params = len(node.args.args) + len(node.args.posonlyargs)
        if num_params > 5:
            smells.append({
                "smell": "TooManyParameters",
                "severity": "MEDIUM",
                "line": func_start,
                "description": f"Function '{node.name}' has {num_params} parameters (>5)",
            })

        depth = _max_nesting_depth(node)
        if depth > 4:
            smells.append({
                "smell": "DeepNesting",
                "severity": "HIGH",
                "line": func_start,
                "description": f"Function '{node.name}' has nesting depth {depth} (>4)",
            })

        complexity = _cyclomatic_complexity(node)
        if complexity > complexity_threshold:
            smells.append({
                "smell": "HighComplexity",
                "severity": "HIGH" if complexity > complexity_threshold * 2 else "MEDIUM",
                "line": func_start,
                "description": f"Function '{node.name}' has cyclomatic complexity {complexity} (threshold: {complexity_threshold})",
            })

        assigned: dict[str, int] = {}
        loaded: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Store):
                    assigned[child.id] = child.col_offset
                elif isinstance(child.ctx, ast.Load):
                    loaded.add(child.id)
        for var in assigned:
            if var not in loaded and not var.startswith("_"):
                smells.append({
                    "smell": "UnusedVariable",
                    "severity": "LOW",
                    "line": func_start,
                    "description": f"Variable '{var}' in '{node.name}' is assigned but never used",
                })

    SAFE_NUMBERS = {0, 1, -1, 2, 100}
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            if node.value not in SAFE_NUMBERS and node.value is not True and node.value is not False:
                smells.append({
                    "smell": "MagicNumber",
                    "severity": "LOW",
                    "line": node.lineno,
                    "description": f"Magic number {node.value} — consider using a named constant",
                })

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            smells.append({
                "smell": "BareExcept",
                "severity": "HIGH",
                "line": node.lineno,
                "description": "Bare 'except:' catches all exceptions including SystemExit and KeyboardInterrupt",
            })

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "print":
                if not _is_in_main_guard(node, tree):
                    smells.append({
                        "smell": "PrintStatement",
                        "severity": "LOW",
                        "line": node.lineno,
                        "description": "print() outside __main__ guard — use logging instead",
                    })

    smells.sort(key=lambda s: (s["line"], s["severity"]))
    return smells


# ──────────────────────────────────────────────────────────────────────────────
# Tool 3: suggest_improvements
# ──────────────────────────────────────────────────────────────────────────────

def suggest_improvements(code: str, focus_area: str) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [{"type": "SyntaxError", "priority": "CRITICAL", "line": exc.lineno or 0,
                 "description": str(exc), "suggestion": "Fix syntax errors first", "impact": "Blocking"}]

    if focus_area == "performance":
        _suggest_performance(tree, suggestions)
    elif focus_area == "readability":
        _suggest_readability(tree, code, suggestions)
    elif focus_area == "maintainability":
        _suggest_maintainability(tree, suggestions)
    else:
        _suggest_performance(tree, suggestions)
        _suggest_readability(tree, code, suggestions)
        _suggest_maintainability(tree, suggestions)

    suggestions.sort(key=lambda s: (["CRITICAL", "HIGH", "MEDIUM", "LOW"].index(s["priority"]), s["line"]))
    return suggestions


def _suggest_performance(tree: ast.AST, suggestions: list[dict[str, Any]]) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.For):
                for stmt in ast.walk(child):
                    if (
                        isinstance(stmt, ast.Expr)
                        and isinstance(stmt.value, ast.Call)
                        and isinstance(stmt.value.func, ast.Attribute)
                        and stmt.value.func.attr == "append"
                    ):
                        suggestions.append({
                            "type": "ListComprehension",
                            "priority": "MEDIUM",
                            "line": child.lineno,
                            "description": "For-loop with .append() can be replaced by a list comprehension",
                            "suggestion": "Use [expr for item in iterable] instead of a loop with list.append()",
                            "impact": "Faster execution and more idiomatic Python",
                        })
                        break

            if isinstance(child, ast.AugAssign):
                if (
                    isinstance(child.op, ast.Add)
                    and isinstance(child.value, ast.Constant)
                    and isinstance(child.value.value, str)
                ):
                    suggestions.append({
                        "type": "StringConcatInLoop",
                        "priority": "HIGH",
                        "line": child.lineno,
                        "description": "String concatenation with += inside a loop is O(n²)",
                        "suggestion": "Collect parts in a list and use ''.join(parts) after the loop",
                        "impact": "Significant performance improvement for large datasets",
                    })

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            if (
                len(node.ops) == 1
                and isinstance(node.ops[0], ast.Gt)
                and len(node.comparators) == 1
                and isinstance(node.comparators[0], ast.Constant)
                and node.comparators[0].value == 0
                and isinstance(node.left, ast.Call)
                and isinstance(node.left.func, ast.Name)
                and node.left.func.id == "len"
            ):
                suggestions.append({
                    "type": "LenComparison",
                    "priority": "LOW",
                    "line": node.lineno,
                    "description": "len(x) > 0 is redundant — sequences are falsy when empty",
                    "suggestion": "Use 'if x:' instead of 'if len(x) > 0:'",
                    "impact": "More idiomatic and marginally faster",
                })


def _suggest_readability(tree: ast.AST, code: str, suggestions: list[dict[str, Any]]) -> None:
    module_has_docstring = (
        isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
        if tree.body else False
    )
    if not module_has_docstring:
        suggestions.append({
            "type": "MissingModuleDocstring",
            "priority": "LOW",
            "line": 1,
            "description": "Module has no docstring",
            "suggestion": 'Add a module-level docstring: """Module description."""',
            "impact": "Improves discoverability and documentation generation",
        })

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            has_docstring = (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            )
            if not has_docstring:
                kind = "Function" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "Class"
                suggestions.append({
                    "type": f"Missing{kind}Docstring",
                    "priority": "LOW",
                    "line": node.lineno,
                    "description": f"{kind} '{node.name}' has no docstring",
                    "suggestion": f'Add a docstring as the first statement in {node.name}',
                    "impact": "Improves code documentation and IDE support",
                })

    for node in ast.walk(tree):
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            if isinstance(node.operand, ast.Compare):
                suggestions.append({
                    "type": "NegativeCondition",
                    "priority": "LOW",
                    "line": node.lineno,
                    "description": "Negative condition 'not (x op y)' can be inverted for clarity",
                    "suggestion": "Invert the comparison operator instead of using 'not'",
                    "impact": "Easier to read and reason about",
                })


def _suggest_maintainability(tree: ast.AST, suggestions: list[dict[str, Any]]) -> None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args_without_annotations = [
                arg for arg in node.args.args
                if arg.annotation is None and arg.arg != "self"
            ]
            if args_without_annotations:
                suggestions.append({
                    "type": "MissingTypeHints",
                    "priority": "MEDIUM",
                    "line": node.lineno,
                    "description": f"Function '{node.name}' has parameters without type annotations: "
                                   f"{[a.arg for a in args_without_annotations]}",
                    "suggestion": "Add type annotations to all parameters and the return type",
                    "impact": "Enables static analysis, better IDE support, and self-documenting code",
                })
            if node.returns is None:
                suggestions.append({
                    "type": "MissingReturnType",
                    "priority": "LOW",
                    "line": node.lineno,
                    "description": f"Function '{node.name}' has no return type annotation",
                    "suggestion": f"Add '-> ReturnType' to the function signature",
                    "impact": "Clearer API contract and better static analysis",
                })

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None or (
                isinstance(node.type, ast.Name) and node.type.id == "Exception"
            ):
                suggestions.append({
                    "type": "BroadExceptionHandling",
                    "priority": "HIGH",
                    "line": node.lineno,
                    "description": "Broad exception handler catches more than intended",
                    "suggestion": "Catch specific exception types (e.g., ValueError, KeyError)",
                    "impact": "Prevents hiding unexpected errors",
                })

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    suggestions.append({
                        "type": "GlobalVariable",
                        "priority": "MEDIUM",
                        "line": node.lineno,
                        "description": f"Module-level variable '{target.id}' acts as mutable global state",
                        "suggestion": "Encapsulate module state in a class or pass as function parameters",
                        "impact": "Reduces coupling and makes testing easier",
                    })

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = (node.end_lineno or node.lineno) - node.lineno + 1
            if length > 40:
                suggestions.append({
                    "type": "LongFunction",
                    "priority": "HIGH",
                    "line": node.lineno,
                    "description": f"Function '{node.name}' is {length} lines — hard to test and maintain",
                    "suggestion": "Extract logical sections into smaller, well-named helper functions",
                    "impact": "Better testability and single-responsibility compliance",
                })
