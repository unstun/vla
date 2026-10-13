# v187: endpoint recovery exercised; full-route acceptance not met

Stage: experiment and analysis. Keep as a reviewed candidate; do not replace
the reference based on this cohort. No RL, stance, map or safety-gate changes.

Five original-start attempts on gpu5070ti:01/03/05 arrived,02/04 failed. All five
passed the predeclared terminal-crawl check; maximum actual-input interval was
1.579132s. The phase audit uses native curve timestamps minus observed yaw
pauses and exact command-value matching; it is not an exact controller-clock
replay. Actual model commands/history were verified across22,290 frames with
zero discrepancy and no gaps.

Attempt03 actually exercised the new branch: generation2, curve1334,
2.0224664cm remaining error,1.519165039s native correction time. The exact
`scan_terminal_correction_timeout` cancellation is recorded at62.537258148s;
the actual policy input first becomes zero at62.597225189s (59.967ms later).
A measured-stop proof precedes generation3, and this attempt reaches the
original final goal. The interval under the actual-input metric is1.579132s.
This is a real physical-run recovery exposure, not only a config or unit test.

Failed attempts02/04 had no timeout event or typed timeout cancellation. They
first stop for ordinary safety rejection/evidence expiry and then repeatedly
lack an admitted trajectory. Do not claim the new branch exclusively caused
those failures, or that the complete system is fixed.

Controls are separate cohorts: unchanged existing v177 binary, attempts06–10,
arrived5/5; unchanged-source v188 rebuild arrived3/5. All649 native source files
match v177 for that rebuild. Controller machine-code/data-relocation/dynamic
string sections are identical; read-only constants differ only in24 path bytes.
This establishes an unchanged-algorithm failing control, not the exclusive root
cause of variation. No statistical generalization is claimed from five trials.

Component checks:40 unique controller cases (43 colcon result entries), actual
plugin revoke/zero/PlannerException regression, original4.9246cm recovery
command regression,2 generated-profile cases,18 host tests, and loaded graph,
controller library and runtime parameter verification passed. Frozen source
integrity passes. Actual spatial starts for all25 current-round attempts are
verified; each failed attempt remains a failed route attempt.

Raw evidence:
`gpu5070ti:/data/sun/vla_mppi_20261009/trials/v187_full_candidate_attemptNN/`.
Local `results/full_repeats/.../remote_artifacts.json` records293 entries/run.
The detailed timeout chain is in
`audits/2026-10-13_v187_terminal_recovery/results/timeout_protocol03.json`.
Overall review: `audits/2026-10-13_terminal_repair_review/REPORT.zh.md`.
