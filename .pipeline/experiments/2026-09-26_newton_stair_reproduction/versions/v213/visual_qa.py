"""Extract actual MP4 frames and a contact sheet for manual visual review."""
from pathlib import Path
import hashlib
import json
import subprocess

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent


def main():
    video = HERE / 'delivered/v212_linux_full_attempt01.mp4'
    frames = json.loads((HERE / 'returned/frames.json').read_text())
    curves = json.loads((HERE / 'returned/curve_frames.json').read_text())
    targets = (0.0, 4.0, 10.0, 30.0, 60.0, 80.0)
    indices = sorted({min(range(len(frames)), key=lambda i: abs(frames[i]['physics_time_s'] - t))
                      for t in targets} | {len(frames) - 1})
    assert indices[0] == 0
    out = HERE / 'returned/visual_qa'
    out.mkdir(exist_ok=False)
    selector = '+'.join(f'eq(n,{i})' for i in indices)
    command = ['ffmpeg', '-v', 'error', '-i', str(video), '-vf', f"select='{selector}'",
               '-fps_mode', 'vfr', '-frames:v', str(len(indices)), str(out / 'sample_%02d.png')]
    subprocess.run(command, check=True)
    contact = Image.new('RGB', (1920, 1170), '#16202b')
    draw = ImageDraw.Draw(contact)
    samples = []
    for j, index in enumerate(indices):
        path = out / f'sample_{j+1:02d}.png'
        with Image.open(path) as decoded:
            assert decoded.size == (1280, 720)
            contact.paste(decoded.resize((640, 360), Image.Resampling.LANCZOS),
                          ((j % 3) * 640, (j // 3) * 390))
        row = frames[index]
        caption = f"Frame {index} | video {index/30:.2f} s | physics {row['physics_time_s']:.2f} s"
        draw.text(((j % 3) * 640 + 10, (j // 3) * 390 + 365), caption, fill='white')
        samples.append(dict(frame=index, file=str(path.relative_to(HERE)),
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            physics_time_s=row['physics_time_s'], video_time_s=index / 30,
                            navigation_status=row['navigation_status'], local_curve=curves[index]))
    contact.save(out / 'contact_sheet.jpg', quality=94)
    (out / 'samples.json').write_text(json.dumps(samples, indent=2) + '\n')
    print(json.dumps({'samples': len(samples), 'contact_sheet': str(out / 'contact_sheet.jpg')}))


if __name__ == '__main__':
    main()
