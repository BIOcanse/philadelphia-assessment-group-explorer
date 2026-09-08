"""Independent explicit-design and saved-prediction checks for kernel validation."""
from formula_validation import ROOT,OUT,Training,metrics,digest,write_json,RTOL
import argparse
import itertools
import json
import math
import numpy as np
import pandas as pd
from scipy.linalg import lstsq
from threadpoolctl import threadpool_limits

def core():
    rng=np.random.default_rng(9182)
    cube=np.array(list(itertools.product([0,1],repeat=4)),dtype=np.int16)
    train=cube[rng.permutation(16)[:12]]
    x=np.repeat(train,rng.integers(1,5,len(train)),axis=0);y=1+rng.normal(0,.1,len(x))
    test=np.vstack([cube,[[2,0,1,1]]]);system=Training(x,y);checks=[]
    for k in range(5):
        columns=[]
        for order in range(k+1):
            for subset in itertools.combinations(range(4),order):
                for levels in itertools.product(*[np.unique(np.vstack([x,test])[:,j]) for j in subset]):
                    columns.append((subset,levels))
        norm=math.sqrt(sum(math.comb(4,t) for t in range(k+1)))
        def design(a):
            return np.array([np.all(a[:,subset]==levels,axis=1).astype(float) for subset,levels in columns]).T/norm
        d=design(x);dt=design(test)
        coef,_,rank,_=lstsq(d,y-y.mean(),cond=math.sqrt(RTOL),lapack_driver='gelsd')
        m=system.fit(k);pred=m.predict(test)
        error=float(np.max(np.abs(pred-(y.mean()+dt@coef))))
        assert error<1e-9,(k,error)
        assert m.rank==rank,(k,m.rank,rank)
        checks.append(dict(degree=k,explicit_rank=int(rank),maximum_prediction_error=error))
    shifted=metrics([.9,1.,1.1],[1.2,1.3,1.4])
    assert abs(shifted['r']-1)<1e-12 and shifted['r2']<0
    assert metrics([1.,1.],[1.,1.])['r'] is None
    assert metrics([.9,1.1],[1.,1.])['r'] is None
    return dict(explicit_design_predictions=checks,correlation_not_accuracy=shifted)

