# Approved mapping admission and separated-lane investigation

Stage: experiment + analysis. Dr Sun approved both recommendations in the
2026-10-08 source survey: compare SCAN/ROG-style input processing on the same
radar record and exercise separate mapping, trajectory execution and emergency
sensor processing while preserving existing safety requirements.

This extends the existing in-progress Mac validation task. No new Trellis task
or second approval is required for the already requested bounded work.

## Requirements and observable acceptance

- R1: Run actual native mapping on the same 188 recorded scans/paired poses and
  support inputs. Compare full FIFO, the upstream timer/latest-buffer admission,
  and the ROG latest-slot admission; label these scheduling adaptations, not
  reproductions of the complete upstream mapping algorithms.
- R2: Measure completion age, processed/skipped observations, map-state changes,
  and transient obstacle retention. Never score faster processing of fewer
  observations as an equivalent-map speedup.
- R3: Exercise mapping, trajectory execution and emergency-sensor work in
  separate lanes. The sensor lane may veto commands; it never grants navigation
  safety or overrides occupancy/support/freshness/cancellation decisions.
- R4: A slow mapper, stale sensor, transient obstacle, ownership change and
  cancellation must remain observable. Existing map freshness is still 250 ms.
  No restamping, inflated-clearance shrink or unchecked trajectory extension.
- R5: Keep v48 reference and frozen v82 failed evidence. Register new integer
  versions, preserving tested sources, identities and all failed outcomes.

## Design and ownership

v84 owns an observation/admission replay executable and analysis under
`versions/v84`. It links the exact v82 native map (synchronous mode for controlled
comparison) and uses existing v81 recorded readers/map digest. Delays induced by
the experiment are labelled; native mapper time is measured separately.

v85 will own the bounded three-lane candidate/probe, using the comparison to
decide which processing changes are safe to test. Scope is a runnable native
component prototype before any physical navigation adoption. Fast sensor veto
is an additional rejection mechanism; it cannot prove an old map safe. If the
comparison demonstrates evidence loss, preserve that result and keep latest-only
out of the navigation runtime.

Expected changes: version-owned replay/probe/test/build/analysis files, this
task's progress, the version index, and scoped evidence/spec notes. Frozen parent
sources, controller PD/RL, goal/yaw/PVA, original stop protocol and thresholds
are unchanged. No formal training, real robot action, wholesale planner swap or
long remote job is included.

## Execution plan

1. Verify exact v82 source hashes and archived v76 input identity. Use the pinned
   amd64 Humble image on Mac, with no competing local Docker containers.
2. Restore only the needed capture prefix; derive paired inputs with frozen v78
   tools. Build the two map dependency packages and the version-owned probe.
3. Run all-frame reference first, then bounded timing/admission comparisons and
   transient-only obstacle negatives. Record changed-map verdicts explicitly.
4. Build/run separated-lane prototype and failure-injection checks against the
   original evidence/command conditions. Decide physical readiness from actual
   results, not implementation completion.
5. Freeze version source/manifests, validate owned changes, save a Chinese-facing
   report and compact evidence. Keep raw/build data under a unique temporary Mac
   root until SHA-verified transfer to gpu5070ti storage; return only compact data.

Remote artifact root: `/home/sun/vla_artifacts/2026-10-08_mapping_admission`.
Local source of truth: `/Users/sun/tongbu/study/phdproject/vla`.
Local return budget: source/configuration and compact JSON/CSV/report below 5 MiB
per version; no fresh full capture/build copied into the repository.
Sync gate: source + input + installed runtime hashes, then raw archive hashes.
No physical 30 Hz, full-route, or real-robot claim follows from replay success.
