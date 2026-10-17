"""Reuse verified historical panels and align the new video by physical time."""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
PREFIX = Path('/home/ubuntu/sun/vla_v234_20261017')
NEW = Path(json.loads((HERE / 'results/partial_video_verification.json').read_text())['render_root']) / 'runs/full01'
OLD = HERE / 'reference'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    original = BASE / 'audits/2026-10-17_v232_physical_comparison/compare_video_v2.py'
    spec = importlib.util.spec_from_file_location('v235_ffmpeg_comparison', original)
    video = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(video)
    old_path = OLD / 'full_physics_comparison.mp4'
    old_proof_path = OLD / 'full_physics_comparison_verification.json'
    old_proof = json.loads(old_proof_path.read_text())
    assert old_proof['passed'] and sha(old_path) == old_proof['video_sha256']
    frames = json.loads((NEW / 'frames.json').read_text())
    times = np.array([f['physics_time_s'] for f in frames])
    assert np.all(np.diff(times) >= 0)
    outcome = json.loads((HERE / 'results/outcome.json').read_text())
    new_path = NEW / 'newton_stair_recorded.mp4'
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
    labels = ['v219 / 5070Ti reference', 'v232 run v233 / 5070Ti', 'v232 run v235 / 40901']
    old_ends = [next(r['sources'][k]['last_physics_s'] for r in old_proof['frame_mapping'] if r['sources'][k].get('ended')) for k in (0, 2)]
    end = max(float(times[-1]), *old_ends)
    for name, begin, finish in (('full_physics_comparison', 0., end),
                                ('stairs_physics_45_55', 45., 55.)):
        out = HERE / 'delivered' / (name + '.mp4')
        assert not out.exists(), 'Preserve delivered attempts'
        count = int(math.ceil((finish - begin) * 30)) + 1
        readers = [video.Reader(old_path), video.Reader(new_path)]
        indexes = [-1, -1]
        images = [None, None]
        mapping = []
        writer = video.Writer(out, 30)
        try:
            for i in range(count):
                t = begin + i / 30
                canvas = Image.new('RGB', (1920, 404), (12, 18, 25))
                draw = ImageDraw.Draw(canvas)
                old_index = min(round(t * 30), len(old_proof['frame_mapping']) - 1)
                assert abs(old_proof['frame_mapping'][old_index]['physics_grid_s'] - t) < 1e-7
                while indexes[0] < old_index:
                    images[0] = readers[0].get_next_data()
                    indexes[0] += 1
                historical = Image.fromarray(images[0])
                canvas.paste(historical.crop((0, 44, 640, 404)), (0, 44))
                canvas.paste(historical.crop((1280, 44, 1920, 404)), (640, 44))
                record = dict(physics_grid_s=t, historical_comparison_frame=old_index,
                              historical_sources=[old_proof['frame_mapping'][old_index]['sources'][k] for k in (0, 2)])
                if t <= times[-1] + 1e-6:
                    index = int(max(0, np.searchsorted(times, t + 1e-9, side='right') - 1))
                    while indexes[1] < index:
                        images[1] = readers[1].get_next_data()
                        indexes[1] += 1
                    canvas.paste(Image.fromarray(images[1]).resize((640, 360), Image.Resampling.LANCZOS), (1280, 44))
                    record['new_source'] = dict(frame=index, source_state_index=frames[index]['source_state_index'],
                                                actual_physics_s=float(times[index]))
                else:
                    draw.text((1295, 205), f"{outcome['overall_result']}: recording ended {times[-1]:.3f}s", font=font, fill=(240, 190, 120))
                    record['new_source'] = dict(ended=True, last_physics_s=float(times[-1]))
                for side, label in enumerate(labels):
                    draw.text((side * 640 + 8, 10), f'{label} | {t:.2f}s', font=font, fill=(245, 245, 245))
                writer.append_data(np.asarray(canvas))
                mapping.append(record)
        finally:
            writer.close()
            for reader in readers:
                reader.close()
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(out), '-f', 'null', '-'], check=True, capture_output=True)
        probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames',
            '-select_streams', 'v:0', '-show_entries', 'stream=width,height,nb_read_frames,avg_frame_rate',
            '-of', 'json', str(out)], text=True))['streams'][0]
        assert int(probe['nb_read_frames']) == count and probe['avg_frame_rate'] == '30/1'
        proof = dict(passed=True, full_decode_passed=True, video_sha256=sha(out), video_bytes=out.stat().st_size,
            frames=count, begin_physics_s=begin, end_physics_s=finish, stream=probe,
            source_videos={str(p): sha(p) for p in (old_path, new_path)},
            old_frame_proof_sha256=sha(old_proof_path), new_frames_sha256=sha(NEW / 'frames.json'),
            selection='Historical verified physical-grid panels; new latest recorded frame not later than grid time. Black after recording end; no state interpolation or physics.',
            frame_mapping=mapping)
        (HERE / 'results' / (name + '_verification.json')).write_text(json.dumps(proof, indent=2) + '\n')
        print(json.dumps({k: proof[k] for k in ('video_bytes', 'frames', 'begin_physics_s', 'end_physics_s')}), flush=True)


if __name__ == '__main__':
    main()
