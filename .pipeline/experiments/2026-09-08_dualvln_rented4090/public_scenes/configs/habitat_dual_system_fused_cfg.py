"""Fused-camera eval config for round 5 of the 2026-09-10 Lite3 camera ablation.

Derived from habitat_dual_system_cam_cfg.py. Changed from it, and nothing else:
  * imports public_scenes/requests/2026-09-10_lite3_camera_ablation/fused_camera_plugin.py
    before anything composes the Habitat config. The plugin registers three extra
    rendered sensors (stock head camera, D435i colour, D435i depth) and the
    fused_rgb_sensor task sensor that overrides the `rgb` observation with the
    level virtual camera image. eval.py executes this file after importing the
    evaluator and before Evaluator.init, so no evaluator or model source changes.
  * refuses to load unless CAM_YAML names a generated vln_cam_<condition>.yaml
    that declares fused_rgb_sensor (a fused YAML cannot compose without the plugin,
    and a non-fused YAML must not be run under the fused config).

Every model setting is identical to the baseline runs public_eval_v1..v5 and to
rounds 1-4: mode, model_path, num_history, resize_w/h, max_new_tokens, vis_debug,
epoch, max_steps_per_episode, save_video, port, dist_url.
"""
import os
import sys

from internnav.configs.agent import AgentCfg
from internnav.configs.evaluator import EnvCfg, EvalCfg

CAM_YAML = os.environ.get('CAM_YAML')
if not CAM_YAML or not CAM_YAML.startswith('public_scenes/configs/vln_cam_'):
    raise RuntimeError('CAM_YAML must name a generated public_scenes/configs/vln_cam_<condition>.yaml')
if 'fused_rgb_sensor' not in open(CAM_YAML).read():
    raise RuntimeError('habitat_dual_system_fused_cfg.py requires a fused condition YAML (fused_rgb_sensor)')
_REQ = os.path.join(os.path.dirname(os.path.abspath(CAM_YAML)), '..', 'requests', '2026-09-10_lite3_camera_ablation')
sys.path.insert(0, os.path.abspath(_REQ))
import fused_camera_plugin  # noqa: E402,F401  (registers sensors + config nodes)

RUN_DIR = os.environ.get('CAM_RUN_DIR', 'public_scenes/runs/pending')

eval_cfg = EvalCfg(
    agent=AgentCfg(
        model_name='internvla_n1',
        model_settings={
            "mode": "dual_system",  # inference mode: dual_system or system2
            "model_path": "checkpoints/InternVLA-N1-DualVLN",  # path to model checkpoint
            "num_history": 8,
            "resize_w": 384,  # image resize width
            "resize_h": 384,  # image resize height
            "max_new_tokens": 1024,  # maximum number of tokens for generation
            "vis_debug": True,  # If vis_debug=True, save debug videos per episode
            "vis_debug_path": os.path.join(RUN_DIR, "vis_debug"),
        },
    ),
    env=EnvCfg(
        env_type='habitat',
        env_settings={
            # habitat sim specifications - agent, sensors, tasks, measures etc. are defined in the habitat config file
            'config_path': CAM_YAML,
        },
    ),
    eval_type='habitat_vln',
    eval_settings={
        # all current parse args
        "output_path": RUN_DIR,  # output directory for logs/results
        "save_video": True,  # whether to save videos
        "epoch": 0,  # epoch number for logging
        "max_steps_per_episode": 500,  # maximum steps per episode
        # distributed settings
        "port": "2333",  # communication port
        "dist_url": "env://",  # url for distributed setup
    },
)
