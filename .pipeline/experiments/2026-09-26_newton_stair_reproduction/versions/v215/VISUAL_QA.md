# v215 actual failed-route video

Passed display checks: 1,618 frames, 53.9333 seconds, 1280x720, 30 FPS, complete
decode and causal source/curve mapping. Local regular MP4 matches the remote
master SHA-256. The first crouch and final physical fall states are included.
No additional physics or state interpolation occurred.

Seven decoded samples were inspected: initial crouch, factory stand, navigation
at about 30 s, then 48/52/53.8 s and the final 54.142 s physical state. The robot
is visible at the stair entrance before tipping; the final caption is explicitly
physical fall (simulation stopped). No arrival or PD success is displayed.

[Full video](delivered/v212_linux_full_attempt01.mp4) ·
[Verification](returned/delivery_verification.json) ·
[Decoded samples](returned/visual_qa/contact_sheet.jpg).

The video is display-validated; its physical source failed. v210 remains the
accepted original-route baseline.
