import re
from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".cpp",
    ".c",
    ".cs",
    ".php",
    ".go",
    ".rs",
    ".html",
    ".css",
    ".sql",
}


def analyze_content(content: str) -> dict:
    issues = []
    suggestions = []

    lines = content.splitlines()

    if not content.strip():
        issues.append("File/content is empty.")

    if len(content) < 50:
        issues.append(
            "Content is very short and may not contain enough information for QA analysis."
        )

    upper_content = content.upper()
    lower_content = content.lower()

    if "TODO" in upper_content:
        issues.append("TODO items were found.")
        suggestions.append(
            "Complete all TODO items before final testing."
        )

    if "FIXME" in upper_content:
        issues.append("FIXME markers were found.")
        suggestions.append(
            "Review and resolve FIXME items."
        )

    if re.search(r"(password|passwd|pwd)\s*=", lower_content):
        issues.append(
            "Possible hardcoded password detected."
        )
        suggestions.append(
            "Move passwords to environment variables or a secrets manager."
        )

    if re.search(
        r"(api[_-]?key|secret[_-]?key)\s*=",
        lower_content,
    ):
        issues.append(
            "Possible hardcoded API key or secret detected."
        )
        suggestions.append(
            "Use environment variables instead of hardcoding secrets."
        )

    long_lines = [
        index + 1
        for index, line in enumerate(lines)
        if len(line) > 120
    ]

    if long_lines:
        issues.append(
            f"{len(long_lines)} line(s) exceed 120 characters."
        )
        suggestions.append(
            "Consider breaking long lines into smaller statements."
        )

    return {
        "summary": {
            "total_lines": len(lines),
            "total_characters": len(content),
            "issues_found": len(issues),
        },
        "issues": issues,
        "suggestions": suggestions,
        "status": "completed",
    }


def analyze_file(file_path: str) -> dict:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {path.suffix}"
        )

    content = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    result = analyze_content(content)

    result["file"] = {
        "name": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": path.stat().st_size,
    }

    return result
