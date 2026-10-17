"""Render retained partial states; missing completion remains missing."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import types

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
PREFIX = Path('/home/ubuntu/sun/vla_v234_20261017')
TASK = PREFIX / 'trials/v235_linux_full_attempt01'
SOURCE = TASK / 'runs/v235_linux_full_attempt01'
ROOT = TASK / os.environ.get('V235_RENDER_ROOT_NAME', 'video_v235')
OUT = ROOT / 'runs/full01'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    outcome = json.loads((HERE / 'results/outcome.json').read_text())
    assert outcome['goal_sent'] is False and not outcome['result_json_present']
    assert not (SOURCE / 'result.json').exists()
    ROOT.mkdir(exist_ok=False)
    OUT.mkdir(parents=True)
    (ROOT / 'cache').mkdir()
    inputs = [SOURCE / name for name in ('video_states.json', 'factory_video_states.json',
        'initial_state.json', 'episode_request.json', 'inputs/stair_scenario.json',
        'clock_samples.jsonl', 'backend_states.jsonl', 'telemetry.jsonl', 'run.log', 'process.json')]
    inputs += [HERE / 'results' / name for name in ('outcome.json', 'full_route_verification.json', 'metrics.json', 'latency.csv')]
    contract = dict(physical_source_root=str(SOURCE), physical_source_run=SOURCE.name,
        physical_parent='v235', native_source='v232', locomotion='v216', display_parent='v220',
        analysis_metrics=str(HERE / 'results/metrics.json'), latency_csv=str(HERE / 'results/latency.csv'),
        parent_manifests={v: sha(BASE / 'versions' / v / 'manifest.json') for v in ('v219', 'v216', 'v232', 'v235')},
        input_files={str(p): sha(p) for p in inputs},
        claim='Partial recorded states only; original result/finish absent, no navigation goal or arrival. No physics or pose interpolation.')
    (ROOT / 'display_contract.json').write_text(json.dumps(contract, indent=2) + '\n')
    code = (BASE / 'versions/v220/render_capture.py').read_text()
    code = code.replace("data['source_files'].items()", "data.get('source_files',data.get('files')).items()")
    namespace = {'__file__': str(HERE / 'render_partial.py'), '__name__': 'v235_partial_causal_display'}
    exec(compile(code, str(HERE / 'render_partial.py'), 'exec'), namespace)
    original = namespace['adapt_renderer']
    def adapt(text, source, display):
        text = original(text, source, display)
        expression = 'json.loads((source / "result.json").read_text()).get("fallen", False)'
        assert text.count(expression) == 1
        text = text.replace(expression, 'False')
        return text.replace('            caption = (',
            '            status = "PARTIAL: sensor deadline exception; navigation goal not sent"\n            caption = (')
    namespace['adapt_renderer'] = adapt
    os.environ.update(NEWTON_RUN_DIR=str(OUT), V220_RENDER_ROOT=str(ROOT),
        V220_DISPLAY_CONTRACT=str(ROOT / 'display_contract.json'),
        WARP_CACHE_PATH=os.environ.get('V235_RENDER_CACHE', str(ROOT / 'cache')),
        PYOPENGL_PLATFORM='egl', PYGLET_HEADLESS='1', CUDA_VISIBLE_DEVICES='',
        OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
    sys.path.insert(0, str(BASE / 'versions/v220'))
    sys.argv = [str(HERE / 'render_partial.py')]
    spec = importlib.util.spec_from_file_location('v235_render_locomotion', BASE / 'versions/v216/activate.py')
    locomotion = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(locomotion)
    locomotion.install()
    # The original qualified display expects splines. This failed pre-goal
    # recording has none; retain the original empty-overlay frame behavior.
    observations = [json.loads(line) for line in (SOURCE / 'artifacts/reactive_observations.jsonl').read_text().splitlines() if line.strip()]
    assert not any(row['event'] in ('bspline', 'pct_route') for row in observations)
    overlay_path = BASE / 'versions/v220/curve_overlay.py'
    overlay_source = overlay_path.read_text()
    guard = "        if not self.total_splines:\n            raise ValueError('No native splines were recorded')"
    assert overlay_source.count(guard) == 1
    overlay_source = overlay_source.replace(guard, '        self.partial_recording_without_splines = not self.total_splines')
    (OUT / 'executed_partial_curve_overlay.py').write_text(overlay_source)
    overlay = types.ModuleType('curve_overlay')
    overlay.__file__ = str(overlay_path)
    exec(compile(overlay_source, str(OUT / 'executed_partial_curve_overlay.py'), 'exec'), overlay.__dict__)
    sys.modules['curve_overlay'] = overlay
    namespace['main']()
    from full_timeline import load_rows
    wanted = load_rows(SOURCE)
    frames = json.loads((OUT / 'frames.json').read_text())
    assert len(frames) == len(wanted)
    for frame, row in zip(frames, wanted):
        assert frame['source_state_index'] == row['source_state_index']
        assert frame['physics_time_s'] == row['physics_time_s']
    result = json.loads((OUT / 'result.json').read_text())
    assert result['render_only_no_physics_steps'] and result['integration_version'] == 'v235'
    assert not (SOURCE / 'result.json').exists()
    verification = json.loads((OUT / 'video_verification.json').read_text())
    assert verification['full_decode_passed']
    for path, expected in contract['input_files'].items():
        assert sha(Path(path)) == expected, path
    proof = dict(passed=True, render_root=str(ROOT), partial_recording=True, frames=len(frames), physics_end_s=frames[-1]['physics_time_s'],
        full_decode_passed=True, original_result_still_absent=True, goal_sent=False,
        render_only_no_physics_steps=True, video_sha256=sha(OUT / 'newton_stair_recorded.mp4'))
    (HERE / 'results/partial_video_verification.json').write_text(json.dumps(proof, indent=2) + '\n')
    shutil.copyfile(OUT / 'newton_stair_recorded.mp4', HERE / 'delivered/v235_partial_attempt01.mp4')
    print(json.dumps(proof), flush=True)


if __name__ == '__main__':
    main()
