"""Export completed research and canonical group references; no model fitting."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workbench'))
from catalog import Catalog
import hashlib
import gzip
import json
import time
import zipfile
import numpy as np
import pandas as pd

TARGET = ROOT / 'workbench/static'
AUDIT = ROOT / 'outputs/research_workbench'
SUPPORTS = [1, 10, 30, 100, 300, 500, 1000, 2000]


def build():
    start = time.perf_counter()
    catalog = Catalog()
    sources = {}

    def source(relative):
        path = ROOT / 'outputs' / relative
        body = path.read_bytes()
        sources[relative] = dict(path='outputs/' + relative, sha256=hashlib.sha256(body).hexdigest(), bytes=len(body))
        return path

    def frame(relative):
        data = pd.read_csv(source(relative))
        sources[relative]['rows'] = len(data)
        return data

    def csv(relative):
        return json.loads(frame(relative).to_json(orient='records', force_ascii=False, double_precision=15))

    def saved(relative):
        return json.loads(source(relative).read_text('utf-8'))

    groups, resolved, indexes = {}, {}, {}
    for cohort, db in catalog.cohorts.items():
        order = np.load(source('group_means/' + cohort + '_closure_index.npy'), mmap_mode='r')
        keys = np.empty(len(order), dtype=[('lo', '<u8'), ('hi', '<u8')])
        keys['lo'] = db.g.stats['closure_lo'][order]
        keys['hi'] = db.g.stats['closure_hi'][order]
        indexes[cohort] = (keys, order)

    def register(cohort, index):
        group_id = f'{cohort}-{int(index):08d}'
        if group_id not in groups:
            row = catalog.cohorts[cohort].g.row(int(index))
            groups[group_id] = [row['n'], row['mean_ratio'], row['condition_codes']]
        return group_id

    def resolve(cohort, codes, expected_n=None, expected_ratio=None):
        key = (cohort, ' '.join(sorted(codes.split())))
        if key not in resolved:
            db = catalog.cohorts[cohort]
            extent = db.g.extent(db.g.condition_ids(codes.split()))
            assert extent, key
            closure = sum(1 << a for a, bits in enumerate(db.g.atom_bits) if extent & bits == extent)
            keys, order = indexes[cohort]
            target = np.array((closure & ((1 << 64) - 1), closure >> 64), dtype=keys.dtype)
            at = int(np.searchsorted(keys, target))
            assert at < len(keys) and keys[at] == target, key
            resolved[key] = register(cohort, order[at])
        group_id = resolved[key]
        n, mean, _ = groups[group_id]
        if expected_n is not None: assert n == expected_n, (key, n, expected_n)
        if expected_ratio is not None: assert abs(mean - expected_ratio) < 1e-11, (key, mean, expected_ratio)
        return group_id

    def register_rows(rows):
        for row in rows:
            group_id = row.get('group_id')
            if group_id:
                cohort, index = group_id.rsplit('-', 1)
                register(cohort, int(index))
        return rows

    payload = dict(schema=1, version=catalog.manifest['version'], app_version='1.1.0', metadata=catalog.metadata(),
        units=dict(group='Distinct non-root member set; cohorts overlap', expression='Supported concrete condition expression, k=1..d; equivalent members are counted again',
                   ratio='Arithmetic mean of individual sale/original-assessment ratios', pp='Percentage points', price_band='2017 transactions: median ratio and interquartile range'),
        cohorts={}, groups=groups, price_bands=csv('exploration/price_bands_2017.csv'), scope=csv('conditional/source_scope.csv'),
        thresholds=csv('group_bias/threshold_counts.csv'), bias_summary=saved('group_bias/report_summary.json'),
        controls=csv('group_bias/standardization.csv'), interactions=csv('conditional/interactions.csv'),
        leads=csv('conditional/研究线索_Research_Leads.csv'), performance=csv('conditional/performance.csv'), gains=csv('conditional/performance_gains.csv'),
        availability=csv('selection_audit/availability_summary.csv'), coverage=csv('selection_audit/coverage_by_price.csv'),
        history_price=csv('selection_audit/history_stages_by_price.csv'), edge_summary=saved('edge_groups/summary.json'),
        conditional_summary=saved('conditional/report_summary.json'),
        research_notes={area:saved(area+'/report_notes.json') for area in ['conditional','group_bias','group_algebra','selection_audit']})
    for row in payload['interactions']:
        row['cell_groups'] = []
        for a, b in [(0, 0), (0, 1), (1, 0), (1, 1)]:
            cell = f'{a}{b}'
            codes = f"{row['field_a']}={row['a' + str(a)]} {row['field_b']}={row['b' + str(b)]}"
            row['cell_groups'].append(resolve(row['cohort'], codes, row['n' + cell], row['mean' + cell]))
        assert abs((row['mean11'] - row['mean10']) - (row['mean01'] - row['mean00']) - row['raw_interaction']) < 1e-11

    for lead in payload['leads']:
        candidates = [r for r in payload['interactions'] if abs(100*r['raw_interaction']-lead['raw_pp']) < 1e-9
                      and abs(100*r['adjusted_interaction']-lead['adjusted_pp']) < 1e-9]
        assert len(candidates) == 1
        lead['interaction_id'] = candidates[0]['interaction_id']
        lead['cohort_id'] = candidates[0]['cohort']
    edges = csv('edge_groups/edge_extremes.csv')
    for row in edges:
        row['expression_id'] = row.pop('group_id')
        row['group_id'] = resolve(row['cohort'], row['condition_codes'], row['n'], row['mean_ratio'])
    payload['edges'] = edges
    for row in payload['controls']:
        assert resolve(row['cohort'], row['original_codes'], row['original_n'], row['original_ratio']) == row['group_id']
        row['parent_id'] = resolve(row['cohort'], row['parent_codes'], row['original_n'] + row['added_n'])
        if row['status'] == 'computed':
            assert row['common_original_n'] > 0 and row['common_added_n'] > 0
            assert abs(row['raw_gap_pp'] - row['support_change_pp'] - row['mix_change_pp'] - row['standardized_gap_pp']) < 1e-9
        else: assert row['standardized_gap_pp'] is None

    for cohort, db in catalog.cohorts.items():
        atlas, algebra = 'group_atlas/' + cohort, 'group_algebra/' + cohort
        info = dict(frontier=csv(atlas + '_frontier_all_n.csv'), candidates=register_rows(csv(atlas + '_candidates.csv')),
            relaxations=csv(atlas + '_relaxations.csv'), slices=csv(atlas + '_slices.csv'), orders=csv(algebra + '_orders.csv'),
            errors=csv(algebra + '_group_errors.csv'), worst=register_rows(csv(algebra + '_worst_groups.csv')),
            unfoldings=csv(algebra + '_unfoldings.csv'), summary=saved(algebra + '_summary.json'),
            histogram=csv('edge_groups/' + cohort + '_histogram.csv'), histogram_orders=csv('edge_groups/' + cohort + '_histogram_by_k.csv'),
            rankings={}, profiles=[])
        for row in info['relaxations']:
            row['parent_id'] = resolve(cohort, row['parent_codes'], row['parent_n'], row['parent_ratio'])
        for row in info['errors']:
            row['worst_group_id'] = register(cohort, row['worst_index'])
        for minimum in SUPPORTS:
            info['rankings'][str(minimum)] = {side: [register(cohort, i) for i in order[(db.n[order] >= minimum) & db.valid[order]][:10]] for side, order in db.orders.items()}
        prefix = 'M' if cohort == 'main' else 'G'
        for row in frame(algebra + '_profiles.csv').to_dict('records'):
            assert int(row['profile_id']) == len(info['profiles'])
            group_id = catalog.manifest['aliases'][f"{prefix}-P{int(row['profile_id']):06d}"]
            info['profiles'].append([group_id, row['n'], row['mean_ratio'], *[int(row[field]) for field in db.g.fields]])
            register(cohort, int(group_id.rsplit('-', 1)[1]))
        assert sum(r[1] for r in info['profiles']) == len(db.g.members)
        assert len(info['profiles']) == info['summary']['profiles']
        assert int(info['frontier'][0]['distinct_groups']) == int(db.valid.sum())
        expr = next(r for r in payload['edge_summary']['histograms'] if r['cohort'] == cohort)
        assert sum(r['group_count'] for r in info['histogram']) == expr['supported_expressions']
        assert sum(r['group_count'] for r in info['histogram_orders'] if r['fields'] > 0) == expr['supported_expressions']
        payload['cohorts'][cohort] = info
        print(json.dumps(dict(stage='cohort', cohort=cohort, linked_groups=len(groups))), flush=True)

    assert len(payload['interactions']) == 4802 and len(payload['controls']) == 1920
    assert sum(r['status'] == 'computed' for r in payload['controls']) == 653
    assert sum(r['n'] for r in payload['price_bands']) == 8595
    payload['chart_sources'] = {
        'priceChart': ['exploration/price_bands_2017.csv'], 'frontierChart': ['group_atlas/{cohort}_frontier_all_n.csv'],
        'expressionChart': ['edge_groups/{cohort}_histogram.csv', 'edge_groups/{cohort}_histogram_by_k.csv'],
        'biasChart': ['group_bias/threshold_counts.csv'],
        'comparisonChart': ['group_bias/standardization.csv', 'group_atlas/{cohort}_relaxations.csv'],
        'timeChart': ['group_atlas/{cohort}_slices.csv'], 'interactionChart': ['conditional/interactions.csv'],
        'interactionScanChart': ['conditional/interactions.csv'], 'rankChart': ['group_algebra/{cohort}_orders.csv'],
        'errorChart': ['group_algebra/{cohort}_group_errors.csv'], 'kernelChart': ['group_algebra/{cohort}_profiles.csv'],
        'performanceChart': ['conditional/performance_gains.csv', 'conditional/performance.csv'],
        'coverageChart': ['selection_audit/coverage_by_price.csv', 'selection_audit/availability_summary.csv']}
    payload['sources'] = list(sources.values())
    body = json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    (TARGET / 'research-data.json').write_bytes(body)
    (TARGET / 'research-data.json.gz').write_bytes(gzip.compress(body,compresslevel=6,mtime=0))
    with zipfile.ZipFile(TARGET / 'research-sources.zip', 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=5) as archive:
        for item in sources.values():
            if Path(item['path']).suffix in ['.csv', '.json']: archive.write(ROOT / item['path'], item['path'])
        archive.writestr('source-manifest.json', json.dumps(payload['sources'], ensure_ascii=False, indent=2))
    AUDIT.mkdir(parents=True, exist_ok=True)
    validation = dict(status='passed', data_version=payload['version'], app_version=payload['app_version'],
        linked_groups=len(groups), resolved_expressions=len(resolved), interactions=4802, controls=1920,
        common_support_comparisons=653, bytes=len(body), seconds=time.perf_counter()-start,
        snapshot_sha256=hashlib.sha256(body).hexdigest(), sources=payload['sources'],
        checks=['Every four-cell n and mean matches its canonical group', 'Every group summary comes from the exact catalog',
                'All condition resolutions match the saved closure index', 'Common-support decomposition reconciles',
                'Unavailable controls remain null', 'Expression histograms reconcile to exhaustive totals',
                'Profile counts reconcile to transaction counts', 'Support frontiers reconcile to registry counts'])
    (AUDIT / 'data-validation.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in validation.items() if k != 'sources'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    build()
