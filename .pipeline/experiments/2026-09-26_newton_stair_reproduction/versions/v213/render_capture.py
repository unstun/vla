"""Display-only Linux EGL port of the frozen causal renderer and close camera for v212_linux_full_attempt01."""
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
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(4 * 1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def verify_manifest(version):
    path = BASE / 'versions' / version / 'manifest.json'
    data = json.loads(path.read_text())
    for name, expected in data['source_files'].items():
        local = ROOT / name if 'snapshot_locations' in data else path.parent / name
        if digest(local) != expected:
            raise ValueError('Frozen source changed: ' + name)
        snapshot = data.get('snapshot_locations', {}).get(name)
        if snapshot and digest(ROOT / snapshot) != expected:
            raise ValueError('Frozen snapshot changed: ' + name)
    return digest(path)


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Renderer adaptation does not match its frozen source')
    return text.replace(old, new)


def adapt_renderer(renderer_text, source, contract):
    renderer_text = replace_once(renderer_text,
        'source = BASE / "runs" / args.source_run',
        'source = Path(' + repr(str(source)) + ')')
    renderer_text = replace_once(renderer_text,
        'source.parent != BASE / "runs"',
        'source.name != args.source_run')
    renderer_text = replace_once(renderer_text,
        "RTF {timing['actual_navigation_rtf']:.4f} | local {timing['local_hz']:.2f} Hz | control {timing['controller_hz']:.2f} Hz | overruns {timing['local_overruns']}",
        "Linux RTF {timing['actual_navigation_rtf']:.3f} | successful local {timing['local_hz']:.2f} Hz | max round {timing['max_solve_ms']:.0f} ms")
    renderer_text = replace_once(renderer_text,
        '    curves, routes = [], []',
        '    from curve_overlay import Overlay\n'
        '    local_overlay = Overlay(source, Path(' + repr(contract['latency_csv']) + '))\n'
        '    curves, routes = [], []')
    old_curve = renderer_text[renderer_text.index('            available = [c for c in curves'):renderer_text.index('            viewer.end_frame()')]
    new_curve = """            available = [curve_meta] if curve_points is not None else []
            if curve_points is not None:
                viewer.log_lines("native_curve", wp.array(curve_points[:-1], dtype=wp.vec3),
                                 wp.array(curve_points[1:], dtype=wp.vec3), colors=(0.0, 0.85, 1.0))
                viewer.log_points("native_curve_tube", wp.array(curve_points, dtype=wp.vec3),
                                  radii=0.025, colors=wp.array(np.tile(np.array([0.02, 0.92, 1.0], dtype=np.float32), (len(curve_points), 1)), dtype=wp.vec3))
            else:
                viewer.log_lines("native_curve", None, None, None)
                viewer.log_points("native_curve_tube", None)
"""
    renderer_text = replace_once(renderer_text, old_curve, new_curve)
    renderer_text = replace_once(renderer_text,
        '        viewer.renderer.spotlight_enabled = False',
        '        viewer.renderer.spotlight_enabled = False\n        viewer.renderer.line_width = 5.0')
    renderer_text = replace_once(renderer_text,
        '            draw.text((22, 53), detail, font=small, fill=(153, 216, 239))',
        '            tid = curve_meta["trajectory_id"]\n'
        '            ms = curve_meta["latest_completed_solve_ms"]\n'
        '            detail = "CYAN: local SCAN " + ("#"+str(tid) if tid is not None else "(no active curve)") + " | ORANGE: global PCT"\n'
        '            if ms is not None: detail += f" | latest solve {ms:.2f} ms"\n'
        '            draw.text((22, 53), detail, font=small, fill=(65, 225, 245))')
    renderer_text = replace_once(renderer_text,
        '                "navigation_status": status, "shape": list(rgb.shape)}))',
        '                "navigation_status": status, "local_curve": curve_meta, "shape": list(rgb.shape)}))')
    renderer_text = replace_once(renderer_text,
        '    (out / "frames.json").write_text(json.dumps(manifest, indent=2) + "\\n")',
        '    (out / "curve_frames.json").write_text(json.dumps(local_overlay.records, indent=2) + "\\n")\n'
        '    (out / "frames.json").write_text(json.dumps(manifest, indent=2) + "\\n")')
    renderer_text = replace_once(renderer_text,
        '            current_routes = [r for r in routes if r["clock_ns"] <= round(t * 1e9)]',
        '            curve_points, curve_meta = local_overlay.frame(row)\n'
        '            route_points = local_overlay.route_points\n'
        '            current_routes = [True] if route_points is not None else []')
    start = renderer_text.index('            if current_routes:\n')
    end = renderer_text.index('            for part in parts:', start)
    renderer_text = replace_once(renderer_text, renderer_text[start:end],
        '            if route_points is not None and len(route_points) > 1:\n'
        '                points = route_points\n'
        '                viewer.log_lines("pct_route", wp.array(points[:-1], dtype=wp.vec3), wp.array(points[1:], dtype=wp.vec3), colors=(1.,.55,.05))\n'
        '            else:\n'
        '                viewer.log_lines("pct_route", None, None, None)\n')
    return renderer_text


def main():
    contract = json.loads(Path(os.environ['V213_DISPLAY_CONTRACT']).read_text())
    audit = json.loads((HERE / 'source_identity.json').read_text())
    for name, expected in audit['files'].items():
        if digest(HERE / name) != expected:
            raise ValueError('Display source changed: ' + name)
    if (HERE / 'manifest.json').exists():
        verify_manifest('v213')
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
    if not out.is_dir() or out.parent.parent != Path(os.environ['V213_RENDER_ROOT']):
        raise ValueError('Expected managed temporary output')
    # Reuse the existing Linux EGL recorded-state display backend.
    os.environ['PYGLET_HEADLESS'] = '1'
    os.environ['PYOPENGL_PLATFORM'] = 'egl'
    parent = BASE / 'versions/v51'
    sys.path.insert(0, str(BASE / 'scripts'))
    sys.path.insert(0, str(parent))
    sys.path.insert(0, str(BASE / 'versions/v40/physics'))

    renderer_path = parent / 'render_episode_v51.py'
    renderer_text = adapt_renderer(renderer_path.read_text(), source, contract)
    renderer_text = replace_once(renderer_text, 'from robot_scene import StairRobot',
        'from robot_scene_v40 import StairRobot')
    renderer_text = replace_once(renderer_text, '                           automatic_contact_capacity=True,',
        '                           automatic_contact_capacity=True, model_device="cpu",')
    renderer_text = replace_once(renderer_text,
        'f"Lite3{version_label} | wall 1:1 {row[\'display_time_s\']:05.2f}s | native {t:05.2f}s"',
        'f"Lite3{version_label} | {row[\'timeline_segment\']} | video {row[\'display_time_s\']:05.2f}s | native {t:05.2f}s"')
    renderer_text = replace_once(renderer_text,
        '            draw.text((22, 53), detail, font=small, fill=(65, 225, 245))',
        '            if row["timeline_segment"]=="startup sim": detail="Startup: "+row["controller_phase"]+" | recorded simulation time"\n'
        '            draw.text((22, 53), detail, font=small, fill=(65, 225, 245))')
    renderer_text = replace_once(renderer_text,
        '                "physics_time_s": t, "display_time_s": row["display_time_s"],',
        '                "timeline_segment":row["timeline_segment"], "physics_time_s": t, "display_time_s": row["display_time_s"],')
    renderer_text = renderer_text.replace('/System/Library/Fonts/Helvetica.ttc',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    renderer = types.ModuleType('render_episode_v51')
    renderer.__file__ = str(renderer_path)
    sys.modules[renderer.__name__] = renderer
    exec(compile(renderer_text, str(renderer_path), 'exec'), renderer.__dict__)
    metrics = json.loads(Path(contract['analysis_metrics']).read_text())
    from full_timeline import load_rows
    renderer.load_recorded_rows = load_rows
    renderer.load_measurements = lambda unused_source: {
        'actual_navigation_rtf': metrics['actual_rtf'],
        'local_hz': metrics['planning']['successful_wall_hz'],
        'max_solve_ms': metrics['planning']['solve_ms']['maximum'],
        'definition': metrics['frequency_definition'],
        'analysis_metrics_sha256': contract['input_files'][contract['analysis_metrics']],
    }
    heading_path = parent / 'render_heading_v51.py'
    heading_text = heading_path.read_text().replace(
        'Path("/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction")',
        'Path(' + repr(str(BASE)) + ')')
    heading_text = replace_once(heading_text,
        'render_episode.load_recorded_rows(EXPERIMENT / "runs" / args.source_run)',
        'render_episode.load_recorded_rows(Path(' + repr(str(source)) + '))')
    heading_text = replace_once(heading_text,
        'TRAIL_M, HEIGHT_M, AHEAD_M, DOWN_M, TAU_S = 1.4, 1.0, 0.6, 0.1, 0.5',
        'TRAIL_M, HEIGHT_M, AHEAD_M, DOWN_M, TAU_S = 1.1, 0.60, 0.25, 0.20, 0.5')
    heading_text = replace_once(heading_text, 'OVERVIEW_S = 1.6', 'OVERVIEW_S = 0.0')
    (out / 'executed_render_episode_host.py').write_text(renderer_text)
    (out / 'executed_render_heading_host.py').write_text(heading_text)
    (out / 'display_contract.json').write_bytes(Path(os.environ['V213_DISPLAY_CONTRACT']).read_bytes())
    remaining = sys.argv[1:]
    sys.argv = [str(heading_path), '--source-run', source.name, *remaining]
    exec(compile(heading_text, str(heading_path), 'exec'),
         {'__name__': '__main__', '__file__': str(heading_path)})
    result = json.loads((out / 'result.json').read_text())
    result['claim'] = ('Original startup sampled by recorded simulation time; navigation sampled by original '
                       'wall timestamps. No invented startup wall timestamps, state interpolation or physics steps.')
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    if not result['render_only_no_physics_steps']:
        raise ValueError('Display unexpectedly executed physics')
    for path, expected in contract['input_files'].items():
        if digest(path) != expected:
            raise ValueError('Recorded input changed during rendering: ' + path)
    (out / 'host_port_verification.json').write_text(json.dumps({
        'kind': 'display_only',
        'physical_source_version': 'v212',
        'native_source_version': 'Nav2 Foxy linux/amd64 SCAN v206; v208 locomotion; v196 direct Twist recorder',
        'source_unchanged': True,
        'render_only_no_physics_steps': True,
        'adapted_renderer_sha256': digest(out / 'executed_render_episode_host.py'),
        'adapted_heading_sha256': digest(out / 'executed_render_heading_host.py'),
        'graphics_context': 'Linux x86_64 EGL headless ViewerGL',
        'physics_acceptance': False,
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
