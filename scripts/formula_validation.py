"""Retrain the original categorical kernel and evaluate held-out group means."""
from pathlib import Path
import os
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.codex/python-packages'))
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import argparse
import hashlib
import itertools
import json
import math
import time
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.linalg import eigh
from threadpoolctl import threadpool_limits
from query_group_means import Groups

OUT=ROOT/'outputs/formula_validation'
SEEDS=[20260908,20260909,20260910]
FRACTIONS=[.1,.25,.5,1.]
RTOL=1e-10

def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def write_json(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False,
        default=lambda v:v.item() if isinstance(v,np.generic) else str(v)),encoding='utf-8')

def save(rows,path):
    pd.DataFrame(rows).to_csv(path,index=False,encoding='utf-8-sig',float_format='%.17g')

def matches(a,b):
    h=np.zeros((len(a),len(b)),dtype=np.uint8)
    for j in range(a.shape[1]):h+=(a[:,j,None]==b[None,:,j])
    return h

def kernel(h,d,k):
    norm=sum(math.comb(d,t) for t in range(k+1))
    values=np.array([sum(math.comb(v,t) for t in range(min(v,k)+1))/norm for v in range(d+1)])
    return values[h]

@dataclass
class Formula:
    x: np.ndarray
    degree: int
    mean: float
    alpha: np.ndarray
    rank: int
    profile_rmse_pp: float
    seconds: float

    def predict(self,x,h=None):
        if self.degree==0:return np.full(len(x),self.mean)
        if h is None:h=matches(x,self.x)
        return self.mean+kernel(h,self.x.shape[1],self.degree)@self.alpha

    def persist(self,path):
        np.savez_compressed(path,profile_bins=self.x,degree=self.degree,baseline=self.mean,
            alpha=self.alpha,rank=self.rank,rank_rtol=RTOL)

class Training:
    def __init__(self,x,y):
        self.x,inv,self.n=np.unique(x,axis=0,return_inverse=True,return_counts=True)
        self.s=np.bincount(inv,weights=y,minlength=len(self.n))
        self.mean=float(np.mean(y));self.root=np.sqrt(self.n)
        self.target=(self.s/self.n-self.mean)*self.root
        self.h=matches(self.x,self.x)

    def fit(self,k):
        start=time.perf_counter()
        if k==0:
            return Formula(self.x,k,self.mean,np.zeros(len(self.x)),1,
                float(100*np.linalg.norm(self.target)/np.sqrt(self.n.sum())),time.perf_counter()-start)
        gram=kernel(self.h,self.x.shape[1],k)*self.root[:,None]*self.root[None,:]
        values,vectors=eigh(gram,overwrite_a=True,check_finite=False,driver='evd')
        keep=values>values[-1]*RTOL
        coordinates=vectors[:,keep].T@self.target
        fitted=vectors[:,keep]@coordinates
        alpha=self.root*(vectors[:,keep]@(coordinates/values[keep]))
        return Formula(self.x,k,self.mean,alpha,int(keep.sum()),
            float(100*np.linalg.norm(self.target-fitted)/np.sqrt(self.n.sum())),time.perf_counter()-start)

def metrics(y,p,w=None,baseline=None):
    y=np.asarray(y,float);p=np.asarray(p,float)
    if not len(y):return dict(groups=0,r=None,r2=None,rmse_pp=None,mae_pp=None,bias_pp=None,baseline_skill=None)
    w=np.ones(len(y))/len(y) if w is None else np.asarray(w,float)/np.sum(w)
    ym=float(w@y);pm=float(w@p);err=p-y
    mse=float(w@(err**2));vy=float(w@((y-ym)**2));vp=float(w@((p-pm)**2))
    base=None if baseline is None else float(w@((y-baseline)**2))
    return dict(groups=len(y),r=None if min(vy,vp)<1e-24 else float(w@((y-ym)*(p-pm))/np.sqrt(vy*vp)),
        r2=None if vy<1e-24 else 1-mse/vy,rmse_pp=100*np.sqrt(mse),mae_pp=float(100*w@np.abs(err)),
        bias_pp=float(100*w@err),baseline_skill=None if base is None or base<1e-24 else 1-mse/base,
        observed_sd_pp=100*np.sqrt(vy),max_abs_pp=float(100*np.max(np.abs(err))))

