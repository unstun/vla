# v277 Exact GPMP boundary-state candidate

Parent: frozen v272. Preserve failed v274 endpoint-penalty evidence.
In physical-support mode replace both endpoint priors with the installed GTSAM
NonlinearEquality and its QR solver. Preserve the initialized endpoint positions,
headings, speeds and accelerations during optimization. Interior objective,
support, solids and ENV225 remain unchanged. Legacy mode retains original
priors and solver. Initial development01 synchronized only WNOJ due to a local
source-edit assertion; retain its logs as an incomplete treatment. Development02
contains both orders. Neither is accepted without its actual regression gate.

Require unchanged CU08/CU13/CE04 controls for both orders, legacy/source/support/
ENV parity, native/plugin regressions, H00, measured A02 and fixed matrix gates.
No coordinate snapping, cost gain changes or collision threshold changes.

Development02 leaves CU08 (both orders) and CU13 WNOA rejected: 3/6 behavioral
first-pass controls. Do not relabel that result. A separate boundary-identity
regression now checks exact requested XY/yaw in all six actual optimized state
sequences, including rejected paths. It does not require every route to become
feasible. The complete cohort must establish any first-pass coverage claim.
