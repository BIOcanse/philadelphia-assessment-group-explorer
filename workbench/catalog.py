"""Read-only group identifiers, ranked queries, and human-readable conditions."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'.codex/workbench-packages'))
from query_group_means import Groups
from group_mean_schema import OUT as CUBE
import functools
import hashlib
import json
import re
import numpy as np
import pandas as pd

OUT=ROOT/'outputs/group_workbench'
COHORTS={'main':'主样本 / Main','positive_garage':'正车库 / Garage'}

class Cohort:
    def __init__(self,name):
        self.name=name;self.g=Groups(name);s=self.g.stats
        self.n=s['n'];self.ratio=s['ratio_sum']/self.n
        self.valid=(s['closure_lo']!=0)|(s['closure_hi']!=0)
        self.orders={side:np.load(CUBE/(name+'_rank_'+side+'.npy'),mmap_mode='r') for side in ['high','low']}
        self.field_labels={a['name']:a['label'].split(' = ',1)[0] for a in self.g.atoms}
    def mask(self,min_n=100,min_ratio=None,max_ratio=None,conditions=()):
        if min_n<1:raise ValueError('最小n必须至少为1 / Minimum n must be positive')
        keep=self.valid&(self.n>=min_n)
        if min_ratio is not None:keep&=self.ratio*100>=min_ratio
        if max_ratio is not None:keep&=self.ratio*100<max_ratio
        if min_ratio is not None and max_ratio is not None and min_ratio>=max_ratio:
            raise ValueError('百分比上界必须大于下界 / Upper bound must exceed lower bound')
        ids=self.g.condition_ids(conditions);bits=sum(1<<a for a in ids)
        if bits:
            lo=np.uint64(bits&((1<<64)-1));hi=np.uint64(bits>>64)
            keep&=((self.g.stats['closure_lo']&lo)==lo)&((self.g.stats['closure_hi']&hi)==hi)
        return keep
    def selected(self,sort='high',**filters):
        if sort not in ['high','low','support']:raise ValueError('Unknown sort')
        keep=self.mask(**filters)
        if sort=='support' and sort not in self.orders:self.orders[sort]=np.argsort(-self.n.astype(np.int64),kind='stable')
        order=self.orders[sort]
        return order[keep[order]]
    @functools.lru_cache(maxsize=4096)
    def row(self,index):
        if index<0 or index>=len(self.g.stats):raise ValueError('组号不存在 / Group ID not found')
        row=self.g.row(index);row['cohort']=self.name;row['cohort_label']=COHORTS[self.name]
        row['is_baseline']=not bool(self.valid[index])
        row['condition_list']=[self.g.atoms[a]['label'] for a in self.g.reduced(self.g.stats[index])]
        return row

class Catalog:
    def __init__(self):
        self.manifest=json.loads((OUT/'registry.json').read_text('utf-8'))
        for relative,expected in self.manifest['sources'].items():
            digest=hashlib.sha256()
            with (ROOT/relative.replace('\\','/')).open('rb') as stream:
                while chunk:=stream.read(8*1024*1024):digest.update(chunk)
            if digest.hexdigest()!=expected:raise ValueError('源数据已变化，请重新生成编号目录 / Rebuild registry: '+relative)
        self.cohorts={c:Cohort(c) for c in COHORTS}
        self.aliases={k.upper():v for k,v in self.manifest['aliases'].items()}
        self.profile_map=pd.read_csv(OUT/'profile_group_crosswalk.csv').fillna('')
        self.by_group={}
        for alias,group_id in self.manifest['aliases'].items():self.by_group.setdefault(group_id,[]).append(alias)
    def metadata(self):
        return dict(version=self.manifest['version'],cohorts=[dict(id=c,label=COHORTS[c],
            groups=int(db.valid.sum()),transactions=len(db.g.members),
            fields=[dict(name=f,label=db.field_labels[f],categories=[dict(code=a['category'],label=a['label'].split(' = ',1)[1])
                for a in db.g.atoms if a['name']==f]) for f in db.g.fields]) for c,db in self.cohorts.items()],
            export_limit=50000,registry_files=self.manifest['exports'])
    def resolve(self,identifier,cohort='main'):
        if cohort not in self.cohorts:raise ValueError('Unknown cohort')
        value=identifier.strip();value=self.aliases.get(value.upper(),value)
        profile=re.fullmatch(r'P(\d+)',value,re.I)
        if profile:
            prefix='M' if cohort=='main' else 'G';value=self.aliases.get(f'{prefix}-P{int(profile[1]):06d}',value)
        short=re.fullmatch(r'([MG])-(\d{1,8})',value,re.I)
        if short:value=('main' if short[1].upper()=='M' else 'positive_garage')+'-'+short[2].zfill(8)
        match=re.fullmatch(r'(main|positive_garage)-(\d{1,8})',value)
        if not match:raise ValueError('未找到该编号；可输入正式组号、M025/G025或M-P000123 / Unknown identifier')
        db=self.cohorts[match[1]];index=int(match[2]);db.row(index)
        return db,index
    def row(self,db,index):
        row=dict(db.row(int(index)));row['aliases']=self.by_group.get(row['group_id'],[])
        return row
    def search(self,cohort='main',offset=0,limit=50,sort='high',**filters):
        if cohort not in self.cohorts:raise ValueError('Unknown cohort')
        if offset<0 or limit<1 or limit>500:raise ValueError('分页范围无效 / Invalid page size')
        db=self.cohorts[cohort];indices=db.selected(sort=sort,**filters);total=len(indices)
        values=db.ratio[indices]*100;hist=[]
        if total:
            start=2*np.floor(values.min()/2);stop=2*np.floor(values.max()/2)+2
            edges=np.arange(start,stop+1,2);counts,_=np.histogram(values,bins=edges)
            hist=[dict(lo=float(a),hi=float(b),mid=float((a+b)/2),count=int(n)) for a,b,n in zip(edges[:-1],edges[1:],counts)]
        return dict(cohort=cohort,total=total,offset=offset,limit=limit,version=self.manifest['version'],
            histogram=hist,rows=[self.row(db,i) for i in indices[offset:offset+limit]],
            min_ratio=float(values.min()) if total else None,max_ratio=float(values.max()) if total else None)
    def detail(self,identifier,cohort='main'):
        db,index=self.resolve(identifier,cohort);g=db.g;row=self.row(db,index);s=g.stats[index]
        closure=g.expression(s,'closure');bits=g.extent(g.expression(s));size=len(g.members)
        positions=np.flatnonzero(np.unpackbits(np.frombuffer(bits.to_bytes((size+7)//8,'little'),dtype=np.uint8),bitorder='little')[:size])
        members=g.members.iloc[positions];r=members.ratio.to_numpy();fields=[]
        for field in g.fields:
            bins=[]
            for a in [a for a in g.atoms if a['name']==field]:
                keep=members['bin_'+field].eq(a['category']).to_numpy();n=int(keep.sum())
                bins.append(dict(category=a['category'],label=a['label'].split(' = ',1)[1],n=n,share=n/len(members),
                    mean_ratio=float(r[keep].mean()) if n else None,condition_code=field+'='+str(a['category'])))
            fields.append(dict(name=field,label=db.field_labels[field],fixed=any(a in closure for a in [a['id'] for a in g.atoms if a['name']==field]),bins=bins))
        assert len(members)==row['n'] and abs(float(r.mean())-row['mean_ratio'])<1e-12
        row.update(version=self.manifest['version'],closure_conditions=[g.atoms[a]['label'] for a in closure],fields=fields,
            members=[dict(record_id=str(i),sale_price=float(v.sale_price_usd),assessment=float(v.assessed_value_usd),ratio=float(v.ratio))
                for i,v in members.iterrows()])
        return row
    def atlas(self,cohort='main',kind='tsne'):
        if cohort not in self.cohorts or kind not in ['tsne','pca']:raise ValueError('Unknown atlas')
        frame=pd.read_csv(ROOT/'outputs/group_atlas'/(cohort+'_projection.csv'))
        return dict(cohort=cohort,kind=kind,scope='既有1320个按规模抽样和候选的组；非全部组 / Existing sampled atlas',
            rows=[dict(group_id=r.group_id,label=r.label,n=int(r.n),mean_ratio=float(r.mean_ratio),
                conditions=r.conditions,x=float(getattr(r,kind+'_x')),y=float(getattr(r,kind+'_y')),
                role=r.sampling_role) for r in frame.itertuples()])
