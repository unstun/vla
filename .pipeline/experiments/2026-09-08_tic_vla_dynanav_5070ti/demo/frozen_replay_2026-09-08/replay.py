"""Bounded frozen-input TIC-VLA diagnostic; uses the real first-call path."""

import argparse
import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path

from controller_probe import ControllerProbe


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    demo = here.parent
    root = demo.parent
    out = here / args.output
    out.mkdir(exist_ok=False)
    plan = json.loads((here / 'plan.json').read_text())
    checks = []

    def verify(path, expected):
        actual = digest(path)
        checks.append({'path': str(path), 'sha256': actual, 'expected': expected})
        if actual != expected:
            raise RuntimeError(f'Sync gate failed: {path}')

    verify(demo / 'manifests/source.json', plan['demo_source_manifest_sha256'])
    for entry in json.loads((demo / 'manifests/source.json').read_text()):
        verify(demo / entry['path'], entry['sha256'])
    for entry in json.loads((here / 'package_sha256.json').read_text()):
        verify(here / entry['path'], entry['sha256'])
    assets = json.loads((root / 'manifests/official_assets.json').read_text())
    for entry in assets['base_model']['files']:
        verify(root / 'models/InternVL3-1B' / entry['path'], entry['sha256'])
    checkpoint = root / 'checkpoints/TIC-VLA-model.ckpt'
    verify(checkpoint, assets['checkpoint']['sha256'])
    save(out / 'sync_gate.json', {'passed': True, 'checks': checks})

    # Imports follow the source/asset gate. The simulator is never imported.
    import numpy as np
    import torch
    import transformers
    import ticvla
    from ticvla import TICVLA

    expected_source = demo / 'work/DynaNav/ticvla.py'
    assert Path(ticvla.__file__).resolve() == expected_source.resolve()
    controller = ControllerProbe(demo / 'work/DynaNav/behavior/nova_carter_test_ticvla.py')
    parity = []
    for fixture in plan['fixtures']:
        original = json.loads((here / fixture['original_first_inference']).read_text())
        command = controller(original['waypoints'])
        expected = fixture['original_stdout_desired_command']
        error = max(abs(command['v_desired_m_s'] - expected['v']),
                    abs(command['w_desired_rad_s'] - expected['w']))
        assert error <= 0.000501, (command, expected)
        parity.append({'fixture': fixture['id'], 'command': command,
                       'stdout_rounded_command': expected, 'max_error': error})
    save(out / 'controller_parity.json', {
        'passed': True, 'source_sha256': controller.source_sha256,
        'source_lines': controller.lines, 'checks': parity})

    def tensor_info(tensor):
        t = tensor.detach().contiguous().cpu()
        return {'shape': list(t.shape), 'dtype': str(t.dtype),
                'sha256': hashlib.sha256(t.view(torch.uint8).numpy().tobytes()).hexdigest(),
                'finite': bool(torch.isfinite(t).all())}

    def cache_info(cache):
        tensors = [[tensor_info(k), tensor_info(v)] for k, v in cache]
        return {'layers': tensors, 'sha256': hashlib.sha256(
            json.dumps(tensors, sort_keys=True).encode()).hexdigest()}

    def seed(value):
        random.seed(value)
        np.random.seed(value)
        torch.manual_seed(value)
        torch.cuda.manual_seed_all(value)

    started = time.perf_counter()
    model = TICVLA(model_path=str(root / 'models/InternVL3-1B'),
                   device='cuda:0', num_action_chunks=30)
    payload = torch.load(checkpoint, map_location='cpu', weights_only=False)
    assert all(k.startswith('model.') for k in payload['state_dict'])
    model.load_state_dict({k[len('model.'):]: v for k, v in payload['state_dict'].items()}, strict=True)
    del payload
    model.eval()
    assert all(not m.training for m in model.modules())
    report = {'plan_sha256': digest(here / 'plan.json'), 'strict_load': True,
              'load_seconds': time.perf_counter() - started,
              'gpu': torch.cuda.get_device_name(0), 'torch': torch.__version__,
              'transformers': transformers.__version__,
              'cuda': torch.version.cuda, 'python': sys.version,
              'deterministic_algorithms': torch.are_deterministic_algorithms_enabled(),
              'cudnn_benchmark': torch.backends.cudnn.benchmark,
              'cudnn_deterministic': torch.backends.cudnn.deterministic,
              'records': [], 'cache_interventions': [],
              'boundary': 'frozen first-call diagnostic; no closed-loop navigation or fix validation'}
    save(out / 'report.json', report)
    try:
        for fixture in plan['fixtures']:
            raw_state = json.loads((here / fixture['state']).read_text())
            robot_state = raw_state['velocity'] + [raw_state['yaw_speed'], 0.0, 0.0]
            pose = {k: raw_state[k] for k in ['position', 'quaternion']}
            image = str(here / fixture['image'])
            base = {}
            for job in plan['jobs_per_fixture']:
                model.reset_episode_state()
                seed(job['seed'])
                captured = {}
                extraction = []

                def capture_head(module, positional, kwargs):
                    captured.update(image=positional[0], state=positional[1],
                                    cache=kwargs['kv_cache'])

                def capture_vlm(module, positional, kwargs):
                    extraction.append({
                        'input_ids': kwargs['input_ids'].detach().cpu().tolist(),
                        'attention_mask': tensor_info(kwargs['attention_mask']),
                        'pixel_values': tensor_info(kwargs['pixel_values']),
                        'image_flags': tensor_info(kwargs['image_flags'])})

                head_hook = model.action_expert.register_forward_pre_hook(capture_head, with_kwargs=True)
                vlm_hook = model.vlm.register_forward_pre_hook(capture_vlm, with_kwargs=True)
                call_started = time.perf_counter()
                try:
                    with torch.no_grad():
                        response, wps, generation, available, gen_pose = model.predict_async(
                            image_paths=[image], instruction=plan['instructions'][job['language']],
                            robot_state=torch.tensor(robot_state, dtype=torch.float32),
                            current_step=120, current_robot_pose=pose,
                            previous_waypoints_text=plan['previous_waypoints_text'],
                            time_delay=0.0, robot_type='wheeled robot')
                    torch.cuda.synchronize()
                    elapsed = time.perf_counter() - call_started
                finally:
                    head_hook.remove()
                    vlm_hook.remove()
                assert available and generation == 120
                assert all(np.array_equal(gen_pose[k], pose[k]) for k in pose)
                gen_pose_json = {k: np.asarray(v).tolist() for k, v in gen_pose.items()}
                assert list(wps.shape) == [1, 30, 2] and bool(torch.isfinite(wps).all())
                assert len(extraction) == 1, len(extraction)
                values = wps[0].float().cpu().numpy()
                record = {**job, 'id': fixture['id'] + '_' + job['id'], 'fixture': fixture['id'],
                          'instruction': plan['instructions'][job['language']],
                          'image_sha256': digest(image), 'history': [fixture['image']],
                          'robot_state_float32': torch.tensor(robot_state, dtype=torch.float32).tolist(),
                          'time_delay': 0.0, 'generation_start_step': generation,
                          'generation_start_pose': gen_pose_json, 'cache_available': available,
                          'seconds_with_observation_hooks': elapsed, 'response': response,
                          'image_features': tensor_info(captured['image']),
                          'action_state': tensor_info(captured['state']),
                          'action_state_values': captured['state'].flatten().float().cpu().tolist(),
                          'cache': cache_info(captured['cache']), 'vlm_extraction_inputs': extraction[0],
                          'waypoints': values.tolist(), 'waypoints_tensor': tensor_info(wps),
                          'controller': controller(values)}
                if job['id'].startswith('seed36_base_'):
                    base[job['language']] = {**captured, 'waypoints': wps, 'record': record}
                report['records'].append(record)
                save(out / 'report.json', report)
                print('FROZEN_REPLAY', record['id'], json.dumps(record['controller']), flush=True)

            # Same image and state; vary ONLY the language-produced semantic cache.
            assert torch.equal(base['zh']['image'], base['en']['image'])
            assert torch.equal(base['zh']['state'], base['en']['state'])
            for receiver in ['zh', 'en']:
                for donor in ['zh', 'en']:
                    with torch.no_grad():
                        replay = model.action_expert(base[receiver]['image'], base[receiver]['state'],
                                                     kv_cache=base[donor]['cache'])
                    assert bool(torch.isfinite(replay).all())
                    error = float((replay - base[donor]['waypoints']).abs().max())
                    item = {'fixture': fixture['id'], 'receiver': receiver, 'cache_donor': donor,
                            'image_features_sha256': base[receiver]['record']['image_features']['sha256'],
                            'action_state_sha256': base[receiver]['record']['action_state']['sha256'],
                            'cache_sha256': base[donor]['record']['cache']['sha256'],
                            'max_abs_error_to_donor_original_m': error,
                            'waypoints': replay[0].float().cpu().tolist(),
                            'controller': controller(replay[0].float().cpu().numpy())}
                    report['cache_interventions'].append(item)
                    save(out / 'report.json', report)
            del base
        report['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
        report['peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
        report['completed'] = True
        save(out / 'report.json', report)
    finally:
        model.cleanup()


if __name__ == '__main__':
    main()
