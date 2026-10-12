"""Package the shared interactive dashboard and data for GitHub Pages."""
from pathlib import Path
import shutil
import dashboard_data as data

ROOT = Path(__file__).resolve().parents[1]


def build():
    site = ROOT / 'site'
    site.mkdir(exist_ok=True)
    for source, target in [('dashboard.html', 'index.html'), ('dashboard.css', 'dashboard.css'), ('dashboard.js', 'dashboard.js')]:
        shutil.copyfile(ROOT / 'frontend' / source, site / target)
    (site / '.nojekyll').touch()
    manifest = {'schema_version': 2, 'built_at': data.utc_now(), 'current_season': data.current_season(), 'leagues': []}
    for league in data.LEAGUES:
        seasons = []
        for path in sorted(data.LIVE.glob(f"dashboard_{league['id']}_*.json"), reverse=True):
            raw = data.read_json(path)
            snapshot = data.snapshot(league['id'], raw['season'])
            teams = [r['team'] for r in snapshot['table']]
            snapshot['predictions'] = [p for h in teams for a in teams if h != a
                                       if (p := data.baseline_prediction(snapshot['matches'], h, a))]
            file = f"data/{league['id']}_{raw['season']}.json"
            data.write_json(site / file, snapshot)
            seasons.append({'id': raw['season'], 'file': file, 'completed': snapshot['completed'],
                            'last_result': snapshot['last_result'], 'fetched_at': snapshot['fetched_at'],
                            'overdue': snapshot['overdue'], 'refresh_ok': snapshot['refresh_ok']})
        manifest['leagues'].append({**league, 'seasons': seasons})
    if any(not league['seasons'] for league in manifest['leagues']):
        raise RuntimeError('Each of the five leagues needs a snapshot before deployment')
    data.write_json(site / 'data' / 'manifest.json', manifest)
    assets = site / 'assets'
    assets.mkdir(exist_ok=True)
    for name in ['report_8658.png', 'scout_2_27_Arsenal.png', 'model_calibration.png', 'model_importance.png']:
        source = ROOT / 'output' / name
        if source.exists():
            shutil.copyfile(source, assets / name)
    print(f"Built dashboard: {sum(len(l['seasons']) for l in manifest['leagues'])} league-seasons")


if __name__ == '__main__':
    build()
