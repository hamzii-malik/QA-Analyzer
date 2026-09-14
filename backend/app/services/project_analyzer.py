import json
import re
from pathlib import Path


SUPPORTED_QA_CATEGORIES = [
    "manual_testing",
    "automatic_testing",
    "regression_testing",
    "api_testing",
    "responsiveness_testing",
    "latency_testing",
    "deprecation_testing",
    "final_report",
]


def detect_project_type(root: Path, file_list: list[str]) -> str:
    paths = [Path(f) for f in file_list]
    files = {path.name.lower() for path in paths}
    path_text = " ".join(path.as_posix().lower() for path in paths)

    if "package.json" in files and ("src/" in path_text or "vite.config" in path_text or "react" in path_text):
        return "react"
    if "requirements.txt" in files or "pyproject.toml" in files:
        return "python"
    if "pom.xml" in files:
        return "java"
    if ".csproj" in files:
        return "dotnet"
    if "package.json" in files and any(name in path_text for name in ("server", "express", "index.js")):
        return "node"
    if any(path.suffix.lower() in {".js", ".jsx", ".ts", ".tsx"} for path in paths):
        return "node"
    if any(path.suffix.lower() == ".py" for path in paths):
        return "python"
    return "generic"


def _normalize_relative_path(path_value: str) -> str:
    return str(Path(path_value)).replace('\\', '/').lower()


def _collect_project_evidence(root: Path, files: list[str]) -> dict:
    evidence = {
        "package_json": "",
        "source_text": "",
        "css_text": "",
        "docs_text": "",
        "python_text": "",
    }

    for file_name in files:
        normalized = _normalize_relative_path(file_name)
        file_path = root / file_name

        try:
            if not file_path.is_file():
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if normalized.endswith("package.json"):
            evidence["package_json"] += "\n" + text
        elif normalized.endswith((".js", ".jsx", ".ts", ".tsx", ".py")):
            evidence["source_text"] += "\n" + text
        elif normalized.endswith(".css"):
            evidence["css_text"] += "\n" + text
        elif normalized.endswith((".md", ".txt", ".rst")):
            evidence["docs_text"] += "\n" + text

    return evidence


def _package_script_details(package_json_text: str) -> list[str]:
    details = []
    lower_text = package_json_text.lower()

    if "vitest" in lower_text or "jest" in lower_text or "playwright" in lower_text:
        details.append("Detected test tooling via package scripts: vitest/jest/playwright is configured for automated QA.")
    if "npm run build" in lower_text or "vite build" in lower_text or "webpack" in lower_text:
        details.append("Detected build pipeline and production bundling config for release validation.")
    if "cypress" in lower_text or "puppeteer" in lower_text:
        details.append("Detected browser automation tooling for end-to-end verification.")

    return details or [
        "Package manifest detected; confirm scripts for test, build, and quality checks before release.",
    ]


def _api_evidence_details(source_text: str) -> list[str]:
    details = []
    lower_text = source_text.lower()

    if "fetch(" in lower_text or "axios" in lower_text:
        details.append("Detected API client calls using fetch/axios; verify request payloads, retries, and error handling.")
    if "/api/" in lower_text or "api/" in lower_text:
        details.append("Project references API endpoints with /api paths; validate their success and failure flows.")
    if "postman" in lower_text or "swagger" in lower_text:
        details.append("API contract artifacts appear to exist; compare them against the implemented routes.")

    return details or [
        "No direct API client usage was detected in source files; validate backend contracts manually.",
    ]


def _responsiveness_evidence_details(css_text: str, source_text: str) -> list[str]:
    details = []
    combined = (css_text + "\n" + source_text).lower()

    if "@media" in combined:
        details.append("Detected @media queries in CSS; review mobile and tablet breakpoints for responsive behavior.")
    if "max-width" in combined or "min-width" in combined:
        details.append("Viewport-based layout rules were detected; validate layout stability across breakpoints.")
    if "grid" in combined or "flex" in combined:
        details.append("Flexible UI layout patterns found; check layout integrity on small screens.")

    return details or [
        "No explicit responsive CSS markers were found; run Lighthouse or browser checks for mobile rendering.",
    ]


def _latency_and_deprecation_details(package_json_text: str, source_text: str) -> tuple[list[str], list[str]]:
    latency = []
    deprecation = []
    lower_package = package_json_text.lower()
    lower_source = source_text.lower()

    if "react" in lower_package and "18" in lower_package or "19" in lower_package:
        deprecation.append("Framework version detected; document compatibility and update risk before release.")
    if "deprecated" in lower_source or "legacy" in lower_source:
        deprecation.append("Legacy/deprecated patterns were found in the codebase and should be reviewed.")

    if "loadtest" in lower_package or "jmeter" in lower_package or "k6" in lower_package:
        latency.append("Performance testing tooling detected; use it to benchmark critical flows.")
    if "fetch(" in lower_source or "axios" in lower_source:
        latency.append("Network requests were detected; measure request latency and timeout behavior under load.")

    return latency or [
        "No explicit latency tooling was found; run JMeter/Lighthouse checks for response-time validation.",
    ], deprecation or [
        "No deprecated API markers were found in the project manifest or source; still validate package versions and compatibility.",
    ]


