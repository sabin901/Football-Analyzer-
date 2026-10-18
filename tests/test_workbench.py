import json
import sys
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_data import stat_map, aggregate_players, parse_summary
from event_workbench import summarize, aggregate, progressive
from forecast_lab import forecast, evaluate, losses, probabilities
from app import app


class WorkbenchTests(unittest.TestCase):
    def test_missing_stats_are_not_zero_and_zero_is_preserved(self):
        self.assertEqual(
            stat_map([{"name": "goals", "value": 0}, {"name": "minutes", "displayValue": "—"}]),
            {"goals": 0.0, "minutes": None},
        )
        matches = [
            {
                "teams": [{"id": "1", "name": "Club"}],
                "players": [
                    {
                        "id": "7",
                        "name": "A",
                        "team_id": "1",
                        "position": "Forward",
                        "starter": True,
                        "stats": {"appearances": 1, "totalGoals": 0, "totalShots": None},
                    }
                ],
            }
        ]
        p = aggregate_players(matches, [])[0]
        self.assertEqual(p["matches"], 1)
        self.assertEqual(p["stats"]["totalGoals"], 0)
        self.assertNotIn("totalShots", p["stats"])
        self.assertEqual(p["stat_samples"]["totalGoals"], 1)

    def test_same_name_different_ids_and_transfer_clubs_stay_separate(self):
        squads = [
            {
                "id": "1",
                "name": "Club",
                "players": [{"id": "7", "name": "A"}, {"id": "8", "name": "A"}],
            },
            {"id": "2", "name": "Other", "players": [{"id": "7", "name": "A"}]},
        ]
        self.assertEqual(len(aggregate_players([], squads)), 3)

    def test_summary_rejects_wrong_season_and_identity(self):
        with self.assertRaises(ValueError):
            parse_summary({"header": {"id": "1", "season": {"year": 2025}}}, "1", "2026-27")
        with self.assertRaises(ValueError):
            parse_summary({"header": {"id": "2", "season": {"year": 2026}}}, "1", "2026-27")

    def test_dismissal_substitution_minutes_and_penalty_exclusion(self):
        team = {"id": 1, "name": "A"}
        events = []

        def add(kind, minute=0, **kw):
            events.append(
                {
                    "id": str(len(events)),
                    "index": len(events),
                    "type": {"name": kind},
                    "minute": minute,
                    "team": team,
                    "period": 1,
                    **kw,
                }
            )

        add(
            "Starting XI",
            tactics={
                "lineup": [
                    {
                        "player": {"id": 1, "name": "Starter"},
                        "position": {"name": "Center Midfield"},
                    },
                    {"player": {"id": 3, "name": "Dismissed"}, "position": {"name": "Right Back"}},
                ]
            },
        )
        add(
            "Substitution",
            60,
            player={"id": 1, "name": "Starter"},
            substitution={"replacement": {"id": 2, "name": "Sub"}},
        )
        add(
            "Bad Behaviour",
            70,
            player={"id": 3, "name": "Dismissed"},
            bad_behaviour={"card": {"name": "Red Card"}},
        )
        add(
            "Shot",
            80,
            player={"id": 2, "name": "Sub"},
            location=[108, 40],
            shot={"type": {"name": "Penalty"}, "statsbomb_xg": 0.78, "outcome": {"name": "Goal"}},
        )
        add("Half End", 95)
        match = {
            "match_id": 1,
            "match_date": "2020-01-01",
            "home_team": {"home_team_name": "A", "home_team_id": 1},
            "away_team": {"away_team_name": "B", "away_team_id": 2},
            "home_score": 1,
            "away_score": 0,
        }
        summary = summarize(events, match)
        p = {r["id"]: r for r in summary["players"]}
        self.assertEqual([p[i]["minutes"] for i in (1, 2, 3)], [60, 30, 70])
        self.assertEqual(p[2]["npxg"], 0)
        self.assertEqual(summary["shots"][0]["xg"], 0.78)
        self.assertEqual(aggregate([summary])[0]["minutes"], 70)
        with self.assertRaises(ValueError):
            summarize(events + [events[-1]], match)

    def test_progression_definition(self):
        self.assertTrue(progressive([60, 40], [80, 40]))
        self.assertFalse(progressive([30, 40], [50, 40]))
        self.assertFalse(progressive([90, 40], [80, 40]))

    def test_no_same_day_or_future_training_leakage(self):
        history = [
            {"date": f"2025-01-{i%28+1:02d}", "home": "A", "away": "B", "hg": i % 4, "ag": i % 3}
            for i in range(60)
        ]
        fixture = {"date": "2025-02-01", "home": "A", "away": "B"}
        p = forecast(history, fixture, "2025-02-01")
        contaminated = history + [
            {"date": "2025-02-01", "home": "A", "away": "B", "hg": 99, "ag": 99},
            {"date": "2025-02-02", "home": "A", "away": "B", "hg": 99, "ag": 99},
        ]
        self.assertEqual(p, forecast(contaminated, fixture, "2025-02-01"))
        self.assertLess(p["training_end"], p["cutoff_exclusive"])
        self.assertAlmostEqual(sum(p["probabilities"]), 1)
        unseen = forecast(history, {"date": "2025-02-01", "home": "New", "away": "B"}, "2025-02-01")
        self.assertEqual(unseen["home_sample"], 0)
        self.assertIsNotNone(unseen)

    def test_proper_score_direction_and_symmetry(self):
        self.assertLess(
            losses([0.8, 0.1, 0.1], 0)["log_loss"], losses([0.1, 0.8, 0.1], 0)["log_loss"]
        )
        self.assertEqual(losses([1, 0, 0], 0)["brier"], 0)
        p = probabilities(1.5, 1.5)
        self.assertAlmostEqual(p[0], p[2])
        self.assertAlmostEqual(sum(p), 1)

    def test_workbench_api_input_bounds_and_pagination(self):
        client = TestClient(app)
        self.assertEqual(client.get("/api/workbench/players/PL?limit=201").status_code, 422)
        self.assertEqual(client.get("/api/workbench/players/PL?offset=-1").status_code, 422)
        self.assertEqual(client.get("/api/workbench/current/not-a-league").status_code, 400)
        r = client.get("/api/workbench/players/PL?limit=2").json()
        self.assertEqual(len(r["players"]), 2)
        self.assertGreater(r["total"], 2)
        self.assertEqual(client.get("/api/workbench/event-match/-1").status_code, 400)


