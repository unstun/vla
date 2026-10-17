# v206 terminal timeout: recorded-input diagnosis

Stage: experiment + analysis. Scope: diagnosis only. No runtime source,
navigation policy, controller parameter, or frozen version was changed. No
new physical simulation was run. The decision analysis ran on gpu5070ti;
only the compact evidence plot was rendered locally.

## Finding

The final effective command really was zero. PD takeover was blocked by the
existing locomotion support gates: first an underloaded hind-right foot, then
a persistently front-heavy contact-force split. The body became quiet, but
quiet motion alone does not satisfy the existing takeover rule.

The deeper design limitation is passive acquisition of a standing posture.
During `STAND_SETTLING`, the implementation continues to return the RL policy
target at gains 20/0.5. It does not actively establish the support configuration
required for the subsequent PD transfer. Consequently, zero velocity can settle
into a posture which never passes the takeover predicate within the task's
deadline. The current record establishes this failure for the captured wait;
it does not establish what an indefinitely extended simulation would do.

## Timeline and checks

Times below are actual solver seconds. Stance inputs occur at the previous
telemetry row's physical time, because telemetry is recorded after the 20 ms
motor interval. Backend terminal notification is mapped through the captured
host/container clock samples and realtime pacing records.

| Event | Time / evidence |
|---|---|
| Last nonzero input ends; StanceHold receives exact zero | 115.548126 s |
| Initial velocity gate | One sample; speed 0.171992 m/s exceeds 0.15 m/s |
| Hind-right force below 10 N | 209 samples including the initial speed failure; approximately 4.18 s |
| First sample with all basic gates satisfied | 119.725830 s |
| First completed support-share dwell rejected | 119.985687 s; front pair 72.886%, limit 65% |
| Navigation failure notification | Approximately 125.296936 s; log reports `terminal_settle_timeout` |
| Continuous zero input before notification | Approximately 9.748810 s; 488 replayed pre-notification samples, none nonzero or stale |
| Rejected support-share windows before failure notification | 19, all rejected on the front-pair share |
| Recording ends | 126.402161 s, including the inherited one-second failure tail |

The complete terminal recording contains 23 rejected balance windows. Four are
after the navigation failure notification; they must not be counted as extra
pre-timeout opportunities. The low-level ten-second settle-window restart also
occurs after the upper-level failure notification. It is not a PD transition.

The final `stance_progress=0.8795166` is progress through another 0.25 s
settling dwell. It is **not** 88% completion of PD takeover. While the mode is
STAND_SETTLING, `policy_owns_joints` remains true. Zero requested body velocity
does not mean zero joint torque or that the hold controller has taken ownership.

During the final five seconds before that notification:

| Measured input | Recorded value | Existing entry requirement |
|---|---:|---:|
| Effective command | Exactly [0, 0, 0] throughout | Max component <= 0.001 |
| Linear speed | Maximum 0.00914 m/s | <= 0.15 m/s |
| Angular speed | Maximum 0.03623 rad/s | <= 0.5 rad/s |
| Body tilt | Maximum 3.477 degrees | <= 10 degrees |
| Minimum individual foot force | 12.962 N | Every foot >= 10 N |
| Front-pair force share | 69.175–72.843%, mean 71.131% | Dwell mean within 35–65% |
| Left-pair share | 52.492–57.551% | Dwell mean within 35–65% |
| Diagonal-pair share | 51.473–62.531% | Dwell mean within 35–65% |

The actual implementation averages per-sample shares across a >=0.25 s dwell;
it does not divide window-mean forces. With this solver clock, a full dwell
contains 14 samples spanning approximately 0.259857 s. All rejected window
means are retained in `results/v206.json`.

“Force share” here means the recorded contact-force magnitude used by
`NewtonStance.measure`, not an independently measured vertical load or a
computed support-polygon margin. These signals establish which code predicate
failed. They alone cannot certify that forcing PD takeover would be stable.

## Deterministic reproduction

