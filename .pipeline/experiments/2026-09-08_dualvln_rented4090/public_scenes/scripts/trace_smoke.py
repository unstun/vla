"""Exercise the added trace code paths against the real environment, without the
model, so a typo in output-only instrumentation cannot burn the GPU budget."""
import json
import sys
from pathlib import Path

sys.path.append('.')
sys.path.append('./third_party/diffusion-policy')

import habitat
import torch
from habitat_baselines.config.default import get_config as get_habitat_config

from internnav.habitat_extensions.vln.habitat_vln_evaluator import _RunTrace, action_code
import internnav.habitat_extensions.vln.measures  # noqa: F401

cfg = get_habitat_config('public_scenes/configs/vln_public_scenes.yaml')
from habitat.config.default_structured_configs import (
    CollisionsMeasurementConfig, FogOfWarConfig, TopDownMapMeasurementConfig)
with habitat.config.read_write(cfg):
    cfg.habitat.task.measurements.update({
        "top_down_map": TopDownMapMeasurementConfig(
            map_padding=3, map_resolution=1024, draw_source=True, draw_border=True,
            draw_shortest_path=True, draw_view_points=True, draw_goal_positions=True,
            draw_goal_aabbs=True,
            fog_of_war=FogOfWarConfig(draw=True, visibility_dist=5.0, fov=90)),
        "collisions": CollisionsMeasurementConfig(),
    })

out = 'public_scenes/runs/_trace_smoke'
env = habitat.Env(cfg)
try:
    obs = env.reset()
    ep = env.current_episode
    t = _RunTrace(out, 'smoke_scene', int(ep.episode_id), ep, 0)
    for a in (action_code.FORWARD, action_code.LEFT, action_code.LOOKDOWN):
        info = env.get_metrics()
        st = env.sim.get_agent_state()
        t.write({
            'record': 'step', 'step_id': 0, 'applied_action': int(a),
            'action_name': action_code(int(a)).name, 'action_source': 'smoke',
            'is_learned_episode_stop': False, 'pixel_goal_active': False,
            'position': [float(v) for v in st.position],
            'rotation_wxyz': [float(st.rotation.w), float(st.rotation.x),
                              float(st.rotation.y), float(st.rotation.z)],
            'distance_to_goal': info.get('distance_to_goal'),
            'collisions': (info.get('collisions') or {}).get('count'),
        })
        env.step(int(a))
    metrics = env.get_metrics()
    t.close(termination_reason='smoke', final_step_id=3, evaluator_step_cap=500,
            metrics={k: (v if not isinstance(v, dict) else None) for k, v in metrics.items()},
            cuda_max_memory_allocated_bytes_whole_run_so_far=(
                torch.cuda.max_memory_allocated() if torch.cuda.is_available() else None))
finally:
    env.close()

lines = Path(t.path).read_text().strip().split('\n')
for ln in lines:
    json.loads(ln)
print('TRACE_SMOKE_OK records=', len(lines))
print(lines[-1][:400])
