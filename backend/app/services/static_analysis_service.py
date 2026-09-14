from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def run_static_tool(tool: str, root: Path, command: list[str], timeout: int = 180) -> dict[str, Any]:
    result = {"tool": tool, "status": "skipped", "findings": [], "summary": {"total": 0, "high": 0, "medium": 0, "low": 0, "info": 0}, "errors": []}
    if not shutil.which(command[0]):
        result["errors"] = [f"{command[0]} is not installed."]
        return result
    try:
        process = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=timeout, shell=False)
        result["status"] = "completed"
        if process.stdout.strip():
            try:
                result["raw"] = json.loads(process.stdout)
            except json.JSONDecodeError:
                result["raw"] = process.stdout[-10000:]
        if process.stderr.strip():
            result["errors"] = [process.stderr[-4000:]]
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["status"] = "failed"
        result["errors"] = [str(exc)]
    return result


def run_static_analysis(root: Path, files: list[str]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    if any(Path(name).suffix.lower() == ".py" for name in files):
        results["ruff"] = run_static_tool("Ruff", root, ["ruff", "check", ".", "--output-format", "json"])
    if any(Path(name).suffix.lower() in {".js", ".jsx", ".ts", ".tsx"} for name in files):
        results["eslint"] = run_static_tool("ESLint", root, ["eslint", ".", "--format", "json"])
    return {"status": "completed", "tools": results, "errors": []}