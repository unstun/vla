# v137 fixed comparison

Start only after all three fixed v137 pilots arrive with measured final PD hold,
no fall and verified execution/copyback/retention. The failed v134, v135 and v136
pilot batches remain separate and prevent their own proposed comparisons.

Both arms use frozen v137 host and the v135 coverage-corrected PCT map, with
unchanged scene, original policy, CPU Newton, sensing, safety deadlines,
six-retry limit and measured-stop criteria. Baseline nativev136 is the exact
compiled behavior used by v136; candidate nativev137 adds bounded fresh-input admission waiting.
Both use map epoch `stair_reactive_coverage_v135` because the data are identical.

Six fresh trials per arm, ABBA blocks: A1 B4 B5 A2 / B6 A3 A4 B7 / A5 B8 B9 A6.
Use the existing bounded runner, sequentially, without concurrent heavy analysis.
Do not replace failures or pool the three pilots with the six fresh candidate
runs. Execution/evidence failure stops the batch; navigation failure stays in
the denominator. Candidate acceptance in this scenario requires6/6arrivals,
zero falls and original measured-stop proof before every replacement owner.

This test isolates the fresh-input waiting change on top of the map repair. It does not
separately estimate the population success-rate effect of the static-map
correction versus original v133. The original trace/native query and v134/v135
pilots provide that diagnosis's evidence, with their stated limitations.
Do not promote this into30Hz, unseen-gap detection, Jetson or hardware acceptance.