`analyze.py` loads the **executed** pure NumPy StanceHold source from each
capture. It uses current-row command and measured forces, previous-row body
state and time, and starts at the final recorded RL-to-settling transition.

- v206: 543 terminal control samples, replayed twice, **zero discrepancies** in
  mode, reason, or progress. No PD entry; 23 balance rejections over the full
  recording, including its failure tail.
- v204: 379 terminal samples, replayed twice, **zero discrepancies**. One balance
  rejection, then transfer at 137.125443 s and FIXED_STAND at 139.139603 s.
  Its transfer began 1.168213 s after the final zero command.
- One-variable diagnostic probe: allowing the balance predicate alone to pass
  makes the recorded v206 decision stream enter STAND_TRANSITION at 119.985687 s.
  The probe stops at that first change of ownership. It does **not** simulate
  the resulting PD forces or prove a successful/appropriate physical transfer.

Only mode/reason/progress decisions are claimed equivalent. This harness does
not claim target/torque parity across PD ownership, nor execute Newton,
ONNX inference, navigation, or motor integration.

## Is v206 responsible?

### What is established

The executed stance state machine, Newton contact-force adapter, and motor/policy
wrapper are byte-identical in the v204 and v206 recordings:

| Executed source | SHA-256 |
|---|---|
| stance_hold.py | `9a97879a5d5ed2f7c9c3e327c1193b1c42cf079eaaf073a855afad53a7dbc306` |
| newton_stance.py | `01721203c6517106f967f2fe1854ef8aeb7a6b3b9f31c4e7e6a8fed2d336a5b9` |
| lite3_newton.py | `2965d0f6b9e14eb2ad3169c9c077e1bb152eb777968565d57e02aa9a60a2cffd` |

`terminal_completion.hpp` is also identical between v204 and v206. Both retain
the ten-second terminal timeout and two-second confirmed FIXED_STAND dwell.
The recorded final input was not a tiny command, an oscillating zero/nonzero
command, or a stale-command fallback. `command_stale=true` in the last saved
sample belongs to the post-failure case latch; it is not the cause of the wait.

The slew limiter did not consume the ten-second budget: the receiver had exact
zero for about 9.75 s before the failure notification. The terminal command
sequence decayed from approximately 0.60 m/s to zero over roughly 0.3 s. There
was no persistent numerical tail preventing StanceHold from arming.

### What remains unresolved

v206 changes the motion history and therefore can change the final body and
foot configuration. That indirect effect is **not excluded** by identical
StanceHold source. The recordings also ran on different hosts: v204 on Mac,
v206 on Linux. They are not a matched version A/B comparison.

The stopping histories visibly differ: v204's final nonzero command was a yaw
correction of about 0.204 rad/s, while v206 approached its final stop with forward
motion. A comparison of these two terminal states cannot isolate the contribution
of any one v206 change.

| v206 change | Relation to the demonstrated failure |
|---|---|
| Preserve same-goal SCAN solve generation | Does not alter the stance predicate; changed upstream trajectory availability could indirectly alter the stopping state |
| Smooth heading attenuation and hysteresis | Alters approach motion; does not operate during the recorded all-zero terminal wait |
| Command slew limiter, including goal braking | Alters the deceleration history; confirmed finite zero arrival, leaving about 9.75 s before notification |
| Brake an expired low-speed local curve | Alters some stop/restart histories; no residual command or cancellation occurred in this final settling interval |

Conclusion: this is a demonstrated support-acquisition failure in the existing
RL-to-PD handover, exposed by the v206 run. It is **not** a demonstrated edit
regression in the stance predicate, and it is **not** proof that v206's motion
changes have no indirect role. There is no evidence here that rolling back one
of the four changes would reliably solve the general problem.

## General design direction — proposed, not implemented

Keep responsibility local and explicit: navigation decides **when to stop**;
the locomotion adapter owns **how to finish stopping and establish a hold**.
Use the existing locomotion boundary rather than adding another navigation
planner, ROS control loop, or scene-specific branch.

