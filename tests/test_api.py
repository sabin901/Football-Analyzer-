from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app import app


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_dashboard_and_assets(self):
        for url in ["/", "/dashboard.js", "/dashboard.css", "/data/manifest.json", "/api/health"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertIn("footlyzer", self.client.get("/").text)

    def test_five_leagues_and_unknown_league(self):
        for league in ["PL", "PD", "SA", "BL1", "FL1"]:
            response = self.client.get(f"/api/dashboard/{league}/2026-27")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["league"], league)
        self.assertEqual(self.client.get("/api/dashboard/unknown/2026-27").status_code, 400)

    def test_missing_season_is_404(self):
        self.assertEqual(self.client.get("/api/dashboard/PL/2099-00").status_code, 404)

    def test_invalid_prediction_and_dataset_key(self):
        r = self.client.get(
            "/api/dashboard/PL/2026-27/predict", params={"home": "bad", "away": "bad"}
        )
        self.assertEqual(r.status_code, 400)
        for route in ["/api/players", "/api/vaep"]:
            self.assertEqual(
                self.client.get(route, params={"key": "../../private"}).status_code, 400
            )
        self.assertEqual(
            self.client.get(
                "/api/scout", params={"competition_id": 2, "season_id": 27, "team": "..\\secret"}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.get(
                "/api/predict/fixture",
                params={
                    "competition": "Premier League",
                    "season": "2025/2026",
                    "home": "A",
                    "away": "A",
                },
            ).status_code,
            400,
        )

    def test_research_scenarios_refit_all_known_matches(self):
        import pandas as pd
        import app as backend

        catalogue = pd.DataFrame(
            [{"competition": "test", "season": "2026/2027"} for _ in range(10)]
        )
        backend._PRED_CACHE.clear()
        with (
            patch.object(
                backend.predictor, "validate", return_value=({"training_only": True}, {"rps": 0.2})
            ),
            patch.object(backend.predictor, "load_catalogue", return_value=catalogue),
            patch.object(backend.predictor, "fit", return_value={"all_known": True}) as fit,
        ):
            model, _ = backend._get_predictor("test", "2026/2027")
            self.assertTrue(model["all_known"])
            self.assertEqual(len(fit.call_args.args[0]), 10)
        backend._PRED_CACHE.clear()
