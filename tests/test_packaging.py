"""A returning visitor must never combine files from incompatible releases."""

import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from build_site import package_frontend


class PackagingTests(unittest.TestCase):
    def test_changed_content_gets_new_url_and_cached_html_keeps_its_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frontend, site = root / "frontend", root / "site"
            (frontend / "assets").mkdir(parents=True)
            (frontend / "dashboard.html").write_text('<script defer src="app.js"></script>')
            (frontend / "app.js").write_text("const version = 1;\n")
            package_frontend(frontend, site)
            old_html = (site / "index.html").read_text()
            old_asset = re.search(r'src="([^"]+)"', old_html)[1]

            (frontend / "app.js").write_text("const version = 2;\n")
            package_frontend(frontend, site)
            new_html = (site / "index.html").read_text()
            new_asset = re.search(r'src="([^"]+)"', new_html)[1]
            self.assertNotEqual(old_asset, new_asset)
            self.assertIn("version = 1", (site / old_asset).read_text())
            self.assertIn("version = 2", (site / new_asset).read_text())

            # A rebuild with unchanged content must not invalidate browser caches.
            package_frontend(frontend, site)
            self.assertEqual(new_html, (site / "index.html").read_text())
