"""Package the shared interactive dashboard and data for GitHub Pages."""

from pathlib import Path
import hashlib
import re
import shutil
import dashboard_data as data
import build_docs
from warehouse import build as build_warehouse
from workbench_data import OUT

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
    site = ROOT / "site"
    site.mkdir(exist_ok=True)
    # dashboard.html is the entry point; index.html is the legacy research UI.
    package_frontend(ROOT / "frontend", site)
    (site / ".nojekyll").touch()
    manifest = {
        "schema_version": 2,
        "built_at": data.utc_now(),
        "current_season": data.current_season(),
        "leagues": [],
    }
    for league in data.LEAGUES:
        seasons = []
        for path in sorted(data.LIVE.glob(f"dashboard_{league['id']}_*.json"), reverse=True):
            raw = data.read_json(path)
            snapshot = data.snapshot(league["id"], raw["season"])
            snapshot["predictions"] = []  # Unvalidated simulator is not published.
            file = f"data/{league['id']}_{raw['season']}.json"
            data.write_json(site / file, snapshot)
            seasons.append(
                {
                    "id": raw["season"],
                    "file": file,
                    "completed": snapshot["completed"],
                    "last_result": snapshot["last_result"],
                    "fetched_at": snapshot["fetched_at"],
                    "overdue": snapshot["overdue"],
                    "refresh_ok": snapshot["refresh_ok"],
                }
            )
        manifest["leagues"].append({**league, "seasons": seasons})
    if any(not league["seasons"] for league in manifest["leagues"]):
        raise RuntimeError("Each of the five leagues needs a snapshot before deployment")
    manifest["crests"] = {}
    for l in manifest["leagues"]:
        teams = data.read_json(OUT / f"current_{l['id']}.json", {}).get("teams", [])
        by_name = {
            data.normalized_name(data.ALIASES.get(t["name"], t["name"])): t.get("logo")
            for t in teams
        }
        names = {r["team"] for s in l["seasons"] for r in data.read_json(site / s["file"])["table"]}
        manifest["crests"][l["id"]] = {
            name: by_name[data.normalized_name(name)]
            for name in names
            if by_name.get(data.normalized_name(name))
        }
    data.write_json(site / "data" / "manifest.json", manifest)
    event_manifest = data.read_json(OUT / "events_manifest.json", {"sets": []})
    current = [data.read_json(p) for p in OUT.glob("current_*.json")]
    catalogue = {
        "built_at": data.utc_now(),
        "league_seasons": sum(len(l["seasons"]) for l in manifest["leagues"]),
        "results": sum(s["completed"] for l in manifest["leagues"] for s in l["seasons"]),
        "current_players": sum(len(d["players"]) for d in current),
        "event_matches": sum(s["imported_matches"] for s in event_manifest["sets"]),
        "events": sum(s["events"] for s in event_manifest["sets"]),
        "event_datasets": len(event_manifest["sets"]),
    }
    data.write_json(OUT / "catalogue.json", catalogue)
    shutil.copytree(OUT, site / "data" / "workbench", dirs_exist_ok=True)
    shutil.copyfile(build_warehouse(), site / "data" / "football.sqlite")
    if (ROOT / "docs").exists():
        build_docs.package_docs(ROOT, site)
    assets = site / "assets"
    assets.mkdir(exist_ok=True)
    for name in [
        "report_8658.png",
        "scout_2_27_Arsenal.png",
        "model_calibration.png",
        "model_importance.png",
    ]:
        source = ROOT / "output" / name
        if source.exists():
            shutil.copyfile(source, assets / name)
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
    print(f"Built dashboard: {sum(len(l['seasons']) for l in manifest['leagues'])} league-seasons")


if __name__ == "__main__":
    build()
