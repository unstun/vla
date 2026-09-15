"""Render an annotated MP4 from a recorded episode, then decode it back to
verify the file is actually playable and non-degenerate."""
import argparse
import json
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def font(size):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def traj_inset(traj, size=180):
    """Top-down plot of the S1 trajectory: x forward (up), y left."""
    img = Image.new('RGB', (size, size), (35, 35, 40))
    d = ImageDraw.Draw(img)
    pts = np.asarray(traj, dtype=np.float64)
    if pts.ndim != 2 or len(pts) < 2:
        return img
    span = max(float(np.abs(pts).max()), 0.5) * 1.15
    def to_px(p):
        # y (left +) -> screen x inverted ; x (forward +) -> screen y inverted
        return (size / 2 - p[1] / span * (size / 2), size - (p[0] / span + 1) * (size / 4) - size / 2)
    for g in (0.5, 1.0, 1.5, 2.0):
        if g < span:
            r = g / span * (size / 2)
            d.ellipse([size/2 - r, size/2 - r, size/2 + r, size/2 + r], outline=(70, 70, 80))
    d.line([size/2, 0, size/2, size], fill=(70, 70, 80))
    d.line([0, size/2, size, size/2], fill=(70, 70, 80))
    px = [to_px(p) for p in pts]
    d.line(px, fill=(90, 170, 255), width=3)
    d.ellipse([px[0][0]-4, px[0][1]-4, px[0][0]+4, px[0][1]+4], fill=(90, 230, 90))
    d.ellipse([px[-1][0]-4, px[-1][1]-4, px[-1][0]+4, px[-1][1]+4], fill=(240, 80, 80))
    f = font(11)
    d.text((4, 4), 'S1 traj (m)', fill=(210, 210, 210), font=f)
    d.text((4, size-15), 'end %.2f,%.2f' % (pts[-1][0], pts[-1][1]), fill=(210, 210, 210), font=f)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-dir', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--fps', type=int, default=4)
    ap.add_argument('--brighten', type=float, default=2.0,
                    help='display-only gain; the recorded PNGs are untouched')
    a = ap.parse_args()

    run = Path(a.run_dir)
    rec = json.loads((run / 'episode_record.json').read_text())
    spec = rec['episode_spec']
    fbig, fsml = font(17), font(14)

    frames = []
    last_llm = ''
    for s in rec['steps']:
        p = Path(s['rgb_path'])
        if not p.is_absolute():
            p = ROOT / p
        if not p.exists():
            continue
        im = Image.open(p).convert('RGB')
        # Show what the model actually consumed: reuse the per-frame
        # auto-exposure gain when the run recorded one, else the display gain.
        gain = s.get('exposure_gain_applied_to_model_input') or a.brighten
        if gain != 1.0:
            im = Image.eval(im, lambda v: min(255, int(v * gain)))
        d = ImageDraw.Draw(im)
        W, H = im.size

        if s.get('llm_output_raw'):
            last_llm = s['llm_output_raw'].replace('\n', ' ')
        lines = [
            'step %3d/%d   inference: %s' % (s['step'], len(rec['steps']), s.get('inference', '-')),
            'applied: %-18s %s' % (s.get('applied_action', '-'),
                                   'COLLISION' if s.get('collided') else ''),
            'proposed: %s' % (s.get('proposed_actions'),),
            'geodesic to target: %s m   exposure x%.2f' % (
                ('%.2f' % s['geodesic_to_target_m'])
                if s.get('geodesic_to_target_m') is not None else 'n/a', gain),
            'S2: %s' % (last_llm[:64] if last_llm else '(none yet)'),
        ]
        bh = 18 * len(lines) + 12
        d.rectangle([0, 0, W, bh], fill=(0, 0, 0))
        for i, ln in enumerate(lines):
            d.text((8, 6 + i * 18), ln, fill=(255, 255, 255), font=fsml)

        d.rectangle([0, H - 26, W, H], fill=(0, 0, 0))
        d.text((8, H - 22), spec['instruction'][:96], fill=(255, 225, 130), font=fsml)

        if s.get('output_pixel'):
            gy, gx = int(s['output_pixel'][0]), int(s['output_pixel'][1])
            if 0 <= gx < W and 0 <= gy < H:
                d.ellipse([gx-9, gy-9, gx+9, gy+9], outline=(255, 60, 60), width=3)
                d.line([gx-13, gy, gx+13, gy], fill=(255, 60, 60), width=2)
                d.line([gx, gy-13, gx, gy+13], fill=(255, 60, 60), width=2)
                d.text((gx+12, gy+10), 'pixel goal', fill=(255, 60, 60), font=fsml)
        if s.get('s1_trajectory_xy'):
            im.paste(traj_inset(s['s1_trajectory_xy']), (W - 190, bh + 8))
        frames.append(np.asarray(im))

    if not frames:
        raise SystemExit('no frames to write')
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimwrite(str(out), frames, fps=a.fps, codec='libx264',
                     quality=8, macro_block_size=1)

    rd = imageio.get_reader(str(out))
    decoded = [np.asarray(f) for f in rd]
    rd.close()
    report = {
        'path': str(out), 'bytes': out.stat().st_size,
        'written_frames': len(frames), 'decoded_frames': len(decoded),
        'shape': list(decoded[0].shape) if decoded else None,
        'fps': a.fps,
        'decoded_frame_mean_luma': [float(np.asarray(f).mean()) for f in decoded[:len(decoded)]],
        'distinct_frames': int(sum(1 for i in range(1, len(decoded))
                                   if np.abs(decoded[i].astype(np.int16)
                                             - decoded[i-1].astype(np.int16)).mean() > 0.5)),
        'brighten_gain_display_only': a.brighten,
    }
    (run / 'video_verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items()
                      if k != 'decoded_frame_mean_luma'}), flush=True)
    print('VIDEO_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
