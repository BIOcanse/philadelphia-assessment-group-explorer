"""Compare a running portable package with the established local query service."""
import argparse
import csv
import io
import json
from pathlib import Path
import time
import urllib.request


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=30) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--portable', default='http://127.0.0.1:8769')
    parser.add_argument('--reference', default='http://127.0.0.1:8767')
    parser.add_argument('--output', type=Path, default=Path('outputs/group_publication/portable-validation.json'))
    args = parser.parse_args(); checks = []; tick = time.perf_counter()
    for cohort in ['main', 'positive_garage']:
        for minimum in [1, 100, 500]:
            for direction in ['high', 'low', 'support']:
                path = f'/api/search?cohort={cohort}&min_n={minimum}&sort={direction}&limit=5'
                expected = json.loads(get(args.reference, path))
                actual = json.loads(get(args.portable, path))
                assert actual == expected, path
                checks.append(f'{cohort}: n>={minimum}, {direction}, count/full histogram/rows')
        for identifier in [cohort+'-00000000', 'M025' if cohort == 'main' else 'G025', 'P1029']:
            path = f'/api/group?cohort={cohort}&id={identifier}'
            assert json.loads(get(args.portable, path)) == json.loads(get(args.reference, path)), path
            checks.append(cohort + ': detail/conditions/members/all fields: ' + identifier)
        path = f'/api/search?cohort={cohort}&min_n=100&condition=age%3D3&min_ratio=105&max_ratio=110&limit=5'
        assert json.loads(get(args.portable, path)) == json.loads(get(args.reference, path)), path
        checks.append(cohort + ': combined condition and ratio filter')
    path = '/api/export.csv?cohort=main&min_n=500&condition=age%3D3&limit=5'
    parsed = lambda base: list(csv.reader(io.StringIO(get(base, path).decode('utf-8-sig'))))
    assert parsed(args.portable) == parsed(args.reference)
    checks.append('Filtered CSV: every cell')
    assert get(args.portable, '/downloads/Group_ID_Dictionary.xlsx') == get(args.reference, '/downloads/Group_ID_Dictionary.xlsx')
    checks.append('Original Excel companion: exact bytes')
    assert b'query-client.js' in get(args.portable, '/') and b'Local edition' in get(args.portable, '/query-client.js')
    checks.append('Local interface served from the portable package')
    result = dict(status='passed', checks=checks, seconds=time.perf_counter()-tick,
                  runtime='Python 3.13.15 / NumPy 2.3.5 / pandas 3.0.1', data_version='groups-b5a7e308e8c6')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(dict(status='passed', checks=len(checks), seconds=result['seconds'])), flush=True)


if __name__ == '__main__':
    main()
