from __future__ import annotations

import shutil
from pathlib import Path


def _tool_status(command: str) -> dict:
    tool_name = command.split()[0]
    present = shutil.which(tool_name) is not None
    return {
        "status": "ready" if present else "not_available",
        "tool": tool_name,
        "command": command,
        "details": (
            [f"{tool_name} is installed and ready for execution."]
            if present
            else [f"{tool_name} is not installed in the current environment; use the suggested command when available."]
        ),
    }


def run_external_qa_checks(project_info: dict) -> dict:
    root = Path(project_info.get("root", "."))
    files = project_info.get("files", [])
    file_set = {str(Path(f)).replace('\\', '/').lower() for f in files}

    checks = {
        "lighthouse": _tool_status("lighthouse http://127.0.0.1:8000 --output html --chrome-flags='--headless'"),
        "jmeter": _tool_status("jmeter -n -t test-plan.jmx -l results.jtl"),
        "postman": _tool_status("newman run collection.json"),
    }

    if not file_set:
        for key, value in checks.items():
            value["status"] = "not_available"
            value["details"] = ["No project files were detected to run the external QA tool against."]

    if root.exists() and not any(root.iterdir()):
        for key, value in checks.items():
            value["status"] = "not_available"
            value["details"] = ["Project root is empty; external QA checks cannot be executed."]

    return checks
