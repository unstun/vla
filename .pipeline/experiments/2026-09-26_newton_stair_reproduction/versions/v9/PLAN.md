# v9: restore the historical lower body collision envelope

Parent: frozen v8. Stage: experiment + analysis. Dr Sun authorized repair.

One configuration change in the Building profile:
`grid_map.obstacles_inflation_z_up: 0.55 -> 0.10` m. Positive obstacle inflation
is the downward extent of the queried robot body. The recorded 0.175 m stair
voxel was consequently blocking body references around 0.45 m in v7/v8.
The historical full Building success used 0.10 m. Original torso collision
boxes are 0.12 m high. Keep the 0.35 m horizontal radius, 0.35 m overhead
extent, terrain/support decisions, history, unknown-space and all speed gates.
The flat profile remains byte-identical to v8.

The native source/build is unchanged from v8. In the original 66-scan
continuation, an isolated upward-inflation change admits a native continuation
with boundary PVA and full-curve collision checks; downward-only and radius-only
changes do not. Evidence: `audits/2026-09-27_v8_geometry_ablation/`.

Validation: repeat against this frozen YAML, run all eight original measured
sensor obstacle cases (including low box, thin wall, static/occluded human and
blocked corridor), then a bounded physical stair trial. An isolated planner
pass is not route completion or physical collision validation. Robot feet and
terrain contacts are separate from the trunk planning envelope.

No obstacle class or coordinates are exempted. No historical label is cleared.
