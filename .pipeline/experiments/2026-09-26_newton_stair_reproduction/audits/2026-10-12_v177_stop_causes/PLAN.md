# v177 stop-by-stop causal audit

Stage: experiment + analysis. Dr Sun requests every recent stop explained and
substantial comparison against open-source implementations.

Scope: five closed v177 original-route captures. Separate physical low-speed
intervals, trajectory revocations, planner retries and normal final hold. Reuse
the frozen capture reader and clock evidence. No navigation behavior changes,
new physics, training, hardware motion or edits to frozen versions.

Ranked hypotheses and falsifiable predictions:
1. Stale map/safety evidence causes some revocations: preceding source timestamps
   exceed the actual gate; geometric validation need not fail.
2. Remaining trajectory/support validation fails: fresh evidence reports a
   geometric rejection, followed by revocation of the same trajectory/owner.
3. Local progress stalls: commands/short curves repeat without sufficient body
   displacement, then the progress checker expires or first-curve timeout fires.
4. Recovery amplifies pauses: measured-stop dwell, replacement admission and
   unsuccessful planning account for the elapsed interval after initial stop.

Owned outputs: this audit directory (read-only analyzers, compact verified event
tables and report); a dated upstream survey with commit/file hashes and precise
code references; task implementation journal. Upstream sources remain reference
material. Do not equate inspected code with executed upstream performance.

Local source of truth is this directory. Run the identical hashed analyzer on
gpu5070ti against `/data/sun/vla_mppi_20261009/trials/v177_*`. Return compact JSON
and verify all file hashes. Raw captures stay on gpu5070ti. Record unresolved
causal gaps rather than invent missing log fields.
