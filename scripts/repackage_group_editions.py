"""Update explicit publication files in verified release ZIPs; preserve all study data."""
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED, ZIP_STORED
from datetime import datetime
import argparse
import hashlib
import json
import time


def sha_file(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def inventory_hash(rows):
    body=json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(body).hexdigest()


def process(config,source_root,base_dir,output_dir,verify_only=False):
    output_dir.mkdir(parents=True,exist_ok=True)
    timestamp=datetime.fromisoformat(config['timestamp']).timetuple()[:6]
    manifest={'version':config['version'],'base_version':config['base_version'],'editions':[]}
    for edition in config['editions']:
        tick=time.perf_counter();base=base_dir/edition['base_name']
        assert sha_file(base)==edition['base_sha256'],base.name
        replacements={}
        for member,source in edition['replacements'].items():
            p=(source_root/source).resolve()
            assert p.is_relative_to(source_root.resolve())
            body=p.read_bytes()
            if p.suffix=='.md':body=body.replace(b'\r\n',b'\n')
            replacements[member]=body
        target=output_dir/edition['name'];expected={};changed=[]
        writer=None if verify_only else ZipFile(target,'w',compression=ZIP_DEFLATED,compresslevel=3)
        try:
            with ZipFile(base) as old:
                names=old.namelist()
                assert len(names)==len(set(names)) and len(names)<=25000
                assert set(replacements).issubset(names)
                for item in old.infolist():
                    p=PurePosixPath(item.filename)
                    assert not p.is_absolute() and '..' not in p.parts and ':' not in item.filename and '\\' not in item.filename
                    # The verified main group catalog is a 488 MB member.
                    assert item.file_size<=600_000_000
                    original=old.read(item)
                    body=replacements.get(item.filename,original)
                    expected[item.filename]={'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
                    if item.filename in replacements:changed.append(item.filename)
                    if writer is not None:
                        info=ZipInfo(item.filename,timestamp)
                        info.create_system=3;info.external_attr=item.external_attr
                        method=ZIP_STORED if edition['kind']=='browser' else ZIP_DEFLATED
                        writer.writestr(info,body,compress_type=method,compresslevel=3)
        finally:
            if writer is not None:writer.close()
        if not verify_only:
            with ZipFile(target) as completed:
                assert set(completed.namelist())==set(expected)
                for name,record in expected.items():
                    body=completed.read(name)
                    assert len(body)==record['bytes'] and hashlib.sha256(body).hexdigest()==record['sha256'],name
        entry={'kind':edition['kind'],'name':edition['name'],'files':len(expected),
               'changed_files':changed,'preserved_files':len(expected)-len(changed),
               'content_inventory_sha256':inventory_hash(expected),'seconds':time.perf_counter()-tick}
        if not verify_only:entry.update(bytes=target.stat().st_size,sha256=sha_file(target))
        manifest['editions'].append(entry)
        print(json.dumps(entry),flush=True)
    manifest['status']='passed';manifest['mode']='expected' if verify_only else 'packaged'
    name='expected-edition-contents.json' if verify_only else 'edition-patch-manifest.json'
    (output_dir/name).write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    if not verify_only:
        sums=''.join(e['sha256']+'  '+e['name']+'\n' for e in manifest['editions'])
        (output_dir/'SHA256SUMS.txt').write_bytes(sums.encode('ascii'))
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--source-root',type=Path,default=Path.cwd())
    parser.add_argument('--base-dir',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    process(json.loads(args.config.read_text(encoding='utf-8')),args.source_root,args.base_dir,args.output_dir,args.verify_only)
