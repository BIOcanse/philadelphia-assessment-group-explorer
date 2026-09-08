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
args=parser.parse_args()
OUT=(ROOT/args.input).resolve()
assert OUT.is_relative_to(ROOT/'outputs')
builder=(ROOT/args.builder).resolve();plan=(ROOT/args.plan).resolve()
assert builder.is_relative_to(ROOT/'scripts') and plan.is_relative_to(ROOT/'docs')
STATIC=ROOT/'workbench/static'
receipt=json.loads((OUT/'report_delivery_validation.json').read_text(encoding='utf-8'))
assert receipt['ok'] and receipt['stages']['verification']=='passed'
assert json.loads((OUT/'validation.json').read_text(encoding='utf-8'))['status']=='passed'
shutil.copyfile(OUT/'research-story.html',STATIC/'research-story.html')
with ZipFile(STATIC/'research-story-sources.zip','w',ZIP_DEFLATED) as z:
    for path in sorted(OUT.iterdir()):
        if path.suffix=='.csv' or path.name in {'artifact.json','validation.json','report_delivery_validation.json','research_story.md'}:
            z.write(path,path.relative_to(ROOT).as_posix())
    for path in [builder,ROOT/'scripts/package_research_story.py',ROOT/'scripts/deliver_report.mjs',plan]:
        z.write(path,path.relative_to(ROOT).as_posix())
    z.writestr('README.txt','Existing evidence and research plan for the main narrative. Original study data are not duplicated here.\nThe builder requires the research workspace and named source files.\nHeld-out validation of the algebraic derivation has not been executed; no score is claimed.\n')
print('Validated research story copied to both editions\' shared UI.')
