"""Close geometry regeneration after all producer logs and original hashes pass."""
from pathlib import Path
import hashlib
import json
import time

ROOT = Path('/home/ubuntu/sun/vla_v286_20261020')
VERSIONS = ROOT / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    output = ROOT / 'evidence/geometry01_closed.json'
    assert not output.exists()
    producer = ROOT / 'evidence/geometry01.json'
    closed = json.loads(producer.read_text())
    assert len(closed['checks']) == 8
    for row in closed['checks']:
        assert row['returncode'] == 0 and sha(Path(row['log'])) == row['sha256']
    final = ROOT / 'geometry_data/generic_mechanisms_v260/native/fixtures'
    expected = json.loads((VERSIONS / 'v280/results/fixture_files.json').read_text())
    names = ['source_triangles.f64', 'source_volumes.txt', 'source_surface.env', 'building/native_original.pct',
        'building/native.support', 'building/navigation.f32', 'building/surface.f32', 'building/physical_floor.f32',
        'building/support_gap.txt', 'building/environment225.env', 'building/static_solids.env']
    files = {name: dict(sha256=sha(final / name), expected_sha256=expected['fixtures/' + name],
        bytes=(final / name).stat().st_size) for name in names}
    assert all(v['sha256'] == v['expected_sha256'] for v in files.values()), files
    report = dict(passed=True, physics_steps=0, core_files=files, exact_original_geometry_files=len(names),
        final_fixtures=str(final), original_native_manifest_sha256=sha(VERSIONS / 'v286/native_manifest.json'),
        producer_receipt_sha256=sha(producer), completed_utc_s=time.time(),
        note='Initial driver reached all eight successful producers, then lacked the transferred comparison manifest; no producer or scored call repeated.')
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(passed=True, exact_original_geometry_files=len(names), physics_steps=0)))


if __name__ == '__main__':
    main()
