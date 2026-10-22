"""Verify returned evidence and decode real videos; never execute physics."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import subprocess
import time

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
VERSION = HERE.parents[1] / 'versions/v286'
FFMPEG = '/opt/homebrew/bin/ffmpeg'
FFPROBE = '/opt/homebrew/bin/ffprobe'
load = lambda p: json.loads(p.read_text())


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verify_video(item):
    name, entry = item
    path = HERE / 'delivered' / name
    assert path.is_file() and not path.is_symlink()
    assert path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256']
    case = name.removeprefix('v286_').removesuffix('_full_attempt01.mp4')
    certificate = load(HERE / 'physical_return' / case / 'video_checks/delivery_verification.json')
    assert certificate['passed'] and certificate['render_only_no_physics_steps']
    assert certificate['video_sha256'] == entry['sha256']
    metadata = json.loads(subprocess.check_output([
        FFPROBE, '-v', 'error', '-select_streams', 'v:0', '-show_streams',
        '-show_format', '-of', 'json', str(path)], text=True))
    video = metadata['streams'][0]
    assert int(video['nb_frames']) == certificate['frames']
    decoded = subprocess.run([FFMPEG, '-v', 'error', '-threads', '2', '-i', str(path),
        '-map', '0:v:0', '-an', '-f', 'null', '-'], capture_output=True, text=True)
    assert decoded.returncode == 0 and not decoded.stderr.strip(), (case, decoded.stderr)
    duration = float(metadata['format']['duration'])
    frames = []
    for index, fraction in enumerate((0.30, 0.80)):
        second = duration * fraction
        frame = HERE / 'results/visual_samples' / f'{case}_{index + 1}.jpg'
        frame.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([FFMPEG, '-v', 'error', '-threads', '2', '-ss', str(second),
            '-i', str(path), '-frames:v', '1', '-q:v', '2', '-y', str(frame)], check=True)
        frames.append(dict(path=str(frame.relative_to(HERE)), video_time_s=second, sha256=sha(frame)))
    return dict(case_id=case, file=str(path.relative_to(HERE)), bytes=entry['bytes'],
        sha256=entry['sha256'], duration_s=duration, frames=int(video['nb_frames']),
        width=video['width'], height=video['height'], full_decode_passed=True,
        render_only_certificate_passed=True, visual_samples=frames)


def main():
    start = time.time()
    inventory = load(HERE / 'physical_return/return_inventory.json')
    for relative, entry in inventory['files'].items():
        path = HERE / 'physical_return' / relative
        assert path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256'], relative
    for name, expected in inventory['analysis_source_files'].items():
        assert sha(HERE / name) == expected, name
    freeze = load(VERSION / 'manifest.json')
    for relative, expected in freeze['source_files'].items():
        assert sha(VERSION / relative) == expected and sha(VERSION / 'source' / relative) == expected
    remote = load(HERE / 'results/final_remote_verification.json')
    assert remote['passed'] and remote['physical_attempts'] == 10 and remote['one_actual_attempt_each']
    assert remote['native_manifest_sha256'] == sha(VERSION / 'native_manifest.json')
    assert remote['execution_manifest_sha256'] == sha(VERSION / 'manifest.json')
    assert len(inventory['videos']) == 10
    with ThreadPoolExecutor(max_workers=2) as pool:
        videos = list(pool.map(verify_video, inventory['videos'].items()))
    by_case = {v['case_id']: v for v in videos}
    order = freeze['physical_cases']
    sheets = []
    for sheet_number in range(2):
        cases = order[sheet_number * 5:(sheet_number + 1) * 5]
        sheet = Image.new('RGB', (1280, 5 * 285), '#e8e8e8')
        draw = ImageDraw.Draw(sheet)
        for row, case in enumerate(cases):
            for column, frame in enumerate(by_case[case]['visual_samples']):
                original = Image.open(HERE / frame['path']).convert('RGB')
                original.thumbnail((640, 255))
                x, y = 640 * column, 285 * row
                draw.text((x + 10, y + 8), f"{case} | video {frame['video_time_s']:.2f} s", fill='black')
                sheet.paste(original, (x, y + 27))
        target = HERE / 'results/visual_samples' / f'contact_sheet_{sheet_number + 1}.jpg'
        sheet.save(target, quality=94)
        sheets.append(dict(path=str(target.relative_to(HERE)), sha256=sha(target)))
    result = dict(passed=True, physics_steps=0, elapsed_s=time.time() - start,
        compact_files_verified=len(inventory['files']), analysis_sources_verified=len(inventory['analysis_source_files']),
        frozen_source_and_snapshot_pairs_verified=len(freeze['source_files']),
        native_manifest_sha256=sha(VERSION / 'native_manifest.json'),
        execution_manifest_sha256=sha(VERSION / 'manifest.json'),
        full_local_videos_verified=10, video_bytes=sum(v['bytes'] for v in videos),
        videos=videos, contact_sheets=sheets, visual_review_pending=True)
    (HERE / 'results/local_physical_delivery_verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('videos', 'contact_sheets')}))


if __name__ == '__main__':
    main()
