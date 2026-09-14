from __future__ import annotations

from pathlib import Path


def prepare_test_execution(root: Path, project_type: str) -> dict:
    if project_type == "python" and (root / "pytest.ini").exists():
        command = "pytest -q"
    elif project_type in {"node", "react"} and (root / "package.json").exists():
        command = "npm test"
    else:
        return {"status": "skipped", "executed": False, "command": None, "passed": 0, "failed": 0, "skipped": 0, "errors": ["No explicit test runner configuration detected."]}
    return {"status": "ready", "executed": False, "command": command, "passed": 0, "failed": 0, "skipped": 0, "errors": ["Execution is disabled by default for uploaded projects."]}