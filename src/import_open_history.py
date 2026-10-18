"""Import CC0 top-five results, reporting every unavailable league-season."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from dashboard_data import LEAGUES, LIVE, parse_openfootball, read_json, write_json, utc_now
from workbench_data import cached_fetch, OUT
from result_corrections import apply_corrections


def run():
    status = []
    def one(item):
        league, year = item
        season = f'{year}-{str(year+1)[-2:]}'
        url = f"https://raw.githubusercontent.com/openfootball/football.json/master/{season}/{league['file']}.json"
        path = LIVE / f"dashboard_{league['id']}_{season}.json"
        try:
            payload = cached_fetch(url, 24*365)
            matches = parse_openfootball(payload, season)
            expected = 18 if league['id'] == 'BL1' or (league['id'] == 'FL1' and year >= 2023) else 20
            teams = {m[k] for m in matches for k in ('home', 'away')}
            if len(teams) != expected: raise ValueError('Unexpected team count')
            complete = len(matches) == expected*(expected-1) and all(m['hg'] is not None for m in matches)
            # Do not pretend the cancelled French 2019/20 season had a complete schedule.
            if not complete and not (league['id'] == 'FL1' and year == 2019):
                raise ValueError('Incomplete historical schedule/results')
            if not complete:
                for m in matches:
                    if m['hg'] is None: m['status'] = 'cancelled'
            result = {'league': league['id'], 'season': season, 'source': 'OpenFootball', 'source_url': url,
                      'license': 'CC0-1.0', 'fetched_at': utc_now(), 'matches': matches,
                      'archive_note': 'Season curtailed; played results only.' if not complete else None}
            write_json(path, apply_corrections(result))
            return {'league': league['id'], 'season': season, 'ok': True, 'matches': len(matches), 'url': url}
        except Exception as exc:
            return {'league': league['id'], 'season': season, 'ok': False, 'error': str(exc), 'url': url}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(one, [(l,y) for y in range(2010,2024) for l in LEAGUES]):
            status.append(result)
            print(result['league'], result['season'], result.get('matches', result.get('error')), flush=True)
    write_json(OUT/'history_import.json', {'fetched_at': utc_now(), 'attempts': status})


if __name__ == '__main__': run()
