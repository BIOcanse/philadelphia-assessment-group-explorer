"""Reconcile desktop test artifacts with the saved research snapshot."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/research_workbench'


def collect(editions):
    data = json.loads((ROOT/'workbench/static/research-data.json').read_text('utf-8'))
    profiles = {p[0]:p for cohort in data['cohorts'].values() for p in cohort['profiles']}
    results = {}
    for edition in editions:
        results[edition] = {}
        for kind in ['ui','race']:
            lines = (OUT/f'{edition}-{kind}-validation.log').read_text('utf-8-sig').splitlines()
            record = json.loads(next(line for line in lines if line.startswith('{"status"')))
            assert record['status'] == 'passed'
            results[edition][kind] = record
        with (OUT/f'{edition}-kernel.csv').open(encoding='utf-8-sig',newline='') as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == 576
        for row in rows:
            a,b = profiles[row['row_group']],profiles[row['column_group']]
            degree,d = int(row['degree']),len(a)-3
            h = sum(x==y for x,y in zip(a[3:],b[3:]))
            kernel = sum(math.comb(h,k) if k<=h else 0 for k in range(degree+1))/sum(math.comb(d,k) for k in range(degree+1))
            expected = kernel*math.sqrt(a[1]*b[1]) if row['count_weighted']=='true' else kernel
            assert abs(float(row['kernel'])-kernel)<1e-12 and abs(float(row['value'])-expected)<1e-10
        for prefix,metric in [('', 'original_mean_ratio'),('adjusted-', 'adjusted_residual')]:
            with (OUT/f'{edition}-{prefix}four-cell.csv').open(encoding='utf-8-sig',newline='') as stream:
                cells = list(csv.DictReader(stream))
            assert len(cells)==4
            interaction = next(r for r in data['interactions'] if r['interaction_id']==cells[0]['interaction_id'])
            column = 'mean' if metric=='original_mean_ratio' else 'residual'
            prediction = 100*(interaction[column+'10']+interaction[column+'01']-interaction[column+'00'])
            for row in cells:
                assert row['metric']==metric and row['unit']==('percent' if column=='mean' else 'percentage_points')
                assert abs(float(row['plotted_value'])-100*interaction[column+row['cell']])<1e-10
                if row['cell']=='11': assert abs(float(row['additive_prediction'])-prediction)<1e-10
        results[edition]['export_reconciliation'] = dict(status='passed',kernel_cells=576,four_cell_rows=8)
    result = dict(status='passed',version='v1.1.0',data_version=data['version'],editions=results,
        review_fixes=['Guard delayed atlas rendering','Use visible cohort for unqualified group lookups',
                      'Invalidate dismissed detail requests','Export additive predictions with metric and units'],
        source_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [
            'workbench/static/app.js','workbench/static/research.js','workbench/static/research.css','workbench/static/index.html']})
    (OUT/'workbench-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(status='passed',editions={c:dict(ui=len(r['ui']['checks']),races=len(r['race']['checks']),export_rows=584) for c,r in results.items()})))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--editions',nargs='+',default=['local','static']);args=parser.parse_args()
    collect(args.editions)
