"""Write the complete once-only offline result from locally returned evidence."""
from pathlib import Path
import hashlib
import json
import statistics

HERE=Path(__file__).resolve().parent
VERSION=HERE.parents[1]/'versions/v284'
load=lambda path:json.loads(path.read_text())
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()


def number(value):
    return '—' if value is None else f'{float(value):.6f}'


def main():
    summary=load(HERE/'offline/matrix_summary.json')
    gate=summary['gate'];rows=summary['calls']
    assert len(rows)==53 and gate['calls']==53
    manifest=load(VERSION/'native_manifest.json')
    complete=load(HERE/'offline/complete.json')
    assert complete['all_cases_finished'] and complete['native_manifest_sha256']==sha(VERSION/'native_manifest.json')
    legal=[r for r in rows if r['expected']=='admit']
    illegal=[r for r in rows if r['expected']=='reject']
    init=[r['metrics']['initialization_s'] for r in legal if 'initialization_s' in r['metrics']]
    original=load(HERE.parent/'2026-10-19_v283_navigation_geometry/offline/matrix_summary.json')
    old=original['gate']
    failed=[r for r in legal if not r['end_to_end_pass']]
    state='PASS' if gate['passed'] else 'FAIL'
    text=f'''# v284 complete 50+3 offline result

The once-only scored matrix and independent geometry audits are complete.
Strict frozen offline gate: **{state}**. Legal full-chain passes:
**{gate['positive_passed']}/50 ({100*gate['positive_passed']/50:.1f}%)**;
illegal controls correctly refused: **{gate['illegal_correct_rejections']}/3**.
Global admissions: {gate['global_admitted']}/50. Global median:
**{gate['global_median_s']:.6f} s**, excluding initialization, versus
{old['global_median_s']:.6f} s in v283. The requested approximately 1.3 s target and
the prewritten 1.5 s operational ceiling are evaluated separately from geometry.

## Fixed protocol and identity

- Native manifest SHA256: `{sha(VERSION/'native_manifest.json')}`.
- Source inventory: 329 composed files; 45 owned frozen source/metadata files and
  snapshots; 172 native tests in 20 suite executions. See the component receipt.
- Same v283 cohort/captured LiDAR/endpoints and all 50 start certificates, byte for
  byte. No planner-score resampling. G05 and CM02 retain the uniform v283 start
  replacements. See [all 50 start audit](../../audits/2026-10-19_v284_static_continuity/all50_start_audit.csv).
- Exact hard radius 0.35 m, cylinder offset 0.18 m, vertical profile unchanged;
  scanner period/deadline 0.1 s. Policy, factory PD and goal tolerances unchanged.
- 53 scored native calls completed before 53 independent audits. CPU quota 2 for
  native timing; shared host, no exclusive-machine claim. Initialization median
  {statistics.median(init):.6f}s is reported separately. No new physics here.
- Frozen evaluator executable inventory SHA256:
  `{manifest['evaluator_inventory_sha256']}`. Source/install/evaluator identity
  checks run before and after the matrix.

Full-chain offline pass means global route admission and one local trajectory
publication from captured stationary inputs, with independent checks. It does
not mean 50 complete physical missions. The separate ten-route Newton batch is
needed to assess actual movement, stalls, arrival, PD and measured geometry.

## Aggregate result

| Metric | v283 | v284 |
|---|---:|---:|
| Legal full-chain passes | {old['positive_passed']}/50 | {gate['positive_passed']}/50 |
| Illegal refusals | {old['illegal_correct_rejections']}/3 | {gate['illegal_correct_rejections']}/3 |
| Global admissions | {old['global_admitted']}/50 | {gate['global_admitted']}/50 |
| First GPMP pass / all legal | {old['first_gpmp_passed']}/50 | {gate['first_gpmp_passed']}/50 |
| First GPMP pass / admitted | {old['first_gpmp_passed']}/{old['global_admitted']} | {gate['first_gpmp_passed']}/{gate['global_admitted']} |
| Median global seconds | {old['global_median_s']:.6f} | {gate['global_median_s']:.6f} |
| p95 global seconds | {old['global_p95_s']:.6f} | {gate['global_p95_s']:.6f} |
| Maximum global seconds | {old['global_max_s']:.6f} | {gate['global_max_s']:.6f} |

Zero admitted negative source/raw margin: **{gate['zero_admitted_negative_raw_margin']}**.
Zero published negative source/raw margin or native support refusal:
**{gate['zero_published_negative_raw_margin']}**.
The fixed ten route identities are {', '.join(manifest['physical_cases'])}.
Their individual full-chain outcomes are retained in the table below.

## Failures retained

'''
    for row in failed:
        text+=f"- {row['case_id']}: global={row['global_admitted']}, local publication={row['scan_published']}; {row.get('scan_failure_reason') or row['metrics'].get('global_error') or 'see case summary/log'}.\n"
    text+='''
CD11's captured trace reaches optimization but fails refinement/dynamic admission
after retiming and the existing fixed-height recovery. It is not relabeled as a
source-field publication veto. CS01's native no-route remains a distinct failure.
Full per-case logs and independent source/raw witnesses remain in the offline
return; no failed formal call is retried.

The unchanged explicit endpoints themselves limit soft-margin improvement:
CD12's requested goal has only +0.005710 m source-solid margin, and CE03's
requested goal +0.019715 m. These values equal their global minima. A soft
cost cannot move fixed endpoints; no uniform 3–5 cm clearance is claimed over
entire paths including those exact goals. Actual arrival-window clearances are
left to the physical measurements, without moving goals or adding a new veto.

## All 53 cases

Margins below are extra metres beyond the unchanged 0.35 m profile; positive
values may saturate at +0.15 m. Missing local margins mean no local publication,
not a zero clearance. Source-triangle and raw-point evidence stay separate in
the machine-readable case summaries.

| Case | Expected | Global | First GPMP | Local | Full pass | Global source min m | Local source min m |
|---|---|---|---|---|---|---:|---:|
'''
    for row in rows:
        text+=f"| {row['case_id']} | {row['expected']} | {row['global_admitted']} | {row['first_gpmp_static_pass']} | {row['scan_published']} | {row['end_to_end_pass']} | {number(row.get('source_margin_min'))} | {number(row.get('local_source_margin_min'))} |\n"
    text+='''
## Evidence

The audit's `offline/` directory contains the original native/audit ledgers,
matrix summary/table, gate, completion certificate and every compact case result.
`results/component_review.json` and qualification logs retain parent/candidate
contrasts and all development failures. The four five-case development batches
are unscored pre-freeze checks; they are not additional formal 53-case matrices
or physical attempts. Heavy captured inputs/builds remain on gpu5070ti.

Source-wall repulsion is a soft bias, not an admission proof: strength 0.1,
extra range 0.07 m, source XY/yaw gradient at actual height and zero soft Z
derivative. SCAN integrates that term at map-resolution quadrature; its legacy
atlas and hard checks keep their original sampling. A safe published curve
does not prove that a dynamically displaced physical robot follows it safely.
'''
    (VERSION/'OFFLINE_RESULTS.md').write_text(text)
    print(json.dumps(dict(strict_offline_gate=state,positive_passed=gate['positive_passed'],median_global_s=gate['global_median_s'])))


if __name__=='__main__':
    main()
