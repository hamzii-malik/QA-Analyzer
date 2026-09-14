from __future__ import annotations

from app.core.config import settings


def generate_fuzz_cases() -> dict:
    limit = max(0, settings.FUZZ_CASES)
    length = max(1, settings.FUZZ_MAX_STRING_LENGTH)
    seeds = ["", " ", "' OR 1=1 --", "<script>alert(1)</script>", "\u2603", "\n\t"]
    cases = [{"type": "string", "value": seed[:length]} for seed in seeds[:limit]]
    if len(cases) < limit:
        cases.extend({"type": "number", "value": value} for value in [0, -1, 1, 2**31, 10**100][: limit - len(cases)])
    return {"status": "completed", "executed": False, "findings": [], "test_cases": cases[:limit], "summary": {"total": len(cases[:limit]), "crashes": 0}, "errors": ["Generated only; uploaded code is not executed automatically."]}