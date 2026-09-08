"""Publish only the validated report and bounded reproducibility files to shared UI."""
from pathlib import Path
import argparse
import json
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--input',default='outputs/research_story',type=Path)
parser.add_argument('--builder',default='scripts/build_research_story.py',type=Path)
parser.add_argument('--plan',default='docs/research_story.md',type=Path)
parser.add_argument('--evidence-dir',type=Path)
parser.add_argument('--extra-source',type=Path,action='append',default=[])
args=parser.parse_args()
OUT=(ROOT/args.input).resolve()
assert OUT.is_relative_to(ROOT/'outputs')
builder=(ROOT/args.builder).resolve();plan=(ROOT/args.plan).resolve()
assert builder.is_relative_to(ROOT/'scripts') and plan.is_relative_to(ROOT/'docs')
STATIC=ROOT/'workbench/static'
receipt=json.loads((OUT/'report_delivery_validation.json').read_text(encoding='utf-8'))
assert receipt['ok'] and receipt['stages']['verification']=='passed'
validation=json.loads((OUT/'validation.json').read_text(encoding='utf-8'))
assert validation['status']=='passed'
shutil.copyfile(OUT/'research-story.html',STATIC/'research-story.html')
with ZipFile(STATIC/'research-story-sources.zip','w',ZIP_DEFLATED) as z:
    for path in sorted(OUT.iterdir()):
        if path.suffix=='.csv' or path.name in {'artifact.json','validation.json','report_delivery_validation.json','research_story.md'}:
            z.write(path,path.relative_to(ROOT).as_posix())
    for path in [builder,ROOT/'scripts/package_research_story.py',ROOT/'scripts/deliver_report.mjs',plan]:
        z.write(path,path.relative_to(ROOT).as_posix())
    for relative in args.extra_source:
        path=(ROOT/relative).resolve();assert path.is_relative_to(ROOT) and path.is_file()
        z.write(path,path.relative_to(ROOT).as_posix())
    if args.evidence_dir:
        evidence=(ROOT/args.evidence_dir).resolve();assert evidence.is_relative_to(ROOT/'outputs')
        queue=[evidence];count=0
        while queue:
            folder=queue.pop(0)
            for path in sorted(folder.iterdir()):
                assert not path.is_symlink()
                if path.is_dir():queue.append(path)
                elif path.suffix in ['.csv','.json','.npz'] and path.name not in ['groups.csv','partitions.csv']:
                    count+=1;assert count<=1000 and path.stat().st_size<20_000_000
                    z.write(path,path.relative_to(ROOT).as_posix())
    status=validation.get('formula_holdout_validation','not executed')
    z.writestr('README.txt','Evidence and reproducible research sources for the main narrative.\nThe builders require the research workspace and named original source files.\nFormula holdout validation status: '+status+'.\nThe frozen protocol records its pre-execution state; current results and validation receipts supersede that status.\nCase predictions, splits and fitted equations are included when an evidence directory is supplied; repeated per-case group tables and large binary catalogs are not duplicated.\n')
print('Validated research story copied to both editions\' shared UI.')
