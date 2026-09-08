"""Publish only the validated report and bounded reproducibility files to shared UI."""
from pathlib import Path
import json
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/research_story'
STATIC=ROOT/'workbench/static'
receipt=json.loads((OUT/'report_delivery_validation.json').read_text(encoding='utf-8'))
assert receipt['ok'] and receipt['stages']['verification']=='passed'
assert json.loads((OUT/'validation.json').read_text(encoding='utf-8'))['status']=='passed'
shutil.copyfile(OUT/'research-story.html',STATIC/'research-story.html')
with ZipFile(STATIC/'research-story-sources.zip','w',ZIP_DEFLATED) as z:
    for path in sorted(OUT.iterdir()):
        if path.suffix=='.csv' or path.name in {'artifact.json','validation.json','report_delivery_validation.json','research_story.md'}:
            z.write(path,'outputs/research_story/'+path.name)
    for name in ['build_research_story.py','verify_research_story.R','package_research_story.py']:
        z.write(ROOT/'scripts'/name,'scripts/'+name)
    z.write(ROOT/'docs/research_story.md','docs/research_story.md')
    z.writestr('README.txt','Derived evidence for the research story. Original study data are not duplicated here.\nThe Python builder requires the research workspace and local scientific dependencies.\nThe base-R script requires only R and the named original CSVs; it was supplied but not executed.\nThe initial private handoff document is identified by hash only and is not distributed.\n')
print('Validated research story copied to both editions\' shared UI.')
