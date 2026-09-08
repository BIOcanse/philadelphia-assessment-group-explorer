"""Group-level mean-ratio ranking, exact conjunction lookup and lossless expansion."""
from group_mean_schema import OUT, DTYPE
import argparse, csv, json, math
import numpy as np
import pandas as pd


class Groups:
    def __init__(self,cohort):
        self.cohort=cohort
        self.meta=json.loads((OUT/(cohort+'.input.json')).read_text('utf-8'))
        self.atoms=self.meta['atoms'];self.fields=self.meta['fields']
        self.stats=np.memmap(OUT/(cohort+'.input_groups.bin'),dtype=DTYPE,mode='r')
        self.members=pd.read_csv(OUT/'record_bins.csv').set_index('record_id').loc[self.meta['record_ids']]
        self.atom_bits=[]
        for a in self.atoms:
            keep=self.members['bin_'+a['name']].eq(a['category']).to_numpy(dtype=np.uint8)
            self.atom_bits.append(int.from_bytes(np.packbits(keep,bitorder='little').tobytes(),'little'))
        self.all_rows=(1<<len(self.members))-1
    def bitset(self,lo,hi):return int(lo)|(int(hi)<<64)
    def extent(self,expression):
        result=self.all_rows
        for atom in expression:result&=self.atom_bits[atom]
        return result
    def condition_ids(self,conditions):
        result=[];owners=set()
        for condition in conditions:
            name,category=condition.split('=',1);category=int(category)
            if name in owners:raise ValueError('At most one category per field')
            found=[a['id'] for a in self.atoms if a['name']==name and a['category']==category]
            if len(found)!=1:raise ValueError('Unknown or absent category: '+condition)
            result+=found;owners.add(name)
        return result
    def expression(self,s,which='generator'):
        bits=self.bitset(s[which+'_lo'],s[which+'_hi'])
        return [a['id'] for a in self.atoms if bits&(1<<a['id'])]
    def reduced(self,s):
        # Remove redundant conditions while preserving exact members; not claimed globally shortest.
        expression=self.expression(s);target=self.extent(expression)
        for atom in list(expression):
            candidate=[a for a in expression if a!=atom]
            if self.extent(candidate)==target:expression=candidate
        return expression
    def row(self,index,rank=None,expression=None):
        s=self.stats[index];n=int(s['n']);mean=float(s['ratio_sum']/n)
        ids=self.reduced(s) if expression is None else expression
        sd=math.sqrt(max(0.,float(s['ratio_sq_sum']-s['ratio_sum']**2/n))/(n-1)) if n>1 else None
        dev=float(s['development_sum']/s['development_n']) if s['development_n'] else None
        test=float(s['test_sum']/s['test_n']) if s['test_n'] else None
        return dict(rank=rank,group_id=f'{self.cohort}-{index:08d}',conditions=' AND '.join(self.atoms[a]['label'] for a in ids) or '全部固定样本 / Entire fixed cohort',
            condition_codes=' '.join(self.atoms[a]['name']+'='+str(self.atoms[a]['category']) for a in ids),
            expression_fields=len(ids),closure_fields=len(self.expression(s,'closure')),n=n,mean_ratio=mean,
            mean_ratio_pct=100*mean,bias_percentage_points=100*(mean-1),sample_sd_percentage_points=None if sd is None else 100*sd,
            below100_share=float(s['low_n']/n),above100_share=float((n-s['low_n']-s['equal_n'])/n),
            equal100_share=float(s['equal_n']/n),cohort_share=n/self.meta['n'],
            development_n=int(s['development_n']),development_mean_ratio=dev,test_n=int(s['test_n']),test_mean_ratio=test,
            partition_direction='同向 / Same side' if dev is not None and test is not None and (dev-1)*(test-1)>0 else '不一致或不足 / Different or unavailable')
    def rank(self,direction='low',min_n=1,limit=100,contains=None):
        order=np.load(OUT/(self.cohort+'_rank_'+direction+'.npy'),mmap_mode='r')
        required=sum(1<<a for a in (contains or []));selected=[]
        # Filter in array chunks so a sparse filter never creates millions of Python objects.
        for start in range(0,len(order),200000):
            ids=order[start:start+200000];s=self.stats[ids];keep=s['n']>=min_n
            if required:
                keep&=(s['closure_lo']&np.uint64(required&((1<<64)-1)))==np.uint64(required&((1<<64)-1))
                keep&=(s['closure_hi']&np.uint64(required>>64))==np.uint64(required>>64)
            selected.extend(ids[keep][:limit-len(selected)].tolist())
            if len(selected)>=limit:break
        return pd.DataFrame([self.row(i,k+1) for k,i in enumerate(selected)])
    def lookup(self,expression):
        extent=self.extent(expression)
        if not extent:return None
        closure=sum(1<<a for a,bits in enumerate(self.atom_bits) if (extent&bits)==extent)
        key=(closure&((1<<64)-1),closure>>64)
        matches=np.flatnonzero((self.stats['closure_lo']==key[0])&(self.stats['closure_hi']==key[1]))
        assert len(matches)==1
        return self.row(int(matches[0]),expression=expression)
    def expand(self,index,min_fields=0,max_fields=21,include=None,exclude=None):
        s=self.stats[index];closure=self.expression(s,'closure');target=self.extent(closure)
        required=set(include or []);forbidden=set(exclude or [])
        # Iterative subset enumeration. Only exact target extents are equivalent.
        stack=[(0,[],self.all_rows)]
        while stack:
            at,expression,extent=stack.pop()
            if len(expression)>max_fields:continue
            if at==len(closure):
                fields={self.atoms[a]['name'] for a in expression}
                if min_fields<=len(expression)<=max_fields and required<=fields and not forbidden&fields and extent==target:
                    yield self.row(index,expression=expression)
                continue
            stack.append((at+1,expression,extent))
            atom=closure[at]
            if self.atoms[atom]['name'] not in forbidden:
                stack.append((at+1,expression+[atom],extent&self.atom_bits[atom]))


