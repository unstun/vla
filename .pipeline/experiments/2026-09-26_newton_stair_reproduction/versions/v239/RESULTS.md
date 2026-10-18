# v239 — reject map-switch cancellation as continuity repair

Parent v238. The one-file A* change polls existing inputs every20ms and aborts
when an adopted map changes. Static A*/B-spline consumers were all rebuilt;
97 native cases pass. Real-clock109–114.5s replay has126 rounds,103 successes
and0 emergency messages with the same979-scan prefix/486 body/56 scan messages.

However, active replacement ownership reveals an expired-curve gap from
111.084140672 to111.268702043s (0.184561371s). Unioning all historical curves
would incorrectly hide it. This candidate fails continuity acceptance despite
zero explicit emergency messages. Source/results are retained; do not adopt.

v240 keeps input delivery while holding the search read snapshot, then uses
the original caller refresh/final-map gates. No physics was run; v232/v233
remains the selected physical baseline.
