# Repeated v122 / v127 comparison and cause investigation

Stage: experiment + analysis. Dr Sun explicitly requested repeated old/new trials
on gpu5070ti to distinguish adaptation-3 regression from pre-existing instability.
This supersedes the earlier adaptation-3 early-stop rule for this investigation;
it does not retrospectively change that recorded experiment or adopt v127.
Inline execution only. No navigation code/configuration changes, threshold
relaxation, rebuilding, training, robot actuation or adaptations 4–5.

## Protocol declared before new trials

Run six additional independently initialized episodes per arm, all on the same
host, original Building corner, CPU Newton, unchanged frozen v127 host entry.
Control means actual retained native v122 at /task/candidate/install; candidate
means native v127 at /task/step3_v127/install. Keep the exact existing binaries,
image and source/configuration receipts. Episode bound remains 90 s with early
native arrival plus measured PD hold. No concurrent physics/build/heavy analysis.

Counterbalanced order (B=candidate, A=baseline): BAAB / ABBA / BAAB.
Concrete IDs: B2,A2,A3,B3,A4,B4,B5,A5,B6,A6,A7,B7. Attempt01 is historical and
reported separately, not selected into the new balanced primary comparison.
Run all twelve despite navigation failures. Stop the batch only for source/
install mismatch, host/resource or execution/retention failure requiring repair;
retain and report that attempt. Never discard failures or replace them silently.

Record exact launch order and pre-run host load, native receipt/source hashes,
arrival/hold, terminal causes, fall/copyback/retention, path/final position, pause
windows, per-round latency and source-age rejection events. Keep raw data on
/data/sun/vla_mppi_20261009; return compact records and hashes to this local audit.
Summarize arm rates and uncertainty without treating six runs as proof of equal
reliability. Use exact Fisher comparison for the count table as descriptive
support, not a binary proof of equivalence. Include all trials and ordering.

## Ranked, falsifiable hypotheses

1. Existing asynchronous sensing/mapping/recovery instability: unchanged v122
   also reproduces the same stale-evidence/progress failure chain in repeated
   trials, and the same frozen curve/map inputs produce equal verdicts.
2. Adaptation-3 semantic regression on uncovered inputs: actual failed native
   curves/boundaries or recorded map/query inputs yield different old/new
   decisions under a frozen replay; isolate a first differing case if found.
3. Adaptation-3 timing regression: verdicts stay equal but candidate consistently
   worsens validation or whole-round tail times/source ages across balanced runs.
4. Host/order disturbance: failures cluster by run order/load/initialization
   rather than arm. Original stale source stamps must not be renewed to test this.

Reproduce the symptom with the frozen loop, then inspect direct stop events and
perform state/input-equivalent differential replay. First inspect retained capture
coverage; do not call regenerated or partial map state an exact live snapshot.
If exact asynchronous map revision cannot be restored, explicitly bound that
claim and still compare captured candidate PVA/dynamics/epoch plus reconstructible
native map queries. Existing 376 fixed-input parity cases remain component evidence.

No production fix is authorized by this diagnosis plan. End with evidence for
shared instability, detected regression, or unresolved causal uncertainty, and a
concrete next seam if certainty remains unavailable. Keep main task in_progress,
v48 broader reference, v122 selected runtime, and the pre-existing Git index lock.
