
from typing import Any

from app.services.security.bandit_service import BanditService
from app.services.security.dependency_service import run_dependency_scan
from app.services.security.semgrep_service import SemgrepService
from app.services.security.zap_service import run_zap_scan


class SecurityRunner:
    """
    Central security scanner orchestrator.

    Currently supported:
        - Bandit
        - Semgrep

    Future scanners:
        - Dependency scanner
        - OWASP ZAP
    """

    def __init__(self) -> None:
        self.bandit = BanditService()
        self.semgrep = SemgrepService()

    def run_bandit(self, project_path: str) -> dict[str, Any]:
        """
        Run Bandit against the supplied project.
        """
        return self.bandit.run_scan(project_path)

    def run_semgrep(self, project_path: str) -> dict[str, Any]:
        """
        Run Semgrep against the supplied project.
        """
        return self.semgrep.run_scan(project_path)

    def run_all(
        self,
        project_path: str,
        scanners: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Run the requested security scanners.

        If scanners is None, all currently available scanners
        are executed.
        """

        if scanners is None:
            scanners = ["bandit", "semgrep", "dependencies", "zap"]

        results: dict[str, Any] = {}

        for scanner in scanners:
            scanner_name = scanner.lower().strip()

            if scanner_name == "bandit":
                results["bandit"] = self.run_bandit(project_path)

            elif scanner_name == "semgrep":
                results["semgrep"] = self.run_semgrep(project_path)

            elif scanner_name == "dependencies":
                results["dependencies"] = run_dependency_scan(project_path)

            elif scanner_name == "zap":
                results["zap"] = run_zap_scan("http://127.0.0.1:8000")

            else:
                results[scanner_name] = {
                    "status": "not_implemented",
                    "tool": scanner_name,
                    "findings": [],
                    "summary": {
                        "total": 0,
                        "high": 0,
                        "medium": 0,
                        "low": 0,
                    },
                    "message": (
                        f"Security scanner '{scanner_name}' "
                        "is not implemented yet."
                    ),
                }

        summary = self._build_summary(results)

        return {
            "status": "completed",
            "project_path": project_path,
            "scanners": results,
            "summary": summary,
        }

    @staticmethod
    def _build_summary(
        results: dict[str, Any],
    ) -> dict[str, int]:
        """
        Combine security findings from all scanners.
        """

        total = 0
        high = 0
        medium = 0
        low = 0

        for result in results.values():
            summary = result.get("summary", {})

            total += int(summary.get("total", 0))
            high += int(summary.get("high", 0))
            medium += int(summary.get("medium", 0))
            low += int(summary.get("low", 0))

        return {
            "total": total,
            "high": high,
            "medium": medium,
            "low": low,
        }


def run_security_scan(
    project_path: str,
    scanners: list[str] | None = None,
) -> dict[str, Any]:
    """
    Convenience function for API routes and QA pipeline.
    """

    runner = SecurityRunner()

    return runner.run_all(
        project_path=project_path,
        scanners=scanners,
    )
