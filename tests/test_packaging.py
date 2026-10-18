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

            # Windows checkout endings must not change content identity.
            (frontend / "app.js").write_bytes(b"const version = 2;\r\n")
            package_frontend(frontend, site)
            self.assertEqual(new_html, (site / "index.html").read_text())


class PublicDocumentationTests(unittest.TestCase):
    def test_personal_documents_and_stale_pages_are_not_published(self):
        from build_docs import package_docs, PUBLIC_DOCS

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docs, site = root / "docs", root / "site"
            docs.mkdir()
            (site / "docs").mkdir(parents=True)
            for name in PUBLIC_DOCS:
                (docs / name).write_text("# Product method\nPublic documentation.")
            for name in [
                "CAREER_RESEARCH",
                "PROJECT_REVIEW",
                "APPLICATION_GUIDE",
                "PORTFOLIO_PLAYBOOK",
            ]:
                (docs / f"{name}.md").write_text("# Personal note\nKeep in the repository.")
                for ext in ["md", "html"]:
                    (site / "docs" / f"{name}.{ext}").write_text("Previously published")
            package_docs(root, site)
            self.assertEqual(
                {p.name for p in (site / "docs").iterdir()},
                PUBLIC_DOCS | {name.replace(".md", ".html") for name in PUBLIC_DOCS},
            )
            self.assertTrue((docs / "CAREER_RESEARCH.md").exists())
            self.assertIn("#view=coverage", (site / "docs/MODEL_CARD.html").read_text())

    def test_retired_personal_bundle_is_removed_even_at_fingerprinted_url(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frontend, site = root / "frontend", root / "site"
            (frontend / "assets").mkdir(parents=True)
            (site / "assets/app").mkdir(parents=True)
            old = site / "assets/app/old.0123456789ab.js"
            old.write_text("function portfolioView() {}")
            (frontend / "dashboard.html").write_text('<script src="app.js"></script>')
            (frontend / "app.js").write_text("const publicApp = true;")
            package_frontend(frontend, site)
            self.assertFalse(old.exists())
