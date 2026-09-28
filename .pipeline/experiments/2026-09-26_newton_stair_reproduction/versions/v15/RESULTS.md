# v15 results

The recorded riser test failed before this version and passes afterward, with
missing-ground, unrelated-floor, tall-step, low-box and slab-underside negatives.
The native build passed in 28.56 s with source identity unchanged.

Two repeated expired-curve replays produce a 2.969 m target and pass PVA/full-curve
checks. The original 66-scan continuation also passes, with a 2.187 m target.
All eight measured geometric sensor cases retain the v10 occupancy and search
outcomes, including low-box detection and blocked unknown cells.

Physical run `v15_building_route01` did not reach the goal. It ran 89.962 s with
1.058 m net forward displacement and 0.079 m vertical displacement; no OOM was
observed and Linux applied-state copyback verified. It stopped after the first
stair advance, with the gate still open and no terminal result. Recorded-state
video is a 24 s diagnostic excerpt, not route acceptance; see video_receipt.json.

The new 189-scan exact pose/cloud replay also fails continuation. Isolated
3-D-search, 1 mm terrain-band and historical-radius diagnostics are retained
under audits/2026-09-27_v15_*; none has been promoted into production. Reusing
the existing strict goal-neighborhood mechanism for blocked local endpoints is
under investigation. Do not treat a seed or endpoint check as a route pass.

Source-note correction: the surveyed CMU source has signed-height logic at
lines 501–508 of the pinned copy; PLAN.md's approximate line pointer is not
the source of truth. No CMU implementation is copied.
