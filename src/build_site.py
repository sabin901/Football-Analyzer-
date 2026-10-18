"""Package the shared interactive dashboard and data for GitHub Pages."""

from pathlib import Path
import hashlib
import re
import shutil
import dashboard_data as data
import build_docs
from warehouse import build as build_warehouse
from open_policy import WORKBENCH as OUT, OPEN, validate_public
import json
import subprocess
import os

ROOT = Path(__file__).resolve().parents[1]


def package_frontend(frontend, site):
    """Give each script and stylesheet a URL tied to its actual content."""
    versioned = site / "assets/app"
    versioned.mkdir(parents=True, exist_ok=True)
    urls = {}
    for pattern in ("*.js", "*.css"):
        for source in frontend.glob(pattern):
            # Normalize checkout line endings so Windows and CI produce the same URL.
            content = source.read_text(encoding="utf-8").encode("utf-8")
            digest = hashlib.sha256(content).hexdigest()[:12]
            name = f"{source.stem}.{digest}{source.suffix}"
            (versioned / name).write_bytes(content)
            urls[source.name] = f"assets/app/{name}"
            shutil.copyfile(source, site / source.name)
    html = (frontend / "dashboard.html").read_text(encoding="utf-8")
    html = re.sub(
        r'(src|href)="([^"/]+\.(?:js|css))"',
        lambda match: f'{match[1]}="{urls[match[2]]}"',
        html,
    )
    (site / "index.html").write_text(html, encoding="utf-8", newline="\n")
    # Retire bundles containing the removed personal section, including old fingerprints.
    # Other cached releases retain their assets. Privacy cleanup takes precedence here.
    for asset in [*versioned.glob("*.js"), *versioned.glob("*.css")]:
        if any(
            token in asset.read_text(encoding="utf-8")
            for token in (
                "portfolioView",
                "'portfolio'",
                "PROJECT_REVIEW.html",
                "portfolio-hero",
                "PORTFOLIO_PLAYBOOK.html",
            )
        ):
            asset.unlink()
    # Keep other previous fingerprints for cached HTML pages.
    shutil.copytree(frontend / "assets", site / "assets", dirs_exist_ok=True)


def build():
    from bundle_data import ensure

    ensure()
    # A clean staging tree prevents retired sources and cached personal pages leaking.
    site = ROOT / ".artifacts/site-staging"
    if site.exists():
        shutil.rmtree(site)
    site.mkdir(parents=True)
    package_frontend(ROOT / "frontend", site)
    (site / ".nojekyll").touch()
    manifest = {
        "schema_version": 3,
        "built_at": data.utc_now(),
        "current_season": data.current_season(),
        "leagues": [],
        "crests": {},
        "publication_policy": "open-licenses-v1",
        "commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "dirty": bool(
            subprocess.check_output(
                ["git", "status", "--porcelain", "--untracked-files=no", "--", ".", ":!data/open"],
                cwd=ROOT,
                text=True,
            ).strip()
        ),
        "data_revision": os.environ.get("FOOTLYZER_DATA_REVISION", "bundled"),
    }
    for league in data.LEAGUES:
        seasons = []
        for path in sorted(data.LIVE.glob(f"dashboard_{league['id']}_*.json"), reverse=True):
            raw = validate_public(data.read_json(path))
            snapshot = data.snapshot(league["id"], raw["season"])
            snapshot["predictions"] = []
            file = f"data/{league['id']}_{raw['season']}.json"
            data.write_json(site / file, snapshot)
            seasons.append(
                {
                    "id": raw["season"],
                    "file": file,
                    **{
                        k: snapshot[k]
                        for k in ("completed", "last_result", "fetched_at", "overdue", "refresh_ok")
                    },
                    "quarantined": len(raw.get("quarantined", [])),
                }
            )
        if not seasons:
            raise RuntimeError(f"No permitted results for {league['id']}")
        manifest["leagues"].append({**league, "seasons": seasons})
    data.write_json(site / "data/manifest.json", manifest)
    event_manifest = validate_public(data.read_json(OUT / "events_manifest.json"))
    current = [validate_public(data.read_json(p)) for p in OUT.glob("current_*.json")]
    catalogue = {
        "built_at": data.utc_now(),
        "league_seasons": sum(len(l["seasons"]) for l in manifest["leagues"]),
        "results": sum(s["completed"] for l in manifest["leagues"] for s in l["seasons"]),
        "current_players": sum(len(d["players"]) for d in current),
        "player_coverage": "2017/18 historical archive",
        "event_matches": sum(s["imported_matches"] for s in event_manifest["sets"]),
        "events": sum(s["events"] for s in event_manifest["sets"]),
        "event_datasets": len(event_manifest["sets"]),
    }
    data.write_json(OUT / "catalogue.json", catalogue)
    for path in OUT.rglob("*.json"):
        relative = path.relative_to(OUT)
        if relative.as_posix() != "catalogue.json":
            validate_public(data.read_json(path))
        target = site / "data/workbench" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    shutil.copyfile(OPEN / "source_registry.json", site / "data/source_registry.json")
    shutil.copyfile(OPEN / "wyscout_sources.json", site / "data/wyscout_sources.json")
    shutil.copyfile(build_warehouse(), site / "data/football.sqlite")
    build_docs.package_docs(ROOT, site)
    base = "https://sabin901.github.io/Football-Analyzer-/"
    pages = [""] + [
        "docs/" + name.replace(".md", ".html") for name in sorted(build_docs.PUBLIC_DOCS)
    ]
    (site / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<url><loc>{base}{p}</loc></url>" for p in pages)
        + "</urlset>",
        encoding="utf8",
    )
    (site / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nSitemap: " + base + "sitemap.xml\n", encoding="utf8"
    )
    target = ROOT / "site"
    old = ROOT / ".artifacts/site-previous"
    if old.exists():
        shutil.rmtree(old)
    if target.exists():
        target.rename(old)
    site.rename(target)
    print(f"Built dashboard: {sum(len(l['seasons']) for l in manifest['leagues'])} league-seasons")


if __name__ == "__main__":
    build()
