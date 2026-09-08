"""Build the independent GitHub Pages edition from the verified native registry."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workbench'))
from catalog import Catalog, OUT as REGISTRY, COHORTS
import argparse
import gzip
import hashlib
import json
import shutil
import time
import zipfile
import numpy as np
import pandas as pd

OUT=ROOT/'outputs/group_pages';RELEASE=OUT/'release';SITE=RELEASE/'site';SHARD_SIZE=100000
PACK=np.dtype([('index','<u4'),('n','<u4'),('ratio','<f8'),('closure_lo','<u8'),('closure_hi','<u8'),('generator_lo','<u8'),('generator_hi','<u8')])
assert PACK.itemsize==48

def put(path,raw,compress=True):
    path.parent.mkdir(parents=True,exist_ok=True)
    body=gzip.compress(raw,compresslevel=3,mtime=0) if compress else raw
    path.write_bytes(body)
    return dict(path=path.relative_to(SITE).as_posix(),bytes=len(body),raw_bytes=len(raw),sha256=hashlib.sha256(body).hexdigest())

def encode(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')

def pack(db,indices):
    source=db.g.stats[indices];data=np.empty(len(indices),dtype=PACK)
    data['index']=indices;data['n']=source['n'];data['ratio']=db.ratio[indices]
    for name in ['closure_lo','closure_hi','generator_lo','generator_hi']:data[name]=source[name]
    return data.tobytes()

def build_data():
    catalog=Catalog();version=catalog.manifest['version'];base=SITE/'data'/version
    manifest=catalog.metadata();manifest.update(format=1,record_bytes=48,shard_size=SHARD_SIZE,core_min_n=100,
        aliases=catalog.manifest['aliases'],binary_cohorts={})
    for name,db in catalog.cohorts.items():
        tick=time.perf_counter();target=base/name;g=db.g
        members=[[str(index),float(r.sale_price_usd),float(r.assessed_value_usd),float(r.ratio),
            *[int(r['bin_'+field]) for field in g.fields]] for index,r in g.members.iterrows()]
        info=dict(records=len(g.stats),field_names=g.fields,atoms=g.atoms,
            members=put(target/'members.json.gz',encode(members)),shards=[],ranks={},core_ranks={})
        for start in range(0,len(g.stats),SHARD_SIZE):
            indices=np.arange(start,min(start+SHARD_SIZE,len(g.stats)))
            info['shards'].append(put(target/f'groups-{start//SHARD_SIZE:03d}.bin.gz',pack(db,indices)))
        core=np.flatnonzero(db.valid&(db.n>=100))
        info['core']=put(target/'core.bin.gz',pack(db,core));info['core_count']=len(core)
        for side in ['high','low']:
            ids=np.asarray(db.orders[side]);ids=ids[db.valid[ids]]
            info['ranks'][side]=put(target/f'rank-{side}.bin.gz',ids.astype('<u4').tobytes())
            selected=ids[db.n[ids]>=100];positions=np.searchsorted(core,selected).astype('<u4')
            assert np.array_equal(core[positions],selected)
            info['core_ranks'][side]=put(target/f'core-{side}.bin.gz',positions.tobytes())
        projection=pd.read_csv(ROOT/'outputs/group_atlas'/(name+'_projection.csv'))
        atlas=[dict(group_id=r.group_id,label=r.label,n=int(r.n),mean_ratio=float(r.mean_ratio),conditions=r.conditions,
            tsne_x=float(r.tsne_x),tsne_y=float(r.tsne_y),pca_x=float(r.pca_x),pca_y=float(r.pca_y),role=r.sampling_role) for r in projection.itertuples()]
        info['atlas']=put(target/'atlas.json.gz',encode(atlas));manifest['binary_cohorts'][name]=info
        print(json.dumps(dict(cohort=name,groups=int(db.valid.sum()),core=len(core),seconds=time.perf_counter()-tick)),flush=True)
    put(SITE/'data/manifest.json',encode(manifest),False)
    downloads=SITE/'downloads';downloads.mkdir(parents=True,exist_ok=True)
    for name in ['main_all_groups.parquet','positive_garage_all_groups.parquet','profile_group_crosswalk.csv','variable_dictionary.csv','focus_groups.csv']:
        shutil.copyfile(REGISTRY/name,downloads/name)

def package_ui():
    SITE.mkdir(parents=True,exist_ok=True)
    for name in ['index.html','app.js','styles.css']:
        shutil.copyfile(ROOT/'workbench/static'/name,SITE/name)
    for name in ['query-client.js','query-worker.js']:
        shutil.copyfile(ROOT/'workbench/pages'/name,SITE/name)
    (SITE/'vendor').mkdir(exist_ok=True)
    shutil.copyfile(ROOT/'workbench/static/vendor/plotly.min.js',SITE/'vendor/plotly.min.js')
    shutil.copyfile(ROOT/'workbench/publication/PLOTLY_LICENSE.txt',SITE/'vendor/PLOTLY_LICENSE.txt')
    shutil.copyfile(ROOT/'workbench/publication/THIRD_PARTY_NOTICES.md',RELEASE/'THIRD_PARTY_NOTICES.md')
    (SITE/'.nojekyll').write_text('',encoding='utf-8')
    workflow=RELEASE/'.github/workflows/pages.yml';workflow.parent.mkdir(parents=True,exist_ok=True)
    workflow.write_text('''name: Publish Group Explorer
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: github-pages
  cancel-in-progress: true
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v6
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v4
        with:
          path: site
      - name: Deploy
        id: deployment
        uses: actions/deploy-pages@v4
''',encoding='utf-8')
    shutil.copyfile(ROOT/'workbench/publication/browser-edition.md',RELEASE/'README.md')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ui-only',action='store_true');args=parser.parse_args()
    start=time.perf_counter()
    if not args.ui_only:build_data()
    package_ui()
    files=sorted(p for p in RELEASE.rglob('*') if p.is_file())
    with zipfile.ZipFile(OUT/'github-pages-release.zip','w',compression=zipfile.ZIP_STORED) as archive:
        for file in files:archive.write(file,file.relative_to(RELEASE).as_posix())
    print(json.dumps(dict(status='built',files=len(files),bytes=sum(p.stat().st_size for p in files),seconds=time.perf_counter()-start)),flush=True)

if __name__=='__main__':main()
