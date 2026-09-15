"""Post-hoc, unambiguous scoring of a recorded episode.

`episode_record.json` carries a `success` field that only tests final geodesic
distance. Upstream Habitat VLN `Success` additionally requires the agent to call
STOP itself, so that field alone would over-claim. Emit every criterion
separately.
"""
import argparse
import json
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-dir', required=True)
    a = ap.parse_args()
    run = Path(a.run_dir)
    r = json.loads((run / 'episode_record.json').read_text())
    spec = r['episode_spec']
    thr = spec['success_distance']
    steps = r['steps']

    geo = [s['geodesic_to_target_m'] for s in steps
           if s.get('geodesic_to_target_m') is not None]
    learned_stop = any(s.get('learned_stop') for s in steps)
    pos = np.asarray([s['position'] for s in steps], dtype=np.float64)
    moved = float(np.linalg.norm(np.diff(pos[:, [0, 2]], axis=0), axis=1).sum())
    # `llm_output_raw` is the agent's last System-2 text and persists across
    # frames, so it is only FRESH on frames where System 2 actually ran.
    s2_texts = [s['llm_output_raw'] for s in steps
                if s.get('inference') == 's2' and s.get('llm_output_raw')]
    lookdown_texts = [s['look_down_llm_output_raw'] for s in steps
                      if s.get('look_down_llm_output_raw')]
    # Pixel goals arrive from the tilted-down System-2 call (upstream design:
    # the model asks to look down, then places the waypoint on the floor view).
    pixel_goals = ([s['output_pixel'] for s in steps if s.get('output_pixel')]
                   + [s['look_down_output_pixel'] for s in steps
                      if s.get('look_down_output_pixel')])

    out = {
        'run_dir': str(run),
        'episode_id': spec['episode_id'],
        'termination': r['termination'],
        'steps_executed': len(steps),
        'step_cap': r['caps']['max_steps'],
        'geodesic_start_m': r['geodesic_start_m'],
        'geodesic_end_m': r['geodesic_end_m'],
        'geodesic_min_m': min(geo) if geo else None,
        'success_distance_m': thr,
        # Distance test at the final pose only. This is what episode_record.json
        # reports as "success"; it is NOT the upstream VLN success measure.
        'success_final_distance_only': bool(geo and r['geodesic_end_m'] < thr),
        # Upstream habitat VLN Success = within the radius AND the agent
        # called STOP itself. This is the measure to quote.
        'success_upstream_stop_based': bool(learned_stop and r['geodesic_end_m'] is not None
                                            and r['geodesic_end_m'] < thr),
        'oracle_success_min_distance': bool(geo and min(geo) < thr),
        'learned_stop_emitted': learned_stop,
        'navigation_error_m': r['geodesic_end_m'],
        'path_length_m': moved,
        'collisions': r['collisions'],
        'applied_action_counts': r['applied_action_counts'],
        'distinct_xz_positions': len({(round(p[0], 2), round(p[2], 2)) for p in pos}),
        's2_calls': r['latency']['s2_calls'],
        's1_calls': r['latency']['s1_calls'],
        's2_pixel_goals_total': len(pixel_goals),
        's2_pixel_goals_level_camera': sum(1 for s in steps if s.get('output_pixel')),
        's2_pixel_goals_from_look_down': sum(1 for s in steps
                                             if s.get('look_down_output_pixel')),
        'pixel_goals': pixel_goals,
        's1_trajectories': sum(1 for s in steps if 's1_trajectory_xy' in s),
        's1_trajectories_all_finite': all(s.get('s1_trajectory_finite', True) for s in steps),
        'look_down_excursions': sum(1 for s in steps
                                    if s.get('applied_action') == 'look_down_excursion'),
        'distinct_s2_outputs_level_camera': sorted(set(s2_texts)),
        'distinct_s2_outputs_look_down': sorted(set(lookdown_texts)),
        'exposure_target_luma': r.get('exposure_target_luma', 0.0),
        'latency': r['latency'],
        'vram_peak': r['vram_peak'],
        'episode_seconds': r['episode_seconds'],
    }
    (run / 'episode_analysis.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
