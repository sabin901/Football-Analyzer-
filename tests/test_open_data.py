import copy
import json
from pathlib import Path
import sys
import unittest
from datetime import date, timedelta, datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from open_policy import validate_public, provenance, WORKBENCH, RESULTS
from open_events import point, progress
from open_results import quality
from forecast_lab import publication_gate, losses, evaluate
from forecast_benchmarks import Challengers
from workbench_data import playing_position, aggregate_players


class OpenDataTests(unittest.TestCase):
    def test_license_gate_fails_closed(self):
        for value in [
            {},
            {"source_id": "espn", "license": "CC0-1.0"},
            {
                **provenance("openfootball"),
                "source_url": "https://example.org",
                "source_sha256": "x",
                "matches": [{"result_source": "ESPN"}],
            },
        ]:
            with self.assertRaises(ValueError):
                validate_public(value)

    def test_coordinate_boundary_and_progression(self):
        self.assertEqual(point({"positions": [{"x": 100, "y": 100}]}), (120, 80))
        self.assertIsNone(point({"positions": [{"x": float("nan"), "y": 0}]}))
        self.assertIsNone(point({"positions": [{"x": 101, "y": 0}]}))
        self.assertTrue(progress({"positions": [{"x": 40, "y": 50}, {"x": 70, "y": 50}]}))
        self.assertFalse(progress({"positions": [{"x": 70, "y": 50}, {"x": 40, "y": 50}]}))

    def test_substitute_is_participation_not_position(self):
        self.assertIsNone(playing_position("Substitute"))
        self.assertIsNone(playing_position(" Bench "))
        match = {
            "teams": [{"id": "t", "name": "Team"}],
            "players": [
                {
                    "id": "p",
                    "team_id": "t",
                    "name": "Player",
                    "position": "Substitute",
                    "starter": False,
                    "stats": {"appearances": 1},
                }
            ],
        }
        second = copy.deepcopy(match)
        second["players"][0]["position"] = "Forward"
        self.assertEqual(aggregate_players([match, second], [])[0]["position"], "Forward")

    def test_open_forecast_gate_rejects_missing_and_modified_inputs(self):
        raw = json.loads((RESULTS / "dashboard_PL_2026-27.json").read_text())
        raw["fetched_at"] = "2026-10-18T12:00:00+00:00"
        q = quality(raw)
        now = datetime(2026, 10, 18, 13, tzinfo=timezone.utc)
        raw["expected_fixtures"] = len(raw["matches"])
        q["results"]["past_missing"] = 0
        raw["quarantined"] = []
        self.assertTrue(publication_gate(raw, q, now)["allowed"])
        q["results"]["past_missing"] = 1
        self.assertFalse(publication_gate(raw, q, now)["allowed"])
        q["results"]["past_missing"] = 0
        raw["matches"][0]["hg"] = 99
        self.assertFalse(publication_gate(raw, q, now)["allowed"])

    def test_challengers_cannot_see_future_or_same_day_results(self):
        rows = [
            {
                "home": f"T{i%4}",
                "away": f"T{(i+1)%4}",
                "hg": i % 3,
                "ag": i % 2,
                "date": (date(2024, 1, 1) + timedelta(days=i)).isoformat(),
            }
            for i in range(160)
        ]
        fixture = {"home": "T0", "away": "T1"}
        cutoff = "2024-06-01"
        a = Challengers(rows).predict(fixture, cutoff)
        changed = [{**m, "hg": 90, "ag": 0} if m["date"] >= cutoff else m for m in rows]
        b = Challengers(changed).predict(fixture, cutoff)
        self.assertEqual(a, b)
        self.assertLess(a["challenger_training_end"], cutoff)
        self.assertAlmostEqual(sum(a["elo"]), 1)
        self.assertAlmostEqual(sum(a["fitted_poisson"]), 1)

    def test_equal_probability_classification_does_not_favor_home(self):
        for actual in range(3):
            self.assertAlmostEqual(losses([1 / 3] * 3, actual)["accuracy"], 1 / 3)

    def test_public_archive_has_no_invented_xg_or_current_squads(self):
        sets = json.loads((WORKBENCH / "events_manifest.json").read_text())["sets"]
        self.assertEqual(sum(s["imported_matches"] for s in sets), 1826)
        self.assertEqual(sum(s["events"] for s in sets), 3071395)
        for league in ("PL", "PD", "SA", "BL1", "FL1"):
            d = validate_public(json.loads((WORKBENCH / f"current_{league}.json").read_text()))
            self.assertTrue(d["historical"])
            self.assertEqual(d["season"], "2017/2018")
            self.assertNotIn("Substitute", {p["position"] for p in d["players"]})
        for file in WORKBENCH.glob("backtest_*.json"):
            for r in json.loads(file.read_text())["records"]:
                self.assertLess(r["challenger_training_end"], r["date"])
                self.assertAlmostEqual(sum(r["fitted_poisson"]), 1)
