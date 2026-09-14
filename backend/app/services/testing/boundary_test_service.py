from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any


COMPARISON_PATTERN = re.compile(r"(?:>=|<=|>|<)\s*(-?\d+(?:\.\d+)?)")


def analyze_boundaries(root: Path, files: list[str]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for file_name in files:
        if Path(file_name).suffix.lower() != ".py":
            continue
        try:
            tree = ast.parse((root / file_name).read_text(encoding="utf-8", errors="ignore"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                expression = ast.unparse(node)
                match = COMPARISON_PATTERN.search(expression)
                if match:
                    boundary = float(match.group(1))
                    values = [boundary - 1, boundary, boundary + 1]
                    findings.append({"category": "boundary", "file": file_name, "line": node.lineno, "condition": expression, "boundary": boundary, "test_cases": values})
    return {"status": "completed", "findings": findings, "summary": {"total": len(findings)}, "errors": []}