import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class BanditService:
    """
    Runs Bandit against a project directory and converts
    the output into a normalized security finding structure.
    """

    EXCLUDED_DIRECTORIES = {
        ".git",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "__pycache__",
        "uploads",
        "reports",
        "dist",
        "build",
    }

    def __init__(self) -> None:
        self.tool_name = "Bandit"

    def _build_exclude_paths(self, project_path: Path) -> str:
        """
        Build a comma-separated list of directories that Bandit
        should ignore.
        """

        excluded_paths = []

        for directory in self.EXCLUDED_DIRECTORIES:
            path = project_path / directory

            if path.exists():
                excluded_paths.append(str(path))

        return ",".join(excluded_paths)

    def run_scan(self, project_path: str) -> dict[str, Any]:
        """
        Run Bandit against the supplied project directory.

        Returns a normalized dictionary containing:
        - status
        - tool
        - findings
        - summary
        - raw_output
        """

        project = Path(project_path).resolve()

        if not project.exists():
            return {
                "status": "error",
                "tool": self.tool_name,
                "message": f"Project path does not exist: {project}",
                "findings": [],
                "summary": {},
            }

        if not project.is_dir():
            return {
                "status": "error",
                "tool": self.tool_name,
                "message": f"Project path is not a directory: {project}",
                "findings": [],
                "summary": {},
            }

        exclude_paths = self._build_exclude_paths(project)

        # Use the exact Python interpreter running this application.
        command = [
            sys.executable,
            "-m",
            "bandit",
            "-r",
            str(project),
            "-f",
            "json",
            "-q",
        ]

        if exclude_paths:
            command.extend(["--exclude", exclude_paths])

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300,
                shell=False,
            )

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "tool": self.tool_name,
                "message": "Bandit scan exceeded the 5-minute timeout.",
                "findings": [],
                "summary": {},
            }

        except Exception as exc:
            return {
                "status": "error",
                "tool": self.tool_name,
                "message": str(exc),
                "findings": [],
                "summary": {},
            }

        raw_output = process.stdout.strip()

        if not raw_output:
            return {
                "status": "completed",
                "tool": self.tool_name,
                "findings": [],
                "summary": {
                    "total": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                },
                "raw_output": process.stderr.strip(),
            }

        try:
            bandit_data = json.loads(raw_output)

        except json.JSONDecodeError:
            return {
                "status": "error",
                "tool": self.tool_name,
                "message": "Bandit returned invalid JSON output.",
                "findings": [],
                "summary": {},
                "raw_output": raw_output,
                "stderr": process.stderr.strip(),
            }

        findings = []

        for result in bandit_data.get("results", []):
            findings.append(
                {
                    "tool": self.tool_name,
                    "test_id": result.get("test_id"),
                    "test_name": result.get("test_name"),
                    "severity": result.get(
                        "issue_severity",
                        "UNKNOWN",
                    ).upper(),
                    "confidence": result.get(
                        "issue_confidence",
                        "UNKNOWN",
                    ).upper(),
                    "message": result.get("issue_text"),
                    "file": result.get("filename"),
                    "line_number": result.get("line_number"),
                    "line_range": result.get("line_range", []),
                    "code": result.get("code"),
                    "more_info": result.get("more_info"),
                }
            )

        # Use Bandit's global totals instead of adding
        # per-file metrics and _totals together.
        metrics = bandit_data.get("metrics", {})
        totals = metrics.get("_totals", {})

        summary = {
            "total": len(findings),
            "high": int(
                totals.get("SEVERITY.HIGH", 0)
            ),
            "medium": int(
                totals.get("SEVERITY.MEDIUM", 0)
            ),
            "low": int(
                totals.get("SEVERITY.LOW", 0)
            ),
        }

        return {
            "status": "completed",
            "tool": self.tool_name,
            "findings": findings,
            "summary": summary,
            "raw_output": bandit_data,
        }


def run_bandit_scan(project_path: str) -> dict[str, Any]:
    """
    Convenience function for the rest of the QA Analyzer.
    """

    service = BanditService()

    return service.run_scan(project_path)