def saved():
    config=json.loads((OUT/'config.json').read_text())
    assert config['script_sha256']==digest(ROOT/'scripts/formula_validation.py')
    for source,sha in config['source_hashes'].items():assert digest(ROOT/source)==sha,source
    raw=pd.read_csv(ROOT/'outputs/group_means/record_bins.csv').set_index('record_id')
    all_cases=pd.read_csv(OUT/'cases.csv');assert len(all_cases)==30
    expected_cases={f'random-{seed}-{fraction:03d}' for seed in [20260908,20260909,20260910] for fraction in [10,25,50,100]}
    expected_cases.update(f'{kind}-20260908-100' for kind in ['profile','spatial','time'])
    for cohort in ['main','positive_garage']:assert set(all_cases.loc[all_cases.cohort.eq(cohort),'case'])==expected_cases
    checks=[];coverage=[]
    for case in all_cases.itertuples():
        folder=OUT/case.cohort/case.case
        split=pd.read_csv(folder/'split.csv');pred=pd.read_csv(folder/'predictions.csv').set_index('record_id')
        train=split.loc[split.role.eq('train'),'record_id'];test=split.loc[split.role.eq('test'),'record_id']
        assert not set(train)&set(test) and set(test)==set(pred.index)
        assert split.loc[split.inner_role.isin(['fit','validation']),'role'].eq('train').all()
        selection=pd.read_csv(folder/'selection.csv')
        d=20 if case.cohort=='main' else 21
        assert selection.degree.tolist()==list(range(d+1))
        best=selection.inner_rmse_pp.min()
        chosen=int(selection.loc[selection.inner_rmse_pp.le(best+1e-10),'degree'].min())
        assert chosen==case.selected_degree
        meta=json.loads((ROOT/f'outputs/group_means/{case.cohort}.input.json').read_text())
        fields=meta['fields'];x=raw.loc[pred.index,['bin_'+f for f in fields]].to_numpy(np.int16)
        np.testing.assert_allclose(pred.actual,raw.loc[pred.index,'sale_price_usd']/raw.loc[pred.index,'assessed_value_usd'],atol=1e-15,rtol=0)
        group_data=pd.read_csv(folder/'groups.csv');max_error=0.;equation_error=0.
        for order in [1,2]:
            partitions=[]
            for subset in itertools.combinations(range(d),order):
                _,inverse,n=np.unique(x[:,subset],axis=0,return_inverse=True,return_counts=True)
                partitions.append((inverse,n))
            for minimum in [10,30,100]:
                represented=[];covered=np.zeros(len(x),bool);groups=0
                for inverse,n in partitions:
                    keep=n>=minimum
                    if keep.sum()<2:continue
                    represented.append(int(n[keep].sum()));covered|=keep[inverse];groups+=int(keep.sum())
                coverage.append(dict(cohort=case.cohort,case=case.case,order=order,minimum_n=minimum,
                    possible_partitions=len(partitions),eligible_partitions=len(represented),excluded_partitions=len(partitions)-len(represented),
                    eligible_groups=groups,total_test_rows=len(x),union_covered_rows=int(covered.sum()),
                    mean_partition_coverage=None if not represented else float(np.mean(represented)/len(x))))
        for role in ['constant','additive','original_k3','selected']:
            model=np.load(folder/(role+'.npz'));u=model['profile_bins'];k=int(model['degree']);mu=float(model['baseline'])
            assert abs(mu-float(raw.loc[train,'ratio'].mean()))<1e-14
            assert {tuple(v) for v in u}=={tuple(v) for v in raw.loc[train,['bin_'+f for f in fields]].to_numpy(np.int16)}
            points=np.unique(np.linspace(0,len(x)-1,15,dtype=int));h=(x[points,None,:]==u[None,:,:]).sum(axis=2)
            norm=sum(math.comb(d,t) for t in range(k+1))
            lookup=np.array([sum(math.comb(int(v),t) for t in range(min(int(v),k)+1))/norm for v in range(d+1)])
            expected=mu+lookup[h]@model['alpha']
            error=float(np.max(np.abs(expected-pred[role].to_numpy()[points])));equation_error=max(equation_error,error)
            assert error<1e-9,(case.case,role,error)
            groups=group_data[group_data.model.eq(role)]
            # All primary groups, plus a fixed sample of paired conditions.
            pairs=groups[groups.order.eq(2)]
            chosen_groups=pd.concat([groups[groups.order.eq(1)],pairs.iloc[::max(1,len(pairs)//20)]])
            for group in chosen_groups.itertuples():
                mask=np.ones(len(x),bool)
                for term in group.condition_codes.split():
                    f,c=term.split('=');mask&=x[:,fields.index(f)]==int(c)
                assert mask.sum()==group.n
                error=max(abs(float(pred.actual.to_numpy()[mask].mean())-group.actual),
                    abs(float(pred[role].to_numpy()[mask].mean())-group.predicted))
                max_error=max(max_error,error);assert error<1e-10
            # Scalar group-weight definitions, independent of Partitions.evaluate.
            score=pd.read_csv(folder/'metrics.csv')
            for order in [1,2]:
                rows=groups[groups.order.eq(order)]
                sizes=rows.groupby('partition').size()
                weights=1/rows.partition.map(sizes).to_numpy()
                np.testing.assert_allclose(rows.partition_weight,weights,atol=1e-14,rtol=0)
                w=weights/weights.sum()
                a=rows.actual.to_numpy();b=rows.predicted.to_numpy()
                if not len(a):continue
                mse=sum(float(ww*(aa-bb)**2) for ww,aa,bb in zip(w,a,b))
                mean=sum(float(ww*aa) for ww,aa in zip(w,a));sst=sum(float(ww*(aa-mean)**2) for ww,aa in zip(w,a))
                expected=score[score.model.eq(role)&score.order.eq(order)&score.minimum_n.eq(30)].iloc[0]
                assert abs(100*math.sqrt(mse)-expected.rmse_pp)<1e-8
                if sst<1e-24:assert pd.isna(expected.r2)
                else:assert abs((1-mse/sst)-expected.r2)<1e-7
                pmean=math.fsum(float(ww*bb) for ww,bb in zip(w,b))
                vp=math.fsum(float(ww*(bb-pmean)**2) for ww,bb in zip(w,b))
                covariance=math.fsum(float(ww*(aa-mean)*(bb-pmean)) for ww,aa,bb in zip(w,a,b))
                if min(sst,vp)<1e-24:assert pd.isna(expected.r)
                else:assert abs(covariance/math.sqrt(sst*vp)-expected.r)<1e-8
                baseline_mse=math.fsum(float(ww*(aa-mu)**2) for ww,aa in zip(w,a))
                if baseline_mse<1e-24:assert pd.isna(expected.baseline_skill)
                else:assert abs(1-mse/baseline_mse-expected.baseline_skill)<1e-7
        if case.kind=='profile':assert case.train_test_shared_profiles==0
        if case.kind=='spatial':assert case.train_test_shared_grids==0
        if case.kind=='time':assert case.train_latest_date<case.test_earliest_date
        checks.append(dict(cohort=case.cohort,case=case.case,groups_checked_error=max_error,equation_error=equation_error,
            train_n=len(train),test_n=len(test),selected_degree=chosen))
    synthetic=pd.read_csv(OUT/'synthetic/metrics.csv');assert len(synthetic)==180
    synthetic_predictions=pd.read_csv(OUT/'synthetic/predictions.csv')
    for setting in synthetic.itertuples():
        rows=synthetic_predictions[synthetic_predictions.signal.eq(setting.signal)&synthetic_predictions.noise_pp.eq(setting.noise_pp)
            &synthetic_predictions.support.eq(setting.support)&synthetic_predictions.degree.eq(setting.degree)]
        assert len(rows)==setting.test_profiles and rows.profile.is_unique
        for truth_column in ['truth','observed']:
            observed=rows[truth_column].to_numpy();predicted=rows.predicted.to_numpy()
            mse=math.fsum(float((a-b)**2) for a,b in zip(observed,predicted))/len(rows)
            assert abs(100*math.sqrt(mse)-getattr(setting,truth_column+'_rmse_pp'))<1e-9
            variance=math.fsum(float((a-float(observed.mean()))**2) for a in observed)/len(rows)
            expected=getattr(setting,truth_column+'_r2')
            if variance<1e-24:assert pd.isna(expected)
            else:assert abs(1-mse/variance-expected)<1e-8
    for signal,degree in [('additive',1),('pair',2),('four_way',4),('eight_way',8)]:
        r=synthetic[synthetic.signal.eq(signal)&synthetic.noise_pp.eq(0)&synthetic.support.eq('complete')]
        assert r.loc[r.degree.ge(degree),'truth_rmse_pp'].max()<1e-8
        assert r.loc[r.degree.lt(degree),'truth_rmse_pp'].min()>5.999
    pd.DataFrame(coverage).to_csv(OUT/'coverage.csv',index=False)
    return dict(status='passed',cases=checks,synthetic_fits=len(synthetic),coverage_rows=len(coverage),source_hashes=config['source_hashes'])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--core-only',action='store_true');args=parser.parse_args()
    with threadpool_limits(limits=2):
        result={'core':core()}
        if not args.core_only:result.update(saved())
        else:result['status']='passed'
    OUT.mkdir(parents=True,exist_ok=True)
    write_json(OUT/('core-validation.json' if args.core_only else 'validation.json'),result)
    print(json.dumps({'status':result['status'],'core_checks':len(result['core']['explicit_design_predictions']),
        'saved_cases':len(result.get('cases',[]))}))