class Partitions:
    """Membership depends on X alone; every field subset defines one partition."""
    def __init__(self,x,fields,order=1,labels=None):
        self.entries=[];self.order=order;self.nrows=len(x)
        for columns in itertools.combinations(range(x.shape[1]),order):
            levels,inv,n=np.unique(x[:,columns],axis=0,return_inverse=True,return_counts=True)
            names=[fields[j] for j in columns]
            descriptions=[];codes=[]
            for level in levels:
                terms=[f'{name}={int(code)}' for name,code in zip(names,level)]
                codes.append(' '.join(terms))
                descriptions.append('；'.join(labels.get(term,term) if labels else term for term in terms))
            self.entries.append(dict(partition=' × '.join(names),inv=inv,n=n,codes=codes,conditions=descriptions))

    def evaluate(self,y,p,minimum_n,baseline):
        rows=[];per_partition=[]
        for e in self.entries:
            n=e['n'];actual=np.bincount(e['inv'],weights=y,minlength=len(n))/n
            predicted=np.bincount(e['inv'],weights=p,minlength=len(n))/n
            keep=n>=minimum_n
            if keep.sum()<2:continue
            per_partition.append(dict(partition=e['partition'],**metrics(actual[keep],predicted[keep],baseline=baseline),
                represented_rows=int(n[keep].sum()),total_rows=self.nrows,minimum_n=minimum_n,order=self.order))
            for i in np.flatnonzero(keep):
                rows.append(dict(partition=e['partition'],condition_codes=e['codes'][i],conditions=e['conditions'][i],
                    n=int(n[i]),actual=float(actual[i]),predicted=float(predicted[i]),
                    partition_weight=1/int(keep.sum()),minimum_n=minimum_n,order=self.order))
        summary=metrics([r['actual'] for r in rows],[r['predicted'] for r in rows],
            [r['partition_weight'] for r in rows] if rows else None,baseline)
        summary.update(partitions=len(per_partition),minimum_n=minimum_n,order=self.order)
        return summary,rows,per_partition

def split_units(indices,units,fraction,seed):
    levels=np.unique(units[indices]);order=np.random.default_rng(seed).permutation(levels)
    n=max(1,min(len(levels)-1,int(math.ceil(fraction*len(levels)))))
    test=indices[np.isin(units[indices],order[:n])]
    return np.setdiff1d(indices,test),test

def chronological(indices,dates,fraction):
    ordered=np.sort(dates[indices]);cut=ordered[min(len(ordered)-1,int((1-fraction)*len(ordered)))]
    # All transactions on the cutoff date stay on the later side.
    return indices[dates[indices]<cut],indices[dates[indices]>=cut]

def inner_split(indices,kind,profile,grid,dates,seed):
    if kind=='profile':return split_units(indices,profile,.25,seed)
    if kind=='spatial':return split_units(indices,grid,.25,seed)
    if kind=='time':return chronological(indices,dates,.25)
    order=np.random.default_rng(seed).permutation(indices);n=max(1,int(math.ceil(len(order)*.25)))
    return order[n:],order[:n]

def seen_status(x,training_x):
    known={tuple(row) for row in training_x}
    seen=np.array([tuple(row) in known for row in x])
    unseen_category=np.zeros(len(x),bool)
    for j in range(x.shape[1]):unseen_category|=~np.isin(x[:,j],np.unique(training_x[:,j]))
    return seen,unseen_category

