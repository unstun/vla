# v22: denser static Building surface evidence

Stage: experiment + analysis. Parent: v21. One source-data change.

The v21 stop contains real sloped tread returns above an incorrectly low map
cell. Original PCT cell [23,127] has no sampled tread in its 2M point prior;
its retained .525343657 m sample is on a vertical face. Recorded true tread
returns at .575821224/.575373321 exceed the existing .05 m floor band.
The same static Building mesh, sampled by pinned Trimesh 5.1.0, supplies a
.571860731 m tread point. The unchanged PCT CPU generator then gives adequate
surface evidence without changing the band, navigation support or global map.

Retain all original 2M points and append the recorded 8M all-surface samples.
Use the generated uninflated-cost surface payload (126659 records). This is an
offline simulation-prior asset repair; no live actor geometry or object labels
enter SCAN. It is not a claim about the density of real-robot SLAM maps.

Publish the hash-pinned packed surface array through the v21 interface. Keep
legacy cost-based source support for replay. Require exactly one explicit
surface source, validate layout and reject mismatches. v21 native behavior is
unchanged. The recorded dense-surface-only test remains a failure; applying
riser inference more broadly belongs to a subsequent separate version.
