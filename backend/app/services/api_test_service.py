from __future__ import annotations

import re
from pathlib import Path
from typing import Any


ROUTE_PATTERN = re.compile(r"@(app|router)\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)")


def discover_api_endpoints(root: Path, files: list[str]) -> dict[str, Any]:
    endpoints: list[dict[str, Any]] = []
    for file_name in files:
        if Path(file_name).suffix.lower() not in {".py", ".js", ".ts", ".jsx", ".tsx"}:
            continue
        try:
            text = (root / file_name).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in ROUTE_PATTERN.finditer(text):
            endpoints.append({"method": match.group(2).upper(), "path": match.group(3), "file": file_name, "tested": False, "reason": "Endpoint discovered; runtime target is not started automatically."})
    return {"status": "completed", "tool": "API endpoint discovery", "endpoints": endpoints, "findings": [], "summary": {"total": len(endpoints), "tested": 0, "untested": len(endpoints)}, "errors": []}