# Complete v251 physical recordings, execution v252

Each file is the entire recorded single attempt, including startup and closure.
Final display pass: render03, 1280 x 720, 30 fps, original causal timeline.
Video duration is distinct from the physical end timestamp.

| Video | Physical result | Physical end s |
|---|---|---:|
| [A02](v252_A02_full_attempt01.mp4) | FAILED: PCT no-route after PD; complete failed recording | 19.781 |
| [G07](v252_G07_full_attempt01.mp4) | PASS: new upstairs goal and terminal PD | 137.810 |
| [R11](v252_R11_full_attempt01.mp4) | PASS: reverse descent and terminal PD | 119.506 |

Native code is frozen v251; original RL, requested endpoints, 0.35 m hard
radius and 0.1 s scan period/deadline are unchanged. There is one formal
physical attempt per route. No baseline adoption or reliability claim.
See the [full report](../RESULTS.md) and per-video delivery verification under
`../physical/{CASE}/results/display/` for source/frame/video SHA binding.
