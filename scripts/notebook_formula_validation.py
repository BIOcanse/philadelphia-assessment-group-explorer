"""Execute and save the report's audit companion using the established scaffold."""
from pathlib import Path
import contextlib
import io
import json

ROOT=Path(__file__).resolve().parents[1]
cells=[dict(cell_type='markdown',id='summary',metadata={},source=['# Formula validation / 公式验证\n\n',
    '## tl;dr\nThe original equation has now been tested on held-out group means. Additive structure predicts some differences; unregularized exact interpolation is unstable.\n\n',
    '## Context & Methods\nThis is a companion audit, not a new fit. Four code cells below are actually executed in order by Python. Full fits: `formula_validation.py real`, `formula_validation.py synthetic`, `formula_validation.py collect`; independent checks: `validate_formula_validation.py`; directory audit: `scan_formula_groups.py`.\n\n',
    '### Key Assumptions\nFrozen historical bins and previously explored 2017 records. Group arithmetic mean of sale/original assessment. Repeated groups are dependent. No pre-sale or citywide claim.\n'])]
sections=[('data','## Data',"""import json,math
from pathlib import Path
import numpy as np
import pandas as pd
root=Path.cwd()
if not (root/'scripts').exists():root=root.parent
out=root/'outputs/formula_validation'
qa=json.loads((out/'validation.json').read_text())
assert qa['status']=='passed' and len(qa['cases'])==30
cases=pd.read_csv(out/'cases.csv')
print(cases.groupby(['cohort','kind']).size().to_string())
"""),('scores','## Results: recompute group scores',"""groups=pd.read_csv(out/'main/random-20260908-100/groups.csv')
for role in ['additive','original_k3','selected']:
    a=groups[groups.model.eq(role)&groups.order.eq(1)]
    weights=1/a.partition.map(a.groupby('partition').size()).to_numpy()
    weights=weights/weights.sum();y=a.actual.to_numpy();p=a.predicted.to_numpy()
    mse=np.sum(weights*(y-p)**2);variance=np.sum(weights*(y-np.sum(weights*y))**2)
    print(role,'groups',len(a),'R2',round(1-mse/variance,6),'RMSE pp',round(100*np.sqrt(mse),6))
"""),('equation','## Results: evaluate the saved equation',"""model=np.load(out/'main/random-20260908-100/selected.npz')
predictions=pd.read_csv(out/'main/random-20260908-100/predictions.csv').set_index('record_id')
bins=pd.read_csv(root/'outputs/group_means/record_bins.csv').set_index('record_id')
meta=json.loads((root/'outputs/group_means/main.input.json').read_text())
ids=predictions.index[:5];x=bins.loc[ids,['bin_'+f for f in meta['fields']]].to_numpy()
u=model['profile_bins'];k=int(model['degree']);d=x.shape[1]
h=(x[:,None,:]==u[None,:,:]).sum(axis=2)
normal=sum(math.comb(d,t) for t in range(k+1))
lookup=np.array([sum(math.comb(v,t) for t in range(min(v,k)+1))/normal for v in range(d+1)])
computed=float(model['baseline'])+lookup[h]@model['alpha']
np.testing.assert_allclose(computed,predictions.loc[ids,'selected'],atol=1e-10,rtol=0)
print('Saved formula degree:',k,'maximum prediction discrepancy:',float(np.max(np.abs(computed-predictions.loc[ids,'selected']))))
"""),('known','## Results: known-answer and complete-directory checks',"""s=pd.read_csv(out/'synthetic/metrics.csv')
print(s[s.signal.eq('four_way')&s.noise_pp.eq(0)&s.support.eq('unseen')&s.degree.isin([3,4,8])][['degree','truth_rmse_pp','truth_r2']].to_string(index=False))
for cohort in ['main','positive_garage']:
    c=json.loads((out/(cohort+'_catalog_summary.json')).read_text())
    assert c['count_mismatches']==0 and c['maximum_ratio_sum_error']<1e-8
    print(cohort,'unique held-out member groups:',c['unique_test_member_groups'])
""")]
environment={}
for count,(id,title,code) in enumerate(sections,1):
    cells.append(dict(cell_type='markdown',id=id+'-title',metadata={},source=[title+'\n']))
    stream=io.StringIO()
    with contextlib.redirect_stdout(stream):exec(compile(code,'formula_validation_companion','exec'),environment)
    cells.append(dict(cell_type='code',id=id,metadata={},execution_count=count,source=code.splitlines(keepends=True),
        outputs=[dict(output_type='stream',name='stdout',text=stream.getvalue().splitlines(keepends=True))]))
cells.append(dict(cell_type='markdown',id='takeaways',metadata={},source=['## Takeaways\n\nMathematical equivalence passed. Generalization depends on support, noise and model selection. Test controlled shrinkage against the prespecified additive baseline before claiming stable joint improvements.\n']))
notebook=dict(nbformat=4,nbformat_minor=5,metadata={'kernelspec':{'name':'python3','language':'python','display_name':'Python 3'}},cells=cells)
path=ROOT/'notebooks/formula_validation.ipynb';path.write_text(json.dumps(notebook,ensure_ascii=False,indent=2),encoding='utf-8')
loaded=json.loads(path.read_text());assert loaded['nbformat']==4
assert [c['execution_count'] for c in loaded['cells'] if c['cell_type']=='code']==[1,2,3,4]
assert len({c['id'] for c in loaded['cells']})==len(loaded['cells'])
print('Companion notebook: four audit cells executed and recorded.')
