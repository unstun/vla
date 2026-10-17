# v234 migration readiness reassessment

Assessment date: 2026-10-17. This updates the acceptance interpretation after
Dr Sun clarified that the powered-off gpu5070ti need not be synchronized.
It does not replace any test output or change navigation/runtime code.

## Operational migration: offline gates passed

The gpu40901 runtime is independently reconstructed from the exact 317-file
v232 source with the v233 execution reference. All 14 native packages build;
fresh tests pass 165 distinct cases / 186 colcon records with zero failures,
errors or skips. Static environmental consumers agree on 30,060 queries;
Building admission rejects 0/3,821 samples and produces the original admitted
route byte for byte. The actual graph runs for 12 seconds and exits normally.
Host, original factory protocol, RL golden frames and rendering/encoding pass
without advancing Newton physics. RL, original endpoints and 0.35 m hard
collision/support thresholds remain unchanged.

Evidence: [returned offline checkpoint](results/offline_summary.json),
[native rebuild receipt](results/native_rebuild_receipt.json),
[final sync receipt](results/final_checkpoint.json), and
[machine-readable reassessment](migration_readiness.json).

## Historical audit: optional, not a runtime prerequisite

The original gpu5070ti native image/install byte comparison and the historical
126,324 + 3 dynamic replay have not been rerun. Their original artifacts remain
on the powered-off source host. These supplementary checks do not block the
source-identical rebuild's migration acceptance or preparation of a new-host
physical experiment. There is no need to power on gpu5070ti for that purpose.

The earlier `full_offline_acceptance: false` in returned checkpoint evidence
and the current source-gate output uses an overly broad definition that also
required these historical audit items. Preserve those original receipts;
`migration_offline_acceptance: true` in this reassessment is the current task
decision. It does not claim the missing historical checks passed.

## Next execution boundary

Prepare the gpu40901 full-route launcher using the verified host binding and
perform its offline preflight before arranging the separately authorized
single full-route experiment. The current v234 entry scripts are offline-only.
No full-route physics has run on gpu40901; arrival, stair execution, terminal
PD standing and host-specific performance remain unvalidated. The accepted
physical baseline remains v232/v233 until a new physical result is recorded.
