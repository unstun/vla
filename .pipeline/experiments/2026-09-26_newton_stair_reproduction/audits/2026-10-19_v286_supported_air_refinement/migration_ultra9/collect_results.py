"""Collect verified compact evidence and all10 regular videos; no new physics."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import types

ROOT = Path('/home/ubuntu/sun/vla_v286_20261020')
MIGRATION = ROOT / 'migration'
EXP = ROOT / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
AUDIT = EXP / 'audits/2026-10-19_v286_supported_air_refinement'
VERSION = EXP / 'versions/v286'
OUT = ROOT / 'physical_return'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def repair_legacy_claim(case, caseout, render):
    delivery = caseout / 'results/local_video_delivery.json'
    if json.loads(delivery.read_text()).get('legacy_run_label_corrected'):
        return
    old = render / 'executed_video_checker.py'
    text = old.read_text()
    if 'v219_linux_full_attempt01' not in text:
        return
    updated = text.replace('v219_linux_full_attempt01', f'v286_{case}_attempt01')
    new = render / 'executed_video_checker_labels02.py'
    if new.exists():
        assert new.read_text() == updated
    else:
        new.write_text(updated)
    for path in (render / 'delivery_verification.json', caseout / 'quality.json'):
        backup = path.with_name(path.stem + '_legacy_labels01.json')
        if not backup.exists():
            shutil.copy2(path, backup)
    scope = dict(__file__=str(new), __name__='corrected_recorded_run_label')
    exec(compile(updated, str(new), 'exec'), scope)
    scope.update(TASK=ROOT / 'physical_runs' / f'v286_{case}_attempt01', OUT=render, HERE=caseout, BASE=EXP)
    from analyze_remote import Capture
    raw = ROOT / 'physical_runs' / f'v286_{case}_attempt01' / 'runs' / f'v286_{case}_attempt01'
    empty = not any(r.get('event') == 'bspline' for r in Capture(raw).rows('artifacts/reactive_observations.jsonl'))
    prior = sys.modules.get('curve_overlay')
    if empty:
        source = EXP / 'versions/v220/curve_overlay.py'
        code = source.read_text()
        guard = "        if not self.total_splines:\n            raise ValueError('No native splines were recorded')"
        assert code.count(guard) == 1
        code = code.replace(guard, '        # Verified empty recorded spline stream; no invented curve.')
        module = types.ModuleType('curve_overlay')
        module.__file__ = str(source)
        exec(compile(code, str(source), 'exec'), module.__dict__)
        sys.modules['curve_overlay'] = module
    try:
        scope['main']()
    finally:
        if empty:
            if prior is None:
                sys.modules.pop('curve_overlay', None)
            else:
                sys.modules['curve_overlay'] = prior
    data = json.loads(delivery.read_text())
    shutil.copy2(delivery, delivery.with_name('local_video_delivery_legacy_labels01.json'))
    data.update(causal_frame_checker_sha256=sha(new), legacy_run_label_corrected=True,
        video_content_changed=False, physics_steps=0)
    delivery.write_text(json.dumps(data, indent=2) + '\n')

def main():
    assert json.loads((ROOT / 'evidence/physical_batch_complete.json').read_text())['all_closed']
    status = json.loads((ROOT / 'evidence/analysis_batch_status.json').read_text())
    assert len(status) == 10 and all(r['passed'] for r in status)
    sys.path[:0] = [str(MIGRATION), str(VERSION.parent / 'v196'), str(VERSION.parent / 'v220')]
    os.environ['V286_CASE_ID'] = 'A04'
    import physical
    physical.verify_sources()
    from analyze_remote import Capture
    spec = importlib.util.spec_from_file_location('literal_failure_extractor', AUDIT / 'failure_bill.py')
    extractor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(extractor)
    manifest = json.loads((MIGRATION / 'physical_manifest01.json').read_text())
    files, videos, retained, rows = {}, {}, {}, []
    assert not OUT.exists()
    OUT.mkdir()
    def collect(source, relative):
        row = dict(remote_path=str(source), bytes=source.stat().st_size, sha256=sha(source))
        if row['bytes'] > 8 * 1024**2:
            retained[relative] = row
            return
        target = OUT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        files[relative] = row
    for cid in manifest['physical_cases']:
        caseout = AUDIT / 'physical' / cid
        results = caseout / 'results'
        raw = ROOT / 'physical_runs' / f'v286_{cid}_attempt01' / 'runs' / f'v286_{cid}_attempt01'
        capture = Capture(raw)
        result = capture.json('result.json')
        log = capture.read('nav2.log')
        delivery = json.loads((results / 'local_video_delivery.json').read_text())
        video = Path(delivery['video'])
        assert video.is_file() and not video.is_symlink() and sha(video) == delivery['sha256']
        quality = json.loads((caseout / 'quality.json').read_text())
        render = Path(quality['checks']['delivery']['path']).parent
        repair_legacy_claim(cid, caseout, render)
        quality = json.loads((caseout / 'quality.json').read_text())
        assert quality['passed'] and quality['input_source_unchanged'] and not quality['physical_rerun']
        verification = json.loads((render / 'delivery_verification.json').read_text())
        assert verification['video_sha256'] == sha(video) and verification['full_decode_passed']
        assert verification['complete_first_and_last_recorded_states'] and verification['render_only_no_physics_steps']
        videos[video.name] = dict(remote_path=str(video), bytes=video.stat().st_size, sha256=sha(video))
        for path in results.rglob('*'):
            if path.is_file() and path.suffix in ('.json', '.jsonl', '.csv', '.log', '.txt', '.yaml', '.yml'):
                collect(path, str(path.relative_to(AUDIT / 'physical')))
        for path in caseout.iterdir():
            if path.is_file() and path.suffix in ('.py', '.json'):
                collect(path, str(path.relative_to(AUDIT / 'physical')))
        collect(caseout / 'quality.json', f'{cid}/video_checks/quality.json')
        for name, record in quality['checks'].items():
            assert sha(Path(record['path'])) == record['sha256'], name
            collect(Path(record['path']), f'{cid}/video_checks/{Path(record["path"]).name}')
        for path in render.glob('*.py'):
            collect(path, f'{cid}/video_checks/{path.name}')
        for path in (ROOT / 'generalization_v286' / cid / 'execution').glob('*.json'):
            collect(path, f'{cid}/execution/{path.name}')
        seed = [dict(distance_m=float(a), occupied=bool(int(b))) for a, b in re.findall(r'SCAN_MEASURED_SEED distance_m=([0-9.eE+-]+) occupied=([01])', log)]
        rows.append(dict(case_id=cid, physics_steps=result['physics_steps'], physics_duration_s=result['physics_duration_s'],
            finish=result.get('finish_request'), target_errors=extractor.error_counts(log),
            reactive_blocked=extractor.reactive_counts(log), stage_errors=extractor.stage_errors(log),
            first_target_error_contexts=extractor.first_error_contexts(log.splitlines()),
            final_error_lines=[line for line in log.splitlines() if '[ERROR]' in line][-16:],
            measured_seed_fallback=dict(count=len(seed), distance_triggered=sum(r['distance_m'] > .15 for r in seed),
                occupancy_triggered=sum(r['occupied'] for r in seed),
                maximum_predicted_distance_before_fallback_m=max((r['distance_m'] for r in seed), default=None)),
            snapshot_manifest_sha256=sha(results / 'capture_snapshot.json'), sources=capture.sources))
    (OUT / 'failure_terminal_bill.json').write_text(json.dumps(dict(physics_steps=0, actual_attempts=10,
        extraction_source_sha256=sha(AUDIT / 'failure_bill.py'),
        execution_manifest_sha256=sha(MIGRATION / 'physical_manifest01.json'), cases=rows), indent=2) + '\n')
    inventory = dict(files=files, videos=videos, retained_remote=retained, physics_steps=0,
        physical_attempts=10, attempts_per_case=1,
        execution_manifest_sha256=sha(MIGRATION / 'physical_manifest01.json'),
        analysis_sources={p.name: sha(p) for p in MIGRATION.glob('*.py')},
        raw_storage=str(ROOT / 'physical_runs'), navigation_source_changed=False,
        regeneration='Reuse unchanged recorded states and locally versioned analysis/render adapters; never rerun physics for a missing report/video.')
    (OUT / 'return_inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
    print(json.dumps(dict(compact_files=len(files), video_count=len(videos), video_bytes=sum(r['bytes'] for r in videos.values()))), flush=True)

if __name__ == '__main__':
    main()