def run_case(g,x,y,aux,profile,train,test,seed,fraction,kind):
    label=f'{kind}-{seed}-{int(fraction*100):03d}'
    folder=OUT/g.cohort/label;folder.mkdir(parents=True,exist_ok=True)
    fit,validation=inner_split(train,kind,profile,aux.grid1km.to_numpy(),aux.sale_date.to_numpy(),seed+101)
    assert not set(train)&set(test) and set(fit)|set(validation)==set(train) and not set(fit)&set(validation)
    labels={f"{a['name']}={a['category']}":a['label'] for a in g.atoms}
    inner=Training(x[fit],y[fit]);inner_h=matches(x[validation],inner.x)
    inner_groups=Partitions(x[validation],g.fields,labels=labels);selection=[]
    for k in range(x.shape[1]+1):
        model=inner.fit(k);pred=model.predict(x[validation],inner_h)
        score,_,_=inner_groups.evaluate(y[validation],pred,5,inner.mean)
        if score['rmse_pp'] is None:raise ValueError('Inner group selection has no supported partitions')
        selection.append(dict(degree=k,rank=model.rank,inner_rmse_pp=score['rmse_pp'],inner_groups=score['groups'],
            inner_partitions=score['partitions'],training_profiles=len(inner.x),training_profile_rmse_pp=model.profile_rmse_pp,
            seconds=model.seconds))
        print(json.dumps(dict(cohort=g.cohort,case=label,stage='select',**selection[-1])),flush=True)
    best=min(r['inner_rmse_pp'] for r in selection)
    degree=min(r['degree'] for r in selection if r['inner_rmse_pp']<=best+1e-10)
    save(selection,folder/'selection.csv')
    system=Training(x[train],y[train]);test_h=matches(x[test],system.x)
    models={k:system.fit(k) for k in sorted({0,1,3,degree})}
    seen,new_category=seen_status(x[test],system.x)
    row_predictions=pd.DataFrame(dict(record_id=g.members.index[test],actual=y[test],seen_profile=seen,new_category=new_category))
    score_rows=[];group_rows=[];partition_rows=[];row_scores=[];support_rows=[]
    layouts={order:Partitions(x[test],g.fields,order,labels) for order in [1,2]}
    role_degrees={'constant':0,'additive':1,'original_k3':3,'selected':degree}
    for role,k in role_degrees.items():
        model=models[k];pred=model.predict(x[test],test_h);row_predictions[role]=pred
        model.persist(folder/(role+'.npz'))
        row_scores.append(dict(model=role,degree=k,**metrics(y[test],pred,baseline=system.mean)))
        for status,mask in [('seen',seen),('unseen',~seen),('new_category',new_category)]:
            if mask.any():
                sublayout=Partitions(x[test][mask],g.fields,1,labels)
                subscore,_,_=sublayout.evaluate(y[test][mask],pred[mask],30,system.mean)
                support_rows.append(dict(model=role,degree=k,support=status,rows=int(mask.sum()),**subscore))
        for order,layout in layouts.items():
            for minimum in [10,30,100]:
                score,rows,parts=layout.evaluate(y[test],pred,minimum,system.mean)
                score_rows.append(dict(model=role,degree=k,rank=model.rank,training_profiles=len(system.x),
                    train_profile_rmse_pp=model.profile_rmse_pp,**score))
                if minimum==30:
                    group_rows.extend(dict(model=role,degree=k,**r) for r in rows)
                    partition_rows.extend(dict(model=role,degree=k,**r) for r in parts)
    row_predictions.to_csv(folder/'predictions.csv',index=False,float_format='%.17g')
    for rows,name in [(score_rows,'metrics'),(group_rows,'groups'),(partition_rows,'partitions'),(row_scores,'row_metrics'),(support_rows,'support_metrics')]:
        save(rows,folder/(name+'.csv'))
    split=pd.DataFrame({'record_id':g.members.index,'role':'unused'})
    split.loc[train,'role']='train';split.loc[test,'role']='test'
    split['inner_role']='unused';split.loc[fit,'inner_role']='fit';split.loc[validation,'inner_role']='validation'
    split.to_csv(folder/'split.csv',index=False)
    meta=dict(cohort=g.cohort,case=label,kind=kind,seed=seed,fraction=fraction,train_n=len(train),test_n=len(test),
        inner_train_n=len(fit),inner_validation_n=len(validation),selected_degree=degree,training_profiles=len(system.x),
        test_seen_profile_n=int(seen.sum()),test_new_category_n=int(new_category.sum()),train_mean=system.mean,
        train_latest_date=str(aux.sale_date.iloc[train].max()),test_earliest_date=str(aux.sale_date.iloc[test].min()),
        train_test_shared_profiles=len(set(profile[train])&set(profile[test])),
        train_test_shared_grids=len(set(aux.grid1km.iloc[train])&set(aux.grid1km.iloc[test])),status='completed')
    write_json(folder/'case.json',meta)
    print(json.dumps(meta),flush=True)
    return meta

def real(cohort,selected_case=None):
    g=Groups(cohort);x=g.members[['bin_'+f for f in g.fields]].to_numpy(np.int16);y=g.members.ratio.to_numpy()
    aux=pd.read_csv(ROOT/'outputs/combinations/record_membership.csv',dtype={'record_id':str,'parcel_id_raw':str})
    aux=aux.set_index('record_id').loc[g.members.index];aux['sale_date']=pd.to_datetime(aux.sale_date)
    assert aux.index.is_unique and aux.parcel_id_raw.is_unique
    _,profile=np.unique(x,axis=0,return_inverse=True);all_ids=np.arange(len(y))
    development=np.flatnonzero(g.members.partition.eq('development'));test=np.flatnonzero(g.members.partition.eq('test'))
    assert len(development)+len(test)==len(y)
    plans=[]
    for seed in SEEDS:
        order=np.random.default_rng(seed).permutation(development)
        for fraction in FRACTIONS:
            train=np.sort(order[:max(1,round(fraction*len(order)))])
            plans.append((train,test,seed,fraction,'random'))
    for kind in ['profile','spatial','time']:
        if kind=='profile':tr,te=split_units(all_ids,profile,.2,SEEDS[0])
        elif kind=='spatial':tr,te=split_units(all_ids,aux.grid1km.to_numpy(),.2,SEEDS[0])
        else:tr,te=chronological(all_ids,aux.sale_date.to_numpy(),.2)
        plans.append((tr,te,SEEDS[0],1.,kind))
    for train,test,seed,fraction,kind in plans:
        name=f'{kind}-{seed}-{int(fraction*100):03d}'
        if selected_case and name!=selected_case:continue
        run_case(g,x,y,aux,profile,train,test,seed,fraction,kind)

