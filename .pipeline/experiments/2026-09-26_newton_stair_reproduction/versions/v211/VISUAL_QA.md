# v211 full-route video review

Passed: 4,104 decoded frames, 136.8 seconds, 1280x720, 30 FPS.
The regular local MP4 matches the remote master SHA-256. Every output frame
maps causally to the captured state, including the first crouch and last PD hold.
All recorded navigation pauses are retained; no new physics or interpolation.

Seven decoded samples were reviewed: initial crouch, factory movement, measured
standing, navigation at approximately 30/60/80 seconds, and the terminal frame.
Robot geometry, authored appearance, orange PCT route and cyan local SCAN curve
are visible. The final caption reads arrived (nav2_arrived). Recorded terminal
state is FIXED_STAND with zero command; continuous final hold is 4.351 seconds.

[Full MP4](delivered/v210_linux_full_attempt01.mp4) ·
[Delivery verification](returned/delivery_verification.json) ·
[Decoded contact sheet](returned/visual_qa/contact_sheet.jpg).

This video displays the single passing v210 physical trial. Its renderer adds
no physics evidence or repeatability claim.
