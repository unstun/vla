# v162 same-source Linux repeated full route

Stage: experiment and analysis. Exactly646native sourcefiles
as Macv160, rebuilt asv161on LinuxAMD64. v162only fixes Linux supervisor
root/RSS handling; source frozen3745pairs/618inputs. Physicalcohort: attempts
01,03,04,05,06. Slot02 failed port preflight beforephysics and is retained.

| Attempt | Accepted full route | Sensor path(m) | Replacement owners with proof | Fall |
|---|---|---:|---:|---|
|01|False|34.497|1|False|
|03|True|77.103|5|False|
|04|False|34.715|1|False|
|05|False|34.600|1|False|
|06|False|64.635|6|False|

Result1/5accepted,0falls: NOT reliability acceptance. All replacement owners
have recorded matching measured-stop proofs; proof does not imply eventual
arrival. Three failures end around34m with PCTno_route;06exhausts6retries
after seven native safety revocations near64.635m. Classify native negative
proof versus actual stale observation from full logs, not stale label alone.

Four recorded body samples from01replay in actual MacnativePCT with unchanged
map: startcell[160,159],layer4,cost50, threshold20; allfail. Diagnosticnearest
traversable start18cm away succeeds; that does not validate the omitted physical
connector. Exact historical RPC scheduling is not reconstructed.

All61returned analysis/log/provenance files match remoteSHA256manifest. All
292rawtrialfiles per physicalrun remain on5070ti, with per-run remote_artifacts
SHA256index. v163tests Nav2explicit reference reuse after no-route and causal
stop, with the same local safety checks; no new map or moved physical start.
