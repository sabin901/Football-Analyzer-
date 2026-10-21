"""Provider contract tests use synthetic fixtures; never require a key or network."""

import copy
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from current_provider import normalize, display_snapshot, upcoming_overlay
from forecast_lab import score_summary, probabilities


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.league = {"id": "PL", "teams": 2}
        self.now = "2026-10-20T20:00:00+00:00"
        season = {"startDate": "2026-08-01"}
        self.fixtures = {
            "competition": {"code": "PL"},
            "matches": [
                {
                    "id": 1,
                    "competition": {"code": "PL"},
                    "season": season,
                    "homeTeam": {"id": 1},
                    "awayTeam": {"id": 2},
                    "utcDate": "2026-10-19T15:00:00Z",
                    "status": "FINISHED",
                    "score": {"fullTime": {"home": 2, "away": 1}},
                    "matchday": 1,
                },
                {
                    "id": 2,
                    "competition": {"code": "PL"},
                    "season": season,
                    "homeTeam": {"id": 2},
                    "awayTeam": {"id": 1},
                    "utcDate": "2026-10-25T15:00:00Z",
                    "status": "TIMED",
                    "score": {"fullTime": {"home": None, "away": None}},
                    "matchday": 2,
                },
            ],
        }
        self.table = {
            "competition": {"code": "PL"},
            "season": season,
            "standings": [
                {
                    "type": "TOTAL",
                    "table": [
                        {
                            "team": {"id": 1, "name": "Alpha"},
                            "position": 1,
                            "playedGames": 1,
                            "won": 1,
                            "draw": 0,
                            "lost": 0,
                            "goalsFor": 2,
                            "goalsAgainst": 1,
                            "points": 3,
                        },
                        {
                            "team": {"id": 2, "name": "Beta"},
                            "position": 2,
                            "playedGames": 1,
                            "won": 0,
                            "draw": 0,
                            "lost": 1,
                            "goalsFor": 1,
                            "goalsAgainst": 2,
                            "points": 0,
                        },
                    ],
                }
            ],
        }

    def convert(self):
        return normalize(self.fixtures, self.table, self.league, "2026-27", self.now)

    def test_table_reconciles_and_incomplete_scores_remain_null(self):
        d = self.convert()
        s = display_snapshot(d)
        self.assertEqual(s["quality"]["standings"]["status"], "matched")
        self.assertEqual(s["table"][0]["team"], "Alpha")
        self.assertIsNone(s["matches"][1]["hg"])
        self.assertEqual(s["source_id"], "football_data_org")
        self.assertEqual(s["license"], "provider-terms")

    def test_wrong_season_duplicate_and_partial_scores_rejected(self):
        for kind in ("season", "duplicate", "score", "competition"):
            fixtures = copy.deepcopy(self.fixtures)
            if kind == "season":
                fixtures["matches"][0]["season"] = {"startDate": "2025-08-01"}
            if kind == "duplicate":
                fixtures["matches"].append(fixtures["matches"][0])
            if kind == "score":
                fixtures["matches"][0]["score"]["fullTime"]["away"] = None
            if kind == "competition":
                fixtures["matches"][0]["competition"]["code"] = "PD"
            with self.assertRaises(ValueError):
                normalize(fixtures, self.table, self.league, "2026-27", self.now)

    def test_table_disagreement_never_claims_reconciliation(self):
        self.table["standings"][0]["table"][0]["goalsFor"] = 3
        d = self.convert()
        self.assertEqual(d["quality"]["standings"]["status"], "mismatch")
        self.assertFalse(upcoming_overlay({}, d, [])["publication"]["allowed"])

    def test_live_score_not_treated_as_final(self):
        self.fixtures["matches"][0]["status"] = "IN_PLAY"
        d = self.convert()
        self.assertIsNone(d["matches"][0]["hg"])
        self.assertEqual(d["matches"][0]["status"], "in_play")

    def test_score_distribution_is_complete_and_symmetric(self):
        d = score_summary(1.5, 1.5)
        self.assertAlmostEqual(
            sum(s["probability"] for s in d["scorelines"]) + d["other_scorelines"], 1
        )
        p = probabilities(1.5, 1.5)
        self.assertAlmostEqual(p[0], p[2])
        self.assertAlmostEqual(sum(p), 1)
        self.assertTrue(0 < d["both_score"] < 1)
        for rate in (float("nan"), float("inf"), -1, 0, 21):
            with self.assertRaises(ValueError):
                probabilities(rate, 1)

    def test_omitted_status_is_rejected(self):
        self.fixtures["matches"][0]["status"] = "UNKNOWN"
        with self.assertRaises(ValueError):
            self.convert()
