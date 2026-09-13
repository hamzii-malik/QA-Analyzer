from __future__ import annotations

from pathlib import Path

from app.services.project_analyzer import generate_project_summary
from app.services.qa_execution import run_external_qa_checks


def run_project_qa_pipeline(project_info: dict) -> dict:
    project_root = Path(project_info.get("root", "."))
    summary = generate_project_summary(project_info)

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
