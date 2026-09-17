#!/usr/bin/env python3
"""Write report/index.html (design.md section 5, the HTML page) from report/report_data.json.

Verdicts, tables, facts and figure-caption numbers come from report_data.json, which make_report.py builds from
returned files. The "Episode 3" and "Disclosed changes" sections are the lead's prose; their numbers were checked
against RESULT.md and isaac_series/e03_failure_analysis.md. Figures and videos are referenced by relative path, so the
page is published together with report/figures/ and report/videos/.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = HERE / 'report'

STATUS_LABEL = {'pass': 'pass', 'fail': 'fail', 'pending': 'lead', 'mismatch': 'mismatch'}
AC_TITLE = {
    'AC0': 'Validity control', 'AC1': 'One-line build', 'AC2': 'Gate rejections removed',
    'AC3': 'Single-call endpoint', 'AC4': 'Occupancy grid', 'AC5': 'Seeds and random init',
    'AC6': 'Follow-up replans', 'AC7': 'Isaac episodes', 'AC8': 'Claim boundary',
}


def figures(panels):
    grid = panels['3_pass_fail_grid']
    counts = grid['counts']
    n_cells = len(grid['starts']) * len(grid['inits'])

    def accepted(m, b):
        return counts[m][b].get('accepted', 0) + counts[m][b].get('accepted_with_collision', 0)

    gate_only = all(set(counts[m]['candidate']) == {'accepted'} and set(counts[m]['original']) <= {'accepted', 'acceleration_gate'}
                    for m in counts if m != 'near_box')
    grid_text = (f'Every native first call: {len(grid["starts"])} starts × {len(grid["inits"])} initializations per map, '
                 'each cell split original / fixed. ')
    if gate_only:
        grid_text += 'On the empty and far-box maps the fix changes only acceleration-gate rejections. '
    if 'near_box' in counts:
        grid_text += (f'On the near-box map it accepts {accepted("near_box", "candidate")} of {n_cells} cases '
                      f'(original {accepted("near_box", "original")}); '
                      f'{counts["near_box"]["candidate"].get("accepted_with_collision", 0)} of its accepted first calls '
                      f'have a collision sample (original {counts["near_box"]["original"].get("accepted_with_collision", 0)}).')
    ends = panels['4_endpoint_distance']
    single = ends['single_call']
    follow = ends['follow_up_report_only']

    def cm(value):
        return f'{100 * value:.1f}'

    def follow_max(build):
        return max(v['max'] for v in follow[build].values() if v.get('n'))

    end_text = (f'Single calls are judged against {ends["limit_m"]:.2f} m: fixed calls end '
                f'{cm(single["candidate"]["min"])}–{cm(single["candidate"]["max"])} cm from the target, original '
                f'{cm(single["original"]["min"])}–{cm(single["original"]["max"])} cm. Follow-up calls are reported only '
                f'(PRD D10); they end up to {cm(follow_max("original"))} cm (original) and '
                f'{cm(follow_max("candidate"))} cm (fixed) from the target.')
    done = panels['6_follow_up_replans']['completed']
    return [
        ('panel3_pass_fail_grid.png', 'Pass/fail grid', grid_text),
        ('panel4_endpoint_distance.png', 'Endpoint distance', end_text),
        ('panel5_top_down_paths.png', 'Top-down paths',
         'The failing resume case, the near-box case and one follow-up sequence, with target and inflated box.'),
        ('panel6_follow_up_replans.png', 'Follow-up replans',
         f'Maximum acceleration per call in each replan sequence. Original: {done["original"]} of {done["total"]} '
         f'sequences complete; fixed: {done["candidate"]} of {done["total"]}.'),
    ]


def esc(value):
    return html.escape(str(value), quote=True)


def fmt(value, digits=3):
    return '–' if value is None else f'{value:.{digits}f}'


def signed(value, digits=2):
    return fmt(value, digits).replace('-', '−')


def failure_text(episodes):
    failed = [e for e in episodes if e['checks_passed'] != e['checks_total']]
    if not failed:
        return 'no episode failed a check'
    parts = []
    for ep in failed:
        names = [c[len(ep['run_id']) + 1:] if c.startswith(ep['run_id'] + '-') else c for c in ep['failed_checks']]
        parts.append(f'e{ep["episode"]:02d} failed {len(names)} check{"s" if len(names) != 1 else ""} '
                     f'({", ".join(names)})')
    return '; '.join(parts)


def verdict_rows(verdicts):
    rows = []
    for item in verdicts:
        status = item['status']
        label = STATUS_LABEL.get(status, status)
        evidence = item['evidence'] or ''
        if item['id'] == 'AC8':
            label = 'stated'
            evidence = 'RESULT.md states the boundary (lead judgement, awaiting review): ' + evidence.split(';')[0]
        rows.append(
            f'<tr><th scope="row"><span class="ac">{esc(item["id"])}</span> {esc(AC_TITLE.get(item["id"], ""))}</th>'
            f'<td><span class="pill pill-{esc(label)}">{esc(label)}</span></td><td>{esc(evidence)}</td></tr>')
    return '\n'.join(rows)


def native_cell(verdict):
    if not isinstance(verdict, dict):
        return '<span class="muted">pending</span>'
    cells = []
    for key in ('original (scan_03)', 'fixed (scan_04)'):
        text = verdict.get(key, 'missing')
        # Green only when every repeat returned a plan ("accepted n/n" and nothing else).
        cls = 'ok' if text.startswith('accepted ') and ',' not in text else 'bad'
        cells.append(f'<span class="{cls}">{esc(text.replace("acceleration_gate", "gate-rejected"))}</span>')
    return ' / '.join(cells)


def episode_rows(episodes):
    rows = []
    for ep in episodes:
        n = ep['episode']
        failed = ep['checks_passed'] != ep['checks_total']
        rows.append(
            f'<tr class="{"row-fail" if failed else ""}" data-ep="{n}">'
            f'<td><button type="button" class="ep-link" data-ep="{n}">e{n:02d}</button></td>'
            f'<td>{fmt(ep["trigger_m"], 2)}</td><td>{fmt(ep["stop_x_m"], 4)}</td>'
            f'<td>{esc(str(ep["stop_vs_original_failure_band"]).replace("_", " "))}</td>'
            f'<td>{native_cell(ep.get("native_verdict_at_stop"))}</td>'
            f'<td><span class="pill pill-{"fail" if failed else "pass"}">{ep["checks_passed"]}/{ep["checks_total"]}</span></td>'
            f'<td>{fmt(ep["arrival_xy_error_a_m"])}</td><td>{fmt(ep["arrival_xy_error_b_m"])}</td>'
            f'<td>{fmt(ep["max_nonfoot_force_n"], 1)}</td><td>{fmt(ep["episode_wall_s"], 1)}</td>'
            f'<td>{"–" if ep["gpu_peak_mib"] is None else format(ep["gpu_peak_mib"], ",.0f")}</td></tr>')
    return '\n'.join(rows)


def episode_js(episodes):
    data = {}
    for ep in episodes:
        n = ep['episode']
        data[n] = {
            'video': ep['walk_video'],
            'timeline': f'figures/panel9_timeline_e{n:02d}.png',
            'run': ep['run_id'],
            'summary': (f'Trigger {fmt(ep["trigger_m"], 2)} m · resume x {fmt(ep["stop_x_m"], 4)} m · '
                        f'{ep["checks_passed"]}/{ep["checks_total"]} checks · arrival A {fmt(ep["arrival_xy_error_a_m"])} m, '
                        f'B {fmt(ep["arrival_xy_error_b_m"])} m'),
            'failed': ep['failed_checks'],
        }
    return json.dumps(data)


def build(data, data_sha):
    panels = data['panels']
    series = data['isaac_series']
    episodes = panels['7_episode_table']
    passed, counted = series['passed_episodes'], series['counted_episodes']
    bound = series.get('success_lower_bound')
    facts = {e['episode']: (e.get('facts') or {}) for e in data.get('episodes', [])}

    def native(ep, build_label):
        verdict = ep.get('native_verdict_at_stop')
        return verdict.get(build_label, '') if isinstance(verdict, dict) else ''

    rejected = [e for e in episodes if 'gate' in native(e, 'original (scan_03)')]
    resumed = sum(1 for e in rejected if native(e, 'fixed (scan_04)').startswith('accepted ')
                  and ',' not in native(e, 'fixed (scan_04)') and facts.get(e['episode'], {}).get('resume_plan_ok'))
    failed = [e for e in episodes if e['checks_passed'] != e['checks_total']]
    checks = max((e['checks_total'] for e in episodes if e['checks_total']), default=0)
    verdicts = {v['id']: v['status'] for v in panels['1_verdicts']}
    native_ok = all(verdicts.get('AC%d' % i) == 'pass' for i in range(7))
    ac7_ok = verdicts.get('AC7') == 'pass'
    bug = panels['2_where_the_bug_bites']
    segments = bug['failure_band']['segments']
    band_lo = min((s['first_rejected_x'] for s in segments), default=None)
    band_hi = max((s['last_rejected_x'] for s in segments), default=None)
    fixed_acc = [p['builds']['candidate']['max_acc'] for p in bug['points']
                 if p['builds'].get('candidate', {}).get('max_acc') is not None]
    places = [e['stop_vs_original_failure_band'] for e in episodes]
    old_failed = [r for r in data.get('sep16_runs', []) if not r.get('review_passed') and r.get('still_pose_xyz')]
    old_inside = sum(1 for r in old_failed if band_lo is not None and band_lo <= r['still_pose_xyz'][0] <= band_hi)
    gaps = [((f['still_pose_xyz'][0] - f['resume_plan_start_xyz'][0]) ** 2
             + (f['still_pose_xyz'][1] - f['resume_plan_start_xyz'][1]) ** 2) ** 0.5
            for f in facts.values() if f.get('still_pose_xyz') and f.get('resume_plan_start_xyz')]
    grid = panels['3_pass_fail_grid']
    sequences = panels['6_follow_up_replans']['completed']['total']
    singles = len(grid['starts']) * len(grid['inits']) * len(grid['maps'])
    if failed and all(c.endswith('raw_physics_stop_dwell') for e in failed for c in e['failed_checks']):
        lede_failure = (f'{"the one failure" if len(failed) == 1 else "the failures"} came from the robot not '
                        'standing still after arriving, not from the planner.')
    elif failed:
        lede_failure = 'failures: ' + failure_text(failed) + '.'
    else:
        lede_failure = 'no episode failed a check.'
    replay_id = (data.get('stop_replay') or {}).get('run_id', 'native replay')
    suite_id = data['native_suite'].get('run_id', 'native suite')
    figure_blocks = '\n'.join(
        f'<figure class="plate"><img src="figures/{esc(f)}" alt="{esc(t)}" loading="lazy">'
        f'<figcaption><strong>{esc(t)}.</strong> {esc(c)}</figcaption></figure>' for f, t, c in figures(panels))
    return TEMPLATE.format(
        passed=passed, counted=counted, bound=fmt(bound), rejected_at=len(rejected), resumed=resumed,
        checks=checks, lede_failure=esc(lede_failure),
        native_class='ok' if native_ok else 'bad',
        native_text='native suite: pass, including the validity control' if native_ok else 'native suite: see the verdict table',
        ac7_class='ok' if ac7_ok else 'bad',
        ac7_text=esc(('met: ' if ac7_ok else 'not met as written: ') + failure_text(episodes)),
        band_lo=signed(band_lo), band_hi=signed(band_hi),
        fixed_acc_lo=fmt(min(fixed_acc, default=None), 2), fixed_acc_hi=fmt(max(fixed_acc, default=None), 2),
        old_failed=len(old_failed), old_inside=old_inside, n_eps=len(episodes),
        new_inside=places.count('inside'), new_edge=places.count('edge'), new_beyond=len(places) - places.count('inside') - places.count('edge'),
        failed_marks=esc(', '.join(f'e{e["episode"]:02d}' for e in failed) or 'none'),
        resume_gap_mm=fmt(1000 * max(gaps, default=0.0), 1),
        per_build=singles + sequences, n_starts=len(grid['starts']), n_inits=len(grid['inits']),
        n_maps=len(grid['maps']), n_sequences=sequences,
        start_ep=failed[0]['episode'] if failed else (episodes[0]['episode'] if episodes else 0),
        verdict_rows=verdict_rows(panels['1_verdicts']),
        episode_rows=episode_rows(episodes), episode_js=episode_js(episodes),
        figure_blocks=figure_blocks, replay_id=esc(replay_id), suite_id=esc(suite_id),
        generated=esc(data.get('generated_utc', '')), data_sha=esc(data_sha[:12]),
    )


TEMPLATE = r'''<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SCAN Fix Qualification</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;650;750&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {{
  --ground: #eef1f0; --surface: #ffffff; --ink: #14201c; --muted: #56655f; --rule: #cfd8d4;
  --fixed: #0072b2; --orig: #c75200; --ok: #1b7a4a; --bad: #b3261e; --lead: #8a5a00;
  --ok-bg: #dcefe4; --bad-bg: #f7dedb; --lead-bg: #f4e8cf; --band: #fbeee3;
  --display: "Archivo", "Helvetica Neue", Arial, sans-serif;
  --body: "Source Serif 4", Georgia, "Times New Roman", serif;
  --mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --ground: #0f1614; --surface: #17211e; --ink: #e3ebe7; --muted: #9aaba4; --rule: #2c3a35;
    --fixed: #5aaee0; --orig: #f08a3c; --ok: #6cc796; --bad: #f08a80; --lead: #e0b460;
    --ok-bg: #1d3a2b; --bad-bg: #452523; --lead-bg: #3d3220; --band: #2d241c;
  }}
}}
:root[data-theme="dark"] {{
  --ground: #0f1614; --surface: #17211e; --ink: #e3ebe7; --muted: #9aaba4; --rule: #2c3a35;
  --fixed: #5aaee0; --orig: #f08a3c; --ok: #6cc796; --bad: #f08a80; --lead: #e0b460;
  --ok-bg: #1d3a2b; --bad-bg: #452523; --lead-bg: #3d3220; --band: #2d241c;
}}
body {{ background: var(--ground); color: var(--ink); font: 400 17px/1.6 var(--body); }}
.wrap {{ max-width: 1120px; margin: 0 auto; padding-inline: 20px; padding-block: 32px 64px; }}
h1, h2, h3 {{ font-family: var(--display); line-height: 1.15; text-wrap: balance; margin: 0; }}
h1 {{ font-size: clamp(30px, 5vw, 44px); font-weight: 750; letter-spacing: -0.01em; }}
h2 {{ font-size: 24px; font-weight: 650; margin-top: 56px; padding-top: 14px; border-top: 2px solid var(--ink); }}
h3 {{ font-size: 17px; font-weight: 650; }}
p {{ max-width: 68ch; margin: 10px 0; }}
.eyebrow {{ font: 500 12px/1.4 var(--mono); letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }}
.muted {{ color: var(--muted); }}
code, .mono {{ font-family: var(--mono); font-size: 0.86em; }}
header {{ display: grid; gap: 14px; }}
.lede {{ font-size: 19px; max-width: 62ch; }}
.facts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 1px; background: var(--rule);
  border: 1px solid var(--rule); margin-top: 22px; }}
.fact {{ background: var(--surface); padding: 14px 16px; display: grid; gap: 4px; align-content: start; }}
.fact b {{ font: 650 30px/1.1 var(--display); font-variant-numeric: tabular-nums; }}
.fact span {{ font-size: 14px; color: var(--muted); line-height: 1.4; }}
.fact.bad b {{ color: var(--bad); }} .fact.ok b {{ color: var(--ok); }}
.boundary {{ margin-top: 22px; border-left: 4px solid var(--lead); background: var(--surface); padding: 12px 16px; font-size: 15px; }}
.boundary p {{ margin: 4px 0; max-width: none; }}
.scroll {{ overflow-x: auto; margin-top: 14px; border: 1px solid var(--rule); background: var(--surface); }}
table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--rule); vertical-align: top; }}
thead th {{ font: 500 11px/1.3 var(--mono); letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); white-space: nowrap; }}
tbody th {{ font-weight: 600; white-space: nowrap; }}
.num td {{ font-family: var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap; font-size: 13px; }}
.ac {{ font-family: var(--mono); color: var(--muted); }}
.pill {{ display: inline-block; font: 500 12px/1 var(--mono); padding: 4px 8px; border-radius: 3px; white-space: nowrap; }}
.pill-pass {{ background: var(--ok-bg); color: var(--ok); }}
.pill-fail, .pill-mismatch {{ background: var(--bad-bg); color: var(--bad); }}
.pill-lead, .pill-stated {{ background: var(--lead-bg); color: var(--lead); }}
.ok {{ color: var(--ok); }} .bad {{ color: var(--bad); }}
tr.row-fail td {{ background: color-mix(in srgb, var(--bad-bg) 45%, transparent); }}
tr.is-current td {{ box-shadow: inset 0 -2px 0 var(--fixed); }}
.ep-link {{ font: 500 13px var(--mono); color: var(--fixed); background: none; border: 1px solid var(--rule); border-radius: 3px; padding: 3px 7px; cursor: pointer; }}
.ep-link:hover, .ep-link:focus-visible {{ border-color: var(--fixed); outline: none; }}
.plate {{ margin: 18px 0 0; background: #ffffff; border: 1px solid var(--rule); padding: 10px; }}
.plate img {{ display: block; width: 100%; height: auto; }}
figcaption {{ font-size: 14px; color: #3d4a45; padding: 10px 4px 2px; max-width: 80ch; }}
.viewer {{ display: grid; gap: 14px; margin-top: 16px; }}
.picker {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.picker button {{ font: 500 13px var(--mono); padding: 7px 11px; border: 1px solid var(--rule); background: var(--surface); color: var(--ink); border-radius: 3px; cursor: pointer; }}
.picker button[aria-pressed="true"] {{ background: var(--ink); color: var(--ground); border-color: var(--ink); }}
.picker button.failed {{ border-color: var(--bad); }}
.picker button:focus-visible {{ outline: 2px solid var(--fixed); outline-offset: 2px; }}
video {{ width: 100%; max-width: 100%; aspect-ratio: 16 / 9; background: #0b0f0e; display: block; }}
.ep-summary {{ font: 400 14px/1.5 var(--mono); }}
.ep-note {{ font-size: 15px; border-left: 3px solid var(--bad); padding-left: 12px; }}
.two {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 18px 28px; align-items: start; }}
ul.plain {{ padding-left: 18px; margin: 8px 0; max-width: 72ch; }}
ul.plain li {{ margin: 6px 0; }}
footer {{ margin-top: 56px; font-size: 13px; color: var(--muted); border-top: 1px solid var(--rule); padding-top: 12px; }}
@media (prefers-reduced-motion: reduce) {{ * {{ scroll-behavior: auto !important; }} }}
</style>

<div class="wrap">
<header>
  <div class="eyebrow">Lite3 VLA · task 09-16 · PCT → SCAN → V12 · 5070 Ti host · 2026-09-17</div>
  <h1>SCAN terminal-acceleration fix</h1>
  <p class="lede">A one-line change in SCAN's planner (<code>planner_manager.cpp:171</code>,
  <code>evaluateAcc(t)</code> → <code>evaluateAcc(time)</code>) removes the replan rejection that stopped the robot
  after a cancel. The native suite passes every criterion. In Isaac, {passed} of {counted} episodes passed all checks;
  {lede_failure}</p>
  <div class="facts">
    <div class="fact"><b>{passed}/{counted}</b><span>Isaac episodes passed all {checks} checks (one-sided 95 % lower bound {bound})</span></div>
    <div class="fact"><b>{rejected_at}/{counted}</b><span>episodes stopped where the original build rejects the resume plan (native replay); {resumed} of them resumed with the fix</span></div>
    <div class="fact {native_class}"><b>AC0–AC6</b><span>{native_text}</span></div>
    <div class="fact {ac7_class}"><b>AC7</b><span>{ac7_text}</span></div>
  </div>
  <div class="boundary">
    <p><strong>Claim boundary.</strong> Simulation only: Isaac Lab and native replays on the 5070 Ti host. One known-map
    route on a flat platform, with no placed obstacle and simulator-truth pose. N = {counted} episodes. No physical-robot,
    SLAM, language-navigation or Pi/Cortex claim. The fix was not checked against an unmodified official build.
    <strong>Adopting <code>scan_04</code> is Dr Sun's decision.</strong></p>
  </div>
</header>

<h2>Verdicts</h2>
<p class="muted">Computed from the returned files and compared with the task's acceptance criteria. AC8 is the lead's judgement.</p>
<div class="scroll"><table>
<thead><tr><th>Criterion</th><th>Status</th><th>Evidence</th></tr></thead>
<tbody>
{verdict_rows}
</tbody></table></div>

<h2>Where the bug bites</h2>
<p>The top chart shows the planned path's maximum acceleration against the resume start position. The original build
(orange) is rejected by the 1.5 m/s² gate for every start between x = {band_lo} and {band_hi} m (shaded). The fixed
build (blue) peaks at {fixed_acc_lo}–{fixed_acc_hi} m/s² at every resume start. Diamonds are native replays of the real
Isaac stops. The lower strip marks where each Isaac run stopped: {old_inside} of the {old_failed} failed Sep 16 runs
stopped inside the band; of the {n_eps} Sep 17 episodes, {new_inside} stopped inside it, {new_edge} at its edge and
{new_beyond} beyond it. Failed Sep 17 marks ({failed_marks}) failed for a different reason (see below).</p>
<figure class="plate"><img src="figures/panel2_where_the_bug_bites.png" alt="Plan acceleration against resume start x for both builds, with the failure band and Isaac stop positions">
<figcaption>Native suite <code>{suite_id}</code>, empty map, polynomial init, seed 0; stop replay <code>{replay_id}</code>.</figcaption></figure>

<h2>Isaac episodes</h2>
<p>Each episode: walk toward goal A, cancel after the trigger distance, wait for a confirmed stop, resubmit A, arrive,
then go to B. The resume x is the still-confirmed pose; each resubmitted plan started within {resume_gap_mm} mm of it.
The native column shows what each build does with a plan from that recorded plan start.</p>
<div class="scroll"><table class="num">
<thead><tr><th>Ep</th><th>Trigger (m)</th><th>Resume x (m)</th><th>vs band</th><th>Native at this pose: original / fixed</th><th>Checks</th><th>Arrival A (m)</th><th>Arrival B (m)</th><th>Non-foot force (N)</th><th>Wall (s)</th><th>GPU peak (MiB)</th></tr></thead>
<tbody>
{episode_rows}
</tbody></table></div>

<div class="viewer" id="viewer">
  <h3>Walk review and timeline</h3>
  <div class="picker" id="picker" role="group" aria-label="Choose an episode"></div>
  <div class="ep-summary" id="ep-summary"></div>
  <div class="ep-note" id="ep-note" hidden></div>
  <div class="two">
    <video id="ep-video" controls preload="metadata" playsinline></video>
    <div>
      <p class="muted" style="margin-top:0">The video is the runner's third-person camera beside the top-down trail and a speed/command strip,
      synchronized by simulation time (12.5 fps; one second of video is one second of simulated time, not wall time).
      The chart below is the same episode's timeline with the review's full-rate still windows.</p>
    </div>
  </div>
  <figure class="plate" style="margin-top:0"><img id="ep-timeline" alt="Episode timeline: speed, command and non-foot force over simulation time"></figure>
</div>

<h2>Episode 3: why one check failed</h2>
<div class="two">
<div>
<p>At goal B the review needs 1.00 s of continuous stillness in the full 0.02 s physics record. One sample at
sim 14.30 s had a yaw rate of 0.1595 rad/s (limit 0.15). The window before the arrival report was therefore 0.88 s.
The backend's own dwell check polls a single overwritten snapshot file and never read that sample, so it reported
arrival.</p>
<p>The runs used the intended V12 <code>model_149999.pt</code> (sha256 <code>a9d31dce…</code>). After a stop the runner
keeps the RL policy running on a zero command and has no PD stance hold. As Dr Sun notes, an RL policy almost never
stands perfectly still, and switching smoothly to a PD hold is hard. The failure sits in the locomotion stop, after
SCAN; resubmission and arrival at A worked. It is counted as a failure, and no threshold was changed.</p>
</div>
<ul class="plain">
<li>Not a planner rejection, collision, reset or contact.</li>
<li>Integrity checks passed: SCAN hash gate before and after, returned hashes.</li>
<li>The series continued under the stop rule (no repeated failure).</li>
<li>A PD stance hold is locomotion-layer work, outside this task.</li>
</ul>
</div>

<h2>Robot paths</h2>
<p>All {n_eps} Sep 17 paths from the simulator's base position, with the Sep 16 runs in grey. The zoom shows the cancel
points, the braking overshoot and the confirmed stops relative to the failure band.</p>
<figure class="plate"><img src="figures/panel8_isaac_top_down.png" alt="Top-down robot paths of all episodes with goals and stop points" loading="lazy"></figure>

<h2>Native suite detail</h2>
<p>{per_build} planner runs per build: {n_starts} start poses × {n_inits} initializations × {n_maps} maps, plus
{n_sequences} follow-up sequences, in the pinned Foxy image on the 5070 Ti host's CPU.</p>
{figure_blocks}

<h2>Disclosed changes to the plan</h2>
<ul class="plain">
<li><strong>AC0</strong>: validity control added before any result; stricter only.</li>
<li><strong>D8, D10</strong>: AC3/AC4 amended after a local preview; follow-up endpoints reported, not judged.</li>
<li><strong>D9</strong>: two bulky files stay on the 5070 Ti; the hash check accepts them as absent only when their recorded hashes match.</li>
<li><strong>D11</strong>: run all 8 episodes; stop early only on the same failure twice in a row, an integrity failure, or a reset, pose-injection or contact-guard failure.</li>
<li><strong>D12</strong>: 6 episodes cancel at 0.40 m, 1 at 0.45 m, 1 at 0.50 m.</li>
<li><strong>D13</strong>: the 1.5 m/s² gate stays; raising it to 2.0 was considered and rejected.</li>
</ul>

<footer>
Generated by <code>make_report_page.py</code> from <code>report_data.json</code> ({data_sha}…, {generated}).
Full record: <code>scan_fix_qualification/RESULT.md</code>. Findings and failure analysis:
<code>isaac_series/e03_failure_analysis.md</code>.
</footer>
</div>

<script>
(function () {{
  var EPISODES = {episode_js};
  var picker = document.getElementById('picker');
  var video = document.getElementById('ep-video');
  var timeline = document.getElementById('ep-timeline');
  var summary = document.getElementById('ep-summary');
  var note = document.getElementById('ep-note');
  var keys = Object.keys(EPISODES).map(Number).sort(function (a, b) {{ return a - b; }});
  function pad(n) {{ return (n < 10 ? '0' : '') + n; }}
  function show(n, scroll) {{
    var ep = EPISODES[n];
    if (!ep) return;
    video.src = ep.video;
    timeline.src = ep.timeline;
    summary.textContent = 'e' + pad(n) + ' · ' + ep.summary;
    if (ep.failed.length) {{ note.hidden = false; note.textContent = 'Failed check: ' + ep.failed.join(', '); }}
    else {{ note.hidden = true; note.textContent = ''; }}
    picker.querySelectorAll('button').forEach(function (b) {{ b.setAttribute('aria-pressed', String(Number(b.dataset.ep) === n)); }});
    document.querySelectorAll('tr[data-ep]').forEach(function (r) {{ r.classList.toggle('is-current', Number(r.dataset.ep) === n); }});
    try {{ localStorage.setItem('scanfix-ep', String(n)); }} catch (e) {{}}
    if (scroll) document.getElementById('viewer').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  }}
  keys.forEach(function (n) {{
    var b = document.createElement('button');
    b.type = 'button'; b.dataset.ep = n; b.id = 'pick-e' + pad(n);
    b.textContent = 'e' + pad(n);
    if (EPISODES[n].failed.length) b.classList.add('failed');
    b.addEventListener('click', function () {{ show(n, false); }});
    picker.appendChild(b);
  }});
  document.querySelectorAll('.ep-link').forEach(function (b) {{
    b.addEventListener('click', function () {{ show(Number(b.dataset.ep), true); }});
  }});
  var start = {start_ep};
  try {{ var saved = Number(localStorage.getItem('scanfix-ep')); if (EPISODES[saved]) start = saved; }} catch (e) {{}}
  show(EPISODES[start] ? start : keys[0], false);
}})();
</script>
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=REPORT / 'report_data.json')
    parser.add_argument('--output', type=Path, default=REPORT / 'index.html')
    args = parser.parse_args()
    raw = args.data.read_bytes()
    data = json.loads(raw)
    args.output.write_text(build(data, hashlib.sha256(raw).hexdigest()), encoding='utf-8')
    print(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
