"""Four physical-time-aligned panels: v219, v233, failed v235, new v236."""
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
OLD = BASE / 'audits/2026-10-17_v235_gpu40901_physical'
PREFIX = Path('/home/ubuntu/sun/vla_v234_20261017')
NEW = PREFIX / 'trials/v236_linux_full_attempt01/video_v236/runs/full01'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    path = BASE / 'audits/2026-10-17_v232_physical_comparison/compare_video_v2.py'
    spec = importlib.util.spec_from_file_location('v236_video_pipes', path)
    video = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(video)
    old_video = OLD / 'delivered/full_physics_comparison.mp4'
    old_proof_path = OLD / 'results/full_physics_comparison_verification.json'
    old_proof = json.loads(old_proof_path.read_text())
    assert sha(old_video) == old_proof['video_sha256']
    frames = json.loads((NEW / 'frames.json').read_text())
    times = np.array([r['physics_time_s'] for r in frames])
    assert np.all(np.diff(times) >= 0)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
    titles = ['v219 / 5070Ti', 'v232 run v233 / 5070Ti', 'v235 / 40901 scanner failure', 'v236 / 40901 scanner repair']
    end = max(float(times[-1]), old_proof['end_physics_s'])
    new_video = NEW / 'newton_stair_recorded.mp4'
    for name, begin, finish in (('full_physics_comparison', 0., end), ('stairs_physics_45_55', 45., 55.)):
        target = HERE / 'delivered' / (name + '.mp4')
        count = int(math.ceil((finish - begin)*30)) + 1
        readers = [video.Reader(old_video), video.Reader(new_video)]
        indexes, images = [-1, -1], [None, None]
        writer, mapping = video.Writer(target, 30), []
        try:
            for i in range(count):
                t = begin + i/30
                canvas = Image.new('RGB', (1280, 808), (12, 18, 25))
                draw = ImageDraw.Draw(canvas)
                old_index = round(t*30)
                record = dict(physics_grid_s=t, historical_comparison_frame=None)
                if old_index < len(old_proof['frame_mapping']):
                    while indexes[0] < old_index:
                        images[0] = readers[0].get_next_data()
                        indexes[0] += 1
                    historical = Image.fromarray(images[0])
                    for panel in range(3):
                        canvas.paste(historical.crop((panel*640, 44, (panel+1)*640, 404)), ((panel%2)*640, (panel//2)*404+44))
                    record['historical_comparison_frame'] = old_index
                else:
                    for panel in range(3):
                        draw.text(((panel%2)*640+15, (panel//2)*404+200), 'Historical recording ended', font=font, fill=(240, 190, 120))
                if t <= times[-1]+1e-6:
                    index = int(max(0, np.searchsorted(times, t+1e-9, side='right')-1))
                    while indexes[1] < index:
                        images[1] = readers[1].get_next_data()
                        indexes[1] += 1
                    canvas.paste(Image.fromarray(images[1]).resize((640, 360), Image.Resampling.LANCZOS), (640, 448))
                    record['new_source'] = dict(frame=index, source_state_index=frames[index]['source_state_index'], actual_physics_s=float(times[index]))
                else:
                    draw.text((655, 604), f'Recording ended {times[-1]:.3f}s', font=font, fill=(240, 190, 120))
                    record['new_source'] = dict(ended=True, last_physics_s=float(times[-1]))
                for panel, title in enumerate(titles):
                    draw.text(((panel%2)*640+8, (panel//2)*404+10), f'{title} | {t:.2f}s', font=font, fill=(245, 245, 245))
                writer.append_data(np.asarray(canvas))
                mapping.append(record)
        finally:
            writer.close()
            for reader in readers:
                reader.close()
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(target), '-f', 'null', '-'], check=True, capture_output=True)
        probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,nb_read_frames,avg_frame_rate', '-of', 'json', str(target)], text=True))['streams'][0]
        assert int(probe['nb_read_frames']) == count and probe['avg_frame_rate'] == '30/1'
        proof = dict(passed=True, full_decode_passed=True, frames=count, stream=probe,
            begin_physics_s=begin, end_physics_s=finish, video_sha256=sha(target), video_bytes=target.stat().st_size,
            source_videos={str(p): sha(p) for p in (old_video, new_video)},
            old_frame_proof_sha256=sha(old_proof_path), new_frames_sha256=sha(NEW/'frames.json'),
            selection='Verified historical panels; new latest recorded frame not later than common physics time. No interpolation or new physics.', frame_mapping=mapping)
        (HERE/'results'/(name+'_verification.json')).write_text(json.dumps(proof, indent=2)+'\n')
        print(json.dumps({k: proof[k] for k in ('frames', 'video_bytes', 'end_physics_s')}), flush=True)


if __name__ == '__main__':
    main()
