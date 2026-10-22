# v265 — Slower exact-cache candidate, rejected

The single-anchor request cache preserves all 70,928 full solid values,
5,000 edge decisions, 70,928 support values and 70,928 scalar ENV values.
74 plugin cases and 97 native regressions pass. No physical attempt occurred.

All six CPU2 recorded controls are slower than frozen v261: A04 2.122 versus
1.636 s; G05 2.145 versus 1.580 s; D07 3.040 versus 2.473 s. The remaining
short controls also regress. These are individual component observations,
not repeated timing distributions. There is no reason to adopt the candidate.

The four-anchor v261 cache remains in use. This candidate is not frozen as an
accepted treatment or promoted to the selected baseline. Full compact logs,
test XML and source/install identities are retained in
[rejected_candidate.json](results/rejected_candidate.json). Returned evidence
hashes have zero mismatches. No compile cache or heavy raw fixture is local.
