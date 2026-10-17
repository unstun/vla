# Strict terminal recovery qualification

The fresh recorded-input search has a reachable, fully checked0.154980m
terminal edge excluded by the old0.10m candidate radius. Step14 preserves the
original failed search and same-map witness in TERMINAL_RESULT.json.

scan29 changes only dyn_a_star.cpp and its interface comment. Original strict
near-goal search runs first. On normal queue exhaustion, longer terminal edges
from valid popped nodes are ordered by reached path length plus edge length,
and checked with the original full segment predicate. The existing total0.2s
budget governs acceptance. Unknown, support, collision, dynamics, optimizer and
final complete sampled-curve checks are unchanged. Cost ordering does not prove
global optimality; the fixed-edge-heading graph does not prove continuous turns.

Native regression: old scan28 has the three predeclared recovery exercise
failures; the other nine cases pass. Final scan29 passes all12 on local clang
and the pinned Foxy g++. The first local scan29 attempt failed compilation
because the logger test double omitted RCLCPP_INFO; its evidence is retained,
and adding the stub macro did not change production source. Independent review
found no blocking issue. NATIVE_RESULT.json records exact inputs and outcomes.

Full Foxy build passed with source hashes matching before and after. Installed
462-file identity is d49f73296d4546e1d9249ebf225920adf58de6a2b5ae832f3a53fcf76c68265a.
The same fresh input (manifest d2bfe404137565a51dbf4aceb0fcf56dfe2d5d5bb2b3fe435e92971534ddb86a)
is now being replayed through the complete original pipeline. Replay, moving
spline and live navigation acceptance remain separate pending results.


Fresh-input result:63 checked seed chains,63 native optimizer-success returns,
zero received moving splines. The first recovered terminal edge is0.17559432m,
chosen after988 of1,313 cost-ordered longer candidates. Its69-node seed and426
resampled positions pass original segment checks. Timed initialization completes
in two refits at79.156101s duration. The final full-curve gate rejects the first
curve at46.347717s. No search-time cap is hit. Four later search failures remain;
callback counts are not a speed or success-rate estimate.

The initial optimizer-guidance search also logs pool exhaustion and returns
without guidance. Whether this is the decisive geometric cause is still under
investigation. It is not grounds to skip the final gate or publish this curve.
Step16 observes first rejected curve geometry and exact footprint after original
failure, preserving the native return and every threshold. Old accepted-input
regression is being checked separately.


Old corrected-input regression completed:scan29 still publishes one accepted
moving cubic after all9,324 sampled checks, with no seed failures or time cap.
See scan29_old_input_regression_v1/review.json. The old successful scan28 case
already had the same optimizer initial-guidance pool exhaustion, so that error
alone does not explain the new input failure. Reviewer confirms four initial
cost evaluations had no committed obstacle directions; optimizer's coarse
prefix check and manager's full final check have different sample coverage.
This is a separate optimizer limitation, not evidence for a collision bypass.
