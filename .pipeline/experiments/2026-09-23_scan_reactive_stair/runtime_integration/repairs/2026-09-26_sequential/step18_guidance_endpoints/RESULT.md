# Same-endpoint guidance diagnosis

scan30 reports complete-curve rejection but all168 bounded collision retries
retain zero paired finite unit-direction constraints. Original guidance AStar
fails during endpoint adjustment. This observer distinguishes that adjustment
failure from failure to find a checked same-endpoint repair path.

At the start of each planning attempt, diagnostic captures are cleared. The
first failing initial guidance search and first failing collision retry only
copy their exact endpoints, control indices, return and control matrix. No
extra occupancy query or search runs until the original optimizer returns false.
Then an independent native100³ AStar pool tries strict same-endpoint search,
starting with the retry snapshot. Original manager failure/publication behavior
is preserved. Actual control snapshot delta, full-curve collision, body/clock,
endpoint footprints and returned path checks are logged.

Independent review found no blocker and full Foxy build passed. Interpret a
repair path only with SUCCESS, at least two nodes, zero endpoint errors and all
edges passing the original complete segment predicate. The all_edges_clear
field alone is not sufficient for a one-node path. Strict success establishes
only a checked guidance route, not a valid constraint set or passing spline.
Pool allocation and extra query overhead are not production timing evidence.

Install identity and same-input replay result will be recorded after completion.


Completed replay: the collision-retry snapshot exactly matches the final
controls (maximum component delta 0). Default search returns INIT_ERR at CP
indices 250/252. Direct connection is blocked at its first sample, but strict
search returns SUCCESS with three nodes, both edges clear and exact endpoints.
All four footprint body/clock stamps are 5.56999988 s. This isolates a missed
checked guidance route under the old adjustment mode.

The initial proxy CP 131/133 case differs from final controls by 0.0026917 m;
strict search still fails with an empty path. This is not evidence to require
initial guidance before allowing a subsequently clear curve. The original
optimizer failure and zero moving publication are preserved in the observer.

Next isolated production candidate: preserve initial proxy behavior, while
actual collision-repair calls opt into exact endpoints. Retain existing
constraint assignment, objective, retry limits and complete curve acceptance.
Native caller-mode tests and paired replay must precede any claim of repair.
