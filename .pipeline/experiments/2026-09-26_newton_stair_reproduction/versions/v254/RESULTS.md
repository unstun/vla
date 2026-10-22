# v254 — Final continuous-endpoint native treatment (offline qualified)

Parent frozen v253, which implements continuous start/goal attachment on v251.
The only runtime change from v253 restores floating-point distance in the legacy
(non-physical) graph branch; its new behavioral regression observes accumulated
sqrt(2), not merely a path shape. Configured physical route bytes are unchanged.

- Complete unchanged 12 x 5 matrix: 55/60 first GPMP/static/cold SCAN passes.
  No graph fallback among admitted routes; B09 remains 0/5.
- All 55 admitted physical-mode `route.csv` files are byte-identical to v253.
- Exact saved A02 measured start `(-6.110767841339111, 6.878930568695068,
  0.3986549973487854)` and original goal pass first GPMP and complete static
  review. Returned start and goal XYZ error are both zero. This is global/static
  replay; nominal scan fixtures are not claimed as a live measured-body replay.
- H00 original-route first GPMP, static review and cold local publication pass;
  the requested goal error is zero.
- Seven PCT targets / 48 cases, 97 native regressions, and 10,855 support parity
  queries pass, with zero typed/export admission mismatches.

Source (321 composed files), installed artifacts (392 files), original runtime
fixtures, evaluator binaries and policy SHA are frozen in the manifest and
inventories. Requested endpoints, RL/PD, 0.35 m hard radius, 0.18 m offsets,
legal height transitions and 0.1 s period/deadline are unchanged. Both GPMP
orders preserve actual boundary positions before interpolation; native dense
height/full-reference checks retain admission authority.

The independent raw-solid margin for B08 remains a negative reference warning;
cold component admission is not full-route collision or foot-contact proof.
v255 binds one separately authorized A02 physical attempt. Its result/video
are recorded separately, without overwriting this offline qualification.