def synthetic():
    folder=OUT/'synthetic';folder.mkdir(parents=True,exist_ok=True)
    cube=np.array(list(itertools.product([0,1],repeat=8)),dtype=np.int16);z=2*cube-1
    signals={'additive':1+.06*z[:,0], 'pair':1+.06*z[:,0]*z[:,1],
             'four_way':1+.06*np.prod(z[:,:4],axis=1),'eight_way':1+.06*np.prod(z,axis=1),'noise_only':np.ones(256)}
    rng=np.random.default_rng(SEEDS[0]);train_profiles=rng.permutation(256)[:205]
    held=np.setdiff1d(np.arange(256),train_profiles);rows=[];predictions=[]
    for name,truth in signals.items():
        for noise in [0.,.04]:
            train_y=np.repeat(truth,4)+rng.normal(0,noise,1024)
            test_y=np.repeat(truth,4)+rng.normal(0,noise,1024)
            for support in ['complete','unseen']:
                tr=np.arange(256) if support=='complete' else train_profiles
                te=np.arange(256) if support=='complete' else held
                xtrain=np.repeat(cube[tr],4,axis=0);ytrain=train_y.reshape(256,4)[tr].ravel()
                system=Training(xtrain,ytrain);cross=matches(cube[te],system.x)
                actual=test_y.reshape(256,4)[te].mean(axis=1)
                for k in range(9):
                    m=system.fit(k);p=m.predict(cube[te],cross)
                    truth_score=metrics(truth[te],p,baseline=system.mean);observed=metrics(actual,p,baseline=system.mean)
                    rows.append(dict(signal=name,noise_pp=100*noise,support=support,degree=k,rank=m.rank,
                        training_profiles=len(tr),test_profiles=len(te),test_repeats_per_profile=4,
                        training_profile_rmse_pp=m.profile_rmse_pp,
                        **{'truth_'+key:value for key,value in truth_score.items()},
                        **{'observed_'+key:value for key,value in observed.items()}))
                    predictions.extend(dict(signal=name,noise_pp=100*noise,support=support,degree=k,
                        profile=int(index),truth=float(a),observed=float(b),predicted=float(c))
                        for index,a,b,c in zip(te,truth[te],actual,p))
    save(rows,folder/'metrics.csv');save(predictions,folder/'predictions.csv')
    write_json(folder/'design.json',dict(seed=SEEDS[0],fields=8,full_profiles=256,unseen_profiles=held.tolist(),
        training_profiles=train_profiles.tolist(),scope='Synthetic controlled experiment; full-state group mean, n=4; not housing support thresholds'))
    print(json.dumps(dict(stage='synthetic',fits=len(rows),status='completed')),flush=True)

def collect():
    cases=[];metric_rows=[];selection_rows=[];row_rows=[];support=[]
    for cohort in ['main','positive_garage']:
        for f in sorted((OUT/cohort).glob('*/case.json')):
            m=json.loads(f.read_text());cases.append(m)
            for filename,bucket in [('metrics',metric_rows),('selection',selection_rows),('row_metrics',row_rows),('support_metrics',support)]:
                table=pd.read_csv(f.parent/(filename+'.csv'))
                for k in ['cohort','case','kind','seed','fraction','train_n','test_n']:table[k]=m[k]
                bucket.extend(table.to_dict('records'))
    for rows,name in [(cases,'cases'),(metric_rows,'metrics'),(selection_rows,'selection'),(row_rows,'row_metrics'),(support,'support_metrics')]:save(rows,OUT/(name+'.csv'))
    print(json.dumps(dict(stage='collected',cases=len(cases),scored_rows=len(metric_rows))),flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['real','synthetic','collect'])
    parser.add_argument('--cohort',choices=['main','positive_garage']);parser.add_argument('--case');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if os.name=='nt':
        import ctypes
        ctypes.windll.kernel32.SetErrorMode(0x8003)
    sources=['outputs/group_means/record_bins.csv','outputs/group_means/bin_definitions.json',
        'outputs/group_means/main.input.json','outputs/group_means/positive_garage.input.json',
        'outputs/combinations/record_membership.csv','scripts/analyze_group_algebra.py','docs/formula_validation.md']
    if args.stage!='collect':write_json(OUT/'config.json',dict(seeds=SEEDS,fractions=FRACTIONS,rtol=RTOL,
        primary_minimum_n=30,inner_minimum_n=5,all_degrees=True,regularization='none',
        source_hashes={s:digest(ROOT/s) for s in sources},script_sha256=digest(__file__)))
    with threadpool_limits(limits=2):
        if args.stage=='real':
            for cohort in ([args.cohort] if args.cohort else ['main','positive_garage']):real(cohort,args.case)
        elif args.stage=='synthetic':synthetic()
        else:collect()

if __name__=='__main__':main()
