#!/usr/bin/env python3
"""Phase D.1b figure: contact sheet of the stage-audit frames (pose A first and last, pose B last; four cameras).

    python3 scripts/phase_d1b_figures.py [--run-dir runs/phase_d1b_stage_audit_kujiale_0031_v1]

Writes analysis/phase_d1b_figures/fig1_d1b_frames_contact_sheet.png and SHA256SUMS.txt. Frames are downscaled with
PIL thumbnail (aspect kept), labelled with the run frame name and native size; no other processing.
"""
import argparse
import hashlib
import pathlib

from PIL import Image, ImageDraw

HERE = pathlib.Path(__file__).resolve().parents[1]
CAMERAS = ['head_eval', 'fusion_head', 'fusion_d435', 'chase']
ROWS = ['A_iter000', 'A_last', 'B_last']


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-dir', type=pathlib.Path, default=HERE / 'runs' / 'phase_d1b_stage_audit_kujiale_0031_v1')
    args = ap.parse_args(argv)
    frames = args.run_dir / 'audit' / 'frames'
    out_dir = HERE / 'analysis' / 'phase_d1b_figures'
    out_dir.mkdir(parents=True, exist_ok=True)
    cell_w, cell_h, label_h = 480, 300, 22
    sheet = Image.new('RGB', (cell_w * len(CAMERAS), (cell_h + label_h) * len(ROWS)), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    for r, tag in enumerate(ROWS):
        for c, cam in enumerate(CAMERAS):
            src = Image.open(frames / '{}_{}.png'.format(tag, cam)).convert('RGB')
            size = src.size
            src.thumbnail((cell_w, cell_h))
            x, y = c * cell_w, r * (cell_h + label_h)
            sheet.paste(src, (x, y + label_h))
            draw.text((x + 4, y + 4), '{} {} {}x{}'.format(tag, cam, *size), fill=(0, 0, 0))
    path = out_dir / 'fig1_d1b_frames_contact_sheet.png'
    sheet.save(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    (out_dir / 'SHA256SUMS.txt').write_text('{}  {}\n'.format(digest, path.name))
    print(path, digest)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
