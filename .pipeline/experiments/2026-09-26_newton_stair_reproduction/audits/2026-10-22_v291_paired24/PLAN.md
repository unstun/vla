# v291/v290 paired24 physical campaign — 2026-10-22

Authorized: ultra9, 24 full physical simulations, no hardware actuation. New source is only a common execution/analysis binding; frozen navigation and stance versions remain byte-identical. Candidate v291 work commit: `8ed419314`; exact native and stance SHA values are bound by the campaign manifest.

## Fixed selection and ordering

Measured routes: D07, CD12, S04, A04, each three independent starts per version. Runs are adjacent parent/candidate pairs. The first member is counterbalanced: six parent-first and six candidate-first pairs. `source/request.json` is the authoritative24-row order. Fresh processes, factory start, controller caches and robot state each time; no state copied from another run. Parent initialization/seeding is unchanged; async executions are not claimed bit-identical.

Future holdouts: CU04 (ascent), CD09 (descent), CM04 (intermediate landing start), CE04 (boundary goal). Exact original scenarios/poses and requested yaws are retained. They were offline-checked before this campaign, but absent from inspected native physical-selection lists and existing v289/v290 physical run directories. They are new **physical** tests, not unseen planning queries or new maps. Do not run them within this24 authorization.

## Conditions

Same ultra9, pinned original debug ROS image, 6 CPU / 6 GiB native container, original host CPU Newton worker with observed flexible affinity. RTF1,1ms physics,50Hz policy,10Hz sensing and absolute100ms scanner deadline; original factory startup, source geometry,0.35m hard radius, original arrival and >=2s measured finalPD gate. Original900s supervisor and600s recording limits retained. Other host workloads are observed, not modified. Record load, resource admission and actual container configuration per invocation. Zero-step preflights check both variants' native graph/profile and actual stance module activation.

No policy, target, tolerance or code tuning after freezing. Every positive-physics attempt counts; failures are retained, never replaced. A startup failure before positive physics is retained separately and diagnosed without silently inventing a successful attempt.

## Measures and decision

Use every ~50Hz telemetry sample for drift, and original sampled source/raw-solid/support geometry audit for route success. Enumerate all contiguous zero-command episodes after first original terminal-region capture. Primary: maximum XY displacement in the **first** episode, plus zero-to-PD delay; also retain worst episode and restarts. Failure before the region is unavailable drift, not zero. A stop with no PD takeover before restart/end is censored and retains its observed maximum; it is not successful stopping. Raw post-zero displacement, pre-PD displacement and post-PD displacement remain separate from clearance and goal error.

Success requires original route arrival, whole-route sampled geometry, and final measuredPD >=2s. Existing page decision: candidate >=10/12, improvement >=3, A04 3/3 and A04 median elapsed time <=parent*1.15. Report all12 per version, paired outcomes, per-route drift medians and sample availability; no significance/reliability claim from three repeats.

## Storage and return

Raw root: `/home/ubuntu/sun/vla_v291_pair24_20261022/physical_runs/`. Preserve original captures, runtime wrappers, positive/failed run ledgers and per-member hashes. Local return allowlist: frozen manifests/requests, compact results, per-run summaries, analysis provenance and HTML; expected <20MB excluding optional review videos. No weights/raw recordings/full logs committed. Keep the local research no-push hold.
