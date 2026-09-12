"""Frozen individual-loss kernel study; preserves previous experiments."""
from formula_validation import (ROOT, Groups, Partitions, metrics, write_json, save,
                                digest, SEEDS, threadpool_limits)
from pathlib import Path
from scipy.linalg import eigh, cho_factor, cho_solve
import argparse
import ctypes
import json
import time
import numpy as np
import pandas as pd

OUT = ROOT / 'outputs/raw_feature_formula'
OLD = ROOT / 'outputs/formula_validation'
LAMBDAS = [1., .1, .01, .001, .0001, .00001, .000001]
ROLES = ['constant', 'bins_group', 'bins_row', 'raw_group', 'raw_row',
         'bins_additive', 'raw_additive']
LOG_FIELDS = {'area', 'cityhall', 'jobs_density', 'assault', 'burglary',
              'vehicle_theft', 'robbery', 'garage'}


def inputs(cohort):
    g = Groups(cohort)
    source = pd.read_csv(ROOT / 'outputs/enrichment/sales_enriched_2017.csv',
                         dtype={'record_id': str, 'parcel_id_raw': str, 'zip5': str})
    assert source.record_id.is_unique and source.parcel_id_raw.is_unique
    source = source.set_index('record_id').loc[g.members.index]
    y = g.members.ratio.to_numpy(float)
    assert np.allclose(y, source.sale_price_usd / source.assessed_value_usd, rtol=0, atol=1e-12)
    definitions = json.loads((ROOT / 'outputs/group_means/bin_definitions.json').read_text('utf-8'))
    mapping = {f['name']: f['source_column'] for f in definitions['fields']}
    bins = g.members[['bin_' + f for f in g.fields]].to_numpy(float)
    raw = np.empty_like(bins)
    info = []
    for j, field in enumerate(g.fields):
        col = mapping[field]
        if field.startswith('school'):
            col = col.replace('_tier', '_score100')
        if field == 'zip':
            raw[:, j] = bins[:, j]
        else:
            raw[:, j] = pd.to_numeric(source[col], errors='raise')
            if field in LOG_FIELDS:
                assert np.all(raw[:, j] >= 0)
                raw[:, j] = np.log1p(raw[:, j])
        info.append(dict(field=field, source_column=col,
                         transform='nominal frozen code' if field == 'zip' else
                         'log1p then training z-score' if field in LOG_FIELDS else 'training z-score'))
    assert np.isfinite(raw).all() and np.isfinite(y).all()
    return g, bins, raw, y, info


def scale(x, fit, numeric):
    center = np.zeros(x.shape[1]); spread = np.ones(x.shape[1])
    center[numeric] = x[fit][:, numeric].mean(axis=0)
    spread[numeric] = x[fit][:, numeric].std(axis=0)
    spread[spread == 0] = 1
    return (x - center) / spread, center, spread


def candidates(representation):
    result = []
    for family, tau in [('additive', 0.), ('joint', .1), ('joint', 1.)]:
        for ell in ([.5, 1., 2.] if representation == 'raw' else [1.]):
            result.append(dict(family=family, tau=tau, ell=ell))
    return result


def gram(a, b, numeric, family, tau, ell):
    result = np.zeros((len(a), len(b))) if family == 'additive' else np.ones((len(a), len(b)))
    for j in range(a.shape[1]):
        if numeric[j]:
            base = (a[:, j, None] - b[None, :, j]) / ell
            np.square(base, out=base); base *= -.5; np.exp(base, out=base)
        else:
            base = (a[:, j, None] == b[None, :, j]).astype(float)
        if family == 'additive':
            result += base / a.shape[1]
        else:
            result *= (1 + tau * base) / (1 + tau)
    return result


def choose(rows, score, additive=False):
    eligible = [r for r in rows if not additive or r['family'] == 'additive']
    best = min(r[score] for r in eligible)
    return next(r for r in eligible if r[score] <= best + 1e-10)


