"""Return only compact verified results and real review MP4s, never raw runs."""
from pathlib import Path
import hashlib
import json
import shutil
import time

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / 'physical_return'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
files = {}
videos = {}
remote = {}


def collect(source, relative):
    entry = dict(remote_path=str(source), bytes=source.stat().st_size, sha256=sha(source))
    if source.stat().st_size > 8 * 1024**2:
        remote[relative] = entry
        return
    target = OUTPUT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    files[relative] = entry


for case in json.loads((HERE.parents[1] / 'versions/v282/selection.json').read_text())['selected']:
    cid = case['case_id']
    directory = HERE / 'physical' / cid
    receipt = directory / 'results/local_video_delivery.json'
    if not receipt.exists():
        continue
    delivery = json.loads(receipt.read_text())
    video = Path(delivery['video'])
    assert video.is_file() and not video.is_symlink() and sha(video) == delivery['sha256']
    videos[video.name] = dict(remote_path=str(video), bytes=video.stat().st_size, sha256=sha(video))
    for source in (directory / 'results').rglob('*'):
        if source.is_file() and source.suffix in ('.json', '.jsonl', '.csv', '.log', '.txt'):
            collect(source, str(source.relative_to(HERE / 'physical')))
    for source in directory.iterdir():
        if source.is_file() and source.suffix in ('.py', '.json'):
            collect(source, str(source.relative_to(HERE / 'physical')))
    # The delivery checker binds the exact render and its zero-physics proof.
    render_root = Path('/home/sun/vla_exec/physical_runs_v282') / f'v282_{cid}_attempt01'
    verified = []
    for quality_path in render_root.glob('video_v282_render*/runs/full01/quality.json'):
        candidate = json.loads(quality_path.read_text())
        certificate = json.loads(Path(candidate['checks']['delivery']['path']).read_text())
        if certificate['video_sha256'] == delivery['sha256']:
            verified.append((quality_path, candidate))
    assert verified, f'{cid}: no matching full-video certificate'
    quality_path, quality = sorted(verified, key=lambda item: str(item[0]))[-1]
    assert quality['passed'] and quality['input_source_unchanged'] and not quality['physical_rerun']
    collect(quality_path, f'{cid}/video_checks/quality.json')
    for name, record in quality['checks'].items():
        if not isinstance(record, dict) or 'path' not in record:
            continue
        source = Path(record['path'])
        assert sha(source) == record['sha256']
        collect(source, f'{cid}/video_checks/{source.name}')

OUTPUT.mkdir(exist_ok=True)
(OUTPUT / 'return_inventory.json').write_text(json.dumps(dict(
    snapshot_utc_s=time.time(), files=files, videos=videos, retained_remote=remote,
    raw_storage='/home/sun/vla_exec/physical_runs_v282', physics_steps=0,
    regeneration='Use the locally versioned postprocess_case.py against the unchanged remote recordings; never rerun formal physics to regenerate media.'), indent=2) + '\n')
print(json.dumps(dict(compact_files=len(files), compact_bytes=sum(r['bytes'] for r in files.values()),
                     videos=len(videos), video_bytes=sum(r['bytes'] for r in videos.values()))))
