"""Recover verified locked dependencies from quarantined local package files.

This reads package metadata as data. It never imports the old packages or runs
their launchers. pip installs these wheels into the newly created environment.
"""
import base64
import csv
import hashlib
import importlib.metadata as metadata
import io
import json
from pathlib import Path
import re
import zipfile
from pip._vendor.packaging.tags import sys_tags

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'scratch/pp1-isolation/copied-venv-DO-NOT-USE/Lib/site-packages'
OUTPUT = ROOT / 'scratch/pp1-isolation/wheels'


def normalized(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    distributions = {normalized(d.metadata['Name']): d
                     for d in metadata.distributions(path=[str(SITE)])}
    manifest = []
    compatible_tags = {str(tag) for tag in sys_tags()}
    for line in (ROOT / 'backend/cultivation-concentration/requirements.lock.txt').read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        name, version = line.split('==')
        dist = distributions[normalized(name)]
        if dist.version != version:
            raise RuntimeError(f'Local version mismatch for {name}')
        wheel_info = dist.read_text('WHEEL')
        tags = [line[5:].strip() for line in wheel_info.splitlines() if line.startswith('Tag: ')]
        # These local wheels use one of the original distribution's declared tags.
        tag = next(tag for tag in tags if tag in compatible_tags)
        filename = f'{normalized(name).replace("-", "_")}-{version}-{tag}.whl'
        destination = OUTPUT / filename
        records = []
        skipped_launchers = 0
        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as wheel:
            for file in dist.files or ():
                source = Path(dist.locate_file(file)).resolve()
                member = None
                if not source.is_relative_to(SITE.resolve()):
                    # pip regenerates entry-point executables from entry_points.txt.
                    if source.parent == (SITE.parents[1] / 'Scripts').resolve() and source.suffix == '.exe':
                        skipped_launchers += 1
                        continue
                    old_prefix = SITE.parents[1].resolve()
                    if source.is_relative_to(old_prefix) and 'Scripts' not in source.relative_to(old_prefix).parts:
                        member = (f'{normalized(name).replace("-", "_")}-{version}.data/data/'
                                  + source.relative_to(old_prefix).as_posix())
                    else:
                        raise RuntimeError(f'Unexpected package file outside copied environment: {file}')
                if source.suffix == '.pyc' or source.name in {'RECORD', 'INSTALLER', 'REQUESTED', 'direct_url.json'}:
                    continue
                data = source.read_bytes()
                if not file.hash:
                    raise RuntimeError(f'Unhashed local package input: {file}')
                digest = base64.urlsafe_b64encode(hashlib.new(file.hash.mode, data).digest()).rstrip(b'=').decode()
                if digest != file.hash.value:
                    raise RuntimeError(f'Installed RECORD hash mismatch: {file}')
                member = member or source.relative_to(SITE).as_posix()
                wheel.writestr(member, data)
                sha256 = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
                records.append((member, 'sha256=' + sha256, str(len(data))))
            record_name = next(p for p, _, _ in records if p.endswith('.dist-info/METADATA')).rsplit('/', 1)[0] + '/RECORD'
            text = io.StringIO(newline='')
            writer = csv.writer(text, lineterminator='\n')
            writer.writerows(records + [(record_name, '', '')])
            wheel.writestr(record_name, text.getvalue())
        manifest.append({'name': name, 'version': version, 'verified_files': len(records),
                         'regenerated_launchers': skipped_launchers, 'wheel': filename})
        print(f'{name}=={version}: {len(records)} files verified', flush=True)
    (OUTPUT.parent / 'local-wheel-manifest.json').write_text(json.dumps(manifest, indent=2))
    print(f'Prepared {len(manifest)} wheels from local package files.', flush=True)


if __name__ == '__main__':
    main()
