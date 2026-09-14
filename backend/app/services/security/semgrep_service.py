import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


class SemgrepService:
    """
    Runs Semgrep against a project directory and converts
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
        "coverage",
        ".pytest_cache",
    }

    def __init__(self) -> None:
        self.tool_name = "Semgrep"

    def _build_exclude_arguments(
        self,
        project_path: Path,
    ) -> list[str]:
        """
        Build Semgrep --exclude arguments for directories
        that should not be scanned.
        """

        arguments: list[str] = []

        for directory in self.EXCLUDED_DIRECTORIES:
            path = project_path / directory

            if path.exists():
                arguments.extend(
                    [
                        "--exclude",
                        directory,
                    ]
                )

        return arguments

    def run_scan(self, project_path: str) -> dict[str, Any]:
        """
        Run Semgrep against the supplied project directory.

        Returns:
            status
            tool
            findings
            summary
            raw_output
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

        # Find the actual Semgrep executable.
        # This avoids the deprecated `python -m semgrep` method.
        semgrep_executable = shutil.which("semgrep")

        if not semgrep_executable:
            return {
                "status": "error",
                "tool": self.tool_name,
                "message": (
                    "Semgrep executable was not found in PATH. "
                    "Make sure Semgrep is installed in the active environment."
                ),
                "findings": [],
                "summary": {
                    "total": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                },
            }

        command = [
            semgrep_executable,
            "scan",
            "--config",
            "auto",
            "--json",
            "--quiet",
        ]

        command.extend(
            self._build_exclude_arguments(project)
        )

        command.append(str(project))

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=600,
                shell=False,
            )

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "tool": self.tool_name,
                "message": "Semgrep scan exceeded the 10-minute timeout.",
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

        stdout = process.stdout.strip()
        stderr = process.stderr.strip()

        if not stdout:
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
                "raw_output": stderr,
            }

        try:
            semgrep_data = json.loads(stdout)

        except json.JSONDecodeError:
            return {
                "status": "error",
                "tool": self.tool_name,
                "message": "Semgrep returned invalid JSON output.",
                "findings": [],
                "summary": {},
                "raw_output": stdout,
                "stderr": stderr,
            }

        findings: list[dict[str, Any]] = []

        for result in semgrep_data.get("results", []):
            extra = result.get("extra", {})
            metadata = extra.get("metadata", {})

            severity = (
                extra.get("severity")
                or metadata.get("severity")
                or "INFO"
            ).upper()

            if severity == "ERROR":
                normalized_severity = "HIGH"
            elif severity == "WARNING":
                normalized_severity = "MEDIUM"
            else:
                normalized_severity = "LOW"

            start = result.get("start", {})
            end = result.get("end", {})

            findings.append(
                {
                    "tool": self.tool_name,
                    "check_id": result.get("check_id"),
                    "severity": normalized_severity,
                    "original_severity": severity,
                    "message": extra.get(
                        "message",
                        "Semgrep security finding.",
                    ),
                    "file": result.get("path"),
                    "line_number": start.get("line"),
                    "end_line": end.get("line"),
                    "column": start.get("col"),
                    "end_column": end.get("col"),
                    "lines": extra.get("lines"),
                    "fingerprint": extra.get("fingerprint"),
                    "metadata": metadata,
                    "fix": extra.get("fix"),
                    "references": metadata.get(
                        "references",
                        [],
                    ),
                }
            )

        summary = {
            "total": len(findings),
            "high": sum(
                1
                for finding in findings
                if finding["severity"] == "HIGH"
            ),
            "medium": sum(
                1
                for finding in findings
                if finding["severity"] == "MEDIUM"
            ),
            "low": sum(
                1
                for finding in findings
                if finding["severity"] == "LOW"
            ),
        }

        return {
            "status": "completed",
            "tool": self.tool_name,
            "findings": findings,
            "summary": summary,
            "raw_output": semgrep_data,
        }


def run_semgrep_scan(
    project_path: str,
) -> dict[str, Any]:
    """
    Convenience function for the rest of the QA Analyzer.
    """

    service = SemgrepService()

    return service.run_scan(project_path)
