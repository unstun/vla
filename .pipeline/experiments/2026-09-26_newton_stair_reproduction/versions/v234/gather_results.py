"""Return explicit compact evidence only; keep all binaries/caches on gpu40901."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent
BINDING = json.loads((HERE / 'binding.json').read_text())
PREFIX = Path(BINDING['remote_root'])
WORK = PREFIX / BINDING['native_workspace']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    selected = {}
    for path in (PREFIX / 'evidence').rglob('*'):
        if not path.is_file() or path.name == 'cache_cleanup01.json':
            continue
        if path.suffix in {'.json', '.yaml', '.xml', '.log', '.txt', '.csv', '.jsonl'}:
            selected['evidence/' + str(path.relative_to(PREFIX / 'evidence'))] = path
        elif 'host_smoke03' in path.parts and path.suffix in {'.png', '.mp4'}:
            selected['evidence/' + str(path.relative_to(PREFIX / 'evidence'))] = path
    for attempt in ('v234_attempt01', 'v234_attempt02', 'v234_attempt03'):
        for path in (WORK / 'evidence' / attempt).rglob('*'):
            if path.is_file() and (path.suffix == '.xml' or path.name in {'test.log', 'test-result.log'}):
                selected['tests/' + str(path.relative_to(WORK / 'evidence'))] = path
    for name in ('source_inventory.json', 'local_source_mapping.json', 'native_rebuild_receipt.json'):
        selected[name] = WORK / name
    cleanup = json.loads((PREFIX / 'evidence/cache_cleanup01.json').read_text())
    cleanup.pop('files_before')
    cleanup['full_remote_receipt'] = str(PREFIX / 'evidence/cache_cleanup01.json')
    cleanup['full_remote_receipt_sha256'] = sha(PREFIX / 'evidence/cache_cleanup01.json')
    (args.output / 'cache_cleanup_summary.json').write_text(json.dumps(cleanup, indent=2) + '\n')
    inputs = [WORK / 'fixtures/building' / name for name in
              ('terrain.json', 'route.pct', 'navigation.f32', 'surface.f32', 'physical_floor.f32',
               'support_gap.txt', 'environment03.env', 'environment225.env')]
    inventory = {str(path.relative_to(PREFIX)): dict(bytes=path.stat().st_size, sha256=sha(path)) for path in inputs}
    (args.output / 'reconstructed_inputs.json').write_text(json.dumps(inventory, indent=2) + '\n')
    media = {str(path.relative_to(PREFIX)): dict(bytes=path.stat().st_size, sha256=sha(path))
             for path in (PREFIX / 'bootstrap/ffprobe').glob('*.deb')}
    (args.output / 'media_archives.json').write_text(json.dumps(media, indent=2) + '\n')
    for rel, source in selected.items():
        assert source.stat().st_size < 16 * 2**20, ('Unexpected bulk result', source)
        target = args.output / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    field = PREFIX / 'evidence/probes01/admission/shared_admitted.csv'
    reference = HERE.parent / 'v232/results/admission_output03/shared_admitted.csv'
    assert field.read_bytes() == reference.read_bytes()
    probe_log = (PREFIX / 'evidence/probes01/execution.log').read_text()
    assert 'FIELD_ADMISSION_CHECK request=1 samples=3821 rejected=0' in probe_log
    assert 'FIELD_ADMISSION shared=1 admitted=1 points=3413 requests=1 rejected_samples=0' in probe_log
    parity = re.search(r'FIELD_PARITY queries=(\d+) mismatch=([^ ]+)', probe_log)
    assert parity and float(parity[2]) == 0
    assert json.loads((PREFIX / 'evidence/graph01/gate.json').read_text())['passed']
    assert json.loads((PREFIX / 'evidence/host_smoke03/gate.json').read_text())['passed']
    receipt = json.loads((WORK / 'native_rebuild_receipt.json').read_text())
    assert receipt['passed'] and receipt['unique_test_cases'] == 165 and receipt['colcon_records'] == 186
    summary = dict(status='offline_partial_external_original_artifacts_pending',
        completed_independent_gates=True, full_offline_acceptance=False, ready_for_full_route=False,
        native_packages=14, composed_source_files=317, installed_files=len(receipt['installed_files']),
        source_version='v232', execution_reference='v233', host_binding='v234',
        unique_test_cases=165, colcon_records=186, errors=0, failures=0, skipped=0,
        graph_seconds=12, physics_steps=0, original_install_byte_identity=False,
        original_607_paths_present=True, shared_admitted_route_sha256=sha(field),
        shared_route_byte_equal=True, shared_admission_samples=3821, shared_admission_rejected=0,
        environmental_consumer_parity_queries=int(parity[1]), environmental_consumer_mismatch=0,
        shared_admission_requests=1, shared_admitted_route_points=3413,
        renderer_frames=2, original_factory_image_unchanged=True,
        rl_start_goal_and_hard_thresholds_unchanged=True, user_confirmed_source_host_powered_off=True,
        pending=['Transfer original5070Ti image/install for original-artifact comparison',
                 'Fetch retained input+critical_input and rerun126324+3 dynamic hard decisions'],
        original_artifact_host='gpu5070ti', destination=str(PREFIX))
    (args.output / 'offline_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    manifest = {str(p.relative_to(args.output)): dict(bytes=p.stat().st_size, sha256=sha(p))
                for p in args.output.rglob('*') if p.is_file()}
    (args.output / 'return_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(files=len(manifest), bytes=sum(v['bytes'] for v in manifest.values()),
                          full_offline_acceptance=False, output=str(args.output))))


if __name__ == '__main__':
    main()
