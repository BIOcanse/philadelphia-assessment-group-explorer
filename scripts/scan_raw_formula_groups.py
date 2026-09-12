"""Aggregate varying individual predictions through the original all-order catalog."""
from raw_feature_formula import ROOT, OUT, ROLES, SEEDS, Groups, write_json, save
from formula_validation import metrics
import ctypes
import json
import struct
import subprocess
import time
import numpy as np
import pandas as pd


def run(cohort):
    start = time.perf_counter(); g = Groups(cohort)
    case = OUT / cohort / f'random-{SEEDS[0]}-100'
    p = pd.read_csv(case / 'predictions.csv').set_index('record_id')
    x = g.members.loc[p.index, ['bin_'+f for f in g.fields]].to_numpy(np.int16)
    unique, inv, n = np.unique(x, axis=0, return_inverse=True, return_counts=True)
    u = len(unique); words = (u+63)//64
    # SUM per old profile, not one representative prediction: raw values differ within bins.
    weights = np.column_stack([n, *[np.bincount(inv, weights=p[c], minlength=u) for c in ['actual', *ROLES]]])
    atoms = []
    for atom in g.atoms:
        bits = np.zeros(words*64, np.uint8)
        bits[:u] = unique[:, g.fields.index(atom['name'])] == atom['category']
        atoms.append(np.packbits(bits, bitorder='little').view('<u8'))
    inp = OUT / (cohort+'_catalog_input.bin'); out = OUT / (cohort+'_catalog.bin')
    with inp.open('wb') as f:
        f.write(struct.pack('<5I', 0x46564c31, u, len(atoms), len(ROLES), words))
        np.array(atoms, dtype='<u8').tofile(f); weights.astype('<f8').tofile(f)
    result = subprocess.run([str(ROOT / 'outputs/formula_validation/scan_formula_groups.exe'), str(inp),
        str(ROOT / f'outputs/group_means/{cohort}.input_groups.bin'), str(out)],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180, check=True)
    summary = json.loads(result.stdout)
    assert summary['count_mismatches'] == 0
    values = np.memmap(out, dtype='<f8', mode='r').reshape(-1, 3+len(ROLES))
    rows = []
    for row in summary['metrics']:
        row.update(cohort=cohort, model=ROLES[row['method_index']]); rows.append(row)
        if row['basis'] == 'unique_test_members' and row['minimum_n'] >= 30:
            v = values[values[:, 1] >= row['minimum_n']]
            if not len(v):
                continue
            check = metrics(v[:, 2], v[:, 3+row['method_index']])
            assert abs(check['rmse_pp']-row['rmse_pp']) < 1e-8
            assert abs(check['r2']-row['r2']) < 1e-7
    # Validate arbitrary-order group sums against direct row membership on a fixed spaced sample.
    for idx in np.linspace(0, len(values)-1, min(40, len(values)), dtype=int):
        v = values[idx]; expression = g.expression(g.stats[int(v[0])])
        mask = np.ones(len(p), bool)
        for atom_id in expression:
            atom = g.atoms[atom_id]
            mask &= x[:, g.fields.index(atom['name'])] == atom['category']
        assert mask.sum() == v[1]
        assert np.max(abs(p.loc[mask, ['actual', *ROLES]].mean().to_numpy()-v[2:])) < 1e-10
    selected = values[:, 3+ROLES.index('raw_row')]
    worst = []
    for idx in np.argsort(abs(selected-values[:, 2]))[-12:][::-1]:
        row = g.row(int(values[idx, 0]))
        row.update(test_n=int(values[idx, 1]), test_actual_pct=100*values[idx, 2],
                   test_predicted_pct=100*selected[idx], error_pp=100*(selected[idx]-values[idx, 2]), cohort=cohort)
        worst.append(row)
    summary.update(cohort=cohort, seconds=time.perf_counter()-start, direct_membership_checks=40,
                   roles=ROLES, aggregation='sums of individual predictions within fixed binned profiles')
    save(rows, OUT / (cohort+'_catalog_metrics.csv')); save(worst, OUT / (cohort+'_catalog_worst.csv'))
    write_json(OUT / (cohort+'_catalog_summary.json'), summary)
    print(json.dumps({k: summary[k] for k in ['cohort', 'canonical_groups', 'saved_unique_n30', 'seconds']}), flush=True)


if __name__ == '__main__':
    ctypes.windll.kernel32.SetErrorMode(0x8003)
    for cohort in ['main', 'positive_garage']:
        run(cohort)
