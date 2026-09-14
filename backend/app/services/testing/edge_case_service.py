from __future__ import annotations

from typing import Any


def generate_edge_cases() -> dict[str, Any]:
    cases = {
        "numeric": [0, 1, -1, 2**31 - 1, 2**31, 0.1],
        "strings": ["", " ", "a" * 500, "<script>", "' OR 1=1 --", "unicode-\u2603", "line\nfeed"],
        "collections": [[], [None], [1], [1, 1], [[1, 2]]],
        "optional": [None, {}, {"missing": True}],
    }
    total = sum(len(values) for values in cases.values())
    return {"status": "completed", "findings": [{"category": "edge", "input_family": name, "test_cases": values} for name, values in cases.items()], "summary": {"total": total}, "errors": []}