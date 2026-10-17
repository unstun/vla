# NVIDIA Isaac Sim 5.1 official police character (local binary copy)

Purpose: prepare a source-verified official human visual for a bounded Lite3
Building-stair pedestrian experiment. These are NVIDIA assets, not Apache-2.0
source code. NVIDIA lists the police character in its
[Isaac Sim 5.1 asset documentation](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/assets/usd_assets_props.html)
and places 3D models and textures under its
[Additional Software and Materials License](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/common/licenses-isaac-sim.html).
The exact binary paths are ignored in this directory to avoid accidental
redistribution; the verified bytes remain local for the experiment.

Source root:
`https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/People/Characters/`

| Local file | Relative source URL | SHA-256 | Bytes |
| --- | --- | --- | ---: |
| `male_adult_police_04.usd` | `male_adult_police_04/male_adult_police_04.usd` | `3110909a21152d10bfcdf16d4e49653bae196d3093efe61a2099b4ee1761733b` | 857735 |
| `textures/male_adult_police_04_BaseColor.png` | `male_adult_police_04/textures/male_adult_police_04_BaseColor.png` | `7713714d56db66cec13e98cc5197d41bd5008ebe6f43c57bfc0ba0272b55ed88` | 7002261 |
| `textures/male_adult_police_04_Normal.png` | `male_adult_police_04/textures/male_adult_police_04_Normal.png` | `8e8cd9850a091e961c6f7ee8d462399c3122014461e218a47e014891e` | 16046671 |
| `textures/male_adult_police_04_ORM.png` | `male_adult_police_04/textures/male_adult_police_04_ORM.png` | `3251967eb0bf6046afc02da3256baae6349299a710a4c14a5a9a5fa540fef279` | 9888095 |
| `original_male_adult_police_04.usd` | `original_male_adult_police_04/male_adult_police_04.usd` | `f715f9dcce9f18132e7cc2ce213f440341ae836cffd458c8d3428080124953f7` | 851950 |
| `Biped_Setup.usd` | `Biped_Setup.usd` | `8b17e30a53ce21320bc41ae979e2208a648bae57ea77e3fb245ea325f5175185` | 20958 |

The existing official-human runtime contract pins the **non-original** USD
URL in the first row. Its only local binary asset dependencies are the three
listed textures; its `OmniPBR.mdl` reference is provided by Isaac Sim at
runtime. `usdcat` opened the local USD crate and confirmed those relative
texture references. A desktop `usdchecker` run could not resolve
`OmniPBR.mdl` outside Isaac Sim, so the full visual remains to be checked in
the pinned Isaac environment. The `original_` variant follows the public
asset-browser path and is retained for comparison, not selected for this
candidate. `Biped_Setup.usd` belongs to animation-retarget provenance; its
16 animation payloads and demo payload were not copied because the selected
run uses a separately pinned replay cache.

Regeneration: download each relative URL from the source root with
`curl --fail --location` into the exact local path above, then check every
SHA-256 before use. Do not silently replace bytes under a filename. The
retarget cache is stored as a generated experiment artifact at
`.pipeline/experiments/2026-09-23_scan_reactive_stair/official_human_cache/`.
