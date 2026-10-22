# v275 preserved partial material correction

Frozen audit manifest:
`9d45c0fd046b353e06c776c30c1123c01762b4fe8d22f740d1fb676b3e41d545`.
All17returned frozen files verify locally. Fifteen boundary/negative controls,
5,000independentfloat32samples(maxdistance/bound0.091131),sevenlegalendpoints,
unchangedB08wallmargin(-0.1333018824m),andthreeinitialriserwitnessespass.

The whole saved-trajectory replay nevertheless retains large negative margins.
The correspondence itself resolves sub-micrometre source sampling differences;
the material rule is incomplete for exactly vertical risers lying below another
finite upward tread. A04/G05face997andM03face1539are concrete counterexamples.
A matched face need not itself be upward to be terrain material. v276 replaces
that whitelist with the complete finite3Dcap volume predicate.

Keep all v275 derived outputs and the v273 original scores. This is not a full
source/point reconciliation, benchmark acceptance or physical pass. No native
code, raw point, body pose, hard radius, planning call or physics step changed.
