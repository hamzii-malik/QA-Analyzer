from pathlib import Path
import zipfile

import pytest

from app.services.archive_service import extract_archive
from app.services.project_detector import detect_project
from app.services.qa_pipeline import _add_evidence_categories
from app.services.testing.boundary_test_service import analyze_boundaries
from app.services.testing.edge_case_service import generate_edge_cases
from app.services.testing.logical_test_service import analyze_logical_cases


def test_project_detector_identifies_fastapi_and_react(tmp_path):
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"dependencies":{"react":"19","vite":"7"}}', encoding="utf-8")
    result = detect_project(tmp_path, ["requirements.txt", "package.json", "main.py", "src/App.jsx"])
    assert result["project_type"] == "react"
    assert "fastapi" in result["frameworks"]
    assert "react" in result["frameworks"]


def test_logical_and_boundary_services_generate_evidence(tmp_path):
    source = "def allowed(age):\n    if age >= 18:\n        return True\n    return False\n"
    (tmp_path / "service.py").write_text(source, encoding="utf-8")
    files = ["service.py"]
    logical = analyze_logical_cases(tmp_path, files)
    boundary = analyze_boundaries(tmp_path, files)
    assert logical["summary"]["total"] == 1
    assert boundary["findings"][0]["test_cases"] == [17.0, 18.0, 19.0]


def test_edge_cases_are_bounded():
    result = generate_edge_cases()
    assert result["status"] == "completed"
    assert result["summary"]["total"] < 25


def test_zip_slip_is_rejected(tmp_path):
    archive = tmp_path / "unsafe.zip"
    destination = tmp_path / "out"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("../../outside.txt", "blocked")
    with pytest.raises(ValueError, match="unsafe path"):
        extract_archive(str(archive), str(destination))


def test_security_and_edge_categories_follow_deprecation():
    summary = {
        "categories": {
            "manual_testing": {},
            "deprecation_testing": {},
            "final_report": {},
        },
        "security": {
            "status": "completed",
            "summary": {"high": 0, "medium": 0},
            "scanners": {},
        },
        "testing": {"edge": {"status": "completed", "findings": []}},
    }
    _add_evidence_categories(summary)
    assert list(summary["categories"]) == [
        "manual_testing",
        "deprecation_testing",
        "security_testing",
        "edge_case_testing",
        "final_report",
    ]
