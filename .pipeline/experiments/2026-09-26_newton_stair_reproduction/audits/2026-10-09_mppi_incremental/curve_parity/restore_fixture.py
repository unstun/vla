"""Restore the original bounded native replay fixture on the execution host."""
from pathlib import Path
import hashlib
import json
import tarfile

task = Path('/data/sun/vla_mppi_20261009')
archive = Path('/home/sun/vla_artifacts/2026-10-08_nav2_sim_repair/attempt01/vla_nav2_sim_repair_v100_v114.tar.gz')
expected = 'd2613a0720606c1c999a1ab858ed4ae71c1fb22ff746e9007b17e5f1ca77c806'
digest = hashlib.sha256()
with archive.open('rb') as stream:
    for chunk in iter(lambda: stream.read(4*1024**2), b''):
        digest.update(chunk)
assert digest.hexdigest() == expected
prefix = 'vla_nav2_simrepair_5z7q27y7/replay_input02/'
destination = task/'fixed_curve_input'
destination.mkdir(exist_ok=False)
with tarfile.open(archive) as bundle:
    for member in bundle:
        if not member.isfile() or not member.name.startswith(prefix):
            continue
        target = destination/member.name[len(prefix):]
        assert target.resolve().is_relative_to(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bundle.extractfile(member).read())
identity = json.loads((destination/'identity.json').read_text())
for name, expected_file in identity['files'].items():
    assert hashlib.sha256((destination/name).read_bytes()).hexdigest() == expected_file, name
(task/'results/fixed_curve_fixture.json').write_text(json.dumps({
    'passed': True, 'archive': str(archive), 'archive_sha256': expected,
    'member_prefix': prefix, 'output': str(destination),
    'identity_sha256': hashlib.sha256((destination/'identity.json').read_bytes()).hexdigest(),
    'files': identity['files']}, indent=2)+'\n')
print('FIXED_CURVE_INPUT_VERIFIED', len(identity['files']))
