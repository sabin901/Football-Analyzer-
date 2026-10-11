"""
Static site generator for GitHub Pages.

GitHub Pages can only serve static files, so this renders a self-contained
dashboard (site/index.html) from local data:
  - the xG model's validation metrics
  - the predictor's accuracy/RPS and fitted team strengths
  - a table of predicted fixtures for a league season
  - (when present) live standings + upcoming fixtures pulled by src/live_api.py

A scheduled GitHub Action re-runs this after each data refresh and publishes
site/ to Pages — so the public page updates on a cadence ("live, even if late").

Usage:
    python src/build_site.py                       # default showcase league
    python src/build_site.py "La Liga" "2015/2016"
"""

import os
import sys
import json
import glob
import html
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.join(HERE, "..")
SITE_DIR = os.path.join(ROOT, "site")
MODELS = os.path.join(ROOT, "models")
LIVE_DIR = os.path.join(ROOT, "data", "live")

import predict as predictor


def _card(title, value, sub=""):
    return (f'<div class="stat"><div class="v">{value}</div>'
            f'<div class="l">{html.escape(title)}</div>'
            f'{f"<div class=s>{html.escape(sub)}</div>" if sub else ""}</div>')


def _fixture_rows(model, teams, n=12):
    """A few illustrative predictions (round-robin sample)."""
    rows, made = [], 0
    for i in range(len(teams)):
        for j in range(len(teams)):
            if i == j:
                continue
            p = predictor.predict(model, teams[i], teams[j])
            if not p:
                continue
            rows.append(p)
            made += 1
            if made >= n:
                return rows
    return rows


def _live_section():
    """Render live standings + upcoming fixtures if src/live_api.py has synced."""
    import pandas as pd
    if not os.path.isdir(LIVE_DIR):
        return ""
    manifest_path = os.path.join(LIVE_DIR, "sync_manifest.json")
    synced = ""
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            synced = json.load(f).get("synced_at", "")
    blocks = []
    for sp in sorted(glob.glob(os.path.join(LIVE_DIR, "standings_*.parquet"))):
        df = pd.read_parquet(sp).head(8)
        comp = df["competition"].iloc[0] if len(df) else os.path.basename(sp)
        tr = "".join(
            f"<tr><td>{int(r.position)}</td><td>{html.escape(str(r.team))}</td>"
            f"<td>{int(r.played)}</td><td>{int(r.points)}</td>"
            f"<td>{int(r.goal_difference):+d}</td></tr>" for r in df.itertuples())
        blocks.append(
            f"<div class=card><h3>{html.escape(str(comp))} — table</h3>"
            f"<table><thead><tr><th>#</th><th>Team</th><th>P</th><th>Pts</th><th>GD</th></tr></thead>"
            f"<tbody>{tr}</tbody></table></div>")
    if not blocks:
        return ""
    return (f'<h2>Live data <span class="muted">· synced {html.escape(synced)}</span></h2>'
            f'<div class="grid">{"".join(blocks)}</div>')


def build(competition="Premier League", season="2015/2016"):
    os.makedirs(SITE_DIR, exist_ok=True)

    # xG model metrics
    xg = {}
    mp = os.path.join(MODELS, "metrics.json")
    if os.path.exists(mp):
        with open(mp) as f:
            xg = json.load(f)

    # Predictor: fit + validate on the showcase league (with recency weighting)
    model, metrics = predictor.validate(competition, season, half_life_days=90)
    teams = model["teams"]
    ratings = predictor.team_ratings(model)
    fixtures = _fixture_rows(model, teams, n=10)

    # --- build HTML ---
    stat_cards = "".join([
        _card("xG model ROC-AUC", xg.get("roc_auc", "—"), "pro range 0.78–0.82"),
        _card("xG shots trained", f'{xg.get("n_shots", "—"):,}' if xg else "—"),
        _card("Predictor accuracy", f'{metrics["accuracy"]*100:.1f}%',
              f'baseline {metrics["baseline_accuracy"]*100:.1f}%'),
        _card("Predictor RPS", metrics["rps"], f'baseline {metrics["baseline_rps"]}'),
        _card("Home advantage", metrics["home_advantage"], f'{competition} {season}'),
    ])

    fx_rows = "".join(
        f"<tr><td>{html.escape(p['home'])}</td><td>{html.escape(p['away'])}</td>"
        f"<td class=a>{p['p_home']*100:.0f}%</td><td>{p['p_draw']*100:.0f}%</td>"
        f"<td class=r>{p['p_away']*100:.0f}%</td>"
        f"<td>{p['expected_home_goals']}–{p['expected_away_goals']}</td>"
        f"<td>{p['most_likely'][0]['score']}</td></tr>" for p in fixtures)

    rt_rows = "".join(
        f"<tr><td>{html.escape(t)}</td><td class=a>{a:+.2f}</td><td class=r>{d:+.2f}</td></tr>"
        for t, a, d in ratings[:12])

    live = _live_section()

    # Optional xT section (if src/xt.py has been run)
    xt_section = ""
    xt_imgs = sorted(glob.glob(os.path.join(ROOT, "output", "xt_surface_*.png")))
    xt_leaders = sorted(glob.glob(os.path.join(ROOT, "output", "xt_leaders_*.json")))
    if xt_imgs:
        import shutil
        shutil.copy(xt_imgs[0], os.path.join(SITE_DIR, "assets"))
        img_name = os.path.basename(xt_imgs[0])
        lead_rows = ""
        if xt_leaders:
            with open(xt_leaders[0]) as f:
                for l in json.load(f)[:10]:
                    lead_rows += (f"<tr><td>{html.escape(l['player'])}</td>"
                                  f"<td>{html.escape(l['team'])}</td>"
                                  f"<td class=a>{l['xt_added']:+.2f}</td></tr>")
        xt_section = f"""
  <h2>Expected Threat — ball progression</h2>
  <div class=grid>
    <div class=card><h3>xT surface</h3>
      <img style="width:100%;border-radius:8px" src="assets/{html.escape(img_name)}" alt="xT surface"></div>
    <div class=card><h3>Top ball progressors (total xT added)</h3>
      <table><thead><tr><th>Player</th><th>Team</th><th>xT</th></tr></thead>
      <tbody>{lead_rows}</tbody></table></div>
  </div>"""

    built = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    doc = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>Football Analyzer</title>
