"""Derived from scripts/eval/configs/habitat_dual_system_cfg.py.

Only these are changed from the pinned upstream config:
  * model_path            -> the verified local BF16 checkpoint
  * config_path           -> derived habitat YAML (asset paths + fixed subset only)
  * output_path           -> this run's directory
  * save_video            -> True   (observability)
  * vis_debug             -> True   (observability; per-episode first-person MP4)
  * vis_debug_path        -> this run's directory

Deliberately NOT changed: mode, num_history, resize_w/h, max_new_tokens,
max_steps_per_episode (500), epoch, port, dist_url.
"""
import os

from internnav.configs.agent import AgentCfg
from internnav.configs.evaluator import EnvCfg, EvalCfg

RUN_DIR = os.environ.get('OFFICIAL_RUN_DIR', './official_r2r/runs/pending')
CKPT = os.environ.get('OFFICIAL_CKPT', './models/InternVLA-N1-DualVLN')

eval_cfg = EvalCfg(
    agent=AgentCfg(
        model_name='internvla_n1',
        model_settings={
            "mode": "dual_system",
            "model_path": CKPT,
            "num_history": 8,
            "resize_w": 384,
            "resize_h": 384,
            "max_new_tokens": 1024,
            "vis_debug": True,
            "vis_debug_path": os.path.join(RUN_DIR, "vis_debug"),
        },
    ),
    env=EnvCfg(
        env_type='habitat',
        env_settings={
            'config_path': 'official_r2r/configs/vln_r2r_subset3.yaml',
        },
    ),
    eval_type='habitat_vln',
    eval_settings={
        "output_path": RUN_DIR,
        "save_video": True,
        "epoch": 0,
        "max_steps_per_episode": 500,
        "port": "2333",
        "dist_url": "env://",
    },
)
