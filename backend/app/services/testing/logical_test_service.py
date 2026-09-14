from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


def analyze_logical_cases(root: Path, files: list[str]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for file_name in files:
        if Path(file_name).suffix.lower() != ".py":
            continue
        try:
            tree = ast.parse((root / file_name).read_text(encoding="utf-8", errors="ignore"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                condition = ast.unparse(node.test)
                findings.append({"category": "logical", "file": file_name, "line": node.lineno, "condition": condition, "test_cases": [{"input": "condition false", "expected": "false branch"}, {"input": "condition true", "expected": "true branch"}]})
    return {"status": "completed", "findings": findings, "summary": {"total": len(findings)}, "errors": []}