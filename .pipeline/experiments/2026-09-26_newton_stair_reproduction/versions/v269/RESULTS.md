# v269 retained independent comparison failure

Twelve standalone C++ physical counterexamples passed. The fixed 512-query
scene comparison reported three collision-sign and four margin differences;
this comparison did not qualify the component for native integration.

The four differences concern open vertical faces 1131, 2225 and 2204. Removing
all closed-volume IDs from the diagnostic leaves the C++ values unchanged.
Changing only the Python reference's projected-intersection prefilter to
bounding-box candidate recall makes all four queries match, with unchanged
finite 3-D clipping and original poses/radius. The original failure receipt and
both diagnostic receipts remain authoritative evidence; v270 owns the repair.

No PCT/SCAN planner integration, matrix run, physical attempt or baseline
promotion occurred in this version.
