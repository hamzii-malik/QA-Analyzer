from __future__ import annotations

import json
import shutil
import subprocess
from ipaddress import ip_address
from urllib.parse import urlparse
from typing import Any

from app.core.config import settings


def _allowed_target(target: str) -> bool:
    parsed = urlparse(target)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    if parsed.hostname.lower() == "localhost":
        return True
    try:
        return ip_address(parsed.hostname).is_loopback
    except ValueError:
        return False


def run_zap_scan(target: str) -> dict[str, Any]:
    base = {"status": "skipped", "tool": "OWASP ZAP", "target": target, "findings": [], "summary": {"total": 0, "high": 0, "medium": 0, "low": 0, "info": 0}, "errors": []}
    if not _allowed_target(target):
        base["errors"] = ["ZAP target must be localhost or a loopback address."]
        return base
    if not settings.ZAP_ENABLED:
        base["errors"] = ["ZAP scanning is disabled by configuration."]
        return base
    executable = settings.ZAP_PATH or shutil.which("zap-baseline.py") or shutil.which("zap-baseline")
    if not executable:
        base["errors"] = ["OWASP ZAP baseline executable was not found."]
        return base
    try:
        process = subprocess.run([executable, "-t", target, "-J", "zap-report.json", "-I"], capture_output=True, text=True, timeout=600, shell=False)
        report = json.loads((__import__("pathlib").Path("zap-report.json")).read_text(encoding="utf-8")) if __import__("pathlib").Path("zap-report.json").exists() else {}
        alerts = report.get("site", [{}])[0].get("alerts", []) if isinstance(report.get("site"), list) else []
        findings = [{"name": alert.get("name"), "risk": alert.get("riskdesc"), "severity": str(alert.get("riskcode", "INFO")).upper(), "url": alert.get("uri"), "description": alert.get("desc"), "evidence": alert.get("evidence")} for alert in alerts]
        base.update({"status": "completed", "findings": findings, "summary": {"total": len(findings), "high": sum(f["severity"] == "HIGH" for f in findings), "medium": sum(f["severity"] == "MEDIUM" for f in findings), "low": sum(f["severity"] == "LOW" for f in findings), "info": sum(f["severity"] == "INFO" for f in findings)}})
        return base
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        base["status"] = "failed"
        base["errors"] = [str(exc)]
        return base