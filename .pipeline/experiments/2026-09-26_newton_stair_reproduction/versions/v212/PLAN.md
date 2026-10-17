# v212: event-triggered global planning

Parent: accepted v210 (v206 navigation and v208 locomotion). Replace only the
periodic PCT invocation with planning at first goal, semantic goal change, or
entry into an ordinary recovery retry. A goal's frame and full pose define a
change; a timestamp refresh alone does not. Cancel/completion resets the gate,
so a new mission with the same coordinates still plans once. In-flight goals
are canceled before planning their replacements. Retain PipelineSequence so
local tracking continues with its original semantics while a replacement plans.

Keep six ordinary retries and Wait 1 s; keep zero retries after stand timeout.
No deviation threshold, dynamic blockage mask, PCT/SCAN algorithm change,
Tracker change, tolerance change or locomotion change. The unrelated 1 Hz
costmap lifecycle update and planner timing diagnostic remain unchanged.

Owned runtime changes: one small BT decorator, its existing library registration,
and navigate.xml. Tests cover the installed plugin's async/goal/cancel behavior,
unchanged recovery semantics and generated profiles. Build only the two affected
packages on gpu5070ti, using the unchanged v206 install as underlay. Preserve all
previous source/install/output versions; final local source is authoritative.

Freeze after component checks. Then run exactly one original historical_full
physical route on gpu5070ti using the same v210 launch conditions and unchanged
v208 adapter. Compare actual global calls, native path messages, completion,
final fixed PD, timing and pauses with recorded v210; do not tune or retry a
moving failure. Return compact provenance and a full recorded-state MP4. Raw
recordings and builds stay remote. Update HTML with the actual result.