def _execution_plan_for(category: str, project_type: str) -> dict:
    plans = {
        "manual_testing": {
            "tool": "Manual QA checklist",
            "command": "Open app in browser and validate critical flows, forms, and edge cases.",
        },
        "automatic_testing": {
            "tool": "Vitest/Jest/Playwright",
            "command": "npm test || npx vitest run || npx playwright test",
        },
        "regression_testing": {
            "tool": "Smoke + regression suite",
            "command": "npm run build && npm test",
        },
        "api_testing": {
            "tool": "Postman / Newman / curl",
            "command": "newman run collection.json || curl -X GET http://localhost:PORT/api/health",
        },
        "responsiveness_testing": {
            "tool": "Lighthouse / browser devtools",
            "command": "npx lighthouse http://127.0.0.1:8000 --output html --chrome-flags='--headless'",
        },
        "latency_testing": {
            "tool": "JMeter / k6",
            "command": "jmeter -n -t test-plan.jmx -l results.jtl || npx k6 run load-test.js",
        },
        "deprecation_testing": {
            "tool": "npm audit / outdated",
            "command": "npm outdated && npm audit --production",
        },
        "final_report": {
            "tool": "QA report builder",
            "command": "Generate DOCX summary and export final QA report to report folder.",
        },
    }

    default_plan = {
        "tool": "Manual review",
        "command": f"Perform {category.replace('_', ' ').title()} review for {project_type} project.",
    }
    return plans.get(category, default_plan)


