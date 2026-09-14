from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def detect_project(root: Path, files: list[str]) -> dict[str, Any]:
    normalized = [Path(name).as_posix() for name in files]
    lower_files = {name.lower() for name in normalized}
    languages: set[str] = set()
    frameworks: set[str] = set()
    dependency_files: list[str] = []
    test_directories = sorted({str(Path(name).parent) for name in normalized if "test" in name.lower()})
    entry_points: list[str] = []

    extension_languages = {
        ".py": "python", ".js": "javascript", ".jsx": "javascript", ".ts": "typescript",
        ".tsx": "typescript", ".java": "java", ".cs": "csharp", ".php": "php",
        ".go": "go", ".rs": "rust", ".cpp": "cpp", ".c": "c", ".html": "html",
        ".css": "css", ".sql": "sql",
    }
    for name in normalized:
        language = extension_languages.get(Path(name).suffix.lower())
        if language:
            languages.add(language)
        if Path(name).name.lower() in {
            "requirements.txt", "pyproject.toml", "setup.py", "pipfile", "package.json",
            "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "pom.xml", "build.gradle",
            "composer.json",
        }:
            dependency_files.append(name)

    def read_text(name: str) -> str:
        path = root / name
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ""

    manifest_text = "\n".join(read_text(name) for name in dependency_files)
    lower_manifest = manifest_text.lower()
    if "react" in lower_manifest:
        frameworks.add("react")
    if "vite" in lower_manifest:
        frameworks.add("vite")
    if "next" in lower_manifest:
        frameworks.add("next")
    if "fastapi" in lower_manifest:
        frameworks.add("fastapi")
    if "flask" in lower_manifest:
        frameworks.add("flask")
    if "django" in lower_manifest or "manage.py" in lower_files:
        frameworks.add("django")
    if "express" in lower_manifest:
        frameworks.add("express")

    for candidate in ("main.py", "app.py", "manage.py", "server.js", "index.js", "src/main.jsx", "src/main.tsx"):
        if candidate.lower() in lower_files:
            entry_points.append(candidate)

    if "frontend" in lower_files or "react" in frameworks:
        project_type = "react"
    elif "fastapi" in frameworks or "flask" in frameworks or "django" in frameworks or "python" in languages:
        project_type = "python"
    elif "java" in languages:
        project_type = "java"
    elif "csharp" in languages:
        project_type = "dotnet"
    elif "javascript" in languages or "typescript" in languages:
        project_type = "node"
    else:
        project_type = "generic"

    return {
        "languages": sorted(languages),
        "frameworks": sorted(frameworks),
        "project_type": project_type,
        "entry_points": entry_points,
        "dependency_files": sorted(set(dependency_files)),
        "test_directories": test_directories,
    }