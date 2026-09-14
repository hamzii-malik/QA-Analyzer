from __future__ import annotations

from pathlib import Path
from typing import Any


def detect_runtime(root: Path, files: list[str], frameworks: list[str] | None = None) -> dict[str, Any]:
    frameworks = frameworks or []
    normalized = {Path(name).as_posix().lower() for name in files}
    entry_points = [name for name in ("main.py", "app.py", "manage.py", "server.js", "index.js") if name in normalized]
    commands: list[str] = []
    if "fastapi" in frameworks:
        commands.append("uvicorn main:app --host 127.0.0.1 --port 0")
    elif "flask" in frameworks:
        commands.append("python app.py")
    elif "react" in frameworks or "express" in frameworks:
        commands.append("npm run dev")
    return {"status": "ready" if entry_points or commands else "skipped", "entry_points": entry_points, "allowed_commands": commands, "executed": False, "errors": []}