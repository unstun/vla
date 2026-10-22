# v269 — Correct native source-surface component

Unqualified C++ port of the repaired v268 geometry. v267 remains an immutable
rejected prototype: strict0.26m contact and open-surface containment failures
are retained. This component loads the orientation-only original geometry and
its Trimesh-certified closed-volume identities. Only closed objects receive an
interior; every actual face remains finite and two-sided for collision.

Boost R-trees bound source faces and closed objects. The strict floor-cap
height interval remains open at0.26m. Generic whole-object terrain exclusion is
allowed only for a certified closed positive volume whose maximum height is
strictly below ground+step and whose intersecting body bottom is above
ground-step: its material must then lie under an actual eligible finite top
cap. Whole eligible upward triangles likewise remove themselves. These are
geometry proofs, not navigation connectivity, hard inflation or endpoint rules.

Require strict-step/open-roof/inverted-volume controls, independent v268 source
queries and exact original poses. Do not modify a frozen planner installation
or claim full-matrix/physical acceptance from this standalone component.
