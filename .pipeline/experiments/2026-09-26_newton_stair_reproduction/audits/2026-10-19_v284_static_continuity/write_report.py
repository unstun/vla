"""Publish the verified single-attempt results without promoting acceptance."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
VERSION = HERE.parents[1] / 'versions/v284'
load = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def value(number, digits=3):
    return '—' if number is None else f'{number:.{digits}f}'


def main():
    summary = load(HERE / 'physical_summary.json')
    rows = summary['cases']
    gate = load(HERE / 'offline/offline_gate.json')
    review = load(VERSION / 'execution_review.json')
    freeze = load(VERSION / 'manifest.json')
    inventory = load(HERE / 'physical_return/return_inventory.json')
    bill = load(HERE / 'results/failure_terminal_bill.json')
    assert summary['formal_attempts'] == len(rows) == len(inventory['videos']) == 10
    assert summary['attempts_per_case'] == freeze['authorized_attempts_per_case'] == 1
    assert not gate['passed'] and review['offline_evaluation']['non_timing_passed']
    assert summary['native_manifest_sha256'] == sha(VERSION / 'native_manifest.json')
    assert summary['execution_manifest_sha256'] == sha(VERSION / 'manifest.json')
    assert all(r['physics_steps'] > 0 for r in bill['cases'])
    old = {r['case_id']: load(HERE / 'results/reference_v283' / r['case_id'] /
                            'command_continuity.json') for r in rows}
    long_holds = sum(r['pauses_ge_60s_after_first_translation'] for r in rows)
    endpoint_lines = sum(len(r['endpoint_rejection_log_lines']) for r in rows)
    physical_outcome = 'UNMET' if summary['goal_pd_and_physical_envelope_clear'] < 10 else 'Review detailed continuity criteria below'
    text = f'''# v284 complete physical execution report

The frozen candidate completed all 53 scored offline requests and the same ten
once-only Newton physical simulation attempts. No physical retry was used.
Goal plus terminal PD: **{summary['goal_and_pd_passed']}/10**. Goal/PD plus
nonnegative sampled physical support-gap and source/raw solid margins:
**{summary['goal_pd_and_physical_envelope_clear']}/10**. The stricter retained
static all-Free screen passes {summary['goal_pd_and_measured_geometry_clear']}/10.
Requested physical outcome: **{physical_outcome}**.

Benchmark acceptance remains **FAIL**: the native global median is
**{gate['global_median_s']:.6f} s**, above the requested approximately 1.3 s and
the original 1.5 s gate. Dr Sun explicitly replied “继续十条，耗时记未达标”.
The separate execution review allowed these ten attempts after every non-timing
criterion passed; the benchmark gate and original selection were not rewritten.

## Main physical finding

The global endpoint/no-route rejection is absent, while all seven failed
recorded prefixes remain measured support/source/raw-clear and terminate with
`Native SCAN has no executable trajectory before timeout`. S04 and CS03 still
cross the solid boundary after the latest curve's nominal expiry. Their first
negative samples have zero applied commands and measured movement in
STAND_SETTLING; S04 reaches its deepest excursion after RL resumes.
Soft wall repulsion does not close that execution gap. See the
[confirmed observations](OBSERVATIONS.md) for exact witnesses and inference limits.

## What changed

- A static mission retains its first admitted global reference. The cache only
  permits trimming a passed prefix; it does not replace the remaining geometry. Same-goal BT status refreshes, transient moving height/yaw
  and local feedback witnesses do not replace that reference. A new goal or
  explicit halt releases it; initial global hard admission remains unchanged.
- SCAN no longer applies v283's source-field publication veto or its forced
  measured-state warm reset. Live map, support and freshness checks remain.
  The narrow local WrongHeight handling uses the existing selected floor and
  physical support coverage; it does not waive SupportGap or move obstacles.
- Nonterminal tracking couples translation and yaw while advancing curve phase.
  Final heading alignment requires the original XY/Z terminal capture region.
- GPMP and SCAN share source-wall soft repulsion over the 0.35–0.42 m radial
  band. Cost is `0.1 * max(0,(0.07-extra_margin)/0.07)^2`, with source XY/yaw
  gradients at actual height and zero soft Z derivative. This is a soft bias,
  not a 0.42 m hard boundary or guaranteed dynamic clearance.

The fixed CD12 and CE03 goals have only +5.710 mm and +19.715 mm static
source-solid margin, respectively. Their exact goals and headings are retained;
soft repulsion cannot guarantee a 3–5 cm margin at an endpoint it cannot move.
The physical table reports the actual achieved arrival-window margins.

Exact 0.35 m hard radius, 0.18 m cylinder offset, vertical profile, 0.1 s scan
period/deadline, locomotion policy, factory PD, goal tolerances and episode
limits are unchanged. Production code has no route-name or coordinate branches.

## Qualification and the complete offline cohort

The parent/candidate tracking probe changes from 0/4 to 4/4 coupled travel
controls. The actual BT same-goal regression plans once across 100 status and
timestamp refreshes, then replans on a new goal or explicit halt. Native checks
pass 172 tests in 20 suite executions, including translated/rotated soft-band
controls, finite differences, 200 cached/full source comparisons, support and
the recorded A04 WrongHeight case. Development failures remain in the logs.

The scored cohort is exactly the frozen v283 50+3, with its captured LiDAR,
headings, goals and three illegal controls. All 50 legal start certificates were
checked; every start has at least 0.10 m static support and source-solid extra
margin. Eight uniform v283 replacements, including G05 and CM02, are retained.
No native scored request or physical attempt was repeated to improve a result.

Offline legal full-chain passes: **{gate['positive_passed']}/50 (96%)**;
global admissions {gate['global_admitted']}/50; illegal refusals
{gate['illegal_correct_rejections']}/3. First GPMP: {gate['first_gpmp_passed']}/50,
or {gate['first_gpmp_passed']}/{gate['global_admitted']} admitted. All admitted
global and published local source/raw margins are nonnegative; all ten selected
cases pass the full offline chain. CD11 local refinement and CS01 global
no-route failures remain. Timing uses CPU quota 2, excludes initialization,
and does not claim an exclusive host. The complete timing table is in the
[offline report](../../versions/v284/OFFLINE_RESULTS.md).

## Ten actual outcomes

| Route | Recorded terminal | Goal + PD | Physical envelope clear | Duration s | Final XY / height error m | Full video |
|---|---|---|---|---:|---:|---|
'''
    for r in rows:
        text += (f"| {r['case_id']} | {r['terminal']} | {r['goal_and_pd_passed']} | "
                 f"{r['measured_physical_envelope_clear']} | {value(r['simulation_duration_s'])} | "
                 f"{value(r['final_xy_error_m'])} / {value(r['final_height_error_m'])} | "
                 f"[MP4]({r['video_file']}) |\n")
    text += '''
## Measured geometry

All margins are extra metres beyond the unchanged profile; +0.15 m is a cap.
Navigation windows start at the real goal request and end at first observed
arrival, or the final preterminal observation on failure. They include initial
planning waits and in-place movement; factory startup and final PD are separate.
The source, independent original raw points, hard physical SupportGap and ENV
soft atlas are separate channels. WrongHeight is retained in static verdict
counts and is not relabeled as a collision or a physical support gap.

| Route | Physical support gap min m | Source solid min m | Raw point min m | Static verdict counts | ENV soft edge min m |
|---|---:|---:|---:|---|---:|
'''
    for r in rows:
        text += (f"| {r['case_id']} | {value(r['physical_gap_min_m'],6)} | "
                 f"{value(r['source_solid_min_m'],6)} | {value(r['raw_point_min_m'],6)} | "
                 f"{json.dumps(r['hard_support_verdict_counts'],sort_keys=True)} | "
                 f"{value(r['ENV_edge_min_m'],6)} |\n")
    text += f'''
These are 10 Hz measured body-pose samples, not continuous-time or foot-contact
certificates. Negative samples remain failures even if the driver reports
arrival. The original static all-Free criterion is retained separately from
physical-envelope clearance, so transient WrongHeight cannot silently disappear.

## Continuity and stops

Recorded global-reference geometry remains the original curve or a suffix on
{summary['cases_with_original_global_geometry']}/10 routes. Exact route-message
epochs, pose-sequence hashes and suffix checks are retained in every
`command_continuity.json`; this uses actual published paths, not just unit tests.

Mid-route low-speed intervals of at least 60 s after the first translation:
**{long_holds}**. Endpoint rejection log lines: **{endpoint_lines}**. Applied
pure-yaw is defined as XY command norm <=0.01 m/s and absolute yaw >0.1 rad/s,
outside the original goal capture region. It is measured from applied telemetry,
not only tracker targets. Sample endpoint durations carry one-sample uncertainty.

| Route | v283 max pause after motion s | v284 max pause after motion s | >=60 s holds | Max nonterminal pure-yaw s | Nonterminal STAND_SETTLING samples | Local success/completed |
|---|---:|---:|---:|---:|---:|---:|
'''
    for r in rows:
        text += (f"| {r['case_id']} | {value(old[r['case_id']]['maximum_low_speed_pause_after_first_translation_s'])} | "
                 f"{value(r['maximum_pause_after_first_translation_s'])} | {r['pauses_ge_60s_after_first_translation']} | "
                 f"{value(r['maximum_nonterminal_pure_yaw_s'])} | {r['nonterminal_stand_settling_samples']} | "
                 f"{r['local_successes']}/{r['local_completed']} |\n")
    text += '''
Low-speed durations include permitted final heading alignment before the
first arrived observation; the separate pure-yaw metric excludes terminal capture.
The v283 comparison reuses its unchanged recordings under exactly the new pause
and applied-command definitions; it adds zero physics. STAND_SETTLING counts,
planning-round success and measured pause duration are different quantities.

## Scanner and execution integrity

| Route | Scan jobs | Deadline failures | Maximum scan ms | Native process failure |
|---|---:|---:|---:|---|
'''
    for r in rows:
        text += (f"| {r['case_id']} | {r['scanner_jobs']} | {r['scanner_deadline_failures']} | "
                 f"{value(r['maximum_scan_ms'])} | {r['native_process_failure']} |\n")
    text += f'''
Totals: {summary['scanner_jobs']} scan jobs, {summary['scanner_deadline_failures']}
deadline failures, {summary['native_process_failures']} native process failures.
The scanner period remains 0.1 s on every attempt.

One A04 zero-step resource preflight was rejected before any physical launch
while an unrelated GPU evaluation occupied the host. Its qualification01 and
graph/deadline logs are retained. Qualification02 continued waiting, then was stopped before physics after the
user authorized sharing based on remaining resources. Qualification03 uses
>=16 GiB available RAM and >=10 GiB output space, records GPU occupancy without
a CPU-execution veto, and completed the ten preflights. This is separate from any actual attempt.
The first continuation monitor also stopped on a transient read of an updating
JSON status file, before any physics. Its receipt/log and original source are
retained; the revised continuation handles that read race. Continuation03 owns the
approved shared-resource execution; earlier waiting processes were stopped
without changing other GPU jobs. Native frozen code is unchanged.
The five earlier v283 disk-gate startup failures remain preserved with their
original correction receipt and hashes; they are not v284 physical attempts.

## Failures and limits

Every terminal error and recovered planner error is retained in the
[terminal bill](results/failure_terminal_bill.json). Full-route completion,
terminal PD, sampled geometry, command continuity and timing are reported
independently. One attempt per route does not establish statistical reliability.
Overall benchmark acceptance remains failed because timing is unmet; no baseline
promotion or source commit is implied by finishing the execution protocol.

## Provenance and delivery

- Native manifest: `{sha(VERSION/'native_manifest.json')}`.
- Execution manifest: `{sha(VERSION/'manifest.json')}`.
- Execution review: `{sha(VERSION/'execution_review.json')}`.
- Return inventory: [all compact files and ten real MP4 hashes](physical_return/return_inventory.json).
- Machine-readable outcomes: [summary](physical_summary.json), [table](physical_table.csv).
- All 50 starts: [certificate verification](results/all50_start_verification.json).
- Raw Newton captures stay on gpu5070ti at `/home/sun/vla_exec/physical_runs_v284`.
- Local review videos are regular MP4 files, never symlinks. Every file has full
  decode, state-coverage, exact hash and zero-render-physics proof. Rendering uses
  the same generic close-body FOV 95 camera on all normal full recordings.
- Recreate media from retained recorded states; never rerun physics to repair
  a video. Source/configuration, compact evidence and review videos return here.
'''
    text += """
