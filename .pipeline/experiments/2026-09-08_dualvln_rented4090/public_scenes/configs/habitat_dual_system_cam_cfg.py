"""Camera-condition eval config for the 2026-09-10 Lite3 camera ablation.

Derived from habitat_dual_system_public_cfg.py. Changed from it, and nothing
else:
  * config_path -> read from the environment variable CAM_YAML (one of the
    generated public_scenes/configs/vln_cam_<condition>.yaml files)
  * output_path / vis_debug_path -> read from CAM_RUN_DIR

Every model setting is identical to the baseline runs public_eval_v1..v5:
mode, model_path, num_history, resize_w/h, max_new_tokens, vis_debug, epoch,
max_steps_per_episode, save_video, port, dist_url. The evaluator resolves
resolution and hfov from the YAML; in dual_system mode it uses no intrinsic or
camera transform, so no model-side camera setting exists to change.

Refuses to load without CAM_YAML so a stale environment can never silently
evaluate the baseline camera under a condition run id.
"""
import os

from internnav.configs.agent import AgentCfg
from internnav.configs.evaluator import EnvCfg, EvalCfg

CAM_YAML = os.environ.get('CAM_YAML')
if not CAM_YAML or not CAM_YAML.startswith('public_scenes/configs/vln_cam_'):
    raise RuntimeError('CAM_YAML must name a generated public_scenes/configs/vln_cam_<condition>.yaml')
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
