"""Display-only Mac port of the frozen causal renderer and close camera."""
import hashlib
import json
import os
from pathlib import Path
import sys
import types

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_manifest(version):
    path = BASE / 'versions' / version / 'manifest.json'
    data = json.loads(path.read_text())
    for name, expected in data['source_files'].items():
        if digest(ROOT / name) != expected:
            raise ValueError('Frozen source changed: ' + name)
        snapshot = data.get('snapshot_locations', {}).get(name)
        if snapshot and digest(ROOT / snapshot) != expected:
            raise ValueError('Frozen snapshot changed: ' + name)
    return digest(path)


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Renderer adaptation does not match its frozen source')
    return text.replace(old, new)


def main():
    contract = json.loads((HERE / 'display_contract.json').read_text())
    verify_manifest('v73')
    for version, expected in contract['parent_manifests'].items():
        if verify_manifest(version) != expected:
            raise ValueError('Parent manifest changed: ' + version)
    source = Path(contract['physical_source_root'])
    if source.resolve() != source or source.name != contract['physical_source_run']:
        raise ValueError('Wrong recorded source')
    for path, expected in contract['input_files'].items():
        if digest(path) != expected:
            raise ValueError('Recorded input changed: ' + path)
    out = Path(os.environ['NEWTON_RUN_DIR'])
    if not out.is_dir() or out.parent.parent != Path(os.environ['V73_TEMP_ROOT']):
        raise ValueError('Expected managed temporary output')
    # ViewerGL(headless=True) already requests an invisible window. Mac needs
    # its native Cocoa context; pyglet's global headless option requests EGL.
    os.environ.pop('PYGLET_HEADLESS', None)
    os.environ['PYOPENGL_PLATFORM'] = 'darwin'
    parent = BASE / 'versions/v51'
    sys.path.insert(0, str(BASE / 'scripts'))
    sys.path.insert(0, str(parent))

    renderer_path = parent / 'render_episode_v51.py'
    renderer_text = replace_once(renderer_path.read_text(),
        'source = BASE / "runs" / args.source_run',
        'source = Path(' + repr(str(source)) + ')')
    renderer_text = replace_once(renderer_text,
        'source.parent != BASE / "runs"',
        'source.name != args.source_run')
    renderer_text = replace_once(renderer_text,
        "RTF {timing['actual_navigation_rtf']:.4f} | local {timing['local_hz']:.2f} Hz | control {timing['controller_hz']:.2f} Hz | overruns {timing['local_overruns']}",
        "Mac RTF {timing['actual_navigation_rtf']:.3f} | successful local {timing['local_hz']:.2f} Hz | max round {timing['max_solve_ms']:.0f} ms")
    renderer = types.ModuleType('render_episode_v51')
    renderer.__file__ = str(renderer_path)
    sys.modules[renderer.__name__] = renderer
    exec(compile(renderer_text, str(renderer_path), 'exec'), renderer.__dict__)
    metrics = json.loads(Path(contract['analysis_metrics']).read_text())
    renderer.load_measurements = lambda unused_source: {
        'actual_navigation_rtf': metrics['actual_rtf'],
        'local_hz': metrics['planning']['successful_wall_hz'],
        'max_solve_ms': metrics['planning']['solve_ms']['maximum'],
        'definition': metrics['frequency_definition'],
        'analysis_metrics_sha256': contract['input_files'][contract['analysis_metrics']],
    }
    heading_path = parent / 'render_heading_v51.py'
    heading_text = replace_once(heading_path.read_text(),
        'render_episode.load_recorded_rows(EXPERIMENT / "runs" / args.source_run)',
        'render_episode.load_recorded_rows(Path(' + repr(str(source)) + '))')
    heading_text = replace_once(heading_text,
        'TRAIL_M, HEIGHT_M, AHEAD_M, DOWN_M, TAU_S = 1.4, 1.0, 0.6, 0.1, 0.5',
        'TRAIL_M, HEIGHT_M, AHEAD_M, DOWN_M, TAU_S = 1.1, 0.60, 0.25, 0.20, 0.5')
    (out / 'executed_render_episode_host.py').write_text(renderer_text)
    (out / 'executed_render_heading_host.py').write_text(heading_text)
    (out / 'display_contract.json').write_bytes((HERE / 'display_contract.json').read_bytes())
    remaining = sys.argv[1:]
    sys.argv = [str(heading_path), '--source-run', source.name, *remaining]
    exec(compile(heading_text, str(heading_path), 'exec'),
         {'__name__': '__main__', '__file__': str(heading_path)})
    result = json.loads((out / 'result.json').read_text())
    if not result['render_only_no_physics_steps']:
        raise ValueError('Display unexpectedly executed physics')
    for path, expected in contract['input_files'].items():
        if digest(path) != expected:
            raise ValueError('Recorded input changed during rendering: ' + path)
    (out / 'host_port_verification.json').write_text(json.dumps({
        'kind': 'display_only', 'physical_source_version': 'v72',
        'native_source_version': 'v71 upstream ROS2', 'source_unchanged': True,
        'render_only_no_physics_steps': True,
        'adapted_renderer_sha256': digest(out / 'executed_render_episode_host.py'),
        'adapted_heading_sha256': digest(out / 'executed_render_heading_host.py'),
        'graphics_context': 'Mac Cocoa, invisible ViewerGL window',
        'physics_acceptance': False,
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