1. Separate the persistent intent to stop/hold from an instantaneous zero
   velocity sample. Return physical progress and the reason for any blockage.
   The same interface should work for PCT, a future VLA route source, and other
   callers. No route name, endpoint coordinate, floor ID, or version check.
2. Give the stop-to-hold operation an actual support-acquisition behavior.
   Deceleration, support establishment, torque-continuous transfer, and holding
   are responsibilities of that one operation. Merely waiting for the zero-speed
   RL policy to happen to distribute forces appropriately provides no completion
   guarantee. Selecting that behavior needs locomotion evidence; this diagnosis
   does not invent or silently install a new standing controller.
3. Evaluate usable support from physical state and the supported controller's
   capabilities. Contact geometry, body motion and feasible forces matter;
   a fixed near-equal force split is a heuristic, not a general definition of
   stable support. Keep the existing predicate until a replacement is justified.
   Do not infer that this particular 71% split is safe solely because speed is low.
4. Give the operation one coherent progress/deadline contract. Navigation should
   receive an explicit success or failure reason, instead of independently
   guessing whether the locomotion wait is making progress. Preserve final
   position/yaw acceptance and the current failure/retry behavior until any
   change to those policies is separately authorized.

Do not “fix” this recording by changing 65% to a value above 73%, extending the
timeout until this route passes, sending a special corrective velocity near
this endpoint, or forcing PD after a fixed delay.

A future implementation can first be checked with bounded stop/hold cases:
different approach speeds and yaw rates, forward/reverse motion, different
gait phases, uneven contact/loading and representative slope/step support.
Positive cases must physically complete the handover; insufficient-support
cases must produce the correct explicit outcome. Permuting legs and rotating
the world frame should not create route-specific behavior. These are proposed
checks; none were launched in this audit.

## Source anchors

- `2026-09-16_pi_cortex_harnessvln/isaac_runner/stance_hold.py`: lines 63–81
  define entry thresholds; 499–567 implement settling and balance rejection;
  549–553 clear the dwell on rejection; 668–669 keep RL ownership until entry.
- `2026-09-26_newton_macos_policy/scripts/newton_stance.py`: lines 58–79
  measure foot forces; 106–126 construct the actual HoldInput and telemetry.
- `versions/v206/src/scan_nav2_controller/src/controller.cpp`: lines 57–60
  configure the terminal timing; 173–180 update the goal window, throw the
  typed timeout, and return the slew-limited brake command.
- `versions/v206/src/scan_nav2_controller/include/scan_nav2_controller/terminal_completion.hpp`:
  lines 22–55 define the terminal wait and physical FIXED_STAND confirmation.
- `versions/v198/newton_episode.py`: lines 313–318 retain one physical second
  after a failed driver result. This explains the post-failure tail.

## Reproduction and retained evidence

Local source of truth: this audit directory. Remote execution directory:
`/data/sun/vla_mppi_20261009/audits/2026-10-15_v206_terminal_settle`.

```sh
/home/sun/vla_exec/envs/newton_worker/bin/python analyze.py \
  --capture /data/sun/vla_mppi_20261009/trials/v206_linux_full_attempt02/runs/v206_linux_full_attempt02 \
  --name v206 --output results
/home/sun/vla_exec/envs/newton_worker/bin/python analyze.py \
  --capture /data/sun/vla_mppi_20261009/mac_archive_v204_20261015/v204_mac_full_attempt01.tar \
  --name v204 --output results
```

The compressed raw captures remain on gpu5070ti. Required compressed members
are checked against their original manifest size and SHA-256 before use.
Returned JSON records each source's digest; CSVs retain every replayed terminal
sample. `source_check.json` verifies all 131 v204 and 111 v206 frozen manifest
entries unchanged. `receipt.json` binds the returned compact results and audit
scripts. The comparison plot is presentation only; all conclusions come from
the replay and recorded values.
