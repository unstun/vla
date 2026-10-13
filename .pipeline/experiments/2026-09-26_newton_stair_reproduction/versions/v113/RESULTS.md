# v113 original Newton result

Not accepted: the requested goal was not reached. Original scene, start, goal,
policy, physical dynamics and safety thresholds were retained. The applied-state
copyback is verified. Actual navigation RTF was 0.99996, measured path 22.835 m,
final body (3.7002, 0.26594, 4.82145), approximately 3.70 m from the requested
body goal; the robot did not fall. The physical run ended at simulation 56.6405 s.

The inflation optimization preserved all 268 moving-scan map hashes and all 14
sliding-boundary hashes. Its isolated moving-input CPU time fell by about 43%.
These component results did not establish navigation success.

The controller stopped first on native negative safety evidence (trajectory 543).
Later it stopped on proof ages 114.937 ms and 104.942 ms, while observation ages
were 214.882 ms and 204.887 ms respectively, within their original 250 ms limit.
The native periodic safety callback shares the planner work group. v114 investigates
an independent read-only native collision validation in the Nav2 controller tick;
no proof lease or map/body validity threshold will be extended.

See analysis/trial01/metrics.json and results/{result,state_copyback}.json.
Raw runtime remains at /private/tmp/vla_newton_v113_v96bqp38 pending verified archival.
