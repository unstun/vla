"""Package compact verified evidence and videos; never return raw/build trees."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
PREFIX = Path('/home/ubuntu/sun/vla_v234_20261017')
OUT = HERE / 'results'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    partial = json.loads((OUT / 'partial_video_verification.json').read_text())
    assert partial['passed'] and partial['render_only_no_physics_steps']
    physical = PREFIX / 'trials/v236_linux_full_attempt01/runs/v236_linux_full_attempt01'
    assert not (physical / 'result.json').exists()
    finish = json.loads((physical / 'artifacts/external_episode/finish_request.json').read_text())
    assert finish['backend_terminal_status'] == 'FAILED'
    outcome = json.loads((OUT/'outcome.json').read_text())
    assert outcome['finish_request_present'] and outcome['recorded_backend_terminal_status'] == 'FAILED'
    ledger = json.loads((PREFIX / 'evidence/v236_physical_launch_once.json').read_text())
    assert ledger['authorized_attempts'] == 1
    videos = {'v236_partial_attempt01.mp4': partial['video_sha256']}
    for name in ('full_physics_comparison', 'stairs_physics_45_55'):
        proof = json.loads((OUT / (name + '_verification.json')).read_text())
        assert proof['passed'] and proof['full_decode_passed']
        videos[name + '.mp4'] = proof['video_sha256']
    for name, expected in videos.items():
        assert sha(HERE / 'delivered' / name) == expected, name
    snapshot = json.loads((OUT / 'capture_snapshot.json').read_text())
    archive = Path(snapshot['archive'])
    assert sha(archive) == snapshot['archive_sha256']
    with zipfile.ZipFile(archive) as source:
        for name, row in snapshot['members'].items():
            data = source.read(name)
            assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
            assert sha(physical / name) == row['sha256'], name
    render = Path(partial['render_root']) / 'runs/full01'
    for name in ('video_verification.json', 'display_contract.json'):
        shutil.copyfile(render / name, OUT / name)
    port=json.loads((render/'host_port_verification.json').read_text())
    assert port['physical_source_version']=='v236' and port['render_only_no_physics_steps']
    (OUT/'display_binding.json').write_text(json.dumps(dict(physical_source_version='v236',native_source_version='v232',
        locomotion='v216',display_parent='v220',original_capture=str(physical),render_root=partial['render_root'],
        recorded_states_only=True,no_render_physics=True),indent=2)+'\n')
    scanner=json.loads((OUT/'scanner_timing_summary.json').read_text());assert scanner['deadline_failures']==0
    evidence = OUT / 'preparation_logs'
    evidence.mkdir(exist_ok=True)
    for name in ('v236_preflight01.log', 'v236_preflight02.log', 'v236_physical01.log',
                 'v236_scan_probe01.log','v236_scan_probe02.log','v236_scan_probe03.log','v236_scan_probe04.log','v236_tests01.log', 'v236_analysis01.log', 'v236_render01.log',
                 'v236_render02.log', 'v236_render03.log', 'v236_compare01.log'):
        path = PREFIX / 'evidence' / name
        if path.is_file():
            shutil.copyfile(path, evidence / name)
    shutil.copyfile(physical / 'run.log', evidence / 'physical_run.log')
    shutil.copyfile(PREFIX / 'evidence/v236_physical_launch_once.json', OUT / 'physical_launch_once.json')
    review = OUT / 'visual_review'
    review.mkdir(exist_ok=True)
    for name, video, t in (('partial_initial.png', 'v236_partial_attempt01.mp4', 0),
                           ('partial_tail.png', 'v236_partial_attempt01.mp4', (partial['frames']-1)/30),
                           ('stairs_not_reached.png', 'stairs_physics_45_55.mp4', 3)):
        subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', str(HERE / 'delivered' / video),
                        '-frames:v', '1', str(review / name)], check=True)
    files = [p for tree in (OUT, HERE / 'delivered') for p in tree.rglob('*') if p.is_file() and p.name != 'return_manifest.json']
    assert not any(p.suffix in ('.npz', '.zip', '.so', '.o', '.a') or 'CMakeFiles' in p.parts for p in files)
    assert sum(p.stat().st_size for p in files) < 150 * 2**20
    manifest = dict(passed=True, physics_attempts=1, full_route_passed=False,
        raw_archive=snapshot['archive'], raw_archive_sha256=snapshot['archive_sha256'],
        files={str(p.relative_to(HERE)): dict(bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(files)})
    (OUT / 'return_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(files=len(files), bytes=sum(p.stat().st_size for p in files), videos=videos)), flush=True)


if __name__ == '__main__':
    main()