def run_case(cohort, name):
    start = time.perf_counter()
    g, bins, raw, y, mapping = inputs(cohort)
    folder = OUT / cohort / name; folder.mkdir(parents=True, exist_ok=True)
    previous = json.loads((OLD / cohort / name / 'case.json').read_text())
    split_path = OLD / cohort / name / 'split.csv'
    split = pd.read_csv(split_path).set_index('record_id').loc[g.members.index]
    train = np.flatnonzero(split.role.eq('train')); test = np.flatnonzero(split.role.eq('test'))
    fit = np.flatnonzero(split.inner_role.eq('fit')); val = np.flatnonzero(split.inner_role.eq('validation'))
    assert not set(train) & set(test) and not set(fit) & set(val)
    assert set(fit) | set(val) == set(train)
    split.to_csv(folder / 'split.csv')
    write_json(folder / 'fields.json', mapping)
    labels = {f"{a['name']}={a['category']}": a['label'] for a in g.atoms}
    inner_layout = Partitions(bins[val], g.fields, labels=labels)
    layouts = {k: Partitions(bins[test], g.fields, k, labels) for k in [1, 2]}
    baseline = float(y[train].mean()); inner_mean = float(y[fit].mean())
    predictions = pd.DataFrame(dict(record_id=g.members.index[test], actual=y[test], constant=baseline))
    selections = []; selected = {}; residuals = []
    for representation, x in [('bins', bins), ('raw', raw)]:
        numeric = np.array([representation == 'raw' and field != 'zip' for field in g.fields])
        z, _, _ = scale(x, fit, numeric)
        scores = []
        for kernel_id, params in enumerate(candidates(representation)):
            tick = time.perf_counter()
            matrix = gram(z[fit], z[fit], numeric, **params)
            eigenvalues, vectors = eigh(matrix, overwrite_a=True, check_finite=False, driver='evd')
            assert eigenvalues.min() > -1e-8 * len(fit)
            eigenvalues = np.maximum(eigenvalues, 0)
            rhs = vectors.T @ (y[fit] - inner_mean)
            projected = gram(z[val], z[fit], numeric, **params) @ vectors
            for penalty in LAMBDAS:
                pred = inner_mean + projected @ (rhs / (eigenvalues + len(fit) * penalty))
                group_score, _, _ = inner_layout.evaluate(y[val], pred, 5, inner_mean)
                assert group_score['rmse_pp'] is not None
                scores.append(dict(representation=representation, kernel_id=kernel_id, **params,
                                   penalty=penalty, row_rmse_pp=metrics(y[val], pred)['rmse_pp'],
                                   group_rmse_pp=group_score['rmse_pp']))
            print(json.dumps(dict(cohort=cohort, case=name, stage='selection', representation=representation,
                                  kernel_id=kernel_id, seconds=round(time.perf_counter()-tick, 2))), flush=True)
        del eigenvalues, vectors, projected, matrix
        selections.extend(scores)
        decisions = {representation + '_row': choose(scores, 'row_rmse_pp'),
                     representation + '_group': choose(scores, 'group_rmse_pp'),
                     representation + '_additive': choose(scores, 'row_rmse_pp', True)}
        z, center, spread = scale(x, train, numeric)
        grouped = {}
        for role, decision in decisions.items():
            key = (decision['kernel_id'], decision['penalty'])
            grouped.setdefault(key, []).append(role)
            selected[role] = decision
        for (_, penalty), roles in grouped.items():
            params = {k: decisions[roles[0]][k] for k in ['family', 'tau', 'ell']}
            matrix = gram(z[train], z[train], numeric, **params)
            matrix.flat[::len(train)+1] += len(train) * penalty
            factor = cho_factor(matrix, check_finite=False)
            alpha = cho_solve(factor, y[train] - baseline, check_finite=False)
            error = np.max(np.abs(matrix @ alpha - (y[train] - baseline)))
            assert error < 1e-8
            pred = baseline + gram(z[test], z[train], numeric, **params) @ alpha
            for role in roles:
                predictions[role] = pred
                np.savez_compressed(folder / (role + '.npz'), train_x=z[train], numeric=numeric,
                                    center=center, spread=spread, train_ids=g.members.index[train].to_numpy(str),
                                    alpha=alpha, baseline=baseline, penalty=penalty, **params)
                residuals.append(dict(model=role, equation_max_residual=float(error)))
            del matrix, factor
    scores = []; groups = []; partitions = []; row_scores = []
    for role in ROLES:
        pred = predictions[role].to_numpy()
        row_scores.append(dict(model=role, **metrics(y[test], pred, baseline=baseline)))
        for order, layout in layouts.items():
            for minimum in [10, 30, 100]:
                score, rows, parts = layout.evaluate(y[test], pred, minimum, baseline)
                scores.append(dict(model=role, **score))
                if minimum == 30:
                    groups.extend(dict(model=role, **r) for r in rows)
                    partitions.extend(dict(model=role, **r) for r in parts)
    for rows, file in [(selections, 'selection'), (scores, 'metrics'), (groups, 'groups'),
                       (partitions, 'partitions'), (row_scores, 'row_metrics'), (residuals, 'equation_checks')]:
        save(rows, folder / (file + '.csv'))
    predictions.to_csv(folder / 'predictions.csv', index=False, float_format='%.17g')
    meta = {k: previous[k] for k in ['cohort', 'case', 'kind', 'seed', 'fraction', 'train_n', 'test_n',
                                    'inner_train_n', 'inner_validation_n']}
    meta.update(selected=selected, train_mean=baseline, status='completed',
                source_split_sha256=digest(split_path), protocol_sha256=digest(ROOT / 'docs/raw_feature_formula.md'),
                script_sha256=digest(__file__), seconds=time.perf_counter()-start)
    write_json(folder / 'case.json', meta)
    print(json.dumps(meta), flush=True)


