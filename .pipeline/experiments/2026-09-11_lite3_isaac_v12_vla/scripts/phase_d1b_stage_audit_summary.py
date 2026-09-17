#!/usr/bin/env python3
"""Phase D.1b gate for one stage-audit run: the frozen thresholds applied to the run record and the host GPU samples.

    python3 scripts/phase_d1b_stage_audit_summary.py --run-dir runs/RUN_ID \
        --thresholds phase_d/stage_audit_thresholds_d1b.json [--out analysis/phase_d1b_stage_audit_summary.json]

Runs on the host (Python 3.10, no numpy) and locally. Writes RUN_DIR/summary.json (and --out if given).
Exit 0 when the scene is admitted to D.1c, 1 when a check fails, 2 when the run record is incomplete, does not match
the frozen thresholds, or cannot be read (a crash of this script is exit 2, never a gate verdict).

GPU peak: the per-second host samples list every compute process as pid:MiB:container12. This run's memory is the sum
over processes of this run's container (runs/RUN_ID/container_id12.txt) per sample; the peak is the maximum of that.
The samples must cover the audit from its first to its last mark with no gap over MAX_SAMPLE_GAP_S, otherwise the
peak is not trusted (exit 2).
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys
import traceback

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'phase_d'))
import stage_audit_lib as lib  # noqa: E402

FROZEN_THRESHOLDS_SHA256 = '227d54ac4bad306e00bafa581f798c4ea4243ef160c69f1409479f2b25660466'
MAX_SAMPLE_GAP_S = 5.0
LOG_PATTERNS = {
    'error_lines': r'\[Error\]',
    'warning_lines': r'\[Warning\]',
    'collision_api_unknown_gprim': r'CollisionAPI applied to an unknown',
    'mdl_messages': r'(?i)\bmdl\b.*(error|fail|could not|cannot|not found)',
    'nested_rigid_body': r'(?i)nested rigid bod|xformstack|resetxformstack|rigid body.*(parent|ancestor)',
    'triangle_mesh_dynamic': r'(?i)triangle mesh.*(dynamic|not supported)|(dynamic|not supported).*triangle mesh',
    'unresolved': r'(?i)unresolved|could not open asset|failed to resolve',
    'out_of_memory': r'(?i)out of memory|CUDA_ERROR_OUT_OF_MEMORY|VK_ERROR_OUT_OF_DEVICE_MEMORY',
    'semantics_deprecated': r'(?i)semanticsapi.*deprecat|deprecat.*semantics',
}


def parse_samples(samples_path, own_cid, vendor_cids):
    rows = []
    if not samples_path.exists():
        return rows
    for line in samples_path.read_text().splitlines()[1:]:
        parts = line.split(',', 3)
        if len(parts) < 4 or not parts[1].strip():
            continue
        try:
            unix_s, device = float(parts[0]), int(parts[1])
        except ValueError:
            continue
        own = vendor = other = 0
        entries = [e for e in parts[3].split(';') if e]
        for entry in entries:
            fields = entry.split(':')
            if len(fields) != 3 or not fields[1].isdigit():
                continue
            mem, cid = int(fields[1]), fields[2]
            if own_cid and cid == own_cid:
                own += mem
            elif cid in vendor_cids:
                vendor += mem
            else:
                other += mem
        rows.append((unix_s, device, own, vendor, other, bool(entries)))
    return rows


def gpu_summary(rows, marks):
    out = {'samples': len(rows), 'isaac_peak_mib': None, 'coverage_ok': False}
    if not rows:
        out['coverage_problem'] = 'no samples'
        return out
    own_rows = [r for r in rows if r[2] > 0]
    out.update({
        'samples_with_own_process': len(own_rows),
        'isaac_peak_mib': max(r[2] for r in rows) if own_rows else None,
        'isaac_peak_unix_s': max(own_rows, key=lambda r: r[2])[0] if own_rows else None,
        'device_peak_mib': max(r[1] for r in rows),
        'vendor_mib_min_max': [min(r[3] for r in rows), max(r[3] for r in rows)],
        'unattributed_mib_max': max(r[4] for r in rows),
        'samples_without_process_list': sum(1 for r in rows if not r[5]),
    })
    stamps = [m['unix_s'] for m in marks if isinstance(m.get('unix_s'), (int, float))]
    if not stamps:
        out['coverage_problem'] = 'run has no timed marks'
        return out
    first, last = min(stamps), max(stamps)
    # The sampler starts before docker run and stops after it exits, so it must bracket every mark, and no gap
    # between consecutive samples that overlaps the audit window may exceed MAX_SAMPLE_GAP_S.
    times = sorted(r[0] for r in rows)
    gaps = [b - a for a, b in zip(times, times[1:]) if b >= first and a <= last]
    problems = []
    if times[0] > first:
        problems.append('no sample before the first mark (first sample {:.1f} s after it)'.format(times[0] - first))
    if times[-1] < last:
        problems.append('no sample after the last mark (sampler stopped {:.1f} s before it)'.format(last - times[-1]))
    if gaps and max(gaps) > MAX_SAMPLE_GAP_S:
        problems.append('largest sample gap in the audit window {:.1f} s'.format(max(gaps)))
    out.update({'marks_window_unix_s': [first, last], 'max_gap_s': round(max(gaps), 2) if gaps else None,
                'coverage_ok': not problems})
    if problems:
        out['coverage_problem'] = '; '.join(problems)
    return out


def summarise(run, thresholds_path, out_path):
    frozen_bytes = thresholds_path.read_bytes()
    thr = json.loads(frozen_bytes)
    summary = {'run': run.name, 'thresholds_sha256': hashlib.sha256(frozen_bytes).hexdigest(), 'problems': []}
    if summary['thresholds_sha256'] != FROZEN_THRESHOLDS_SHA256:
        summary['problems'].append('thresholds file {} is not the frozen {}'.format(
            summary['thresholds_sha256'], FROZEN_THRESHOLDS_SHA256))

    result_path, marker = run / 'audit' / 'stage_audit_result.json', run / 'audit' / 'STAGE_AUDIT_COMPLETE'
    result = json.loads(result_path.read_text()) if result_path.exists() else {}
    if not result:
        summary['problems'].append('no stage_audit_result.json')
    if result and result.get('thresholds_sha256') != summary['thresholds_sha256']:
        summary['problems'].append('run used thresholds {} not the frozen {}'.format(
            result.get('thresholds_sha256'), summary['thresholds_sha256']))
    if not marker.exists():
        summary['problems'].append('STAGE_AUDIT_COMPLETE missing' + ('; error recorded' if result.get('error') else ''))
    elif marker.read_text().strip() != hashlib.sha256(result_path.read_bytes()).hexdigest():
        summary['problems'].append('STAGE_AUDIT_COMPLETE does not match the result file')
    if result.get('error'):
        summary['error_tail'] = result['error'].strip().splitlines()[-6:]
    if result.get('static_errors') or result.get('section_errors'):
        summary['section_errors'] = {k: v.strip().splitlines()[-1] for k, v in
                                     dict(result.get('static_errors') or {}, **(result.get('section_errors') or {})).items()}

    cid_file = run / 'container_id12.txt'
    own_cid = cid_file.read_text().strip() if cid_file.exists() else ''
    if not re.fullmatch(r'[0-9a-f]{12}', own_cid):
        summary['problems'].append('no container id for this run ({!r}); its GPU memory cannot be attributed'.format(own_cid))
    vendor_cids = set()
    before = (run / 'compute_apps_before.txt').read_text() if (run / 'compute_apps_before.txt').exists() else ''
    for entry in filter(None, before.strip().split(';')):
        fields = entry.split(':')
        if len(fields) == 3 and fields[2] != '-':
            vendor_cids.add(fields[2])
    gpu = gpu_summary(parse_samples(run / 'samples.csv', own_cid, vendor_cids), result.get('marks', []))
    gpu['own_container_id12'], gpu['vendor_container_id12s'] = own_cid, sorted(vendor_cids)
    if not gpu['coverage_ok']:
        summary['problems'].append('GPU samples do not cover the audit: ' + gpu.get('coverage_problem', '?'))
    summary['gpu'] = gpu
    summary['gate'] = lib.evaluate(result, thr, isaac_peak_mib=gpu.get('isaac_peak_mib') if gpu['coverage_ok'] else None)

    log = (run / 'sim.log').read_text(errors='replace') if (run / 'sim.log').exists() else ''
    scan = {}
    for key, pattern in LOG_PATTERNS.items():
        hits = [line.strip()[:300] for line in log.splitlines() if re.search(pattern, line)]
        scan[key] = {'count': len(hits), 'first': hits[:5]}
    summary['log_scan'] = scan

    st = result.get('static') or {}
    summary['facts'] = {
        'objects': len(st.get('objects', [])), 'group_counts': st.get('group_counts'),
        'excluded_children': len(st.get('excluded_children') or []),
        'layers': (st.get('dependencies') or {}).get('layers'), 'assets': (st.get('dependencies') or {}).get('assets'),
        'reset_s': (result.get('kit_stage') or {}).get('reset_s'),
        'objects_match_static': (result.get('kit_stage') or {}).get('objects_match_static'),
        'marks': [{k: m.get(k) for k in ('mark', 't_s', 'device_used_mib')} for m in result.get('marks', [])],
        'docker_exit_code': (run / 'exit_code').read_text().strip() if (run / 'exit_code').exists() else None,
        'container_killed_by_driver': (run / 'CONTAINER_KILLED_BY_DRIVER').exists(),
        'killed_after_record': (run / 'KILLED_AFTER_RECORD').exists(),
    }
    text = json.dumps(summary, indent=1, default=str) + '\n'
    (run / 'summary.json').write_text(text)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text)
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-dir', type=pathlib.Path, required=True)
    ap.add_argument('--thresholds', type=pathlib.Path, required=True)
    ap.add_argument('--out', type=pathlib.Path)
    args = ap.parse_args(argv)
    try:
        summary = summarise(args.run_dir, args.thresholds, args.out)
    except Exception:  # noqa: BLE001 - a crash here is never a gate verdict
        print('SUMMARY_CRASHED\n' + traceback.format_exc())
        return 2
    for c in summary['gate']['checks']:
        print('{:9s} {}'.format(c['verdict'], c['check']))
    gpu = summary['gpu']
    print('gpu: isaac peak {} MiB, device peak {} MiB, vendor {} MiB, coverage_ok={}; log errors {}'.format(
        gpu.get('isaac_peak_mib'), gpu.get('device_peak_mib'), gpu.get('vendor_mib_min_max'), gpu.get('coverage_ok'),
        summary['log_scan']['error_lines']['count']))
    for p in summary['problems']:
        print('PROBLEM', p)
    print('ADMIT_TO_D1C={} failed={}'.format(summary['gate']['admit_to_d1c'], summary['gate']['failed']))
    if summary['problems']:
        return 2
    return 0 if summary['gate']['admit_to_d1c'] else 1


if __name__ == '__main__':
    sys.exit(main())