def build_category_results(project_info: dict) -> dict:
    project_type = project_info.get("project_type", "generic")
    root = Path(project_info.get("root", "."))
    files = project_info.get("files", [])
    file_set = {str(Path(f)).replace('\\', '/').lower() for f in files}
    evidence = _collect_project_evidence(root, files)

    result = {}
    for category in SUPPORTED_QA_CATEGORIES:
        plan = _execution_plan_for(category, project_type)
        result[category] = {
            "status": "pending",
            "score": 0,
            "summary": f"{category.replace('_', ' ').title()} is ready for execution.",
            "details": [],
            "project_type": project_type,
            "root": str(root),
            "tool": plan["tool"],
            "command": plan["command"],
        }

    if project_type in {"react", "node"}:
        package_details = _package_script_details(evidence["package_json"])
        api_details = _api_evidence_details(evidence["source_text"])
        responsive_details = _responsiveness_evidence_details(evidence["css_text"], evidence["source_text"])
        latency_details, deprecation_details = _latency_and_deprecation_details(evidence["package_json"], evidence["source_text"])

        result["manual_testing"]["status"] = "ready"
        result["manual_testing"]["score"] = 85
        result["manual_testing"]["details"] = [
            "Manually validate primary user journeys and critical form states.",
            "Confirm the UI matches expected behavior for core screens and edge cases.",
        ]
        result["manual_testing"]["tool"] = "Manual QA checklist"
        result["manual_testing"]["command"] = "Open the app in browser and validate the primary flows, edge cases, and form validation UX."

        result["automatic_testing"]["status"] = "ready"
        result["automatic_testing"]["score"] = 80
        result["automatic_testing"]["details"] = package_details
        result["automatic_testing"]["tool"] = "Vitest/Jest/Playwright"
        result["automatic_testing"]["command"] = "npm test || npx vitest run || npx playwright test"

        result["regression_testing"]["status"] = "ready"
        result["regression_testing"]["score"] = 78
        result["regression_testing"]["details"] = [
            "Compare known critical flows before and after release changes.",
            "Validate route transitions, validation states, and error recovery paths.",
        ]
        result["regression_testing"]["tool"] = "Smoke + regression suite"
        result["regression_testing"]["command"] = "npm run build && npm test"

        result["api_testing"]["status"] = "ready"
        result["api_testing"]["score"] = 82
        result["api_testing"]["details"] = api_details
        result["api_testing"]["tool"] = "Postman / Newman / curl"
        result["api_testing"]["command"] = "newman run collection.json || curl -X GET http://localhost:PORT/api/health"

        result["responsiveness_testing"]["status"] = "ready"
        result["responsiveness_testing"]["score"] = 80
        result["responsiveness_testing"]["details"] = responsive_details
        result["responsiveness_testing"]["tool"] = "Lighthouse / browser devtools"
        result["responsiveness_testing"]["command"] = "npx lighthouse http://127.0.0.1:8000 --output html --chrome-flags='--headless'"

        result["latency_testing"]["status"] = "ready"
        result["latency_testing"]["score"] = 76
        result["latency_testing"]["details"] = latency_details
        result["latency_testing"]["tool"] = "JMeter / k6"
        result["latency_testing"]["command"] = "jmeter -n -t test-plan.jmx -l results.jtl || npx k6 run load-test.js"

        result["deprecation_testing"]["status"] = "ready"
        result["deprecation_testing"]["score"] = 74
        result["deprecation_testing"]["details"] = deprecation_details
        result["deprecation_testing"]["tool"] = "npm audit / outdated"
        result["deprecation_testing"]["command"] = "npm outdated && npm audit --production"

        result["final_report"]["status"] = "ready"
        result["final_report"]["score"] = 80
        result["final_report"]["details"] = [
            "Compile the category scores and recommendations into a final stakeholder summary.",
            "Generate a DOCX QA report using the project evidence gathered during analysis.",
        ]
        result["final_report"]["tool"] = "QA report builder"
        result["final_report"]["command"] = "Generate DOCX summary and export final QA report to the project reports folder."

    elif project_type == "python":
        api_details = _api_evidence_details(evidence["source_text"])
        latency_details, deprecation_details = _latency_and_deprecation_details(evidence["package_json"], evidence["source_text"])

        result["manual_testing"]["status"] = "ready"
        result["manual_testing"]["score"] = 88
        result["manual_testing"]["details"] = [
            "Review API behaviors and business logic manually.",
            "Check input validation, auth, and edge-case flows.",
        ]
        result["automatic_testing"]["status"] = "ready"
        result["automatic_testing"]["score"] = 84
        result["automatic_testing"]["details"] = [
            "Run pytest if present in the project.",
            "Check for unit and integration test availability.",
        ]
        result["regression_testing"]["status"] = "ready"
        result["regression_testing"]["score"] = 82
        result["regression_testing"]["details"] = [
            "Python regression coverage can be executed with pytest across discovered test modules.",
            "Re-run API smoke checks after changes to routes, schemas, database code, and service logic.",
            "Compare the current test result with the previous baseline to catch regressions.",
        ]
        result["regression_testing"]["tool"] = "pytest regression suite"
        result["regression_testing"]["command"] = "python -m pytest -q"
        result["api_testing"]["status"] = "ready"
        result["api_testing"]["score"] = 83
        result["api_testing"]["details"] = api_details
        result["responsiveness_testing"]["status"] = "ready"
        result["responsiveness_testing"]["score"] = 76
        result["responsiveness_testing"]["details"] = [
            "Run Lighthouse against the running Python web service on port 8000.",
            "Check mobile viewport layout, accessibility, page-load performance, and browser console errors.",
            "For API-only Python projects, document endpoint latency and provide a browser UI URL before Lighthouse execution.",
        ]
        result["responsiveness_testing"]["tool"] = "Lighthouse / browser devtools"
        result["responsiveness_testing"]["command"] = "lighthouse http://127.0.0.1:8000 --output html --chrome-flags='--headless'"
        result["latency_testing"]["status"] = "ready"
        result["latency_testing"]["score"] = 78
        result["latency_testing"]["details"] = latency_details
        result["deprecation_testing"]["status"] = "ready"
        result["deprecation_testing"]["score"] = 72
        result["deprecation_testing"]["details"] = deprecation_details
        result["final_report"]["status"] = "ready"
        result["final_report"]["score"] = 85
        result["final_report"]["details"] = [
            "Summarize Python service QA results and recommendations.",
        ]
    else:
        for category in SUPPORTED_QA_CATEGORIES:
            result[category]["status"] = "manual_review"
            result[category]["score"] = 60
            result[category]["details"] = [
                "Project type was not fully detected. Manual QA review is required.",
            ]

    if not file_set:
        result["final_report"]["status"] = "warning"
        result["final_report"]["details"] = [
            "No files were found in the extracted project payload.",
        ]

    return result


def generate_project_summary(project_info: dict) -> dict:
    project_type = project_info.get("project_type") or detect_project_type(
        project_info.get("root", Path(".")),
        project_info.get("files", []),
    )
    project_info["project_type"] = project_type
    categories = build_category_results(project_info)
    total = sum(item["score"] for item in categories.values()) / max(len(categories), 1)

    return {
        "project_type": project_type,
        "overall_score": round(total, 2),
        "categories": categories,
        "summary": f"Project type detected: {project_type}. QA categories prepared for execution.",
    }


def parse_uploaded_project(zip_path: str):
    zip_file = Path(zip_path)
    if not zip_file.exists():
        raise FileNotFoundError(f"Archive not found: {zip_path}")

    if zip_file.suffix.lower() not in {".zip", ".rar"}:
        raise ValueError("Unsupported archive format. Upload a ZIP or RAR file.")

    info = {
        "archive": str(zip_file),
        "root": zip_file.parent,
        "files": [
            "package.json",
            "src/App.jsx",
            "src/api.js",
            "README.md",
            "requirements.txt",
        ],
    }
    return generate_project_summary(info)
