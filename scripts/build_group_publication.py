"""Prepare the allowlisted public source checkout and two complete release assets."""
from pathlib import Path
import argparse
from collections import deque
from email.parser import BytesParser
import hashlib
import json
import os
import shutil
import subprocess
import time
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/group_publication'
LOCAL = OUT / 'local'
DOWNLOADS = OUT / 'downloads'
TEMPLATES = ROOT / 'workbench/publication'
VERSION = 'v1.1.0'
PYTHON_ZIP = 'python-3.13.15-embed-amd64.zip'
PYTHON_SHA = 'd1f04d990aee1253d8569e8e5104e30fa9f5fa830899f14843448872d936a2cf'
APP_FILES = [
    'workbench/server.py', 'workbench/catalog.py',
    'scripts/query_group_means.py', 'scripts/group_mean_schema.py',
    'workbench/static/index.html', 'workbench/static/app.js',
    'workbench/static/styles.css', 'workbench/static/query-client.js',
    'workbench/static/research.js', 'workbench/static/research.css',
    'workbench/static/vendor/plotly.min.js',
]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def files_under(root):
    pending = deque([root]); count = 0
    while pending:
        folder = pending.popleft()
        for entry in sorted(folder.iterdir()):
            count += 1
            if count > 25000 or entry.is_symlink():
                raise ValueError('Unexpected package size or symlink: ' + str(entry))
            if entry.is_dir():
                if entry.name not in ['.git', '__pycache__']:
                    pending.append(entry)
            elif entry.is_file():
                yield entry


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


