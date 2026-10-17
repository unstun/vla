# v209: recorded v208 stop comparison

Display-only video of the four completed v208 physical probes, with v206 hold
on the left and the v208 candidate on the right. Two independent initialized
states are shown as separate chapters. Reuse original Building/robot geometry,
v51 authored appearance and streaming encoder. No physics, policy inference,
navigation changes, state interpolation, or full-route acceptance.

Execution: gpu5070ti only. Freeze source and dependency hashes before rendering;
verify and archive the closed physical captures before reading them for display.
Reconstruct body transforms using Newton forward kinematics from recorded joint
coordinates; compare the torso pose with the independently recorded sensor pose.
Sample recorded states causally on a 30 FPS simulation-time grid. The final
frame holds the last recorded state for at most one extra video frame.

Return a regular MP4, full-decode/frame-count proof, input hashes, frame mapping,
and three decoded review images. Keep raw captures and render intermediates on
gpu5070ti. Preserve v206/v208 source and all existing videos.
