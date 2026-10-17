# Official-human animation replay cache

Local source of truth for a generated animation cache copied from the prior
`gpu5070ti` Office experiment archive:

`/home/sun/machine-dog-nav-runs/2026-08-17_office_l0_scan_crowd/results/office_crowd_dryrun22/`

| Local file | SHA-256 |
| --- | --- |
| `official_human_retarget_cache.npz` | `ac58a683fe9dd85ec3ad0266c7653b289dc1dd9b256d2abac0cc96ac7e45cfcb` |
| `official_human_retarget_cache.json` | `51e1b0a84cc489f38c69b79b17176a5d7fd2f119ee42cada66f56b272be412db` |
| `official_human_cache_sha256.txt` | `07973dab14d85c5e9fb95ca3165adfe4fb59e9890854d89648ff7b58da374a56` |

The manifest records schema 1, 30 fps, 101 joints, 60 idle frames, 90 walk
frames, the exact NVIDIA Isaac Sim 5.1 character/Biped URLs, and content hash
`76c19b57ebd03e01820e6b9db79bde8f2f3e436302744ef457278af8d17ef5b3`.
It describes ControlRig retargeted output, with `local_procedural_gait=false`.
The VLA task independently verified NPZ/manifest file hashes and recomputed
the content hash with the pinned `official_human_contract.py`. This is an
experiment artifact, not upstream source. The NPZ is ignored by exact path
to avoid accidental redistribution of generated NVIDIA animation content;
the manifest and provenance stay reviewable.

Regeneration requires the pinned NVIDIA character and Biped sources in the
Isaac Sim 5.1 environment, the original Office retarget procedure, and a
fresh content-hash comparison. Do not substitute a different animation cache
or treat this archive as a Building-stair runtime result.
