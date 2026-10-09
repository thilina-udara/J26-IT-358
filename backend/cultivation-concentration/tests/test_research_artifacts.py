"""Private artifact installation must reject corruption and unsafe overwrites."""
import hashlib
import json
import zipfile
import pytest
from scripts.research_artifacts import install


def bundle(tmp_path, name='models/experimental/fixture.bin', content=b'reviewed'):
    root = tmp_path / 'component'
    (root / 'models').mkdir(parents=True)
    archive = tmp_path / 'inputs.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr(name, content)
    catalog = {'bundle_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
               'files': {name: hashlib.sha256(content).hexdigest()}}
    (root / 'models/artifact_catalog.json').write_text(json.dumps(catalog))
    return root, archive


def test_hash_verified_install_is_idempotent_and_preserves_local_differences(tmp_path):
    root, archive = bundle(tmp_path)
    assert install(archive, root) == install(archive, root) == 1
    destination = root / 'models/experimental/fixture.bin'
    destination.write_bytes(b'local-change')
    with pytest.raises(ValueError, match='overwrite'):
        install(archive, root)
    assert destination.read_bytes() == b'local-change'


def test_bundle_corruption_has_no_partial_writes(tmp_path):
    root, archive = bundle(tmp_path)
    archive.write_bytes(archive.read_bytes() + b'corrupt')
    with pytest.raises(ValueError, match='hash'):
        install(archive, root)
    assert not (root / 'models/experimental').exists()


def test_component_path_escape_rejected(tmp_path):
    root, archive = bundle(tmp_path, '../escaped.bin')
    with pytest.raises(ValueError, match='escapes'):
        install(archive, root)
    assert not (tmp_path / 'escaped.bin').exists()
