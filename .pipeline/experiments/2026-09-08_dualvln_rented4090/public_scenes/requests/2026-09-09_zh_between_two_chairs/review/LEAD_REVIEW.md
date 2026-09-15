---
origin: ai+local_evidence
date: 2026-09-09
reviewer: Codex
status: corrections_required
runtime_verdict: accepted_qualitative_trial
user_task_success: unscored
---

# Review of the user-instruction trial

The recorded official-evaluator rollout is accepted as a qualitative trial.
The policy approached a pair of chairs and emitted STOP. Exact satisfaction of
the requested spatial relation has not been established. No new inference was
run during this review.

## Verified observations

- The request remains unchanged. The executed annotation stores the exact input
  plus a terminal period sentinel; the executed evaluator's `[:-1]` removes only
  that sentinel. Reconstructed the base prompt from the actual evaluator source
  and verified equality with the request's UTF-8 text and hash.
- All eight source/config/annotation/scene identities in `inputs.json` match
  the current local bytes. The annotation and trace header preserve the requested
  start pose. Evaluator SHA-256 remains `a05268d5...`, as in public runs v2–v5.
- The surviving supervisor record reports exit 0, no timeout, and **54.207 s**.
  The trace contains 51 action entries, 13 S2 calls, and 14 S1 calls.
- The opening eight LEFT actions turn 120 degrees before translation. Across
  the trace: 27 FORWARD, 13 LEFT, 5 RIGHT, 5 LOOKDOWN, and 1 STOP entries.
  Recomputed planar path length: **6.750 m**; planar net displacement:
  **6.692 m**. The return's approximately 6.9 m displacement is imprecise.
- The last S2 output is literally `STOP`, and terminal action provenance is
  `s2_action_sequence` at step 50. It is not an S1 segment-stop or fallback.
  The trace records zero collisions.
- Both delivered videos match the return's hashes and decode without errors:
  first-person 51 frames at 5 fps; composite 51 frames at 6 fps. Their playback
  duration is different from execution wall time. Fresh frames were extracted
  locally for inspection; see `lead_checks.json` and the adjacent PNGs.

## Visual assessment

The policy turns toward two ornate striped chairs near a window, approaches,
and stops with both chairs still visible ahead. The view supports proximity to
the pair, but cannot establish that the agent's position lies geometrically
between their centers or footprints. No intended pair or coordinate target was
specified, so user-task success stays unscored. Do not label this as a verified
successful spatial-relation test or as general language competence.

The claim that these are the same target chairs as original English episode 1
is unsupported. That episode's successful v1 terminal pose is over 16 m from
this trial's terminal pose; repeated chair appearances are not identity evidence.
Describe the visible pair without importing an old route's semantic target.

## Corrections and limitations

1. **Full runtime prompts are missing.** `verify_instruction_delivery.py` copies
   the template into a constant and applies equivalent string operations. It
   does not call the actual runtime prompt builder. Source/annotation inspection
   supports the verbatim base-instruction conclusion, but the return should call
   this a source-matched reconstruction. The executed evaluator was not modified
   to record every resolved S2 prompt, random conjunction, or tokenized input.
   Its `s2_call` records are outputs, not complete prompt transcripts.

2. **Failed-attempt evidence was deleted and the run ID reused.** The executor
   explicitly reports deleting two failed remote attempts before the successful
   `zh_chairs_v1`. Their original raw logs and source/annotation identities are
   not present in the returned run directory. This prevents auditing all attempts
   and independently establishing where each failed. Restore original evidence
   if recoverable; otherwise record the irrecoverable gap. Do not reconstruct
   invented logs or claim complete attempt provenance. Use unique IDs on retries.

3. **Bookkeeping markers are still displayed.** Moving the dummy goal near the
   start is not equivalent to hiding goal/reference markers. The composite still
   shows red/green bookkeeping marks at the start. They are not the intended
   chair target and cannot establish success. Hide them with an output-only
   configuration/visualization change for a corrected video, preserving the
   original recording. The `success0` filename reflects dummy-goal scoring only.

4. **Bookkeeping documentation and state are stale.** The freeze-script header
   and provenance note still say the goal equals the start, although its stored
   coordinates are different. The eval config also changes the distributed port
   to 2334, which its change description omits. Request/task dispatch metadata
   still say prepared. Correct these descriptions and record executed status
   separately from pending review and qualitative user-task assessment.

Keep the original request, annotation, raw outputs, and videos unchanged while
correcting derived documentation. This review adds only its report, checks, and
extracted inspection frames; no implementation was changed or committed.
