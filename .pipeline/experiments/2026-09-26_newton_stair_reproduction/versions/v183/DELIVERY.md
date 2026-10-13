# v183 stopping videos

Display-only replay of v182's twelve closed Mac Newton episodes. All per-frame
hashes, causal source indices, actual time-zero starts and full video decoding
passed. Both combined files include all six trials in order and are 221.5 s,
6645 frames, 1280 by 720, 30 fps. No physics was advanced for rendering.

- `delivered/flat_example_02.mp4`: the 0.6 m/s command condition paired with the
  worst low-speed flat condition; both walk/stop cycles, including initialization.
- `delivered/stairs_example_06.mp4`: the 1.0 m/s stair-scene command condition;
  retains residual motion at the second stop, not a selected perfect stop.
- `delivered/flat_all6.mp4` and `delivered/stairs_all6.mp4`: complete cohorts.
- Low-speed counterparts remain in v181. They are controls below the project
  planned-cruise floor and must not be presented as nominal-range qualification.

`DELIVERY.json` binds all original clips and combined hashes; `examples.json`
binds the two regular-file examples. `quality.json` records visual review.
On-screen displacement includes braking; the report's late excursion excludes
the first two seconds. Neither is a world-position holding guarantee.

Durable raw: `gpu5070ti:/data/sun/vla_mppi_20261009/policy_stop_v182_mac/archives/`.
Returned raw receipts are in `v182/results/raw_receipts/`. Review videos and
source/configuration copies are archived under the same storage root's
`source_versions/v183/` (and v179–v182 for their respective versions); the local
repository remains the source of truth. See `delivery_inventory.json` and
`remote_storage_verified.json` for exact storage byte verification.

To regenerate, restore each verified raw archive into the owned temporary run
root recorded by `results/render_cohort.py`, restore its matching receipt, and
run frozen `render.py --run RUN --output FRESH_OUTPUT --archive-receipt RECEIPT`
with the pinned local Newton environment and inherited assets. Use a fresh
supervised output per clip. The renderer verifies the v182/v183 manifests and
every raw member before consuming recorded poses. `results/build_delivery.py`
checks source-frame identity and concatenates complete clips without resimulation.
Retain source records and failures; do not silently overwrite delivered videos.
