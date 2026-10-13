# v178: review video of the first v177 full-route repetition

Display only; parent displayv148, physical sourcev177 attempt01. The source was
selected as the first completed repetition, not the fastest or smoothest.
Preserve original physicalframe0, factoryPDstartup, complete route, every pause
and recovery, and terminal measured hold. No interpolation, stitching, resetting,
prefix removal or acceleration. Startup uses recorded simulation timestamps;
navigation uses original walltimestamps at1:1. Cyan is the controller-admitted
local curve; orange is the global reference. Solve timing shows only the latest
completed solve available at that frame, including failures.

Render only after the complete five-trial physical cohort closes, to avoid GPU
or CPU contention with the physical tests. Construct the pinned CPU model but
execute no physics steps; EGL is used for graphics. Verify source hashes before
and after rendering, all frame indices and causality, full MP4 decoding, actual
arrival/hold, and inspect beginning/middle/end images. Return a regular MP4 plus
compact checks; keep raw/master data on gpu5070ti. The video is one recorded run
and does not by itself establish repeated navigation success or30Hz planning.
