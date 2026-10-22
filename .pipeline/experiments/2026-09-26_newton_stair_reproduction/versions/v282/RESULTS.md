# v282 — ten representative source-model physical attempts

Executed frozen nativev280 after the v281 fixed50 gate passed. All ten formal
routes ran exactly once with unchanged endpoints/headings, RL,0.35m hard model
and0.1s scans. Four reached goal and passed terminalPD: D07,S04,CD12,CM07.
Six failed: A04,G05,CU06,CM02,CS03,CE03. All6236 scans met deadline; no native
process crash. Every outcome and complete video returned locally.

Measured geometry limits the result: D07/CD12 arrive but have negative solid
margins; CD12 also has4SupportGap samples. Only S04/CM07 combine arrival/PD with
no refusal or negative margin in the10Hz measured navigation pose audit. This
is not a continuous-time or foot-contact proof. No baseline promotion.

See the [complete report](../../audits/2026-10-19_v280_source_generalization/RESULTS.md),
[full table](../../audits/2026-10-19_v280_source_generalization/physical_table.csv),
and [all10localvideos](../../audits/2026-10-19_v280_source_generalization/delivered/README.md).
Ten real MP4s total72,466,870bytes;462compact files total9,426,541bytes, all SHA
verified. Raw captures/builds remain on gpu5070ti. No formal retry or code repair
during the fixed-version experiment; selected baseline remainsv232/v233.
