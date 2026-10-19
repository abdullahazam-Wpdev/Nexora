"""Exact unique replacements: no fuzzy edits or paths outside declared scope."""

import json


def apply_edits(original, raw):
    spec = json.loads(raw) if isinstance(raw, str) else raw
    if (
        not isinstance(spec, dict)
        or set(spec) != {"edits"}
        or not isinstance(spec["edits"], list)
        or not 1 <= len(spec["edits"]) <= 8
    ):
        raise ValueError("Expected 1..8 exact edits")
    changed = {}
    for edit in spec["edits"]:
        if not isinstance(edit, dict) or set(edit) != {"path", "old", "new"}:
            raise ValueError("Each edit requires only path, old, new")
        path, old, new = (edit[k] for k in ("path", "old", "new"))
        if (
            path not in original
            or not isinstance(old, str)
            or not old
            or not isinstance(new, str)
        ):
            raise ValueError("Invalid scope or replacement")
        text = changed.get(path, original[path])
        if text.count(old) != 1:
            raise ValueError("Replacement anchor must match exactly once")
        if old == new:
            raise ValueError("Replacement makes no change")
        changed[path] = text.replace(old, new, 1)
    return changed
