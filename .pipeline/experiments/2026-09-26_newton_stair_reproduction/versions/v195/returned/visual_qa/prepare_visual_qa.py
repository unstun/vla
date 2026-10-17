"""Decode exact delivered frames for visual review; never alter source states."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont

VERSION = Path('/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v195')
frames = json.loads((VERSION / 'returned/frames.json').read_text())
video = VERSION / 'delivered/v194_mac_full_attempt01.mp4'
assert video.is_file() and not video.is_symlink()
qa = VERSION / 'returned/visual_qa'
qa.mkdir(exist_ok=False)
indices = [0, 120, 301]
indices += [min(range(len(frames)), key=lambda i: abs(frames[i]['physics_time_s'] - target))
            for target in (30., 64.29629516601562, 74.49069213867188, 85., 106., 134.)]
indices += [len(frames)-1]
assert len(indices) == len(set(indices)) == 10 and indices == sorted(indices)
select = '+'.join(f'eq(n\\,{i})' for i in indices)
command = [shutil.which('ffmpeg'), '-nostdin', '-v', 'error', '-i', str(video),
           '-vf', 'select=' + select, '-fps_mode', 'vfr', str(qa / 'sample_%02d.png')]
subprocess.run(command, check=True, timeout=120)
assert len(list(qa.glob('sample_*.png'))) == 10
font = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 16)
sheet = Image.new('RGB', (1280, 1920), '#111827')
draw = ImageDraw.Draw(sheet)
samples = []
for j, i in enumerate(indices):
    p = qa / f'sample_{j+1:02d}.png'
    with Image.open(p) as im:
        assert im.size == (1280, 720)
        sheet.paste(im.resize((640, 360)), ((j % 2)*640, (j // 2)*384))
    f = frames[i]
    draw.text(((j % 2)*640+6, (j // 2)*384+363),
              f'Frame {i} | video {i/30:.3f}s | physics {f["physics_time_s"]:.3f}s',
              font=font, fill='white')
    samples.append({'frame': i, 'file': str(p.relative_to(VERSION)),
                    'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                    'physics_time_s': f['physics_time_s'], 'video_time_s': f['display_time_s'],
                    'navigation_status': f['navigation_status'], 'local_curve': f['local_curve']})
sheet.save(qa / 'contact_sheet.jpg', quality=95)
(qa / 'samples.json').write_text(json.dumps(samples, indent=2)+'\n')
(qa / 'extraction.json').write_text(json.dumps({'command': command,
    'video_sha256': hashlib.sha256(video.read_bytes()).hexdigest(),
    'frames': indices, 'decoded_sample_size': [1280,720],
    'contact_sheet_sha256': hashlib.sha256((qa/'contact_sheet.jpg').read_bytes()).hexdigest(),
    'extractor_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
shutil.copyfile(__file__, qa / 'prepare_visual_qa.py')
print(json.dumps({'samples':indices, 'contact_sheet':str(qa/'contact_sheet.jpg')}))
