"""Install an explicitly supplied, hash-verified private PP1 bundle; never train."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def install(bundle, root=ROOT):
    catalog = json.loads((root / 'models/artifact_catalog.json').read_text())
    bundle = Path(bundle)
    if hashlib.sha256(bundle.read_bytes()).hexdigest() != catalog['bundle_sha256']:
        raise ValueError('Bundle hash does not match the reviewed catalog')
    with zipfile.ZipFile(bundle) as archive:
        # Validate the complete payload before writing any file.
        verified = {}
        for name, digest in catalog['files'].items():
            destination = (root / name).resolve()
            if not destination.is_relative_to(root.resolve()):
                raise ValueError('Artifact path escapes component')
            data = archive.read(name)
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError(f'Artifact hash mismatch: {name}')
            if destination.exists() and destination.read_bytes() != data:
                raise ValueError(f'Refusing to overwrite different local file: {name}')
            verified[destination] = data
        for destination, data in verified.items():
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                destination.write_bytes(data)
    return len(verified)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    args = parser.parse_args()
    print(f'Installed/verified {install(args.bundle)} private artifact inputs')
