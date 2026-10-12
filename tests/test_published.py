from pathlib import Path
import json
import unittest

SITE = Path(__file__).resolve().parents[1] / "site"


class PublishedTests(unittest.TestCase):
    def test_all_five_leagues_and_consistent_snapshots(self):
        manifest = json.loads((SITE / "data/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual({l["id"] for l in manifest["leagues"]}, {"PL","PD","SA","BL1","FL1"})
        for league in manifest["leagues"]:
            self.assertTrue(league["seasons"])
            for season in league["seasons"]:
                data = json.loads((SITE / season["file"]).read_text(encoding="utf-8"))
                self.assertEqual(data["league"], league["id"])
                self.assertEqual(data["season"], season["id"])
                expected = 20 if league['id'] == 'FL1' and int(season['id'][:4]) < 2023 else league['teams']
                self.assertEqual(len(data["table"]), expected)
                self.assertEqual(sum(r["p"] for r in data["table"]), data["completed"]*2)
                self.assertEqual(sum(r["gf"] for r in data["table"]), sum(r["ga"] for r in data["table"]))
                for p in data["predictions"]:
                    self.assertNotEqual(p["home"], p["away"])
                    self.assertAlmostEqual(p["p_home"]+p["p_draw"]+p["p_away"],1)

    def test_frontend_matches_the_packaged_version(self):
        root = SITE.parent / "frontend"
        for a,b in [("dashboard.html","index.html"),("dashboard.js","dashboard.js"),("dashboard.css","dashboard.css"),("workbench.js","workbench.js"),("workbench.css","workbench.css"),("spatial.js","spatial.js"),("icons.js","icons.js")]:
            self.assertEqual((root/a).read_bytes(), (SITE/b).read_bytes())
