"""Independent equation and pandas aggregation checks for the raw-feature study."""
from raw_feature_formula import ROOT, OUT, OLD, ROLES, inputs, plans, digest, write_json
import itertools
import json
import numpy as np
import pandas as pd


def independently_score(y, p, weights=None):
    y = np.asarray(y); p = np.asarray(p)
    w = np.ones(len(y)) if weights is None else np.asarray(weights)
    w = w / w.sum()
    ym = np.sum(w*y); pm = np.sum(w*p)
    vy = np.sum(w*(y-ym)**2); vp = np.sum(w*(p-pm)**2)
    mse = np.sum(w*(y-p)**2)
    return dict(r=None if min(vy, vp) < 1e-24 else np.sum(w*(y-ym)*(p-pm))/np.sqrt(vy*vp),
                r2=None if vy < 1e-24 else 1-mse/vy, rmse_pp=100*np.sqrt(mse),
                mae_pp=100*np.sum(w*np.abs(y-p)), bias_pp=100*np.sum(w*(p-y)))


def verify_score(actual, expected):
    for key, value in actual.items():
        if value is None:
            assert pd.isna(expected[key]), (key, expected[key])
        else:
            assert abs(value-expected[key]) < 1e-8, (key, value, expected[key])


def independent_kernel(a, b, numeric, family, tau, ell):
    similarities = []
    for j in range(a.shape[1]):
        if numeric[j]:
            similarities.append(np.exp(-np.subtract.outer(a[:, j], b[:, j])**2 / (2*ell**2)))
        else:
            similarities.append(np.equal.outer(a[:, j], b[:, j]).astype(float))
    if family == 'additive':
        return np.mean(similarities, axis=0)
    return np.prod([(1+tau*v)/(1+tau) for v in similarities], axis=0)


def core():
    from raw_feature_formula import gram, scale
    from scipy.linalg import solve
    x = np.array(list(itertools.product([0., 1.], repeat=4)))
    numeric = np.zeros(4, bool)
    for tau in [.1, 1.]:
        expansion = np.zeros((16, 16))
        for size in range(5):
            for subset in itertools.combinations(range(4), size):
                same = np.ones((16, 16))
                for j in subset:
                    same *= np.equal.outer(x[:, j], x[:, j])
                expansion += tau**size * same / (1+tau)**4
        assert np.max(np.abs(expansion-gram(x, x, numeric, 'joint', tau, 1.))) < 1e-14
    # A pure joint signal cancels in every single-field mean.
    signal = .1*np.prod(2*x-1, axis=1)
    for j in range(4):
        for level in [0, 1]:
            assert abs(signal[x[:, j] == level].mean()) < 1e-14
    k = gram(x, x, numeric, 'joint', 1., 1.)
    alpha = solve(k+16e-6*np.eye(16), signal)
    assert np.max(np.abs(k@alpha-signal)) < .00003
    z, center, spread = scale(x, np.array([0, 1]), np.ones(4, bool))
    assert np.array_equal(center, x[:2].mean(axis=0)) and np.isfinite(z).all()
    return dict(all_order_expansion='passed', cancelling_marginal_example='passed',
                dense_solve='passed', train_only_scaling='passed')


