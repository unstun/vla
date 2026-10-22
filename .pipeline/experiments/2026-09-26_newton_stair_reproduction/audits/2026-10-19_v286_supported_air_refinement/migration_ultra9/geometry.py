"""Regenerate pinned geometry in an isolated canonical-path container."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import time

ROOT = Path('/home/ubuntu/sun/vla_v286_20261020')
OLD = Path('/home/ubuntu/sun/vla_v234_20261017')
CANON = Path('/data/sun/vla_mppi_20261009')
TAG = os.environ.get('V286_GEOMETRY_ID', '01')
assert len(TAG) == 2 and TAG.isdigit()
DATA = ROOT / ('geometry_data' if TAG == '01' else 'geometry_data' + TAG)
EXP_REL = '.pipeline/experiments/2026-09-26_newton_stair_reproduction'
VERSIONS = ROOT / 'repo' / EXP_REL / 'versions'
PYTHON = OLD / 'env/newton_worker/bin/python'
ROS_IMAGE = 'sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def fnv(data):
    value = 14695981039346656037
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return str(value)


def main():
    receipt = ROOT / 'evidence' / ('geometry' + TAG + '.json')
    assert not receipt.exists() and not DATA.exists()
    DATA.mkdir()
    legacy = DATA / 'generic_mechanisms_v259/native/fixtures'
    shutil.copytree(ROOT / 'native/fixtures', legacy)
    shutil.copytree(OLD / 'support_coverage_v134', DATA / 'support_coverage_v134')
    assert sha(DATA / 'support_coverage_v134/triangles.f64') == 'f3910b7c8106977d1f6e3364c464a9144c7946a0585c8cdcff4346d7add342fc'
    (DATA / 'repo').mkdir()
    source_v224 = DATA / 'environment_score_v224/fixtures/building'
    source_v224.mkdir(parents=True)
    shutil.copy2(legacy / 'building/environment03.env', source_v224 / 'environment03.env')
    for name in ['generic_mechanisms_v256', 'physical_traversability_v247']:
        shutil.copytree(legacy, DATA / name / 'native/fixtures')
    for folder in [legacy, DATA / 'generic_mechanisms_v256/native/fixtures']:
        (folder / 'probe225.env').write_text('export ENVIRONMENT_INPUT=/work/fixtures/building/environment225.env\n'
            + 'export ENVIRONMENT_FNV=' + fnv((folder / 'building/environment225.env').read_bytes()) + '\n')
    analysis_image = json.loads(subprocess.check_output(['docker', 'image', 'inspect', 'ubuntu:22.04'], text=True))[0]['Id']
    report = dict(stage='prepared', physics_steps=0, checks=[], analysis_image=analysis_image,
        ros_image=ROS_IMAGE, original_native_manifest_sha256=sha(VERSIONS / 'v286/native_manifest.json'),
        scope='Geometry regeneration only; no new captured cohort or scored call')

    def save():
        receipt.write_text(json.dumps(report, indent=2) + '\n')

    def run(label, command):
        path = ROOT / 'evidence' / ('geometry' + TAG + '_' + label + '.log')
        save()
        began = time.monotonic()
        with path.open('x') as log:
            code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
        report['checks'].append(dict(label=label, returncode=code, wall_s=time.monotonic() - began,
            log=str(path), sha256=sha(path)))
        report['stage'] = label if code == 0 else 'failed'
        save()
        assert code == 0, (label, code)

    def analysis(label, code):
        run(label, ['docker', 'run', '--rm', '--pull=never', '--user', f'{os.getuid()}:{os.getgid()}',
            '--cpus=2', '--memory=6g', '-e', 'OPENBLAS_NUM_THREADS=1', '-e', 'OMP_NUM_THREADS=1',
            '-e', 'PYTHONDONTWRITEBYTECODE=1', '-v', str(OLD) + ':' + str(OLD) + ':ro',
            '-v', str(DATA) + ':' + str(CANON) + ':rw',
            '-v', str(ROOT / 'repo') + ':' + str(CANON / 'repo') + ':ro',
            '--entrypoint', str(PYTHON), analysis_image, '-c', code])

    exporter = ROOT / ('exporter' + TAG)
    exporter.mkdir()
    common = 'source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && '
    versions_container = '/task/repo/' + EXP_REL + '/versions'
    run('exporter_build', ['docker', 'run', '--rm', '--pull=never', '--user', f'{os.getuid()}:{os.getgid()}',
        '--cpus=2', '--memory=6g', '-v', str(ROOT) + ':/task:ro', '-v', str(ROOT / 'native') + ':/work:ro',
        '-v', str(ROOT / 'export_source') + ':/source:ro', '-v', str(exporter) + ':/exporter:rw',
        '--entrypoint', '/bin/bash', ROS_IMAGE, '-c', common
        + 'cmake -S /source -B /exporter/build -DVERSIONS_ROOT=' + versions_container
        + ' -DCMAKE_BUILD_TYPE=Release && cmake --build /exporter/build -j2'])

    def export_support(label, fixtures):
        out = ROOT / ('geometry_exports' + TAG) / label
        out.mkdir(parents=True)
        (out / 'ros_home').mkdir()
        (out / 'ros_logs').mkdir()
        environment_fnv = fnv((fixtures / 'building/environment225.env').read_bytes())
        shell = common + 'export CASE_INPUT=/work/fixtures PROBE_OUTPUT=/export REPLAY_INPUT=/work/fixtures/building '
        shell += 'ENVIRONMENT_INPUT=/work/fixtures/building/environment225.env ENVIRONMENT_FNV=' + environment_fnv
        shell += ' ROS_DOMAIN_ID=155 ROS_LOCALHOST_ONLY=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 && '
        shell += '/exporter/build/support_export --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level warn'
        run(label, ['docker', 'run', '--rm', '--pull=never', '--user', f'{os.getuid()}:{os.getgid()}',
            '--cpus=2', '--memory=6g', '-e', 'ROS_HOME=/export/ros_home', '-e', 'ROS_LOG_DIR=/export/ros_logs',
            '-v', str(ROOT / 'native') + ':/work:ro', '-v', str(fixtures) + ':/work/fixtures:ro',
            '-v', str(exporter) + ':/exporter:ro', '-v', str(out) + ':/export:rw',
            '--entrypoint', '/bin/bash', ROS_IMAGE, '-c', shell])
        shutil.copy2(out / 'native.support', fixtures / 'building/native.support')
        return fnv((out / 'native.support').read_bytes())

    base_fnv = export_support('legacy_support', legacy)
    assert base_fnv == '1404261889151999461', base_fnv
    analysis('native_pct', 'import runpy;runpy.run_path(' + repr(str(CANON / 'repo' / EXP_REL / 'versions/v247/prepare_fixtures.py')) + ',run_name="__main__")')
    pct = DATA / 'physical_traversability_v247/native/fixtures/building'
    for name in ['native_original.pct', 'native_original.pct.json', 'terrain247.json', 'environment247.json']:
        shutil.copy2(pct / name, legacy / 'building' / name)
    analysis('legacy_solids', 'import runpy;runpy.run_path(' + repr(str(CANON / 'repo' / EXP_REL / 'versions/v256/prepare_solid_evidence.py')) + ',run_name="__main__")')
    for name in ['static_solids.env', 'static_solids.json']:
        shutil.copy2(DATA / 'generic_mechanisms_v256/native/fixtures/building' / name, legacy / 'building' / name)
    final = DATA / 'generic_mechanisms_v260/native/fixtures'
    shutil.copytree(legacy, final)
    producer = CANON / 'repo' / EXP_REL / 'versions/v260/development/point_plane_attempt/prepare_floor.py'
    # The trailing historical snapshot copy is not a geometry producer. Its old
    # output is unavailable; the current native exporter certifies the final field.
    code = 'from pathlib import Path;import sys;p=Path(' + repr(str(producer)) + ');sys.path.insert(0,str(p.parent));'
    code += 's=p.read_text().split("\\nimport shutil\\nsnapshot=")[0];exec(compile(s,str(p),"exec"),{"__file__":str(p),"__name__":"__main__"})'
    analysis('upward_provenance', code)
    producer = CANON / 'repo' / EXP_REL / 'versions/v260/prepare_floor.py'
    analysis('mesh_floor', 'import runpy,sys;sys.path.insert(0,' + repr(str(producer.parent))
        + ');runpy.run_path(' + repr(str(producer)) + ',run_name="__main__")')
    final_fnv = export_support('mesh_support', final)
    assert final_fnv == '15212154834549674106', final_fnv
    producer = CANON / 'repo' / EXP_REL / 'versions/v268/export.py'
    analysis('source_topology', 'import runpy,sys;sys.path.insert(0,' + repr(str(producer.parent))
        + ');runpy.run_path(' + repr(str(producer)) + ',run_name="__main__")')
    expected = json.loads((VERSIONS / 'v268/results/geometry_export.json').read_text())
    for key, source_name, target_name in [('normalized_triangles', 'triangles_oriented.f64', 'source_triangles.f64'),
        ('closed_volumes', 'closed_volumes.txt', 'source_volumes.txt')]:
        source = DATA / 'source_topology_v268' / source_name
        assert sha(source) == expected[key]['sha256'], (key, sha(source))
        shutil.copy2(source, final / target_name)
    text = 'SURFACE271B .35 .18 .55 .35 .3 .15\n'
    for name in ['source_triangles.f64', 'source_volumes.txt']:
        text += '"/work/fixtures/' + name + '" ' + fnv((final / name).read_bytes()) + '\n'
    (final / 'source_surface.env').write_text(text)
    original = json.loads((VERSIONS / 'v280/results/fixture_files.json').read_text())
    core = ['source_triangles.f64', 'source_volumes.txt', 'source_surface.env', 'building/native_original.pct',
        'building/native.support', 'building/navigation.f32', 'building/surface.f32', 'building/physical_floor.f32',
        'building/support_gap.txt', 'building/environment225.env', 'building/static_solids.env']
    report['core_files'] = {name: dict(sha256=sha(final / name),
        expected_sha256=original['fixtures/' + name], bytes=(final / name).stat().st_size) for name in core}
    assert all(r['sha256'] == r['expected_sha256'] for r in report['core_files'].values())
    report.update(stage='passed', completed_utc_s=time.time(), exact_original_geometry_files=len(core),
        native_support_fnv64=final_fnv, final_fixtures=str(final))
    save()


if __name__ == '__main__':
    main()
