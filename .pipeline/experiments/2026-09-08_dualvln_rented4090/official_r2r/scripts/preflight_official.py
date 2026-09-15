"""Drive the OFFICIAL InternNav Habitat evaluator code path as far as the
available data allows, and record exactly where it stops.

This does not substitute a custom scene or runner. It uses the pinned upstream
modules and the derived official config, and reports the precise first missing
input together with the paths Habitat actually asks for.
"""
import json
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / 'work' / 'InternNav'))
sys.path.insert(0, str(ROOT / 'work' / 'InternNav' / 'third_party' / 'diffusion-policy'))

REPORT = {'stages': []}


def stage(name, fn):
    entry = {'stage': name}
    try:
        entry['result'] = fn()
        entry['ok'] = True
    except BaseException as exc:
        entry['ok'] = False
        entry['error_type'] = type(exc).__name__
        entry['error'] = str(exc)[:2000]
        entry['traceback_tail'] = traceback.format_exc()[-2500:]
    REPORT['stages'].append(entry)
    print(('  OK   ' if entry['ok'] else '  FAIL ') + name
          + ('' if entry['ok'] else ' -> %s: %s' % (entry['error_type'], entry['error'][:200])),
          flush=True)
    return entry['ok']


def s_versions():
    import habitat, habitat_sim, torch, transformers, diffusers
    import habitat_baselines
    return {'habitat_lab': habitat.__version__, 'habitat_sim': habitat_sim.__version__,
            'habitat_baselines': getattr(habitat_baselines, '__version__', 'n/a'),
            'torch': torch.__version__, 'torch_cuda': torch.version.cuda,
            'transformers': transformers.__version__, 'diffusers': diffusers.__version__,
            'python': sys.version.split()[0]}


def s_dataset_registered():
    from habitat.core.registry import registry
    ds = registry.get_dataset('R2RVLN-v1')
    return {'R2RVLN-v1_registered': ds is not None,
            'class': getattr(ds, '__name__', None),
            'module': getattr(ds, '__module__', None)}


def s_evaluator_import():
    import internnav.habitat_extensions.vln.habitat_vln_evaluator as ev
    return {'module': ev.__file__, 'MAX_STEPS': ev.MAX_STEPS,
            'MAX_LOCAL_STEPS': ev.MAX_LOCAL_STEPS,
            'action_codes': {c.name: int(c) for c in ev.action_code}}


def s_habitat_config():
    from habitat_baselines.config.default import get_config as get_habitat_config
    cfg = get_habitat_config('official_r2r/configs/vln_r2r_subset3.yaml')
    d = cfg.habitat.dataset
    sim = cfg.habitat.simulator
    rgb = sim.agents.main_agent.sim_sensors.rgb_sensor
    REPORT['habitat_config'] = {
        'dataset_type': d.type, 'split': d.split,
        'scenes_dir': d.scenes_dir, 'data_path': d.data_path,
        'forward_step_size': sim.forward_step_size, 'turn_angle': sim.turn_angle,
        'tilt_angle': sim.tilt_angle,
        'rgb': {'width': rgb.width, 'height': rgb.height, 'hfov': rgb.hfov,
                'position': list(rgb.position)},
        'success_distance': cfg.habitat.task.measurements.success.success_distance,
        'max_episode_steps': cfg.habitat.environment.max_episode_steps,
    }
    return REPORT['habitat_config']


def s_dataset_loads():
    from habitat.datasets import make_dataset
    from habitat_baselines.config.default import get_config as get_habitat_config
    cfg = get_habitat_config('official_r2r/configs/vln_r2r_subset3.yaml')
    ds = make_dataset(cfg.habitat.dataset.type, config=cfg.habitat.dataset)
    eps = ds.episodes
    return {'episodes_loaded': len(eps),
            'episode_ids': [e.episode_id for e in eps],
            'scene_ids': sorted({e.scene_id for e in eps}),
            'instructions': [e.instruction.instruction_text for e in eps]}


def s_scene_files_present():
    from habitat_baselines.config.default import get_config as get_habitat_config
    cfg = get_habitat_config('official_r2r/configs/vln_r2r_subset3.yaml')
    from habitat.datasets import make_dataset
    ds = make_dataset(cfg.habitat.dataset.type, config=cfg.habitat.dataset)
    need = []
    for scene in sorted({e.scene_id for e in ds.episodes}):
        glb = Path(cfg.habitat.dataset.scenes_dir) / scene
        need.append({'scene_id': scene, 'expected_glb': str(glb), 'glb_exists': glb.exists(),
                     'expected_navmesh': str(glb.with_suffix('.navmesh')),
                     'navmesh_exists': glb.with_suffix('.navmesh').exists()})
    REPORT['required_scene_files'] = need
    missing = [n for n in need if not n['glb_exists']]
    if missing:
        raise FileNotFoundError('missing MP3D scene mesh(es): '
                                + ', '.join(n['expected_glb'] for n in missing))
    return need


def s_env_constructs():
    import habitat
    from habitat_baselines.config.default import get_config as get_habitat_config
    cfg = get_habitat_config('official_r2r/configs/vln_r2r_subset3.yaml')
    env = habitat.Env(cfg)
    n = len(env.episodes)
    env.close()
    return {'episodes': n}


def main():
    print('Official evaluator preflight (pinned upstream modules, derived config)\n', flush=True)
    stage('official env versions', s_versions)
    stage('R2RVLN-v1 dataset registered by habitat-lab', s_dataset_registered)
    stage('InternNav official evaluator imports', s_evaluator_import)
    stage('official habitat config loads', s_habitat_config)
    stage('derived 3-episode annotation loads', s_dataset_loads)
    stage('MP3D scene meshes present', s_scene_files_present)
    stage('habitat.Env constructs', s_env_constructs)

    failed = [s for s in REPORT['stages'] if not s['ok']]
    REPORT['first_blocker'] = failed[0]['stage'] if failed else None
    REPORT['all_stages_passed'] = not failed
    out = Path('official_r2r/setup/preflight_report.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(REPORT, indent=2) + '\n')
    print('\nfirst blocker: %s' % REPORT['first_blocker'], flush=True)
    print('PREFLIGHT_REPORT_WRITTEN ' + str(out), flush=True)


if __name__ == '__main__':
    main()
