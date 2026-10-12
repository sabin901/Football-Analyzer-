import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from spatial_workbench import summarize_spatial, aggregate_spatial
from fastapi.testclient import TestClient
from app import app


class SpatialTests(unittest.TestCase):
    def match(self):
        return {
            "id": 1,
            "date": "2020-01-01",
            "source_url": "https://example.org",
            "event_sha256": "hash",
            "players": [
                {"id": 7, "name": "A", "team_id": 1, "team": "Home"},
                {"id": 8, "name": "B", "team_id": 2, "team": "Away"},
            ],
        }

    def event(self, loc, period=1, kind="Pass", player=7, team=1):
        return {
            "player": {"id": player},
            "team": {"id": team},
            "type": {"name": kind},
            "period": period,
            "location": loc,
        }

    def test_mass_conservation_missing_boundaries_and_no_half_rotation(self):
        events = [
            self.event([120, 80]),
            self.event([120.2, 40]),
            self.event([0, 0], 2),
            self.event(None),
            self.event([999, 30]),
            self.event([float("nan"), 2]),
            self.event([0, 0], 5),
            self.event([0, 0], player=8, team=2),
        ]
        d = summarize_spatial(events, self.match())
        self.assertEqual(d["located"], 4)
        self.assertEqual(sum(row[-1] for row in d["cells"]), 4)
        self.assertEqual(d["missing_location"], 1)
        self.assertEqual(d["invalid_location"], 2)
        self.assertEqual(d["edge_clamped"], 1)
        self.assertIn([0, 1, 0, 95, 1], d["cells"])
        self.assertIn([0, 2, 0, 0, 1], d["cells"])
        self.assertIn([1, 1, 0, 0, 1], d["cells"])

    def test_categories_are_mutually_exclusive_and_shootouts_excluded(self):
        kinds = ["Pass", "Carry", "Shot", "Pressure", "Interception", "Ball Receipt*", "Dribble"]
        d = summarize_spatial([self.event([60, 40], kind=k) for k in kinds], self.match())
        self.assertEqual(d["located"], 7)
        self.assertEqual({r[2] for r in d["cells"]}, set(range(7)))
        self.assertEqual(len(d["cells"]), 7)

    def test_aggregate_remaps_ids_without_combining_transfers(self):
        a = summarize_spatial([self.event([10, 10])], self.match())
        b = summarize_spatial([self.event([10, 10], player=8, team=2)], self.match())
        b["players"][1]["id"] = 7
        d = aggregate_spatial([a, b])
        self.assertEqual(d["located"], 2)
        self.assertEqual(sum(r[-1] for r in d["cells"]), 2)
        self.assertEqual(len([p for p in d["players"] if p["id"] == 7]), 2)
        self.assertEqual([p["matches"] for p in d["players"] if p["id"] == 7], [1, 1])

    def test_unknown_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize_spatial([self.event([1, 1], player=999)], self.match())

    def test_archive_contract_and_season_totals(self):
        base = ROOT / "data/workbench"
        manifest = json.loads((base / "spatial_manifest.json").read_text(encoding="utf8"))
        self.assertEqual({s["league"] for s in manifest["sets"]}, {"PL", "PD", "SA", "BL1", "FL1"})
        for s in manifest["sets"]:
            d = json.loads((base / f"spatial_{s['key']}.json").read_text(encoding="utf8"))
            self.assertEqual(len(d["match_ids"]), s["imported_matches"])
            self.assertEqual(len(set(d["match_ids"])), len(d["match_ids"]))
            self.assertEqual(sum(r[-1] for r in d["cells"]), d["located"])
            self.assertEqual(
                len({(p["id"], p["team_id"]) for p in d["players"]}), len(d["players"])
            )
            total = 0
            for mid in d["match_ids"]:
                m = json.loads(
                    (base / "spatial_matches" / f"{mid}.json").read_text(encoding="utf8")
                )
                event = json.loads(
                    (base / "event_matches" / f"{mid}.json").read_text(encoding="utf8")
                )
                self.assertEqual(m["source_hash"], event["event_sha256"])
                self.assertEqual(sum(r[-1] for r in m["cells"]), m["located"])
                total += m["located"]
                for i, period, kind, cell, n in m["cells"]:
                    self.assertTrue(
                        0 <= i < len(m["players"])
                        and period in (1, 2, 3, 4)
                        and 0 <= kind < 7
                        and 0 <= cell < 96
                        and n > 0
                    )
            self.assertEqual(total, d["located"])

    def test_api_validates_spatial_paths(self):
        client = TestClient(app)
        self.assertEqual(client.get("/api/workbench/spatial/manifest").status_code, 200)
        self.assertEqual(client.get("/api/workbench/spatial/2_27").status_code, 200)
        for key in ("-1", "abc", "9999999999999999999"):
            self.assertEqual(client.get("/api/workbench/spatial-match/" + key).status_code, 400)
        self.assertEqual(client.get("/api/workbench/spatial-match/99999999").status_code, 404)

    def test_seo_text_has_no_hyphens_and_links_are_canonical(self):
        for file in [ROOT / "site/index.html", *list((ROOT / "site/docs").glob("*.html"))]:
            text = file.read_text(encoding="utf8")
            titles = re.findall(r"<title>(.*?)</title>", text)
            descriptions = re.findall(
                r'<meta[^>]+(?:name|property)="(?:description|og:title|og:description|twitter:title|twitter:description)" content="([^"]+)"',
                text,
            )
            self.assertTrue(titles)
            self.assertNotRegex(" ".join(titles + descriptions), r"[–—-]")
            self.assertIn('rel="canonical"', text)


if __name__ == "__main__":
    unittest.main()
