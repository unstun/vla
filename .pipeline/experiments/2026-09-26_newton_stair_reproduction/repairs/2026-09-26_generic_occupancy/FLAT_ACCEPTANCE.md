# Prospective flat-control acceptance

Stage: experiment + analysis. Defined before the full-rate human repeat and
the first continuous box run. `flat_static_human_live_v4` is an arrival pilot
with contact candidates recorded at 50 Hz; it does not satisfy the full-rate
contact evidence requirement below.

Use the same SCAN42 v9 build, `geometry_smac_approach_flat.yaml`, flat support
prior, original sensor rig/pattern and policy/controller for both human and box.
Only actual scene geometry changes. Native planning receives no obstacle class,
identity, location or dimensions. The static human uses its five visible USD
meshes. The box uses Newton's native box shape for both sensing and physics.

For each separately identified continuous episode require:

1. Original interface checks pass, including complete applied-state provenance,
   unfiltered sensor pairing, native build identity and measured stop.
2. Native backend records actual original-goal arrival after quiescence. The
   final XY distance is below 0.25 m. Cancellation or driver `FINISHED` alone
   does not qualify.
3. A read-only observer checks obstacle contacts before every 1 ms physics
   integration step. Its count equals the physical step count and it reports
   zero nonpositive surface separations using Newton's own contact helper.
   A separate frozen-overlap negative control must detect contact.
4. Body up-z stays above 0.9 and base height above 0.25 m, matching the prior
   stance/capacity qualification range. No reset or pose injection occurs in
   the navigation episode.
5. Sensor/command freshness watchdogs, collision occupancy rules, final curve
   PVA/dynamics/full collision checks and original arrival tolerances remain
   active. The total task wall budget is explicitly 240 s to allow slow CPU
   execution; observation ends at 27 physics seconds followed by measured stop.

Passing these two scenes validates only these local control cases. It does not
close original Isaac A4, stair navigation, obstacle-removal clearing, hardware
sensing equivalence or unrestricted real-world generalization.