class WorkbenchDataTests(unittest.TestCase):
    def test_imported_current_identity_and_coverage(self):
        for path in (ROOT / "data/open/workbench").glob("current_*.json"):
            d = json.loads(path.read_text(encoding="utf8"))
            self.assertEqual(d["coverage"]["squads"], d["coverage"]["expected_teams"])
            self.assertEqual(len({m["id"] for m in d["matches"]}), len(d["matches"]))
            self.assertEqual(
                len({(p["id"], p["team_id"]) for p in d["players"]}), len(d["players"])
            )
            for p in d["players"]:
                self.assertLessEqual(p["starts"], p["matches"])
                self.assertTrue(all(n <= p["matches"] for n in p["stat_samples"].values()))

    def test_backtest_audit_is_before_fixture(self):
        for path in (ROOT / "data/open/workbench").glob("backtest_*.json"):
            d = json.loads(path.read_text(encoding="utf8"))
            for r in d["records"]:
                self.assertLess(r["training_end"], r["date"])
                self.assertEqual(r["date"], r["cutoff_exclusive"])
                self.assertAlmostEqual(sum(r["probabilities"]), 1)

    def test_event_catalogue_matches_detail_files(self):
        path = ROOT / "data/open/workbench/events_manifest.json"
        d = json.loads(path.read_text(encoding="utf8"))
        for s in d["sets"]:
            data = json.loads((path.parent / f"events_{s['key']}.json").read_text(encoding="utf8"))
            self.assertEqual(len(data["matches"]), s["imported_matches"])
            for m in data["matches"]:
                self.assertTrue((path.parent / "event_matches" / f"{m['id']}.json").exists())

    def test_all_shots_have_valid_probabilities_and_provider_coordinates(self):
        for path in (ROOT / "data/open/workbench/event_matches").glob("*.json"):
            d = json.loads(path.read_text(encoding="utf8"))
            self.assertEqual(len({p["id"] for p in d["players"]}), len(d["players"]))
            for p in d["players"]:
                self.assertGreaterEqual(p["minutes"], 0)
            for s in d["shots"]:
                self.assertTrue(-1 <= s["x"] <= 121 and -1 <= s["y"] <= 81)
                self.assertIsNone(s["xg"])


if __name__ == "__main__":
    unittest.main()