def plans():
    return [f'random-{seed}-{fraction:03d}' for seed in SEEDS for fraction in [50, 100]] + [
        f'{kind}-{SEEDS[0]}-100' for kind in ['profile', 'spatial', 'time']]


def combine():
    cases = []; frames = {k: [] for k in ['metrics', 'row_metrics', 'selection']}
    for cohort in ['main', 'positive_garage']:
        for name in plans():
            folder = OUT / cohort / name
            meta = json.loads((folder / 'case.json').read_text())
            assert meta['script_sha256'] == digest(__file__)
            cases.append({k: v for k, v in meta.items() if k != 'selected'})
            for key in frames:
                f = pd.read_csv(folder / (key + '.csv'))
                for col in ['cohort', 'case', 'kind', 'seed', 'fraction', 'train_n', 'test_n']:
                    f[col] = meta[col]
                frames[key].append(f)
    save(cases, OUT / 'cases.csv')
    for key, fs in frames.items():
        pd.concat(fs, ignore_index=True).to_csv(OUT / (key + '.csv'), index=False, float_format='%.17g')
    write_json(OUT / 'provenance.json', {str(p.relative_to(ROOT)): digest(p) for p in [
        ROOT / 'docs/raw_feature_formula.md', Path(__file__), ROOT / 'scripts/formula_validation.py',
        ROOT / 'outputs/enrichment/sales_enriched_2017.csv', ROOT / 'outputs/group_means/record_bins.csv',
        ROOT / 'outputs/group_means/bin_definitions.json']})


def main():
    ctypes.windll.kernel32.SetErrorMode(0x8003)
    parser = argparse.ArgumentParser()
    parser.add_argument('--cohort', choices=['main', 'positive_garage'])
    parser.add_argument('--case'); parser.add_argument('--combine', action='store_true')
    args = parser.parse_args()
    with threadpool_limits(limits=2):
        if args.combine:
            combine(); return
        for cohort in ([args.cohort] if args.cohort else ['main', 'positive_garage']):
            for name in ([args.case] if args.case else plans()):
                run_case(cohort, name)
        if not args.case and not args.cohort:
            combine()


if __name__ == '__main__':
    main()
