"""Verify all recorded-state clips and concatenate without omitting trials."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import shutil

HERE = Path(__file__).resolve().parents[1]
BASE = HERE.parents[1]
RAW = Path('/private/tmp/vla_policy_stop_20261012')
sys.path.insert(0, str(BASE / 'versions/v51'))
from artifacts import video_check


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    records = []
    for terrain in ('flat', 'stairs'):
        for attempt in range(1, 7):
            run = f'v179_{terrain}{attempt:02d}'
            source = RAW / 'runs' / run
            render = RAW / 'render181' / run
            proof = json.loads((render / 'video_verification.json').read_text())
            video = render / 'newton_stair_recorded.mp4'
            assert sha(video) == proof['sha256']
            rows = json.loads((source / 'recorded_frames.json').read_text())
            frames = [json.loads(line) for line in (render / 'frames.jsonl').read_text().splitlines()]
            assert len(frames) == proof['frames']
            assert frames[0]['source_index'] == 0 and frames[0]['display_time_s'] == 0
            for index, item in enumerate(frames):
                row = rows[item['source_index']]
                assert item['frame_index'] == index
                assert item['recorded_time_s'] == row['physics_time_s'] <= item['display_time_s']
                assert item['recorded_state_sha256'] == hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
                assert item['rgb24_shape'] == [720, 1280, 3]
            assert frames[-1]['display_time_s'] >= rows[-1]['physics_time_s'] - 1/30
            archived = json.loads((RAW / 'receipts' / (run + '.json')).read_text())
            assert archived['remote_verified']
            assert sha(source / 'recorded_frames.json') == archived['files']['recorded_frames.json']['sha256']
            request = json.loads((source / 'probe_request.json').read_text())
            assert request['source_manifest_sha256'] == sha(BASE / 'versions/v179/manifest.json')
            target = HERE / 'results' / run
            target.mkdir(parents=True, exist_ok=True)
            for name in ('video_verification.json', 'display_source.json', 'video_encoding.json', 'appearance.json'):
                shutil.copyfile(render / name, target / name)
            records.append(dict(run=run, terrain=terrain, attempt=attempt, path=str(video),
                bytes=video.stat().st_size, sha256=sha(video), frames=len(frames), seconds=len(frames)/30,
                frame_source_identity_pass=True, starts_at_zero=True, no_future_state=True,
                supervisor_closed=(RAW / 'runs' / ('v181_render_' + run[5:]) / 'process.json').exists()))
    combined = []
    output = HERE / 'delivered'
    for terrain in ('flat', 'stairs'):
        clips = [r for r in records if r['terrain'] == terrain]
        listing = RAW / f'{terrain}_concat.txt'
        listing.write_text(''.join("file '" + r['path'] + "'\n" for r in clips))
        video = output / f'{terrain}_all6.mp4'
        if video.exists():
            raise FileExistsError(video)
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(listing),
            '-c', 'copy', '-movflags', '+faststart', str(video)], check=True)
        expected = sum(c['frames'] for c in clips)
        stream = video_check(video, expected, 30)
        offset = 0.
        for clip in clips:
            clip['combined_start_s'] = offset
            offset += clip['seconds']
        combined.append(dict(terrain=terrain, path=str(video), bytes=video.stat().st_size,
            sha256=sha(video), frames=expected, stream=stream, all_six_runs_in_order=True,
            full_decode_passed=True, seconds=offset))
    evidence = dict(physics_version='v179', display_version='v181', runs=records, combined=combined,
        source_sha256=sha(Path(__file__)), omitted_physics_runs=[], physics_rerun_for_video=False,
        recovered_after_driver_interruption=['v179_flat04'],
        recovery_limit='flat04 video completed and independently verified; original supervisor exit record unavailable')
    (HERE / 'DELIVERY.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(combined), flush=True)


if __name__ == '__main__':
    main()
