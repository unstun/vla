# G2 proposal — flat-ground V12 primitives

2026-10-23, after Phase A. **Pending Dr Sun's explicit yes.** This is a budget/scope proposal;
no primitive harness has been executed and no Phase B source freeze is claimed.

## Requested host and budget

- Host: ultra9, existing private CPU Newton worker environment. No real robot or Building route.
- Required matrix: 31 cells ×3 fresh starts = **93 runs**. No optional v291-assistance arm (+12 runs).
- Per-run bound: **120 simulated seconds including startup**. Expected total wall time **1–3 hours**;
  hard campaign wall budget **4 hours**. Worst-case simulation exposure 11,160 s =3.1 hours.
- Every started run and failure counts; no replacements. If the cap stops the campaign, retain remaining
  cells as unrun. A development preflight must import/inspect without stepping physics. No extra
  positive-physics smoke outside the 93 slots.
- The earlier suggested 40-run cap cannot cover the mandatory three repeats. This proposal retains the
  required matrix rather than silently dropping cells or repeats.

## Fixed scope

| Family | Cells | Repeats | Runs |
|---|---:|---:|---:|
| Forward 0.05/0.10/0.15/0.20/0.25/0.30/0.40 m/s | 7 | 3 | 21 |
| Backward −0.10/−0.20 m/s | 2 | 3 | 6 |
| Lateral ±0.10/±0.20 m/s | 4 | 3 | 12 |
| Pure yaw ±0.3/±0.6/±1.0 rad/s, standing and walking entry | 12 | 3 | 36 |
| Stop after 0.4/0.2/0.1 m/s and +1.0 rad/s yaw | 4 | 3 | 12 |
| Rotate 90° /180°, then approach 0.3 m at qualified speed and stop | 2 | 3 | 6 |
| Total | 31 | 3 | 93 |

Use the PRD's `FlatSceneRobot` scripted-command harness, original factory startup and hash-pinned v216
stance in auto mode; assistance off. Default flat-scene Warp CPU path preserves the prescribed parent
physics family; any backend change needs an explicit documented choice before the source freeze.
Verify actual loaded policy/stance modules and runtime inputs in zero-step preflight.

Before scored execution, freeze the entire slot list, stage order, command durations, all metric rules,
source hashes, actual runtime module hashes and bounded output roots in Phase B PLAN.md/frozen.json.
Low-speed cells and yaw/stop cells precede rotate-approach cells. The rule selecting the latter's speed
must be frozen in advance; no candidate direction/speed is filled from hindsight. If no tested speed
qualifies, dependent slots are blocked/unrun and reported. Do not substitute a different speed.

The existing backward/lateral grid stops at 0.2 m/s. If these directions do not qualify, report their
usable floor as unestablished; do not apply a forward-only floor to them. Any added speeds require a
separate scope decision. C must use the measured directional envelope, not extrapolated capability.

## Outputs and preservation

Proposed remote root: `/home/ubuntu/sun/vla_v12_primitives_20261023/`; refuse an existing scored slot.
Keep raw ~50 Hz telemetry, every failure and per-run host-load/admission receipts there. Local return:
frozen source/config/hashes, compact cell metrics, qualification rows, figures and REPORT.md. No weights,
videos or full logs committed. Record actual storage bytes after the source/schema preflight.

Derived outputs: executable `v_floor` by supported direction, `wz_turn`, measured worst drift plus a
stated margin, and stop distance by tested entry speed. Keep the PRD's 0.8 tracking criterion in every
repeat. Stop and report before C if no realistic clearance supports the observed turn drift.
G3 remains separate; no paired Building evaluation is included.