def main():
    checks = []; core_checks = core()
    for cohort in ['main', 'positive_garage']:
        g, bins, raw, y, mapping = inputs(cohort)
        for name in plans():
            folder = OUT / cohort / name
            meta = json.loads((folder / 'case.json').read_text())
            assert meta['script_sha256'] == digest(ROOT / 'scripts/raw_feature_formula.py')
            assert meta['protocol_sha256'] == digest(ROOT / 'docs/raw_feature_formula.md')
            split = pd.read_csv(folder / 'split.csv').set_index('record_id').loc[g.members.index]
            original = pd.read_csv(OLD / cohort / name / 'split.csv').set_index('record_id').loc[g.members.index]
            pd.testing.assert_frame_equal(split, original)
            tr = np.flatnonzero(split.role.eq('train')); te = np.flatnonzero(split.role.eq('test'))
            inner = np.flatnonzero(split.inner_role.eq('fit'))
            assert not set(tr) & set(te)
            assert len(tr) == meta['train_n'] and len(te) == meta['test_n']
            assert len(inner) == meta['inner_train_n']
            assert int(split.inner_role.eq('validation').sum()) == meta['inner_validation_n']
            p = pd.read_csv(folder / 'predictions.csv').set_index('record_id')
            assert list(p.index) == list(g.members.index[te])
            assert np.max(abs(p.actual-y[te])) < 1e-14
            assert np.max(abs(p.constant-y[tr].mean())) < 1e-14
            selection = pd.read_csv(folder / 'selection.csv', float_precision='round_trip')
            equation_max = 0.
            for role in ROLES[1:]:
                decision = meta['selected'][role]
                eligible = selection[selection.representation.eq(role.split('_')[0])]
                if role.endswith('_additive'):
                    eligible = eligible[eligible.family.eq('additive')]
                score = 'group_rmse_pp' if role.endswith('_group') else 'row_rmse_pp'
                best = eligible[eligible[score] <= eligible[score].min()+1e-10].iloc[0]
                for key in ['family', 'tau', 'ell', 'penalty', 'kernel_id']:
                    assert decision[key] == best[key], (cohort, name, role, key)
                model = np.load(folder / (role + '.npz'))
                x = raw if role.startswith('raw') else bins
                numeric = model['numeric']; center = np.zeros(x.shape[1]); spread = np.ones(x.shape[1])
                center[numeric] = x[tr][:, numeric].mean(axis=0)
                spread[numeric] = x[tr][:, numeric].std(axis=0); spread[spread == 0] = 1
                assert np.array_equal(center, model['center']) and np.array_equal(spread, model['spread'])
                assert np.array_equal(model['train_ids'], g.members.index[tr].to_numpy(str))
                z = (x-center)/spread
                assert np.array_equal(z[tr], model['train_x'])
                params = dict(numeric=numeric, family=str(model['family']), tau=float(model['tau']), ell=float(model['ell']))
                # Independent kernel with small blocks avoids retaining a 20 x n x n tensor.
                max_error = 0.
                for at in range(0, len(te), 24):
                    matrix = independent_kernel(z[te[at:at+24]], z[tr], **params)
                    pred = float(model['baseline']) + matrix @ model['alpha']
                    max_error = max(max_error, float(np.max(abs(pred-p[role].to_numpy()[at:at+24]))))
                assert max_error < 1e-9
                eq = independent_kernel(z[tr[:8]], z[tr], **params) @ model['alpha']
                eq += len(tr)*float(model['penalty'])*model['alpha'][:8]
                equation_max = max(equation_max, float(np.max(abs(eq-(y[tr[:8]]-y[tr].mean())))))
                assert equation_max < 1e-8
            row_scores = pd.read_csv(folder / 'row_metrics.csv').set_index('model')
            for role in ROLES:
                verify_score(independently_score(p.actual, p[role]), row_scores.loc[role])
            frame = pd.DataFrame(bins[te], columns=g.fields)
            frame['actual'] = p.actual.to_numpy()
            for role in ROLES:
                frame[role] = p[role].to_numpy()
            saved = pd.read_csv(folder / 'metrics.csv')
            all_rows = pd.read_csv(folder / 'groups.csv')
            for order in [1, 2]:
                aggregated = []
                for subset in itertools.combinations(g.fields, order):
                    grouped = frame.groupby(list(subset), sort=True)
                    data = grouped[['actual', *ROLES]].mean()
                    data['n'] = grouped.size()
                    data['partition'] = ' × '.join(subset)
                    indexes = data.index.tolist()
                    data['condition_codes'] = [' '.join(f'{field}={int(code)}' for field, code in
                        zip(subset, [key] if order == 1 else key)) for key in indexes]
                    aggregated.append(data.reset_index(drop=True))
                groups = pd.concat(aggregated, ignore_index=True)
                for minimum in [10, 30, 100]:
                    eligible = groups[groups.n >= minimum].copy()
                    counts = eligible.groupby('partition').size()
                    eligible = eligible[eligible.partition.isin(counts[counts >= 2].index)]
                    if not len(eligible):
                        continue
                    weights = 1 / eligible.partition.map(counts)
                    for role in ROLES:
                        row = saved[saved.model.eq(role)&saved.order.eq(order)&saved.minimum_n.eq(minimum)].iloc[0]
                        assert row.groups == len(eligible)
                        verify_score(independently_score(eligible.actual, eligible[role], weights), row)
                        if minimum == 30:
                            actual_rows = all_rows[all_rows.model.eq(role)&all_rows.order.eq(order)].set_index(['partition', 'condition_codes'])
                            expected = eligible.set_index(['partition', 'condition_codes']).loc[actual_rows.index]
                            assert np.array_equal(actual_rows.n, expected.n)
                            assert np.max(abs(actual_rows.actual-expected.actual)) < 1e-12
                            assert np.max(abs(actual_rows.predicted-expected[role])) < 1e-12
            checks.append(dict(cohort=cohort, case=name, test_rows=len(te), equation_max_residual=equation_max,
                               predictions='all rows independently reloaded', group_scores='all nonempty thresholds recomputed'))
            print(json.dumps(checks[-1]), flush=True)
    hashes = json.loads((OUT / 'provenance.json').read_text())
    for path, sha in hashes.items():
        assert digest(ROOT / path) == sha
    for path in ['scripts/query_group_means.py', 'scripts/group_mean_schema.py',
                 'scripts/scan_raw_formula_groups.py', 'scripts/scan_formula_groups.cpp',
                 'outputs/formula_validation/scan_formula_groups.exe',
                 'outputs/group_means/main.input.json', 'outputs/group_means/positive_garage.input.json']:
        hashes[path] = digest(ROOT / path)
    write_json(OUT / 'validation.json', dict(status='passed', cases=len(checks), core=core_checks,
        checks=checks, source_hashes=hashes, validator_sha256=digest(__file__),
        equation_scope='all saved predictions; independent residual check first 8 train rows per equation; full residual checked by fitter',
        limitation='retrospective internal tests; not external confirmation'))


if __name__ == '__main__':
    main()