<style>
:root{{--bg:#0d1117;--panel:#12161c;--line:#232b35;--fg:#e8edf2;--muted:#8a97a6;--accent:#4ea1ff;--gold:#ffd34e;--red:#ff6b6b}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}}
header{{padding:40px 24px 24px;text-align:center;border-bottom:1px solid var(--line)}}
header h1{{margin:0;font-size:30px}}header p{{color:var(--muted);margin:8px 0 0}}
main{{max-width:1040px;margin:0 auto;padding:28px 20px 70px}}
h2{{margin:34px 0 14px;font-size:20px}}h3{{margin:0 0 12px;font-size:15px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}}
.stat{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}}
.stat .v{{font-size:24px;font-weight:700;color:var(--accent)}}.stat .l{{color:var(--muted);font-size:12px;margin-top:4px}}
.stat .s{{color:var(--muted);font-size:11px;margin-top:2px;opacity:.8}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;margin-bottom:16px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}@media(max-width:760px){{.grid{{grid-template-columns:1fr}}}}
table{{width:100%;border-collapse:collapse;font-size:13.5px}}th{{text-align:left;color:var(--muted);font-weight:500;padding:7px 8px}}
td{{padding:7px 8px;border-top:1px solid var(--line)}}td.a{{color:var(--accent)}}td.r{{color:var(--red)}}
.muted{{color:var(--muted);font-weight:400;font-size:13px}}
a{{color:var(--accent)}}footer{{text-align:center;color:var(--muted);font-size:12px;padding:30px}}
.gallery{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}@media(max-width:760px){{.gallery{{grid-template-columns:1fr}}}}
.gallery img{{width:100%;border-radius:10px;border:1px solid var(--line)}}
</style></head><body>
<header>
  <h1>⚽ Football Analyzer</h1>
  <p>xG model · post-match & scouting reports · match predictor — built on StatsBomb open data</p>
  <p class=muted><a href="https://github.com/sabin901/Football-Analyzer-">github.com/sabin901/Football-Analyzer-</a></p>
</header>
<main>
  <h2>At a glance</h2>
  <div class=stats>{stat_cards}</div>

  {live}

  <h2>Predicted fixtures <span class=muted>· {html.escape(competition)} {html.escape(season)} model</span></h2>
  <div class=card><table>
    <thead><tr><th>Home</th><th>Away</th><th>Home win</th><th>Draw</th><th>Away win</th><th>Exp. goals</th><th>Likeliest</th></tr></thead>
    <tbody>{fx_rows}</tbody></table></div>

  <h2>Fitted team strengths</h2>
  <div class=card><table>
    <thead><tr><th>Team</th><th>Attack</th><th>Defence</th></tr></thead>
    <tbody>{rt_rows}</tbody></table></div>

  {xt_section}

  <h2>Sample outputs</h2>
  <div class=gallery>
    <img src="assets/report_8658.png" alt="post-match report">
    <img src="assets/scout_2_27_Arsenal.png" alt="scouting report">
  </div>
</main>
<footer>Built {built} · data: StatsBomb open data · xG & predictions from this repo's own models</footer>
</body></html>"""

    with open(os.path.join(SITE_DIR, "index.html"), "w") as f:
        f.write(doc)

    # copy sample images into site/assets
    assets = os.path.join(SITE_DIR, "assets")
    os.makedirs(assets, exist_ok=True)
    import shutil
    for img in ["report_8658.png", "scout_2_27_Arsenal.png",
                "model_calibration.png", "model_importance.png"]:
        src = os.path.join(ROOT, "output", img)
        if os.path.exists(src):
            shutil.copy(src, assets)

    print(f"Built site -> {os.path.join(SITE_DIR, 'index.html')}")
    print(f"  predictor: {competition} {season} · acc {metrics['accuracy']*100:.1f}% · RPS {metrics['rps']}")
    print(f"  live section: {'included' if live else 'none yet (run src/live_api.py sync)'}")


if __name__ == "__main__":
    comp = sys.argv[1] if len(sys.argv) > 1 else "Premier League"
    season = sys.argv[2] if len(sys.argv) > 2 else "2015/2016"
    build(comp, season)
