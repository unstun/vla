"""Derived eval config for the zh_between_two_chairs request.

Identical to habitat_dual_system_public_cfg.py except:
  * config_path -> the request-specific Habitat YAML
  * RUN_DIR env var -> ZH_CHAIRS_RUN_DIR (separate namespace)

All model, observation, and control parameters are unchanged.
"""
import os

from internnav.configs.agent import AgentCfg
from internnav.configs.evaluator import EnvCfg, EvalCfg

RUN_DIR = os.environ.get('ZH_CHAIRS_RUN_DIR', 'public_scenes/runs/zh_chairs_pending')

eval_cfg = EvalCfg(
    agent=AgentCfg(
        model_name='internvla_n1',
        model_settings={
            "mode": "dual_system",
            "model_path": "checkpoints/InternVLA-N1-DualVLN",
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
            'config_path': 'public_scenes/configs/vln_zh_between_two_chairs.yaml',
        },
    ),
    eval_type='habitat_vln',
    eval_settings={
        "output_path": RUN_DIR,
        "save_video": True,
        "epoch": 0,
        "max_steps_per_episode": 500,
        "port": "2334",
        "dist_url": "env://",
    },
)
