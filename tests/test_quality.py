"""Source disagreement must never be presented as verified sporting truth."""

import copy
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from club_identity import resolver, club_key
from dashboard_data import standings, read_json, LIVE
from data_quality import (
    parse_standings,
    compare_results,
    quality_for,
    results_digest,
    apply_standings,
)
from forecast_lab import publication_gate, update_forecast_log
from result_corrections import apply_corrections


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "league": "PL",
            "season": "2023-24",
            "matches": [
                {"date": "2023-08-12", "home": "Everton FC", "away": "Arsenal FC", "hg": 1, "ag": 0}
            ],
        }
        fields = {
            "p": "gamesPlayed",
            "w": "wins",
            "d": "ties",
            "l": "losses",
            "gf": "pointsFor",
            "ga": "pointsAgainst",
            "pts": "points",
            "rank": "rank",
        }
        rows = standings(self.snapshot["matches"])
        entries = []
        for i, row in enumerate(rows):
            row["rank"] = 2 - i
            if row["team"] == "Everton FC":
                row["pts"] = 0
            entries.append(
                {
                    "team": {"id": str(i + 1), "displayName": row["team"]},
                    "stats": [
                        {"name": source, "value": row[key]} for key, source in fields.items()
                    ],
                }
            )
        self.raw = {
            "season": {"year": 2023},
            "children": [{"standings": {"season": 2023, "name": "overall", "entries": entries}}],
        }

    def test_provider_points_and_order_survive_result_reconciliation(self):
        q = {"standings": parse_standings(self.raw, self.snapshot)}
        rows = apply_standings(self.snapshot, q)
        self.assertEqual(q["standings"]["status"], "matched")
        self.assertEqual(rows[0]["team"], "Arsenal FC")
        self.assertEqual(rows[1]["pts"], 0)
        self.assertEqual(rows[1]["match_points"], 3)
        self.assertEqual(rows[1]["adjustment"], -3)
        self.assertEqual(standings(self.snapshot["matches"])[0]["pts"], 3)

    def test_wrong_season_unknown_club_and_incomplete_table_rejected(self):
        for mutate in [
            lambda d: d["season"].update(year=2024),
            lambda d: d["children"][0]["standings"]["entries"][0]["team"].update(
                displayName="Unknown United"
            ),
            lambda d: d["children"][0]["standings"]["entries"].pop(),
        ]:
            raw = copy.deepcopy(self.raw)
            mutate(raw)
            with self.assertRaises(ValueError):
                parse_standings(raw, self.snapshot)

    def test_aggregate_disagreement_does_not_override_result_table(self):
        raw = copy.deepcopy(self.raw)
        next(
            s
            for s in raw["children"][0]["standings"]["entries"][0]["stats"]
            if s["name"] == "pointsFor"
        )["value"] = 9
        q = {"standings": parse_standings(raw, self.snapshot)}
        self.assertEqual(q["standings"]["status"], "mismatch")
        self.assertEqual(apply_standings(self.snapshot, q), standings(self.snapshot["matches"]))

    def test_result_scores_dates_and_missing_records_checked_without_mutation(self):
        original = copy.deepcopy(self.snapshot)
        prefix = "Date,HomeTeam,AwayTeam,FTHG,FTAG\n"
        self.assertEqual(
            compare_results(prefix + "12/08/2023,Everton,Arsenal,1,0\n", self.snapshot)["status"],
            "matched",
        )
        for row in ["12/08/2023,Everton,Arsenal,2,0\n", "13/08/2023,Everton,Arsenal,1,0\n"]:
            self.assertEqual(compare_results(prefix + row, self.snapshot)["status"], "conflict")
        self.assertEqual(compare_results(prefix, self.snapshot)["status"], "partial")
        self.assertEqual(self.snapshot, original)
        with self.assertRaises(ValueError):
            compare_results(prefix + "12/08/2023,Fake United,Arsenal,1,0\n", self.snapshot)

    def test_old_verification_does_not_apply_to_changed_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "quality_PL_2023-24.json"
            p.write_text(
                json.dumps(
                    {
                        "results_digest": results_digest(self.snapshot["matches"]),
                        "standings": {"status": "matched"},
                    }
                )
            )
            self.assertEqual(
                quality_for(self.snapshot, Path(tmp))["standings"]["status"], "matched"
            )
            self.snapshot["matches"][0]["hg"] = 2
            self.assertEqual(
                quality_for(self.snapshot, Path(tmp))["standings"]["status"], "unavailable"
            )

    def test_identity_mapping_is_explicit_and_unambiguous(self):
        self.assertEqual(club_key("Inter"), club_key("FC Internazionale Milano"))
        self.assertEqual(resolver(["Everton FC"])("Everton"), "Everton FC")
        self.assertIsNone(resolver(["Everton FC"])("Everton United"))
        with self.assertRaises(ValueError):
            resolver(["Inter", "FC Internazionale Milano"])

    def test_reviewed_correction_is_idempotent_and_refuses_new_source_values(self):
        case = {
            "league": "PL",
            "season": "2023-24",
            "home": "Everton FC",
            "away": "Arsenal FC",
            "before": {"hg": 1},
            "after": {"hg": 2},
            "reason": "review",
            "sources": ["https://example.com/evidence"],
            "reviewed_at": "2026-10-18",
        }
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "corrections.json"
            registry.write_text(json.dumps({"corrections": [case]}))
            with patch("result_corrections.REGISTRY", registry):
                output = apply_corrections(copy.deepcopy(self.snapshot))
                self.assertEqual(output, apply_corrections(copy.deepcopy(output)))
                output["matches"][0]["hg"] = 5
                with self.assertRaises(ValueError):
                    apply_corrections(output)

    def test_awarded_result_keeps_goals_separate_from_outcome(self):
        match = {
            "home": "Bastia",
            "away": "Lyon",
            "date": "2017-04-16",
            "hg": 0,
            "ag": 0,
            "awarded_winner": "Lyon",
        }
        table = {r["team"]: r for r in standings([match])}
        self.assertEqual((table["Lyon"]["w"], table["Lyon"]["gf"], table["Lyon"]["pts"]), (1, 0, 3))
        self.assertEqual((table["Bastia"]["l"], table["Bastia"]["ga"]), (1, 0))

    def test_probability_publication_requires_current_reconciled_inputs(self):
        now = datetime(2026, 10, 18, tzinfo=timezone.utc)
        snapshot = {"fetched_at": now.isoformat()}
        quality = {
            "checked_at": now.isoformat(),
            "standings": {"status": "matched"},
            "results": {"status": "matched"},
        }
        self.assertTrue(publication_gate(snapshot, quality, now)["allowed"])
        self.assertEqual(
            publication_gate(snapshot, quality, now + timedelta(hours=35))["valid_until"],
            (now + timedelta(hours=36)).isoformat(),
        )
        self.assertFalse(publication_gate(snapshot, quality, now + timedelta(hours=37))["allowed"])
        quality["results"] = {"status": "conflict"}
        self.assertFalse(publication_gate(snapshot, quality, now)["allowed"])
        quality["results"] = {"status": "partial", "unmatched": [{"source": "local"}]}
        self.assertFalse(publication_gate(snapshot, quality, now)["allowed"])

    def test_forecast_record_freezes_predictions_and_rejects_late_or_moved_games(self):
        prediction = {
            "date": "2026-10-20",
            "home": "A",
            "away": "B",
            "probabilities": [0.6, 0.2, 0.2],
        }
        snapshot = {"season": "2026-27", "matches": [dict(prediction, hg=None, ag=None)]}
        log, _ = update_forecast_log({}, [prediction], snapshot, "2026-10-18T12:00:00+00:00")
        changed = {**prediction, "probabilities": [0.1, 0.1, 0.8]}
        updated, _ = update_forecast_log(log, [changed], snapshot, "2026-10-19T12:00:00+00:00")
        self.assertEqual(updated["records"][0]["probabilities"], prediction["probabilities"])
        late, _ = update_forecast_log({}, [prediction], snapshot, "2026-10-20T00:01:00+00:00")
        self.assertEqual(late["records"], [])
        snapshot["matches"][0].update(hg=1, ag=0)
        settled, summary = update_forecast_log(log, [], snapshot, "2026-10-21T12:00:00+00:00")
        self.assertEqual(summary["accuracy"], 1)
        snapshot["matches"][0]["date"] = "2026-10-21"
        moved, summary = update_forecast_log(settled, [], snapshot, "2026-10-22T12:00:00+00:00")
        self.assertEqual(summary["settled"], 0)
        self.assertEqual(moved["records"][0]["status"], "rescheduled")

    def test_historical_open_source_does_not_claim_official_deductions(self):
        pl = read_json(LIVE / "dashboard_PL_2023-24.json")
        everton = next(r for r in apply_standings(pl, quality_for(pl)) if r["team"] == "Everton FC")
        self.assertEqual(everton["pts"], 48)
        self.assertNotIn("rank", everton)
        self.assertEqual(quality_for(pl)["standings"]["status"], "computed")
        data = read_json(LIVE / "dashboard_PL_2019-20.json")
        self.assertEqual(len(data["quarantined"]), 66)
        self.assertFalse(any(m.get("result_review") for m in data["matches"]))
