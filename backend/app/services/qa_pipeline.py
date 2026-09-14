from __future__ import annotations

from pathlib import Path

from app.services.project_analyzer import generate_project_summary
from app.services.qa_execution import run_external_qa_checks
from app.services.project_detector import detect_project
from app.services.runtime_detector import detect_runtime
from app.services.api_test_service import discover_api_endpoints
from app.services.security.security_runner import run_security_scan
from app.services.static_analysis_service import run_static_analysis
from app.services.testing.boundary_test_service import analyze_boundaries
from app.services.testing.edge_case_service import generate_edge_cases
from app.services.testing.logical_test_service import analyze_logical_cases


def _safe_security_scan(project_root: Path) -> dict:
    try:
        return run_security_scan(str(project_root))
    except Exception as exc:
        return {
            "status": "failed",
            "scanners": {},
            "summary": {"total": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
            "errors": [str(exc)],
        }


def _safe_call(function, *args) -> dict:
    try:
        return function(*args)
    except Exception as exc:
        return {"status": "failed", "findings": [], "summary": {"total": 0}, "errors": [str(exc)]}


def run_project_qa_pipeline(project_info: dict) -> dict:
    project_root = Path(project_info.get("root", "."))
    summary = generate_project_summary(project_info)
    summary["project_detection"] = detect_project(project_root, project_info.get("files", []))
    summary["runtime"] = detect_runtime(project_root, project_info.get("files", []), summary["project_detection"].get("frameworks", []))
    summary["api_testing"] = discover_api_endpoints(project_root, project_info.get("files", []))
    summary["security"] = _safe_security_scan(project_root)
    files = project_info.get("files", [])
    summary["static_analysis"] = _safe_call(run_static_analysis, project_root, files)
    summary["testing"] = {
        "logical": _safe_call(analyze_logical_cases, project_root, files),
        "boundary": _safe_call(analyze_boundaries, project_root, files),
        "edge": generate_edge_cases(),
    }
    security_summary = summary["security"].get("summary", {})
    deductions = (security_summary.get("high", 0) * 8) + (security_summary.get("medium", 0) * 4) + (security_summary.get("low", 0) * 1)
    summary["score_breakdown"] = {"base": 100, "security_deductions": deductions, "final": max(0, min(100, round(summary["overall_score"] - deductions, 2)))}
    summary["overall_score"] = summary["score_breakdown"]["final"]

    category_results = summary["categories"]
    final_report = category_results.get("final_report", {})
    final_report["status"] = final_report.get("status", "ready")
    final_report["tool"] = final_report.get("tool", "QA report builder")
    final_report["command"] = final_report.get(
        "command",
        "Generate DOCX summary and export final QA report to the project reports folder.",
    )

    summary["external_checks"] = run_external_qa_checks(project_info)
    summary["final_report"] = final_report
    summary["project_root"] = str(project_root)
    summary["execution_ready"] = True

    return summary
