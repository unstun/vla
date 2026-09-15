---
origin: ai+user_instruction
date: 2026-09-09
executor: Opus
status: prepared_not_dispatched
---

# Run the user's instruction once from the displayed castle start

Write responses and `OPUS_RETURN.md` in English. Preserve quoted user input exactly.

## Request and scope

Read the adjacent `request.json`. It contains the exact user instruction, its
UTF-8 hash, and the same start pose as the first castle video shown to the user.
Run that instruction once through the existing official evaluator. Preserve its
wording without translation, paraphrasing, or extra route/landmark hints.

- Source of Truth: `/Users/sun/tongbu/study/phdproject/vla`.
- Own `.pipeline/experiments/2026-09-08_dualvln_rented4090` (`EXP`) and the
  existing `.trellis/tasks/09-08-dualvln-rented4090` task. Keep request-specific
  configs, provenance, and this return beside `request.json`; use a fresh run ID.
- Remote copy: `/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090`;
  SSH `ubuntu@117.50.179.202` / `rented4090`, existing key authentication.
- Read `AGENTS.md` and `EXP/review/PUBLIC_SCENES_LEAD_REVIEW.md`.
  You are not alone in the repository. Preserve concurrent edits and previous
  frozen episodes, records, videos, and the running `isaac-sim` workload.
- One bounded pretrained simulation is authorized. No training, physical robot
  actuation, language comparison, navigation retries, or infrastructure changes.
  Repair ordinary configuration/runtime failures without changing the request.

## Execute

1. Reuse the verified original BF16 checkpoint
   `InternRobotics/InternVLA-N1-DualVLN` at
   `a698a9e898b4001621a319e1bc89f02ec715cc86`, InternNav source commit
   `7a5c62400ac45b313d9b709c740b64191556a242`, and castle assets at Habitat test
   scene revision `910c783fb954da8497ea5f811b843a76590ddddc`. The working
   Habitat-Lab 0.2.4 / Habitat-Sim 0.3.3 environment is
   `official_r2r/official_env_024`; do not repeat its installation or asset downloads.

2. Build a separate one-episode annotation and derived evaluation config using
   the request's scene and exact start pose. Preserve official observation,
   camera, trajectory conversion, action queue, replanning, and STOP behavior.
   Launch through `work/InternNav/scripts/eval/eval.py`; do not use the old custom
   `sim_runner.py`. Parameterize the existing launcher/preflight where needed:
   checks must validate this request's actual config and annotation from the
   real `work/InternNav` launch directory, not the old two-episode baseline.

3. **Prove verbatim instruction delivery before inference.** Upstream embeds
   `episode.instruction.instruction_text[:-1]`, which would delete the last
   character of this user's unpunctuated input. A data-only compatibility option
   is to store `request.instruction + '.'` in the derived annotation, so upstream
   removes only that terminal sentinel. Keep the original request unchanged and
   record the annotation text and the exact text consumed by the prompt template
   separately. Assert byte-for-byte UTF-8 equality of the consumed instruction
   and `request.instruction`. Use the actual prompt-building path for this check;
   do not merely check JSON round-tripping. Retain the normal upstream wrapper.

4. **Treat this as qualitative instruction following.** No coordinate ground
   truth for the intended pair of chairs has been specified. Do not reuse the
   previous route's goal as a success criterion or select a target after observing
   the rollout. If Habitat requires goal/reference fields, isolate and label them
   as bookkeeping only; report their raw metrics separately and mark user-task
   success as unscored pending visual review. No goal-distance termination or
   action guidance may be added. Hide unrelated reference paths/goal markers in
   the displayed top-down map with an output-only change; show the actual path
   and start. Do not present the old green reference route as this instruction's
   intended path.

5. Run one episode, with the official 500-step evaluator cap and a **900-second
   wall deadline enforced by `scripts/run_job.py`**. Preserve failure or early
   STOP; do not translate and retry until it succeeds. Log the seed/RNG settings
   actually used. Record every resolved S2 prompt, including the randomly selected
   image conjunction, plus raw outputs, actions, poses, STOP source, and inference
   observation identities. Preserve lossless inference inputs where practical.

6. Return the actual first-person video and synchronized top-down path view,
   including the starting and terminal frames. Describe which chairs the policy
   appears to select, final position, collisions, and whether it emitted learned
   STOP. Separate observed behavior from interpretation. Decode and inspect the
   local MP4s before claiming delivery.

## Sync Gate and return

Author changes locally. Verify source, request, derived config/annotation, and
asset identity before remote execution. Return raw logs, prompts, observations,
action/pose traces, videos, and result metadata to the same local relative paths
and verify hashes. Refresh manifests after the final file edits, avoiding the
stale derived-file hashes found in the prior review.

Write `OPUS_RETURN.md` beside this package with the exact executed instruction,
run ID/command/exit/deadline, actual behavior and STOP provenance, local video
paths, qualitative-assessment limitation, deviations, and sync status. Keep the
task at `review` pending lead acceptance. Do not stage or commit.
