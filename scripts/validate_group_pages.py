"""Check every static record/rank and the publish boundary, without changing data."""
from build_group_pages import ROOT, OUT, SITE, RELEASE, PACK, SHARD_SIZE, Catalog
import gzip
import hashlib
import json
import time
import numpy as np

def main():
    tick=time.perf_counter();m=json.loads((SITE/'data/manifest.json').read_text('utf-8'));catalog=Catalog()
    assert m['version']==catalog.manifest['version'] and m['aliases']==catalog.manifest['aliases']
    expected={'index.html','app.js','styles.css','query-client.js','query-worker.js','vendor/plotly.min.js','vendor/PLOTLY_LICENSE.txt','.nojekyll','data/manifest.json'}
    def raw(file):
        expected.add(file['path']);body=(SITE/file['path']).read_bytes()
        assert len(body)==file['bytes'] and hashlib.sha256(body).hexdigest()==file['sha256']
        decoded=gzip.decompress(body);assert len(decoded)==file['raw_bytes'];return decoded
    results=[]
    for name,db in catalog.cohorts.items():
        info=m['binary_cohorts'][name];seen=0
        for part,file in enumerate(info['shards']):
            values=np.frombuffer(raw(file),dtype=PACK);indices=np.arange(part*SHARD_SIZE,part*SHARD_SIZE+len(values))
            source=db.g.stats[indices]
            np.testing.assert_array_equal(values['index'],indices);np.testing.assert_array_equal(values['n'],source['n'])
            np.testing.assert_array_equal(values['ratio'],db.ratio[indices])
            for field in ['closure_lo','closure_hi','generator_lo','generator_hi']:np.testing.assert_array_equal(values[field],source[field])
            seen+=len(values)
        assert seen==len(db.g.stats)==info['records']
        core=np.frombuffer(raw(info['core']),dtype=PACK);ids=np.flatnonzero(db.valid&(db.n>=100))
        np.testing.assert_array_equal(core['index'],ids)
        for field in ['n','closure_lo','closure_hi','generator_lo','generator_hi']:np.testing.assert_array_equal(core[field],db.g.stats[ids][field])
        np.testing.assert_array_equal(core['ratio'],db.ratio[ids])
        for side in ['high','low']:
            full=np.frombuffer(raw(info['ranks'][side]),dtype='<u4');source=np.asarray(db.orders[side]);source=source[db.valid[source]]
            np.testing.assert_array_equal(full,source)
            subset=np.frombuffer(raw(info['core_ranks'][side]),dtype='<u4')
            np.testing.assert_array_equal(ids[subset],source[db.n[source]>=100])
        members=json.loads(raw(info['members']));assert len(members)==len(db.g.members)
        assert [r[0] for r in members]==db.g.members.index.to_list()
        np.testing.assert_array_equal(np.array([r[4:] for r in members]),db.g.members[['bin_'+f for f in db.g.fields]].to_numpy(int))
        np.testing.assert_array_equal(np.array([r[1:4] for r in members]),db.g.members[['sale_price_usd','assessed_value_usd','ratio']].to_numpy(float))
        atlas=json.loads(raw(info['atlas']));assert len(atlas)==1320
        results.append(dict(cohort=name,groups=seen-1,core=len(core),full_bytes=sum(f['bytes'] for f in info['shards']),
            initial_bytes=info['core']['bytes']+info['core_ranks']['high']['bytes']+info['members']['bytes']))
    for name in ['main_all_groups.parquet','positive_garage_all_groups.parquet','profile_group_crosswalk.csv','variable_dictionary.csv','focus_groups.csv']:expected.add('downloads/'+name)
    actual={p.relative_to(SITE).as_posix() for p in SITE.rglob('*') if p.is_file()};assert actual==expected,(actual-expected,expected-actual)
    files=[p for p in RELEASE.rglob('*') if p.is_file()]
    assert all(not p.is_symlink() for p in files)
    sizes=[p.stat().st_size for p in files];assert max(sizes)<100*1024**2 and sum(sizes)<1024**3
    html=(SITE/'index.html').read_text('utf-8')
    assert 'href="/' not in html and 'src="/' not in html
    assert '127.0.0.1' not in html and 'localhost' not in (SITE/'query-client.js').read_text('utf-8')
    assert (SITE/'query-client.js').read_bytes()!=(ROOT/'workbench/static/query-client.js').read_bytes()
    result=dict(status='passed',version=m['version'],cohorts=results,files=len(files),bytes=sum(sizes),largest_file_bytes=max(sizes),
        two_editions=True,all_binary_records_and_ranks='passed',seconds=time.perf_counter()-tick,
        files_sha256={p.relative_to(RELEASE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    (OUT/'package_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='files_sha256'}),flush=True)

if __name__=='__main__':main()