## Recorded curve witness review

This query-only reconstruction uses the actual latest published curve at selected
stop/clearance witnesses, with its nominal elapsed phase. It is not exact internal
tracker scheduling, a replayed mission or a causal ablation. Whole-curve source
queries use 10 ms nominal samples and the original 0.8 s heading lookahead.
Expired curves are explicitly counted; degenerate endpoint headings use the
measured yaw and carry no heading-accuracy claim; their endpoint discrepancy does not
prove that a controller was executing that curve. Static support query counts
include WrongHeight, distinct from physical support gaps.

| Route | Witnesses | Max nominal position discrepancy m | Expired witnesses | Selected curve source min m | Static support refused queries |
|---|---:|---:|---:|---:|---:|
"""
    for r in rows:
        diagnostic=load(HERE/'physical_return'/r['case_id']/'results/recorded_curve_diagnosis.json')
        targets=diagnostic['targets']
        planned=[p for t in targets for p in t['poses'] if p['role']=='planned_at_nominal_phase']
        minima=[t['curve_source_solid_min_m'] for t in targets if t['curve_source_solid_min_m'] is not None]
        text+=(f"| {r['case_id']} | {len(targets)} | "
               f"{value(max((p['nominal_position_error_m'] for p in planned),default=None))} | "
               f"{sum(p['curve_expired_at_query'] for p in planned)} | "
               f"{value(min(minima,default=None),6)} | {sum(t['curve_support_rejections'] for t in targets)} |\n")
    text += """
