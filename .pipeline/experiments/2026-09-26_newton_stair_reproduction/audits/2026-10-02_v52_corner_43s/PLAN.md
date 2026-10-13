# v52 corner failure at 43 seconds

Stage: experiment + analysis. Analysis of frozen v52_realtime_trial02 only.
No navigation, goal/yaw/PVA, collision/support, stop or deadline changes.
Bulk original data, converted replay inputs and debug builds remain on gpu5070ti;
return compact evidence, diagrams/plots and source/provenance only.

Feedback loop: extract the first persistent failed nominal round and preceding
accepted curve from original logs; replay captured observer input with the frozen
native library and fixed clock, requiring the first seed to match the live seed.
Repeat the failure, inspect actual collision/support queries, then run one-variable
counterfactual probes through original native admission/safety code. A replay that
does not reproduce the original boundary is evidence of replay limits, not a fix.

Ranked hypotheses:

1. A target-connector miss clears eligibility for an otherwise owned curve.
   Prediction: original logs show connector failure before identity rejection,
   without an owner change; restoring the same binding in an isolated replay
   permits a fully validated shorter warm candidate.
2. Expired-curve start PVA differs from the measured body pose.
   Prediction: the original start yields hard-boundary collision while the
   existing measured-state initializer changes that query/result. This is a
   diagnostic counterfactual, not authorization to change live start policy.
3. New corner occupancy/support makes spline fitting inconsistent with its seed.
   Prediction: exact query probes identify raw-history, support-layer, inflation
   or heading-dependent rejection; frozen/current and preceding map inputs differ.
4. Controller/gate ownership independently stops commands.
   Prediction: raw, admitted and applied commands diverge, or ownership changes
   before the first lost continuation; pure latency is insufficient to explain it.

Distinguish proven trigger, sustaining feedback loop, time cost and remaining
uncertainty. Keep logs and failed attempts. No physics or robot actuation required.

Completed diagnostic: see REPORT.md and verification.json. The original ranked
hypotheses were updated by evidence: route regeneration clears the accepted
binding before the first nominal failure; a long target still fails connector
admission when binding is restored; later front-footprint support is missing
through the existing guarded evidence-floor rule. Fixed-clock/live prefix
differences prompted a native freshness predicate probe. Expiry and controller
finish are downstream effects. No proposed navigation fix was implemented.
