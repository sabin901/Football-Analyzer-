import copy
from datetime import date
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import dashboard_data as d


class DataTests(unittest.TestCase):
    def test_atomic_write_retries_temporary_lock_but_surfaces_persistent_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'snapshot.json'
            d.write_json(path, {'version':1})
            original=d.os.replace
            calls=[]
            def locked_once(source,target):
                calls.append(1)
                if len(calls)==1:raise PermissionError('temporary lock')
                original(source,target)
            with patch.object(d.os,'replace',side_effect=locked_once),patch.object(d.time,'sleep'):
                d.write_json(path,{'version':2})
            self.assertEqual(d.read_json(path),{'version':2})
            with patch.object(d.os,'replace',side_effect=PermissionError('persistent lock')) as replace,patch.object(d.time,'sleep'):
                with self.assertRaises(PermissionError):d.write_json(path,{'version':3})
                self.assertEqual(replace.call_count,6)
            self.assertEqual(d.read_json(path),{'version':2})

    def test_season_rollover(self):
        self.assertEqual(d.current_season(date(2026, 6, 30)), "2025-26")
        self.assertEqual(d.current_season(date(2026, 7, 1)), "2026-27")

    def test_source_formats_and_missing_scores(self):
        source = {"matches": [
            {"team1": "A", "team2": "B", "date": "2026-09-01", "score": {"ft": [0, 0]}},
            {"team1": "B", "team2": "A", "date": "2026-09-02", "score": [1, 0]},
            {"team1": "A", "team2": "C", "date": "2026-10-20"},
        ]}
        rows = d.parse_openfootball(source, "2026-27", date(2026, 10, 12))
        self.assertEqual([r["hg"] for r in rows], [0, 1, None])
        table = {r["team"]: r for r in d.standings(rows)}
        self.assertEqual((table["B"]["pts"], table["B"]["p"]), (4, 2))
        self.assertEqual(table["C"]["p"], 0)
        self.assertIsNone(table["C"]["ppg"])

    def test_reject_future_and_duplicate_results(self):
        match = {"team1": "A", "team2": "B", "date": "2026-11-01", "score": [1, 0]}
        with self.assertRaises(ValueError):
            d.parse_openfootball({"matches": [match]}, "2026-27", date(2026, 10, 12))
        match["date"] = "2026-09-01"
        with self.assertRaises(ValueError):
            d.parse_openfootball({"matches": [match, match]}, "2026-27", date(2026, 10, 12))

    def test_bad_score_rejected(self):
        for score in ([True, 0], [-1, 0], [1], [1.5, 2]):
            with self.assertRaises(ValueError):
                d.parse_openfootball({"matches": [{"team1": "A", "team2": "B", "date": "2026-09-01", "score": score}]}, "2026-27", date(2026, 10, 12))

    def test_failed_refresh_preserves_last_good_data_and_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "dashboard_PL_2026-27.json"
            original = {"fetched_at": "2026-09-01T00:00:00Z", "matches": []}
            d.write_json(path, original)
            def fail(_):
                raise TimeoutError("Source unavailable")
            with patch.object(d, "LEAGUES", [d.LEAGUES[0]]):
                self.assertEqual(d.sync(["2026-27"], root, fail), ["PL_2026-27"])
            self.assertEqual(d.read_json(path), original)
            self.assertFalse(d.read_json(root / "dashboard_sync.json")["leagues"]["PL_2026-27"]["ok"])

    def test_home_away_and_form(self):
        rows = [{"home": "A", "away": "B", "hg": 2, "ag": 0, "date": "2026-09-01"},
                {"home": "B", "away": "A", "hg": 1, "ag": 1, "date": "2026-09-02"}]
        home = {r["team"]: r for r in d.standings(rows, "home")}
        self.assertEqual(home["A"]["pts"], 3)
        self.assertEqual(home["B"]["pts"], 1)
        recent = d.standings(rows, last=1)
        self.assertTrue(all(r["p"] == 1 and r["form"] == ["D"] for r in recent))

    def test_overdue_is_not_upcoming_or_completed(self):
        payload = {"matches": [{"home": "A", "away": "B", "hg": None, "ag": None, "date": "2026-09-01"}]}
        snapshot = d.enrich(payload, today=date(2026, 10, 12))
        self.assertEqual((snapshot["overdue"], snapshot["completed"]), (1, 0))
        self.assertIsNone(snapshot["last_result"])

    def test_poisson_probability_invariants_and_sample_gate(self):
        rows = [{"home": "A", "away": "B", "hg": 2, "ag": 1, "date": "2026-09-01"} for _ in range(30)]
        self.assertIsNone(d.baseline_prediction(rows[:10], "A", "B"))
        p = d.baseline_prediction(rows, "A", "B")
        self.assertAlmostEqual(p["p_home"] + p["p_draw"] + p["p_away"], 1)
        self.assertTrue(all(0 <= p[k] <= 1 for k in ["p_home", "p_draw", "p_away"]))
        self.assertAlmostEqual(p["home_goals"], 2)
        with self.assertRaises(ValueError):
            d.baseline_prediction(rows, "A", "A")
        with self.assertRaises(ValueError):
            d.baseline_prediction(rows, "A", "Unknown")

    def test_dataset_traversal_rejected(self):
        with self.assertRaises(ValueError):
            d.snapshot("../../etc", "2026-27")
        with self.assertRaises(ValueError):
            d.snapshot("PL", "../../passwd")

    def test_scoreboard_resolves_identity_and_preserves_abandoned_status(self):
        matches = [{"home": "Arsenal FC", "away": "Chelsea FC", "date": "2026-10-10", "hg": None, "ag": None}]
        event = {"date": "2026-10-10T15:00Z", "status": {"type": {"completed": True}}, "competitions": [{"competitors": [
            {"homeAway": "away", "team": {"displayName": "Chelsea"}, "score": "1"},
            {"homeAway": "home", "team": {"displayName": "Arsenal"}, "score": "2"}]}]}
        errors = d.supplement_results(matches, "PL", "2026-27", fetch=lambda _: {"events": [event]}, today=date(2026,10,12))
        self.assertFalse(errors)
        self.assertEqual((matches[0]["hg"], matches[0]["ag"]), (2,1))
        self.assertEqual(matches[0]["result_source"], "ESPN")
        event["status"]["type"] = {"completed": False, "name": "STATUS_ABANDONED"}
        d.supplement_results(matches, "PL", "2026-27", fetch=lambda _: {"events": [event]}, today=date(2026,10,12))
        self.assertIsNone(matches[0]["hg"])
        self.assertEqual(matches[0]["status"], "abandoned")
        self.assertEqual(d.enrich({"matches": matches}, today=date(2026,10,12))["overdue"], 0)

    def test_scoreboard_failure_keeps_verified_scores(self):
        matches = [{"home":"Arsenal FC", "away":"Chelsea FC", "date":"2026-10-10", "hg":None, "ag":None}]
        previous = {"matches": [{**matches[0], "hg":2, "ag":1, "result_source":"ESPN", "result_checked_at":"original"}]}
        def fail(_):
            raise TimeoutError()
        errors = d.supplement_results(matches, "PL", "2026-27", previous, fail, date(2026,10,12))
        self.assertTrue(errors)
        self.assertEqual(matches[0]["hg"], 2)
        self.assertEqual(matches[0]["result_checked_at"], "original")

    def test_unmapped_scoreboard_teams_are_never_guessed(self):
        matches = [{"home":"Arsenal FC", "away":"Chelsea FC", "date":"2026-10-10", "hg":None, "ag":None}]
        event = {"date":"2026-10-10T15:00Z", "status":{"type":{"completed":True}}, "competitions":[{"competitors":[
            {"homeAway":"home", "team":{"displayName":"Arsenal Women"}, "score":"2"},
            {"homeAway":"away", "team":{"displayName":"Chelsea"}, "score":"1"}]}]}
        self.assertTrue(d.supplement_results(matches,"PL","2026-27",fetch=lambda _: {"events":[event]},today=date(2026,10,12)))
        self.assertIsNone(matches[0]["hg"])


if __name__ == "__main__":
    unittest.main()