Every selected pose, applied command, stance mode, curve identity and native
verdict is retained in each route's `results/recorded_curve_diagnosis.json`.
Query inputs/full query margins remain remote with a compact hash inventory;
the local script regenerates them from the unchanged recordings with zero physics.
These witnesses narrow remaining failures but do not establish a new fix.
"""
    (HERE / 'RESULTS.md').write_text(text)
    (VERSION / 'RESULTS.md').write_text(f'''# v284 result

The full 50+3 cohort and ten once-only Newton physical attempts are complete.
Offline: 48/50 legal and 3/3 illegal, with nonnegative admitted/published
source/raw margins. Global median {gate['global_median_s']:.6f} s: timing unmet.
The explicit user timing exception allowed execution without changing acceptance.

Goal plus PD: {summary['goal_and_pd_passed']}/10. Goal/PD plus sampled physical
support-gap and source/raw envelope clearance:
{summary['goal_pd_and_physical_envelope_clear']}/10. Static all-Free plus goal/PD:
{summary['goal_pd_and_measured_geometry_clear']}/10. Mid-route >=60 s low-speed
holds: {long_holds}. Scanner deadline failures: {summary['scanner_deadline_failures']}.

See the [complete report](../../audits/2026-10-19_v284_static_continuity/RESULTS.md)
for every route, retained failure, strict verdict, comparison and full video.
Exact 0.35 m and 0.1 s are unchanged. No baseline promotion is claimed.
''')
    print(json.dumps(dict(report=str(HERE/'RESULTS.md'),goal_pd=summary['goal_and_pd_passed'],
        goal_pd_physical_clear=summary['goal_pd_and_physical_envelope_clear'],
        long_holds=long_holds,strict_offline_gate=gate['passed'])))


if __name__ == '__main__':
    main()