def main():
    parser=argparse.ArgumentParser(description='Every output row is a condition GROUP; sort metric is mean(sale/assessment).')
    parser.add_argument('mode',choices=['rank','lookup','expand','bins'])
    parser.add_argument('--cohort',choices=['main','positive_garage'],default='main');parser.add_argument('--direction',choices=['low','high'],default='low')
    parser.add_argument('--min-n',type=int,default=1);parser.add_argument('--limit',type=int,default=100)
    parser.add_argument('--condition',action='append',default=[]);parser.add_argument('--group-id');parser.add_argument('--output')
    parser.add_argument('--min-fields',type=int,default=0);parser.add_argument('--max-fields',type=int,default=21)
    parser.add_argument('--include',nargs='*',default=[]);parser.add_argument('--exclude',nargs='*',default=[])
    args=parser.parse_args()
    if args.min_n<1 or args.limit<1:parser.error('min-n and limit must be positive')
    groups=Groups(args.cohort)
    if args.mode=='bins':print(pd.DataFrame(groups.atoms)[['name','category','label']].to_string(index=False));return
    if args.mode=='expand':
        if not args.group_id or not args.output:parser.error('expand requires --group-id and --output; all matching expressions are streamed')
        prefix,index=args.group_id.rsplit('-',1)
        if prefix!=args.cohort:parser.error('group-id and cohort disagree')
        count=0
        with open(args.output,'w',encoding='utf-8-sig',newline='') as f:
            writer=None
            for row in groups.expand(int(index),args.min_fields,args.max_fields,args.include,args.exclude):
                if writer is None:writer=csv.DictWriter(f,fieldnames=row.keys());writer.writeheader()
                writer.writerow(row);count+=1
        print('Equivalent condition expressions:',count);return
    conditions=groups.condition_ids(args.condition)
    if args.mode=='lookup':
        row=groups.lookup(conditions);frame=pd.DataFrame([row]) if row else pd.DataFrame()
    else:frame=groups.rank(args.direction,args.min_n,args.limit,conditions)
    if args.output:frame.to_csv(args.output,index=False,encoding='utf-8-sig')
    if not frame.empty:print(frame[['group_id','conditions','n','mean_ratio_pct','bias_percentage_points']].to_string(index=False))
    print('Groups:',len(frame))


if __name__=='__main__':main()
