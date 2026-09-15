# Goal visibility audit

Question: could the failed Chinese run be caused by the vending machine being
too distant or visually occluded?

This is a read-only audit of existing runs; no new simulator run was launched.
Eight retained model-facing front images were copied locally for frames
120/180/240/300 of Chinese run `20260908T151850Z_e8fd96` and English run
`20260908T150231Z_f402d9`. All eight files match the remote SHA-256 and byte counts
in `remote_hashes.json`. These are original front-camera JPEGs, not overhead
images, output overlays or reconstructed views.

## Observations

- The configured start-to-goal planar distance is 13.2007 m. This measures the
  goal point, not the physical center of the vending-machine mesh.
- At frame 120, the vending machine is visible near the back wall, just to the
  right of the foreground person in the image. It is relatively small but not
  fully occluded. The two runs' initial images are visually very similar; their
  byte hashes are different, so they are not identical input fixtures.
- In the Chinese run, the commanded yaw rate reaches approximately -1.2 rad/s
  by frame 150. By frame 180 the front camera primarily sees the glass wall and
  outdoors; the vending machine has left the image. Frame 240 shows a nearby
  person and water dispenser. Thus later loss of target visibility follows the
  early turn; it does not establish that initial total occlusion caused the turn.
- The English run proceeds forward. By frame 300 its distance to the goal is
  about 9.709 m; the Chinese run's is about 13.550 m. The English front frames
  continue to show the target while approaching it.
- The model loader requests `input_size=448, max_num=1` in the pinned runtime.
  Small image scale could therefore contribute to recognition difficulty, but
  this audit does not measure recognition reliability or establish a cause.

The model-generated descriptions provide a secondary clue: the first English
response names a vending machine, while the first Chinese response refers to an
exhibit/wall and later responses mention other objects. Generated descriptions
are not independent ground truth for what the model recognized.

## Claim boundary and useful next test

Distance and occlusion remain plausible contributors, but initial complete
occlusion is not supported by these frames. A single English success and Chinese
failure do not isolate language, visibility or stochastic variability. In
particular, the English instruction included go-straight and stop directions
that the shorter Chinese instruction omitted.

Use semantically matched Chinese/English commands under the same scene and
starting conditions first. Then change distance or pedestrian occlusion one at
a time. A closer, unobstructed target provides a useful visibility control.
