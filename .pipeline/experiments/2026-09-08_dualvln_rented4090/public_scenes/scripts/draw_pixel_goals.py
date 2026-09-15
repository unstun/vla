"""Draw each System-2 pixel goal on the exact camera view the model was shown.

The evaluator already draws the goal on `save_raw_image`, which at that step is
the tilted look-down frame the goal came from, but it uses the raw coordinates
without rescaling. The model emits (row, col) in Qwen2.5-VL's *processed* image
space, whose size is image_grid_thw x patch_size (14 px). This rescales into the
saved image's own pixel space and writes both markers, so the difference is
visible rather than assumed.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PATCH = 14  # Qwen2.5-VL patch size; image_grid_thw is counted in these units


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()

    run_dir = ROOT / 'public_scenes/runs' / a.run
    out_dir = Path(a.out) if a.out else run_dir / 'pixel_goal_overlays'
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []

    for trace in sorted((run_dir / 'trace_0').glob('*.jsonl')):
        recs = [json.loads(l) for l in open(trace)]
        s2_by_step = {}
        for r in recs:
            if r['record'] == 's2_call':
                s2_by_step.setdefault(r['step_id'], []).append(r)
        for r in recs:
            if r['record'] != 'pixel_goal':
                continue
            src = run_dir / 'trace_0' / r['model_input_image_png']
            img = cv2.imread(str(src))
            if img is None:
                continue
            h, w = img.shape[:2]
            s2 = s2_by_step.get(r['step_id'], [])[-1]
            _, gh, gw = s2['image_grid_thw'][-1]
            proc_h, proc_w = gh * PATCH, gw * PATCH
            gx_raw, gy_raw = int(r['pixel_goal_row_col'][0]), int(r['pixel_goal_row_col'][1])
            gx = int(round(gx_raw * w / proc_w))
            gy = int(round(gy_raw * h / proc_h))
            vis = img.copy()
            cv2.circle(vis, (gx_raw, gy_raw), 10, (0, 0, 255), 2)        # as upstream draws it
            cv2.drawMarker(vis, (gx, gy), (0, 255, 0), cv2.MARKER_CROSS, 26, 2)  # rescaled
            cv2.putText(vis, f"{trace.stem} step {r['step_id']}  view={s2['branch']}",
                        (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
            cv2.putText(vis, f"model text '{s2['raw_output_text'].strip()}' -> row,col {gy_raw},{gx_raw}"
                             f" in {proc_w}x{proc_h}; rescaled to {gx},{gy} in {w}x{h}",
                        (8, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 0), 1)
            dst = out_dir / f'{trace.stem}_step{r["step_id"]:04d}_goal.png'
            cv2.imwrite(str(dst), vis)
            rows.append({'episode_trace': trace.name, 'step_id': r['step_id'],
                         'model_view': s2['branch'], 'model_text': s2['raw_output_text'],
                         'processed_space_wh': [proc_w, proc_h], 'image_wh': [w, h],
                         'raw_xy': [gx_raw, gy_raw], 'rescaled_xy': [gx, gy],
                         'overlay': str(dst.relative_to(ROOT))})

    (out_dir / 'pixel_goals.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(f'wrote {len(rows)} overlays to {out_dir.relative_to(ROOT)}')
    views = {}
    for r in rows:
        views[r['model_view']] = views.get(r['model_view'], 0) + 1
    print('pixel goals by the view the model actually saw:', views)


if __name__ == '__main__':
    main()
