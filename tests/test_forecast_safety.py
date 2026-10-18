"""Incomplete schedules must not masquerade as full-season probabilities."""

from datetime import date, timedelta
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from forecast_lab import forecast, season_scenarios


class ForecastSafetyTests(unittest.TestCase):
    def history(self):
        return [
            {
                "home": "A" if i % 2 else "B",
                "away": "B" if i % 2 else "A",
                "hg": i % 3,
                "ag": i % 2,
                "date": (date(2025, 1, 1) + timedelta(days=i)).isoformat(),
            }
            for i in range(60)
        ]

    def test_unresolved_fixture_withholds_rank_probabilities(self):
        history = self.history()
        future = {"home": "A", "away": "B", "hg": None, "ag": None, "date": "2025-04-01"}
        missing = {**future, "home": "B", "away": "A", "date": "2025-03-10"}
        result = season_scenarios({"matches": history + [future, missing]}, history, "2025-03-15")
        self.assertEqual(result["simulated_fixtures"], 1)
        self.assertEqual(result["omitted_fixtures"], 1)
        self.assertFalse(result["complete_schedule"])
        self.assertTrue(all(t["first"] is None and t["top_four"] is None for t in result["teams"]))

    def test_complete_schedule_is_reproducible_and_ranks_sum_to_one(self):
        history = self.history()
        snapshot = {
            "matches": history
            + [{"home": "A", "away": "B", "hg": None, "ag": None, "date": "2025-04-01"}]
        }
        result = season_scenarios(snapshot, history, "2025-03-15")
        self.assertEqual(result, season_scenarios(snapshot, history, "2025-03-15"))
        self.assertTrue(result["complete_schedule"])
        self.assertAlmostEqual(sum(t["first"] for t in result["teams"]), 1)

    def test_new_teams_have_explicit_prior_and_limited_sample(self):
        p = forecast(
            self.history(), {"home": "New", "away": "B", "date": "2025-03-16"}, "2025-03-15"
        )
        self.assertEqual(p["sample_status"], "limited")
        self.assertEqual(p["home_sample"], 0)
        self.assertEqual(p["prior_weight_home"], 1)
        self.assertAlmostEqual(sum(p["probabilities"]), 1)
