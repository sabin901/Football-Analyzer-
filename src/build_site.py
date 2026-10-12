"""Package the shared interactive dashboard and data for GitHub Pages."""

from pathlib import Path
import shutil
import dashboard_data as data
import build_docs
from warehouse import build as build_warehouse
from workbench_data import OUT

ROOT = Path(__file__).resolve().parents[1]


def build():
    site = ROOT / "site"
    site.mkdir(exist_ok=True)
    # dashboard.html is the entry point; index.html is the legacy research UI.
    shutil.copyfile(ROOT / "frontend/dashboard.html", site / "index.html")
    for pattern in ("*.js", "*.css"):
        for source in (ROOT / "frontend").glob(pattern):
            shutil.copyfile(source, site / source.name)
    shutil.copytree(ROOT / "frontend/assets", site / "assets", dirs_exist_ok=True)
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
            teams = [r["team"] for r in snapshot["table"]]
            snapshot["predictions"] = [
                p
                for h in teams
                for a in teams
                if h != a
                if (p := data.baseline_prediction(snapshot["matches"], h, a))
            ]
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
        shutil.copytree(ROOT / "docs", site / "docs", dirs_exist_ok=True)
        build_docs.build(ROOT, site)
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
    pages = [""] + ["docs/" + p.with_suffix(".html").name for p in (ROOT / "docs").glob("*.md")]
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
