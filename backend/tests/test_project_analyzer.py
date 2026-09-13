from pathlib import Path

from app.services.project_analyzer import (
    build_category_results,
    detect_project_type,
    generate_project_summary,
)
from app.services.qa_pipeline import run_project_qa_pipeline
from app.services.qa_execution import run_external_qa_checks


def test_detect_project_type_for_react_project():
    root = Path("/tmp/demo-react")
    assert detect_project_type(root, ["package.json", "src/App.jsx"]) == "react"


def test_build_category_results_contains_expected_categories():
    result = build_category_results({
        "project_type": "react",
        "root": Path("/tmp/demo-react"),
        "files": [
            "package.json",
            "src/App.jsx",
            "src/api.js",
            "src/App.css",
            "README.md",
        ],
    })

    assert "manual_testing" in result
    assert "automatic_testing" in result
    assert "regression_testing" in result
    assert "api_testing" in result
    assert "responsiveness_testing" in result
    assert "latency_testing" in result
    assert "deprecation_testing" in result
    assert "final_report" in result


def test_generate_project_summary_uses_project_evidence_for_category_details(tmp_path):
    project_root = tmp_path / "demo-react"
    src_dir = project_root / "src"
    src_dir.mkdir(parents=True)
    (project_root / "package.json").write_text(
        '{"scripts":{"test":"vitest run","build":"vite build"},"dependencies":{"react":"^19.0.0"}}',
        encoding="utf-8",
    )
    (src_dir / "App.jsx").write_text(
        "export default function App(){ fetch('/api/users'); return <div>OK</div>; }",
        encoding="utf-8",
    )
    (src_dir / "App.css").write_text("@media (max-width: 768px) { .card { width: 100%; } }", encoding="utf-8")

    result = generate_project_summary({
        "root": project_root,
        "files": [
            "package.json",
            "src/App.jsx",
            "src/App.css",
        ],
    })

    automatic = result["categories"]["automatic_testing"]
    api = result["categories"]["api_testing"]
    responsive = result["categories"]["responsiveness_testing"]

    assert "vitest" in " ".join(automatic["details"]).lower()
    assert "fetch" in " ".join(api["details"]).lower()
    assert "@media" in " ".join(responsive["details"]).lower()


def test_python_projects_prepare_regression_and_responsiveness_checks(tmp_path):
    project_root = tmp_path / "python-service"
    project_root.mkdir()
    (project_root / "requirements.txt").write_text("fastapi\npytest\n", encoding="utf-8")
    (project_root / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")

    result = generate_project_summary({
        "root": project_root,
        "files": ["requirements.txt", "main.py"],
    })

    regression = result["categories"]["regression_testing"]
    responsiveness = result["categories"]["responsiveness_testing"]

    assert regression["status"] == "ready"
    assert "pytest" in regression["command"]
    assert responsiveness["status"] == "ready"
    assert "127.0.0.1:8000" in responsiveness["command"]


def test_run_project_qa_pipeline_builds_final_report(tmp_path):
    project_root = tmp_path / "demo-react"
    src_dir = project_root / "src"
    src_dir.mkdir(parents=True)
    (project_root / "package.json").write_text(
        '{"scripts":{"test":"vitest run","build":"vite build"},"dependencies":{"react":"^19.0.0"}}',
        encoding="utf-8",
    )
    (src_dir / "App.jsx").write_text(
        "fetch('/api/users'); export default function App(){ return <div>QA</div>; }",
        encoding="utf-8",
    )
    (src_dir / "App.css").write_text("@media (max-width: 600px) { .layout { display: block; } }", encoding="utf-8")

    result = run_project_qa_pipeline({
        "root": project_root,
        "files": [
            "package.json",
            "src/App.jsx",
            "src/App.css",
        ],
    })

    assert result["project_type"] == "react"
    assert result["overall_score"] >= 0
    assert result["final_report"]["status"] in {"ready", "warning"}
    assert "tool" in result["final_report"]
    assert "command" in result["final_report"]


def test_run_external_qa_checks_returns_tool_statuses(tmp_path):
    project_root = tmp_path / "demo-react"
    src_dir = project_root / "src"
    src_dir.mkdir(parents=True)
    (project_root / "package.json").write_text(
        '{"scripts":{"test":"vitest run","build":"vite build"}}',
        encoding="utf-8",
    )
    (src_dir / "App.jsx").write_text("fetch('/api/users');", encoding="utf-8")

    result = run_external_qa_checks({
        "root": project_root,
        "files": [
            "package.json",
            "src/App.jsx",
        ],
    })

    assert "lighthouse" in result
    assert "jmeter" in result
    assert "postman" in result
    assert result["lighthouse"]["status"] in {"ready", "not_available"}
    assert result["jmeter"]["status"] in {"ready", "not_available"}
    assert result["postman"]["status"] in {"ready", "not_available"}
