"""Prepare independent held-out profile aggregates and scan the existing directory."""
from formula_validation import ROOT,OUT,SEEDS,Groups,write_json,save,metrics
import ctypes
import json
import shutil
import struct
import subprocess
import time
import numpy as np
import pandas as pd

ROLES=['constant','additive','original_k3','selected']

def run(cohort):
    tick=time.perf_counter();g=Groups(cohort);case=OUT/cohort/f'random-{SEEDS[0]}-100'
    p=pd.read_csv(case/'predictions.csv').set_index('record_id')
    x=g.members.loc[p.index,['bin_'+f for f in g.fields]].to_numpy(np.int16)
    unique,inv,n=np.unique(x,axis=0,return_inverse=True,return_counts=True);U=len(unique);W=(U+63)//64
    weights=np.column_stack([n,*[np.bincount(inv,weights=p[c],minlength=U) for c in ['actual',*ROLES]]])
    atoms=[]
    for a in g.atoms:
        bits=np.zeros(W*64,np.uint8);bits[:U]=unique[:,g.fields.index(a['name'])]==a['category']
        atoms.append(np.packbits(bits,bitorder='little').view('<u8'))
    inp=OUT/(cohort+'_catalog_input.bin');out=OUT/(cohort+'_catalog.bin')
    with inp.open('wb') as f:
        f.write(struct.pack('<5I',0x46564c31,U,len(atoms),len(ROLES),W))
        np.array(atoms,dtype='<u8').tofile(f);weights.astype('<f8').tofile(f)
    result=subprocess.run([str(OUT/'scan_formula_groups.exe'),str(inp),
        str(ROOT/f'outputs/group_means/{cohort}.input_groups.bin'),str(out)],
        stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=180,check=True)
    summary=json.loads(result.stdout);summary['cohort']=cohort;summary['seconds']=time.perf_counter()-tick
    values=np.memmap(out,dtype='<f8',mode='r').reshape(-1,3+len(ROLES))
    assert len(values)==summary['saved_unique_n30']
    rows=[];worst=[]
    for row in summary['metrics']:
        row['cohort']=cohort;row['model']=ROLES[row['method_index']];rows.append(row)
        if row['basis']=='unique_test_members' and row['minimum_n']>=30:
            v=values[values[:,1]>=row['minimum_n']]
            check=metrics(v[:,2],v[:,3+row['method_index']],baseline=v[0,3] if len(v) else None)
            if len(v):
                assert abs(check['rmse_pp']-row['rmse_pp'])<1e-8
                assert abs(check['r2']-row['r2'])<1e-7
                if check['r'] is None:assert row['r'] is None
                else:assert abs(check['r']-row['r'])<1e-8
    # Largest residuals are explicitly post-test diagnostics, not new confirmation claims.
    selected=values[:,6];order=np.argsort(np.abs(selected-values[:,2]))[-12:][::-1]
    for i in order:
        group=g.row(int(values[i,0]));group.update(test_n=int(values[i,1]),test_actual_pct=100*values[i,2],
            test_predicted_pct=100*selected[i],error_pp=100*(selected[i]-values[i,2]),cohort=cohort)
        worst.append(group)
    save(rows,OUT/(cohort+'_catalog_metrics.csv'));save(worst,OUT/(cohort+'_catalog_worst.csv'))
    write_json(OUT/(cohort+'_catalog_summary.json'),summary)
    print(json.dumps({k:summary[k] for k in ['cohort','canonical_groups','empty_test_groups','unique_test_member_groups','saved_unique_n30','count_mismatches','seconds']}),flush=True)

if __name__=='__main__':
    ctypes.windll.kernel32.SetErrorMode(0x8003)
    subprocess.run([shutil.which('g++'),'-O3','-std=c++17','-static',str(ROOT/'scripts/scan_formula_groups.cpp'),
        '-o',str(OUT/'scan_formula_groups.exe')],stdin=subprocess.DEVNULL,check=True,timeout=120)
    for cohort in ['main','positive_garage']:run(cohort)
