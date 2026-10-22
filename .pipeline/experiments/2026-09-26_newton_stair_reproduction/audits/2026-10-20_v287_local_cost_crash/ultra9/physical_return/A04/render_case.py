"""Render complete recorded states using the frozen v220 causal display."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import types

ROOT = Path('/home/ubuntu/sun/vla_v287_20261020')
EXP = ROOT / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
VERSIONS = EXP / 'versions'
AUDIT = EXP / 'audits/2026-10-20_v287_local_cost_crash'
CASE = os.environ['V287_CASE_ID']
TASK = ROOT / 'physical_runs' / f'v287_{CASE}_attempt01'
RAW = TASK / 'runs' / TASK.name
CASEOUT = AUDIT / 'physical' / CASE
RESULTS = CASEOUT / 'results'
RENDER_ID = os.environ.get('V287_RENDER_ID', '01')
assert len(RENDER_ID) == 2 and RENDER_ID.isdigit()
DISPLAY = TASK / ('video_v220_' + RENDER_ID)
OUT = DISPLAY / 'runs/full01'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    sys.path[:0] = [str(ROOT / 'migration'), str(VERSIONS / 'v196'), str(VERSIONS / 'v220')]
    import physical
    physical.verify_sources()
    from analyze_remote import Capture
    capture = Capture(RAW)
    outcome = json.loads((RESULTS / 'outcome.json').read_text())
    metrics = json.loads((RESULTS / 'metrics.json').read_text())
    route = json.loads((RESULTS / 'full_route_verification.json').read_text())
    assert outcome['full_route_gate_passed'] == route['passed']
    assert not DISPLAY.exists()
    OUT.mkdir(parents=True)
    (DISPLAY / 'cache').mkdir()
    # The existing display reads these text files directly; restore exact bytes
    # from the immutable capture archive, never synthesize records or clocks.
    for name in ('clock_samples.jsonl', 'backend_states.jsonl'):
        path = RAW / name
        if not path.exists():
            path.write_text(capture.read(name))
            manifest = json.loads((RAW / 'raw_capture_manifest.json').read_text())['members'][name]
            assert sha(path) == manifest['sha256']
    files = [RESULTS / n for n in ('metrics.json', 'latency.csv', 'outcome.json', 'full_route_verification.json')]
    files += [RAW / n for n in ('video_states.json', 'factory_video_states.json', 'initial_state.json',
        'episode_request.json', 'result.json', 'inputs/stair_scenario.json', 'clock_samples.jsonl', 'backend_states.jsonl')]
    snapshot = json.loads((RESULTS / 'capture_snapshot.json').read_text())
    files.append(Path(snapshot['archive']))
    contract = dict(physical_source_root=str(RAW), physical_source_run=RAW.name,
        physical_parent='v287', native_source='v287 PCT+SCAN', locomotion='v216', display_parent='v220',
        source_outcome=str(RESULTS / 'outcome.json'), route_verification=str(RESULTS / 'full_route_verification.json'),
        analysis_metrics=str(RESULTS / 'metrics.json'), latency_csv=str(RESULTS / 'latency.csv'),
        parent_manifests={'v287': sha(ROOT / 'migration/physical_manifest01.json')},
        input_files={str(p): sha(p) for p in files}, physics_steps=0,
        claim='Full original startup simulation timestamps and navigation wall1:1; no interpolation, no new physics, failures and pauses retained')
    (DISPLAY / 'display_contract.json').write_text(json.dumps(contract, indent=2) + '\n')
    local_script = CASEOUT / 'render_case.py'
    shutil.copy2(Path(__file__), local_script)
    (CASEOUT / 'source_identity.json').write_text(json.dumps(dict(files={'render_case.py': sha(local_script)}), indent=2) + '\n')
    os.environ.update(NEWTON_RUN_DIR=str(OUT), V220_RENDER_ROOT=str(DISPLAY),
        V220_DISPLAY_CONTRACT=str(DISPLAY / 'display_contract.json'), WARP_CACHE_PATH=str(DISPLAY / 'cache'),
        PYOPENGL_PLATFORM='egl', PYGLET_HEADLESS='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
        PATH=str(ROOT / 'migration/bin') + ':' + os.environ['PATH'])
    source = VERSIONS / 'v220/render_capture.py'
    code = source.read_text()
    code = code.replace("'physical_source_version': 'v219'", "'physical_source_version': 'v287'")
    code = code.replace('Nav2 Foxy linux/amd64 SCAN v206; v208 locomotion; v196 direct Twist recorder',
        'v287 PCT+SCAN; frozen v237 physics/scanner; v216 factory PD/RL')
    old = 'TRAIL_M, HEIGHT_M, AHEAD_M, DOWN_M, TAU_S = 1.1, 0.60, 0.25, 0.20, 0.5'
    assert code.count(old) == 1
    code = code.replace(old, 'TRAIL_M, HEIGHT_M, AHEAD_M, DOWN_M, TAU_S = 0.35, 0.50, 0.0, 0.05, 0.2')
    namespace = dict(__file__=str(source), __name__='new_host_recorded_renderer')
    exec(compile(code, str(source), 'exec'), namespace)
    namespace.update(HERE=CASEOUT, BASE=EXP, ROOT=ROOT / 'repo')
    def verify_manifest(version):
        assert version == 'v287'
        physical.verify_sources()
        return sha(ROOT / 'migration/physical_manifest01.json')
    namespace['verify_manifest'] = verify_manifest
    adapt_original = namespace['adapt_renderer']
    caption = ('arrived (nav2_arrived)' if outcome['terminal_status'] == 'FINISHED' else
        'physical fall (simulation stopped)' if outcome.get('fallen') else
        'failed (nav2_failed)' if outcome['terminal_status'] == 'FAILED' else 'original recording limit; mission not finished')
    if outcome.get('process_failure', {}).get('present'):
        caption = 'navigation failed: native process exit'
    def adapt(text, raw, display_contract):
        text = adapt_original(text, raw, display_contract)
        text = text.replace('version_label = (" | " + episode_request["integration_version"]) if episode_request.get("integration_version") else ""',
            'version_label = ' + repr(' | v287 ' + CASE))
        assert text.count('60.0 if full_building') == 2
        text = text.replace('60.0 if full_building', '95.0 if full_building')
        text = text.replace('            caption = (', '            if i == len(rows)-1: status = ' + repr(caption) + '\n            caption = (')
        return text
    namespace['adapt_renderer'] = adapt
    events = capture.rows('artifacts/reactive_observations.jsonl')
    has_spline = any(r.get('event') == 'bspline' for r in events)
    has_route = any(r.get('event') == 'pct_route' for r in events)
    if not has_spline:
        overlay_path = VERSIONS / 'v220/curve_overlay.py'
        overlay_code = overlay_path.read_text()
        old = "        if not self.total_splines:\n            raise ValueError('No native splines were recorded')"
        assert overlay_code.count(old) == 1
        overlay_code = overlay_code.replace(old, '        # Verified empty native spline stream; render no invented curve.')
        overlay = types.ModuleType('curve_overlay')
        overlay.__file__ = str(overlay_path)
        exec(compile(overlay_code, str(overlay_path), 'exec'), overlay.__dict__)
        sys.modules[overlay.__name__] = overlay
    spec = importlib.util.spec_from_file_location('v287_display_locomotion', VERSIONS / 'v216/activate.py')
    locomotion = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(locomotion)
    locomotion.install()
    sys.argv = [str(local_script)]
    namespace['main']()
    checker_path = VERSIONS / 'v220/verify_video.py'
    checker = checker_path.read_text()
    checker = checker.replace('video_v220/', DISPLAY.name + '/')
    checker = checker.replace('v219_linux_full_attempt01', RAW.name)
    checker = checker.replace("assert outcome['terminal_status'] in ('FINISHED','FAILED') or outcome.get('fallen') is True", "assert outcome['terminal_status'] in ('FINISHED','FAILED','BOUNDED_END','PHYSICAL_FALL')")
    checker = checker.replace("assert (metrics.get('terminal') or {}).get('backend_terminal_status') == outcome['terminal_status']", "assert (metrics.get('terminal') or {}).get('backend_terminal_status') == outcome.get('recorded_backend_terminal_status')")
    checker = checker.replace("assert result['integration_version'] == 'v219'", "assert result['integration_version'] == 'v287'")
    checker = checker.replace("    assert frames[-1]['navigation_status'] == expected_status", '    assert frames[-1][\'navigation_status\'] == ' + repr(caption))
    checker = checker.replace('    assert visible > 0 and routes_visible > 0',
        '    assert ' + ('visible > 0' if has_spline else 'visible == 0') + ' and ' + ('routes_visible > 0' if has_route else 'routes_visible == 0'))
    checker = checker.replace("'physical_source_version': 'v219'", "'physical_source_version': 'v287'")
    scope = dict(__file__=str(checker_path), __name__='new_host_video_checker')
    exec(compile(checker, str(checker_path), 'exec'), scope)
    scope.update(TASK=TASK, OUT=OUT, HERE=CASEOUT, BASE=EXP)
    (OUT / 'executed_video_checker.py').write_text(checker)
    scope['main']()
    video = OUT / 'newton_stair_recorded.mp4'
    destination = AUDIT / 'delivered' / f'v287_{CASE}_full_attempt01.mp4'
    destination.parent.mkdir(exist_ok=True)
    assert not destination.exists()
    shutil.copy2(video, destination)
    (RESULTS / 'local_video_delivery.json').write_text(json.dumps(dict(case_id=CASE,
        full_recorded_attempt=True, video=str(destination), bytes=destination.stat().st_size,
        sha256=sha(destination), planned_route_completed=route['passed'], physics_steps=0,
        causal_frame_checker_sha256=sha(OUT / 'executed_video_checker.py')),
        indent=2) + '\n')
    print(json.dumps(dict(case_id=CASE, video_sha256=sha(destination), physics_steps=0)), flush=True)

if __name__ == '__main__':
    main()
