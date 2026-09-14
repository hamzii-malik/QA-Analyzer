from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _empty(tool: str, status: str = "skipped", message: str = "") -> dict[str, Any]:
    return {"status": status, "tool": tool, "findings": [], "summary": {"total": 0, "high": 0, "medium": 0, "low": 0, "info": 0}, "errors": [message] if message else []}


def _summary(findings: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"total": len(findings), "high": 0, "medium": 0, "low": 0, "info": 0}
    for finding in findings:
        severity = str(finding.get("severity", "INFO")).lower()
        summary[severity if severity in summary else "info"] += 1
    return summary


def run_dependency_scan(root: str) -> dict[str, Any]:
    project = Path(root)
    findings: list[dict[str, Any]] = []
    errors: list[str] = []
    ran = False

    requirements = project / "requirements.txt"
    if requirements.exists():
        executable = shutil.which("pip-audit")
        if executable:
            ran = True
            try:
                process = subprocess.run([executable, "-r", str(requirements), "-f", "json"], capture_output=True, text=True, timeout=180, shell=False)
                payload = json.loads(process.stdout or "[]")
                for item in payload if isinstance(payload, list) else payload.get("dependencies", []):
                    for vulnerability in item.get("vulns", []):
                        findings.append({"package": item.get("name"), "installed_version": item.get("version"), "severity": "HIGH", "vulnerability": vulnerability.get("id"), "fixed_version": ", ".join(vulnerability.get("fix_versions", [])), "description": vulnerability.get("description", "")})
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                errors.append(f"pip-audit: {exc}")
        else:
            errors.append("pip-audit is not installed; dependency scan skipped for Python.")

    package_json = project / "package.json"
    if package_json.exists():
        executable = shutil.which("npm")
        if executable:
            ran = True
            try:
                process = subprocess.run([executable, "audit", "--json"], cwd=project, capture_output=True, text=True, timeout=180, shell=False)
                payload = json.loads(process.stdout or "{}")
                advisories = payload.get("vulnerabilities", {})
                for package, advisory in advisories.items():
                    findings.append({"package": package, "installed_version": advisory.get("range"), "severity": str(advisory.get("severity", "INFO")).upper(), "vulnerability": ", ".join(advisory.get("via", [])) if isinstance(advisory.get("via"), list) else str(advisory.get("via", "")), "fixed_version": str(advisory.get("fixAvailable", "")), "description": "npm audit vulnerability"})
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                errors.append(f"npm audit: {exc}")

    status = "completed" if ran else "skipped"
    return {"status": status, "tool": "Dependency audit", "findings": findings, "summary": _summary(findings), "errors": errors}