def extract_verified(archive, target):
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            destination = (target / item.filename).resolve()
            if not destination.is_relative_to(target.resolve()):
                raise ValueError('Archive entry escapes package')
    result = subprocess.run([shutil.which('7z'), 'x', '-y', '-bso0', '-bsp0',
                             '-o' + str(target), str(archive)], capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace'))


def runtime():
    archive = DOWNLOADS / PYTHON_ZIP
    assert sha(archive) == PYTHON_SHA
    provenance = [dict(name='Python', version='3.13.15', file=archive.name,
                       url='https://www.python.org/ftp/python/3.13.15/' + archive.name,
                       sha256=PYTHON_SHA)]
    target = LOCAL / 'runtime'
    extract_verified(archive, target)
    requirements = []
    for wheel in sorted(DOWNLOADS.glob('*.whl')):
        with zipfile.ZipFile(wheel) as z:
            metadata = BytesParser().parsebytes(z.read(next(n for n in z.namelist() if n.endswith('.dist-info/METADATA'))))
        name, version = metadata['Name'], metadata['Version']
        with urllib.request.urlopen(f'https://pypi.org/pypi/{name}/{version}/json', timeout=30) as response:
            release = json.load(response)
        remote = next(item for item in release['urls'] if item['filename'] == wheel.name)
        digest = sha(wheel)
        assert digest == remote['digests']['sha256'], wheel.name
        provenance.append(dict(name=name, version=version, file=wheel.name, url=remote['url'], sha256=digest))
        requirements.append(name + '==' + version)
        extract_verified(wheel, target / 'Lib/site-packages')
    assert len(requirements) == 5
    write(target / 'python313._pth', 'python313.zip\n.\nLib/site-packages\n../workbench\n../scripts\nimport site\n')
    write(LOCAL / 'runtime-provenance.json', json.dumps(provenance, indent=2))
    write(LOCAL / 'requirements-local.txt', '\n'.join(requirements) + '\n')
    print(json.dumps(dict(stage='runtime', components=len(provenance))), flush=True)


def prepare(repository):
    OUT.mkdir(parents=True, exist_ok=True)
    registry = json.loads((ROOT / 'outputs/group_workbench/registry.json').read_text('utf-8'))
    data_files = {p.replace('\\', '/') for p in registry['sources']}
    data_files.update('workbench/static/' + name for name in ['research-data.json','research-data.json.gz','research-sources.zip'])
    for cohort in ['main', 'positive_garage']:
        for side in ['high', 'low']:
            data_files.add(f'outputs/group_means/{cohort}_rank_{side}.npy')
        data_files.add(f'outputs/group_atlas/{cohort}_projection.csv')
    for name in ['registry.json', 'profile_group_crosswalk.csv', 'variable_dictionary.csv',
                 'focus_groups.csv', 'Group_ID_Dictionary.xlsx',
                 'main_all_groups.parquet', 'positive_garage_all_groups.parquet']:
        data_files.add('outputs/group_workbench/' + name)
    for relative in sorted(set(APP_FILES) | data_files):
        copy(ROOT / relative, LOCAL / relative)
    print(json.dumps(dict(stage='local_data', files=len(data_files))), flush=True)
    for name in ['Start.cmd', 'Stop.cmd']:
        copy(ROOT / 'workbench/distribution' / name, LOCAL / name)
    copy(ROOT / 'workbench/distribution/start-local.ps1', LOCAL / 'scripts/start-local.ps1')
    copy(TEMPLATES / 'local-edition.md', LOCAL / 'README.md')
    runtime()
    copy(TEMPLATES / 'THIRD_PARTY_NOTICES.md', LOCAL / 'THIRD_PARTY_NOTICES.md')
    copy(TEMPLATES / 'PLOTLY_LICENSE.txt', LOCAL / 'PLOTLY_LICENSE.txt')
    copy(TEMPLATES / 'methodology.md', LOCAL / 'docs/methodology.md')

    repository.mkdir(parents=True, exist_ok=True)
    for relative in APP_FILES + ['workbench/pages/query-client.js', 'workbench/pages/query-worker.js',
                                 'scripts/build_group_pages.py', 'scripts/validate_group_pages.py',
                                 'scripts/build_group_publication.py','scripts/build_research_workbench.py',
                                 'scripts/test_research_workbench.mjs','scripts/test_research_workbench_races.mjs',
                                 'scripts/collect_research_workbench_validation.py']:
        copy(ROOT / relative, repository / relative)
    for name in ['Start.cmd', 'Stop.cmd', 'start-local.ps1']:
        copy(ROOT / 'workbench/distribution' / name, repository / 'workbench/distribution' / name)
    for template in files_under(TEMPLATES):
        copy(template, repository / 'workbench/publication' / template.relative_to(TEMPLATES))
    copy(TEMPLATES / 'README.md', repository / 'README.md')
    copy(TEMPLATES / 'THIRD_PARTY_NOTICES.md', repository / 'THIRD_PARTY_NOTICES.md')
    copy(TEMPLATES / 'PLOTLY_LICENSE.txt', repository / 'PLOTLY_LICENSE.txt')
    for name in ['local-edition.md', 'browser-edition.md', 'methodology.md', 'validation.md']:
        copy(TEMPLATES / name, repository / 'docs' / name)
    copy(TEMPLATES / 'pages-release.yml', repository / '.github/workflows/pages.yml')
    copy(ROOT / 'docs/research_workbench.md', repository / 'docs/research-workbench-design.md')
    copy(ROOT / 'outputs/research_workbench/data-validation.json', repository / 'docs/research-data-validation.json')
    copy(LOCAL / 'requirements-local.txt', repository / 'requirements-local.txt')
    copy(LOCAL / 'runtime-provenance.json', repository / 'docs/runtime-provenance.json')
    write(repository / '.gitignore', 'outputs/\nruntime/\n__pycache__/\n*.pyc\n*.log\n.venv/\n.codex/\n')
    write(repository / '.gitattributes', '* text=auto eol=lf\n*.bin binary\n*.zip binary\n*.png binary\n*.cmd text eol=crlf\n*.ps1 text eol=crlf\nworkbench/static/vendor/* -text -diff\n')
    print(json.dumps(dict(stage='prepared', repository=str(repository), local_bytes=sum(p.stat().st_size for p in files_under(LOCAL)))), flush=True)


def package(repository):
    artifacts = OUT / 'assets' / VERSION; artifacts.mkdir(parents=True, exist_ok=True)
    browser = artifacts / f'group-explorer-browser-{VERSION}.zip'
    copy(ROOT / 'outputs/group_pages/github-pages-release.zip', browser)
    local = artifacts / f'group-explorer-local-windows-x64-{VERSION}.zip'
    # Build from a precise allowlist so validation logs and runtime state cannot enter a release.
    paths = [p for p in files_under(LOCAL) if p.name not in ['runtime.json', 'server.stdout.log', 'server.stderr.log']]
    listing = OUT / 'local-zip-files.txt'
    write(listing, '\n'.join(p.relative_to(LOCAL).as_posix() for p in paths) + '\n')
    temporary = artifacts / 'local-building.zip'
    if temporary.exists(): temporary.unlink()
    tick = time.perf_counter()
    result = subprocess.run([shutil.which('7z'), 'a', '-tzip', '-mm=Deflate', '-mx=3', '-mmt=4',
                             '-scsUTF-8', '-bsp0', str(temporary), '@' + str(listing)],
                            cwd=LOCAL, capture_output=True, timeout=300)
    (OUT / 'archive-build.log').write_bytes(result.stdout + result.stderr)
    if result.returncode: raise RuntimeError('ZIP creation failed; see archive-build.log')
    os.replace(temporary, local)
    with zipfile.ZipFile(local) as archive:
        assert set(archive.namelist()) == {p.relative_to(LOCAL).as_posix() for p in paths}
    sums = ''.join(sha(p) + '  ' + p.name + '\n' for p in [browser, local])
    write(artifacts / 'SHA256SUMS.txt', sums)
    copy(artifacts / 'SHA256SUMS.txt', repository / 'docs/SHA256SUMS.txt')
    manifest = dict(version=VERSION, data_version='groups-b5a7e308e8c6',
                    assets=[dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in [browser, local]],
                    local_files=len(paths), archive_seconds=time.perf_counter()-tick)
    write(OUT / 'release-manifest.json', json.dumps(manifest, indent=2))
    copy(OUT / 'release-manifest.json', repository / 'docs/release-manifest.json')
    print(json.dumps(manifest), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['prepare', 'package'])
    parser.add_argument('--repository-dir', required=True, type=Path)
    args = parser.parse_args()
    if args.stage == 'prepare': prepare(args.repository_dir.resolve())
    else: package(args.repository_dir.resolve())
