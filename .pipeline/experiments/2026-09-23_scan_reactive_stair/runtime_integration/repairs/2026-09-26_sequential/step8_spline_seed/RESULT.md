# Spline-seed failure diagnosis

The first invalid representation is already the re-sampled point chain, before
spline fitting. The original 76-point seed passes every shared segment check.
The manager keeps 24 samples of a quintic arc-length progression; its straight
connections can cross original turns. Actual sampled edge 10 rejects at sample
2. Maximum source edge length is 0.086603 m versus 0.324706 m after sampling;
101-point-per-chord comparison estimates up to 0.052713 m deviation from the
original polyline. This distance estimate is not a continuous bound or a
collision result; the rejection itself is an actual native map query.

The initially fitted cubic also fails the complete sampled curve gate at
1.686944 s: its rear footprint exceeds the terrain height band. The optimized
curve first fails at 0.668788 s with rear UnknownObstacle. Thus optimization
worsens this observed curve; it is not the first stage that loses safety.
The first fitted position residual is 0.329847 mm at the start and 1.047600 mm
at the goal. Initial p/v/a remain identical after optimization because the
first/last three controls are fixed. These are soft-fit residuals, not exact
boundary preservation. The first fitted curve does not fail at t=0.

The internal optimizer search failure is also localized: search 6 starts from
a free initial start but an occupied adjusted end. It advances that end 51
times before its Y index leaves the pool. The original occupancy wrapper only
returns 0/1, so the legacy -1 early exit does not occur. Its boolean logs do
not by themselves distinguish Unknown from occupied, or prove which endpoint
coordinate/heading change first caused the blocked verdict.

`scan25_optimizer_trace_v2` builds in the pinned Foxy image and has a matching
460-file install identity. The first trace includes all three modules, 1,131
buffered records, 31 search calls and zero dropped records. Additional point
chain/curve queries execute only after the original optimizer has returned
failure. The observer changes no acceptance, objective or collision threshold;
its overhead and subsequent callback counts are not performance evidence.
The v1 local preparation failed on an ambiguous source anchor before execution
and remains preserved. `GEOMETRY_TRACE.json` links the raw log and geometry.

Next: preserve every original nonzero edge/corner in the sample chain, bound
spacing, keep total initial duration and report quintic timing approximation.
All new subedges must be checked under the unchanged actual heading predicate:
subdivision can trigger its under-1-cm XY body-yaw fallback. Fitting residuals,
optimizer behavior, complete final gate and actual dynamics remain separate
acceptance stages. No navigation-success claim is made.
