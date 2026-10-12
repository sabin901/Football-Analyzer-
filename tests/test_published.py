from pathlib import Path
import json
import unittest

SITE = Path(__file__).resolve().parents[1] / "site"


class PublishedTests(unittest.TestCase):
    def test_all_five_leagues_and_consistent_snapshots(self):
        manifest = json.loads((SITE / "data/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual({l["id"] for l in manifest["leagues"]}, {"PL", "PD", "SA", "BL1", "FL1"})
        for league in manifest["leagues"]:
            self.assertTrue(league["seasons"])
            for season in league["seasons"]:
                data = json.loads((SITE / season["file"]).read_text(encoding="utf-8"))
                self.assertEqual(data["league"], league["id"])
                self.assertEqual(data["season"], season["id"])
                expected = (
                    20
                    if league["id"] == "FL1" and int(season["id"][:4]) < 2023
                    else league["teams"]
                )
                self.assertEqual(len(data["table"]), expected)
                self.assertEqual(sum(r["p"] for r in data["table"]), data["completed"] * 2)
                self.assertEqual(
                    sum(r["gf"] for r in data["table"]), sum(r["ga"] for r in data["table"])
                )
                for p in data["predictions"]:
                    self.assertNotEqual(p["home"], p["away"])
                    self.assertAlmostEqual(p["p_home"] + p["p_draw"] + p["p_away"], 1)

    def test_frontend_matches_the_packaged_version(self):
        root = SITE.parent / "frontend"
        assets = [("dashboard.html", "index.html")]
        assets += [(p.name, p.name) for p in root.iterdir() if p.suffix in {".js", ".css"}]
        for source, target in assets:
            self.assertEqual((root / source).read_bytes(), (SITE / target).read_bytes())

    def test_entrypoint_scripts_and_league_assets_exist(self):
        import re

        html = (SITE / "index.html").read_text(encoding="utf-8")
        for script in re.findall(r'<script[^>]*src="([^"]+)"', html):
            self.assertTrue((SITE / script).is_file(), script)
        sources = json.loads((SITE / "assets/leagues/sources.json").read_text())
        self.assertEqual({row["league"] for row in sources}, {"PL", "PD", "SA", "BL1", "FL1"})
        for row in sources:
            source = SITE.parent / "frontend/assets/leagues" / row["file"]
            published = SITE / "assets/leagues" / row["file"]
            self.assertGreater(source.stat().st_size, 1000)
            self.assertEqual(source.read_bytes(), published.read_bytes())
