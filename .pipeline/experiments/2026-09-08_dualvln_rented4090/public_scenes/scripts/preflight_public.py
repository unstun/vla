"""Preflight the official evaluator from the directory the launcher actually uses.

Lead review O1: the previous preflight chdir'd to the experiment root while the
launcher chdir'd to work/InternNav, so it could not see the path failures that
would stop the real run. This one refuses to run anywhere except the official
launch directory, and resolves every path exactly as the evaluator will.

It stops at the first failing stage and records the traceback, so a later stage
is never reported as passed or failed on the strength of an earlier one.
"""
import argparse
import gzip
import hashlib
import json
import os
import sys
import traceback
from pathlib import Path

sys.path.append('.')
sys.path.append('./third_party/diffusion-policy')

REPORT = {'stages': []}


def stage(name, fn):
    entry = {'stage': name}
    if REPORT['stages'] and not REPORT['stages'][-1]['ok']:
        entry.update(ok=False, skipped=True,
                     detail='not attempted: an earlier stage failed')
        REPORT['stages'].append(entry)
        return None
    try:
        entry['detail'] = fn()
        entry['ok'] = True
    except Exception:
        entry['ok'] = False
        entry['traceback'] = traceback.format_exc()
    REPORT['stages'].append(entry)
    return entry.get('detail')


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--eval-config', default='public_scenes/configs/habitat_dual_system_public_cfg.py')
    ap.add_argument('--out', default='public_scenes/setup/preflight_public_report.json')
    a = ap.parse_args()

    cwd = Path.cwd()
    REPORT['launch_directory'] = str(cwd)
    if cwd.name != 'InternNav':
        raise SystemExit(f'must run from the official launch directory work/InternNav, not {cwd}')

    def s_versions():
        import habitat
        import habitat_baselines
        import habitat_sim
        import torch
        import transformers
        import diffusers
        return {
            'python': sys.version.split()[0],
            'habitat_lab': habitat.__version__,
            'habitat_lab_path': habitat.__file__,
            'habitat_baselines': habitat_baselines.__version__,
            'habitat_sim': habitat_sim.__version__,
            'torch': torch.__version__,
            'transformers': transformers.__version__,
            'diffusers': diffusers.__version__,
            'cuda_available': torch.cuda.is_available(),
            'cuda_device': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        }

    def s_paths():
        wanted = {
            'eval_config': a.eval_config,
            'habitat_yaml': 'public_scenes/configs/vln_public_scenes.yaml',
            'annotations': 'public_scenes/data/vln_ce/raw_data/public/val_unseen/val_unseen.json.gz',
            'scene_glb': 'public_scenes/data/scene_data/public/skokloster-castle/skokloster-castle.glb',
            'scene_navmesh': 'public_scenes/data/scene_data/public/skokloster-castle/skokloster-castle.navmesh',
            'aux_depth_encoder': 'checkpoints/depth_anything_v2_metric_hypersim_vits.pth',
            'model_checkpoint_config': 'checkpoints/InternVLA-N1-DualVLN/config.json',
        }
        out, missing = {}, []
        for k, rel in wanted.items():
            p = Path(rel)
            out[k] = {'relative_to_launch_dir': rel, 'exists': p.exists(),
                      'resolves_to': str(p.resolve()) if p.exists() else None}
            if not p.exists():
                missing.append(rel)
        if missing:
            raise RuntimeError(f'unresolvable from the launch directory: {missing}')
        return out

    def s_aux_encoder_relative():
        # internvla_n1_arch.py hardcodes MODEL_PATH_TO = "checkpoints", relative to cwd
        from internnav.model.basemodel.internvla_n1 import internvla_n1_arch as arch
        p = Path(arch.MODEL_PATH_TO) / 'depth_anything_v2_metric_hypersim_vits.pth'
        if not p.exists():
            raise RuntimeError(f'{p} unreachable from {Path.cwd()}')
        return {'MODEL_PATH_TO': arch.MODEL_PATH_TO, 'resolved': str(p.resolve()),
                'bytes': p.stat().st_size}

    def s_evaluator_import():
        # internnav/evaluator/__init__.py swallows this failure with a warning,
        # so import it directly and let it raise.
        import internnav.habitat_extensions.vln  # noqa: F401
        from internnav.evaluator import Evaluator
        # Upstream's @Evaluator.register decorator returns None, so the module-level
        # name HabitatVLNEvaluator is None after decoration; the class only survives
        # in Evaluator.evaluators, which is what eval.py actually looks up.
        cls = Evaluator.evaluators.get('habitat_vln')
        if cls is None:
            raise RuntimeError(f'habitat_vln not registered; have {sorted(Evaluator.evaluators)}')
        return {'registered_evaluators': sorted(Evaluator.evaluators),
                'habitat_vln_class': cls.__name__,
                'habitat_vln_module': cls.__module__}

    def s_eval_cfg():
        import importlib.util
        spec = importlib.util.spec_from_file_location('preflight_eval_cfg', a.eval_config)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cfg = mod.eval_cfg
        return {'eval_type': cfg.eval_type,
                'model_settings': {k: v for k, v in cfg.agent.model_settings.items()},
                'env_settings': dict(cfg.env.env_settings),
                'eval_settings': dict(cfg.eval_settings)}

    def s_habitat_config():
        from habitat_baselines.config.default import get_config as get_habitat_config
        cfg = get_habitat_config('public_scenes/configs/vln_public_scenes.yaml')
        sim = cfg.habitat.simulator
        agent = sim.agents.main_agent
        return {
            'dataset_type': cfg.habitat.dataset.type,
            'split': cfg.habitat.dataset.split,
            'scenes_dir': cfg.habitat.dataset.scenes_dir,
            'data_path': cfg.habitat.dataset.data_path,
            'forward_step_size': float(sim.forward_step_size),
            'turn_angle': int(sim.turn_angle),
            'tilt_angle': int(sim.tilt_angle),
            'action_space_config': str(sim.action_space_config),
            'rgb': {'w': int(agent.sim_sensors.rgb_sensor.width),
                    'h': int(agent.sim_sensors.rgb_sensor.height),
                    'hfov': int(agent.sim_sensors.rgb_sensor.hfov),
                    'position': [float(v) for v in agent.sim_sensors.rgb_sensor.position]},
            'depth': {'min': float(agent.sim_sensors.depth_sensor.min_depth),
                      'max': float(agent.sim_sensors.depth_sensor.max_depth)},
            'success_distance': float(cfg.habitat.task.measurements.success.success_distance),
            'max_episode_steps': int(cfg.habitat.environment.max_episode_steps),
            'measurements': sorted(cfg.habitat.task.measurements.keys()),
            'actions': sorted(cfg.habitat.task.actions.keys()),
        }

    def s_annotations():
        p = Path('public_scenes/data/vln_ce/raw_data/public/val_unseen/val_unseen.json.gz')
        data = json.loads(gzip.open(p, 'rt').read())
        return {
            'path': str(p), 'sha256': sha256_file(p), 'bytes': p.stat().st_size,
            'n_episodes': len(data['episodes']),
            'episodes': [{'episode_id': e['episode_id'], 'scene_id': e['scene_id'],
                          'instruction': e['instruction']['instruction_text'],
                          'geodesic_distance': e['info']['geodesic_distance'],
                          'goal_radius': e['goals'][0]['radius']} for e in data['episodes']],
        }

    def s_scene_hashes():
        man = json.loads(Path('public_scenes/setup/public_scene_manifest.json').read_text())
        out = []
        for row in man['files']:
            p = Path(row['path'].replace('public_scenes/', 'public_scenes/', 1))
            digest = sha256_file(p)
            out.append({'path': str(p), 'sha256': digest,
                        'matches_manifest': digest == row['sha256'],
                        'verified_against_upstream_lfs': row['sha256_verified_against_upstream']})
        if not all(r['matches_manifest'] for r in out):
            raise RuntimeError('scene asset hash mismatch')
        return out

    def s_env_constructs():
        import habitat
        from habitat_baselines.config.default import get_config as get_habitat_config
        import internnav.habitat_extensions.vln.measures  # noqa: F401
        cfg = get_habitat_config('public_scenes/configs/vln_public_scenes.yaml')
        env = habitat.Env(cfg)
        try:
            obs = env.reset()
            ep = env.current_episode
            return {
                'n_episodes_loaded': len(env.episodes),
                'first_episode_id': ep.episode_id,
                'first_scene_id': ep.scene_id,
                'observation_keys': sorted(obs.keys()),
                'rgb_shape': list(obs['rgb'].shape),
                'depth_shape': list(obs['depth'].shape),
                'depth_min_max_normalised': [float(obs['depth'].min()), float(obs['depth'].max())],
                'metrics_keys': sorted(env.get_metrics().keys()),
                'initial_distance_to_goal': float(env.get_metrics()['distance_to_goal']),
            }
        finally:
            env.close()

    stage('official env versions', s_versions)
    stage('all paths resolve from the launch directory', s_paths)
    stage('auxiliary depth encoder at upstream relative MODEL_PATH_TO', s_aux_encoder_relative)
    stage('InternNav official evaluator imports (not swallowed)', s_evaluator_import)
    stage('derived eval config loads', s_eval_cfg)
    stage('official habitat config composes', s_habitat_config)
    stage('frozen public annotations load', s_annotations)
    stage('scene assets match the download manifest', s_scene_hashes)
    stage('habitat.Env constructs and resets', s_env_constructs)

    failed = [s for s in REPORT['stages'] if not s['ok']]
    REPORT['first_blocker'] = failed[0]['stage'] if failed else None
    REPORT['all_stages_passed'] = not failed
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(REPORT, indent=2, sort_keys=True) + '\n')
    for s in REPORT['stages']:
        print(('PASS  ' if s['ok'] else ('SKIP  ' if s.get('skipped') else 'FAIL  ')) + s['stage'])
    print('ALL_STAGES_PASSED' if REPORT['all_stages_passed']
          else f"FIRST_BLOCKER: {REPORT['first_blocker']}")
    return 0 if REPORT['all_stages_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
