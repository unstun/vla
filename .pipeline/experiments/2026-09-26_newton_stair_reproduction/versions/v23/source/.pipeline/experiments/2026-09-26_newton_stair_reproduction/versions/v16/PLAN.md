# v16: bounded recovery with SCAN's fixed-height optimization mode

Stage: experiment + analysis. Parent: v15. One logical behavior change:
retain the existing three-axis attempt, then retry an optimization-stage failure
once with the existing fixed-height mode and the same start/goal PVA.

The 189-scan diagnostic in `audits/2026-09-27_v15_optimizer_collision` isolates
height smoothing: with the separately labelled physical-ground diagnostic input,
the three-axis optimizer lowers the curve below the existing body-support band.
The fixed-height mode yields a complete, PVA-matching, collision-clear native
continuation. This does not establish the safety of that diagnostic ground input;
v16 does not adopt it. The v5 recorded case requires three-axis optimization, so
fixed-height cannot replace it globally.

Reuse the existing SCAN fixed-height implementation and native graph initializer.
No new optimizer, objective, geometric clearance, ground classification or speed
threshold is introduced. The complete attempt is repeated, including refinement,
boundary PVA, dynamic limits, minimum cruise and full-curve checks. Restore the
configured mode even on exceptions; count one final failed call rather than two
attempts. Do not retry when initialization never reached optimization.

Validation:
1. Freeze all source/configuration inputs and build with unchanged identities.
2. Replay the old 66/67-scan successful inputs and current 189-scan failure.
3. Repeat the diagnostic-only physical-ground fixture to confirm the bounded
   recovery reaches the existing complete gates. Keep its label separate.
4. Confirm the configured height mode is restored after accepted and rejected
   calls; keep the v5 three-axis-required case available for regression.
5. Run the version-bound short Building physics with production ground input.
   It alone determines physical route acceptance. Preserve failures and video.
