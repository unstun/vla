"""Derived from scripts/eval/configs/habitat_dual_system_cfg.py.

Changed from the pinned upstream config, and nothing else:
  * config_path    -> the derived habitat YAML (2 asset-path lines differ from upstream)
  * output_path    -> this run's directory
  * save_video     -> True   (observability)
  * vis_debug      -> True   (observability; per-episode first-person MP4)
  * vis_debug_path -> this run's directory

Deliberately identical to upstream, including the value: mode, model_path,
num_history, resize_w, resize_h, max_new_tokens, epoch, max_steps_per_episode,
port, dist_url. `model_path` still reads `checkpoints/InternVLA-N1-DualVLN`
because public_scenes/scripts/link_launch_dir.sh makes that upstream relative
path resolve from the official launch directory.
"""
import os

from internnav.configs.agent import AgentCfg
from internnav.configs.evaluator import EnvCfg, EvalCfg

RUN_DIR = os.environ.get('PUBLIC_RUN_DIR', 'public_scenes/runs/pending')

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
            'config_path': 'public_scenes/configs/vln_public_scenes.yaml',
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
