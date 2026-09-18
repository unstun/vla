#!/usr/bin/env python3
"""Reuse the accepted P2B pilot with an optional passive display observer."""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil


HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
BASE_SCRIPT = EXPERIMENT / 'isaac_runner/run_two_goal_pilot.py'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def load_base():
    spec = importlib.util.spec_from_file_location('p2b_probe_package', BASE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError('observer insertion anchor is not unique: ' + old)
    return text.replace(old, new, 1)


def add_observer_hooks(text):
    text = replace_once(text, 'import time\n', 'import time\nfrom observer.session import DisplayProbe\n')
    text = replace_once(text, '    processes = []\n', '    processes = []\n    probe = DisplayProbe(run_root)\n')
    text = replace_once(text, '        bridge_cmd = [\n', '        probe.start()\n\n        bridge_cmd = [\n')
    text = replace_once(text, '        processes.append(("runner", runner_proc))\n',
                        '        processes.append(("runner", runner_proc))\n        probe.record_process("isaac", runner_proc.pid)\n')
    text = replace_once(text, '    finally:\n        cleanup_records = []\n',
                        '    finally:\n        try:\n            result["observer"] = probe.stop()\n'
                        '        except BaseException as observer_error:\n            result["observer_error"] = str(observer_error)\n'
                        '        cleanup_records = []\n')
    compile(text, 'remote_worker_with_observer.py', 'exec')
    return text


def prepare(mode, run_id, base, args):
    local_run, commands = base.prepare(args)
    shutil.copytree(HERE / 'observer', local_run / 'observer', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    gpu_display = mode == 'rviz-gpu'
    rviz_config_file = 'pointcloud_' + run_id + '.rviz'
    shutil.copyfile(local_run / 'observer/pointcloud.rviz', local_run / 'observer' / rviz_config_file)
    config = {
        'mode': mode,
        'rviz_image_id': '980cec478c0659eaecc87b5bb79685bc3399135a2ce4033d5e815defe4478ed2',
        'display': ':0',
        'xauthority': '/run/user/1000/gdm/Xauthority',
        'renderer_requested': ('NVIDIA hardware OpenGL; require NVIDIA RTX 5070 Ti in Ogre.log'
                               if gpu_display else 'Mesa software, LIBGL_ALWAYS_SOFTWARE=1; verify Ogre.log'),
        'capture_encoder': 'h264_nvenc' if gpu_display else 'libx264',
        'gpu_display': gpu_display,
        'rviz_config_file': rviz_config_file,
        'viewer_cpu_limit_cores': 2,
        'viewer_memory_limit_bytes': 2147483648,
        'draw_rate_hz': 10,
        'decay_seconds': 0,
        'pointcloud_topic': '/quad_0/cloud_raw',
        'pointcloud_qos': 'BEST_EFFORT KEEP_LAST depth 1',
        'capture_scope': 'own RViz window only',
        'capture_time_basis': 'wall time',
        'capture_in_display_condition_only': True,
        'run_id': run_id,
    }
    if gpu_display:
        config['nvidia_runtime'] = json.loads((HERE / 'nvidia_runtime.json').read_text())
    write_json(local_run / 'observer/config.json', config)
    original = (local_run / 'remote_worker.py').read_text()
    updated = add_observer_hooks(original)
    (local_run / 'remote_worker.py').write_text(updated)
    source = json.loads((local_run / 'source_env_hashes.json').read_text())
    source['pointcloud_observer'] = {
        'base_packager_sha256': sha256(BASE_SCRIPT),
        'wrapper_sha256': sha256(Path(__file__)),
        'original_remote_worker_sha256': hashlib.sha256(original.encode()).hexdigest(),
        'observed_remote_worker_sha256': hashlib.sha256(updated.encode()).hexdigest(),
        'config': config,
        'source': {str(p.relative_to(local_run)): sha256(p) for p in (local_run / 'observer').rglob('*') if p.is_file()},
    }
    write_json(local_run / 'source_env_hashes.json', source)
    manifest = json.loads((local_run / 'inputs/package_manifest.json').read_text())
    paths = {entry['path'] for entry in manifest['files']}
    paths.update(str(p.relative_to(local_run)) for p in (local_run / 'observer').rglob('*') if p.is_file())
    manifest['files'] = [{'path': p, 'sha256': sha256(local_run / p), 'bytes': (local_run / p).stat().st_size} for p in sorted(paths)]
    write_json(local_run / 'inputs/package_manifest.json', manifest)
    commands['sync_whitelist'].append('observer/')
    commands['sync'].insert(commands['sync'].index('--exclude=*'), '--include=/observer/***')
    write_json(local_run / 'commands.json', commands)
    request = json.loads((local_run / 'run_request.json').read_text())
    request['pointcloud_display_mode'] = mode
    request['comparison_protocol'] = str(HERE / 'PROTOCOL.md')
    write_json(local_run / 'run_request.json', request)
    return local_run, commands


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['off', 'rviz', 'rviz-gpu'], default='rviz-gpu',
                        help='Display profile; NVIDIA rendering and NVENC recording are the default.')
    parser.add_argument('--run-id')
    parser.add_argument('--execute', action='store_true')
    options = parser.parse_args()
    run_id = options.run_id or datetime.now(timezone.utc).strftime('pointcloud_%Y%m%dT%H%M%SZ_') + options.mode
    base = load_base()
    args = base.build_parser().parse_args([
        '--run-id', run_id,
        '--local-runs-root', str(HERE / 'runs'),
        '--remote-root', '/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/pointcloud_display',
        '--accepted-scan-build-dir', str(EXPERIMENT / 'p2b_execution/builds/scan_03'),
        '--remote-scan-workspace', '/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_03',
        '--lead-authorized-execute',
        # PROTOCOL.md keeps the actual4 control settings (hold off); the launcher default is auto since the
        # stance-hold task's PRD D8.
        '--stance-hold', 'off',
    ])
    if (HERE / 'runs' / run_id).exists():
        local_run, commands = base.load_prepared_run(args)
    else:
        local_run, commands = prepare(options.mode, run_id, base, args)
    actual_mode = json.loads((local_run / 'observer/config.json').read_text())['mode']
    if actual_mode != options.mode:
        raise ValueError('prepared observer mode differs from requested mode')
    print(json.dumps({'run_id': run_id, 'mode': actual_mode, 'local_run': str(local_run), 'execute': options.execute}), flush=True)
    if options.execute:
        base.execute(args, local_run, commands)


if __name__ == '__main__':
    main()
