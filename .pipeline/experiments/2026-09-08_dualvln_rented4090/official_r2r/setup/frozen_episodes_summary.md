# Frozen R2R val_unseen subset (3 episodes)

Frozen **before** any model trial, by a rule that cannot depend on model outcomes.

- Selection rule: `group val_unseen by scene_id; keep scenes with >= 3 episodes; sort those scene_ids lexicographically and take the first; within it sort by int(episode_id) ascending and take the first 3`
- Source annotation SHA-256: `d173d8028537f30ab652dc5d24ead737e2b6010b6a4599f974351685710d18e8`
- Source contains 1839 episodes across 11 scenes; 11 scenes had >= 3 episodes.
- Selected scene: `mp3d/2azQ1b91cZZ/2azQ1b91cZZ.glb` (252 episodes in that scene)
- Derived subset SHA-256: `ea7ef5bc98904c5885d8a94abe83d6d932137a53a648ebdcbbbbe84e89e4735b` (47374 bytes), metadata keys preserved: ['instruction_vocab']

| episode_id | trajectory_id | geodesic (m) | instruction |
| --- | --- | --- | --- |
| 10 | 57 | 7.113 | Walk into the living room and keep walking straight past the living room. Then walk into the entrance under the balcony. Wait in the entrance to the other room. |
| 11 | 57 | 7.113 | Walk across the floor and wait the archway. |
| 12 | 57 | 7.113 | Move forward to the doorway on the opposite side of the hall.  Stop in the archway. |

All three share `trajectory_id` 57: R2R gives each trajectory three independent human
instructions, and the fixed rule (first three numeric episode IDs in the first eligible
scene) landed on one such group. The subset therefore tests **instruction variation over
one route**, not three distinct routes. The rule was fixed in advance and is left unchanged.

Shared start position `[16.4891, 0.1271, 8.9708]`, start rotation `[-0.0, 0.0, 0.0, 1.0]`, goal `[16.4652, 0.1271, 1.8579]` (radius 3.0).
