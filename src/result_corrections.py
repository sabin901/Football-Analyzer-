"""Reviewed source corrections with previous values and supporting URLs."""

import json
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[1] / "data/live/result_corrections.json"


def apply_corrections(payload):
    if not REGISTRY.exists():
        return payload
    rows = json.loads(REGISTRY.read_text(encoding="utf-8"))["corrections"]
    matches = {(m["home"], m["away"]): m for m in payload["matches"]}
    for item in rows:
        if (item["league"], item["season"]) != (payload["league"], payload["season"]):
            continue
        match = matches.get((item["home"], item["away"]))
        if match is None:
            raise ValueError("Reviewed fixture is missing from the source schedule")
        values = {k: match.get(k) for k in item["before"]}
        expected_after = {k: item["after"].get(k, match.get(k)) for k in item["before"]}
        if values != item["before"] and values != expected_after:
            raise ValueError("Reviewed fixture changed upstream; manual review required")
        match.update(item["after"])
        match["result_review"] = {k: item[k] for k in ("reason", "sources", "reviewed_at")}
        if "reference_result" in item:
            match["result_review"]["reference_result"] = item["reference_result"]
    payload["matches"].sort(key=lambda m: (m.get("date") or "9999", m["home"]))
    return payload
