# v250 — continuous support-gap distance

Parent: v249. Negative-only mask keeps the exact original uncertain source
squares, levels, .26 m height matching and .35 m cylinder radius. Existing
raster bins become a broad-phase index; the actual continuous centre must be
within .35 m of an original source square before refusal. No new map, snap,
endpoint offset, clearance tuning, selectedSurface waiver or freshness change.

Evidence: A02 original-mesh continuous disc clearance is .3783769186 m at the
rear and .6357481170 m at the front. Six source squares reject the rear target
bin, yet none intersect the actual disc. Runtime/static consumers must all be
rebuilt, with native parity, original-gap negatives and saved G07 replay.
